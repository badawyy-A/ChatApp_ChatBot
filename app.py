from flask import Flask, request, jsonify, send_file, Response
from flask_cors import CORS
import speech_recognition as sr
from gtts import gTTS
import io
import os
import uuid
import json
import logging
from pydub import AudioSegment

# Imports based on project structure
from model import GeminiAPI
from utils.session_manager import SessionManager
from deep_translator import GoogleTranslator

import joblib

from helpers import extract_features

import numpy as np

from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs

load_dotenv()
tts_api_key = os.getenv("ELEVENLABS_API_KEY2")
client = ElevenLabs(api_key=tts_api_key)


app = Flask(__name__)
CORS(app)

# --- Global Objects ---
try:
    gemini = GeminiAPI()
except EnvironmentError as e:
    logging.critical(f"Failed to initialize GeminiAPI: {e}")
    gemini = None
except Exception as e:
    logging.critical(f"An unexpected error occurred initializing GeminiAPI: {e}", exc_info=True)
    gemini = None

session_manager = SessionManager()
recognizer = sr.Recognizer()

# --- Helper Functions ---

def speech_to_text(audio_file, language="en-US"):
    """Converts audio file to text using SpeechRecognition."""
    if not audio_file or not audio_file.filename:
        return None, "No audio file provided or filename missing."

    filename = audio_file.filename
    _, ext = os.path.splitext(filename)
    ext = ext.lower()
    temp_wav_path = f"temp_{uuid.uuid4()}.wav"
    temp_orig_path = temp_wav_path.replace(".wav", ext)

    try:
        audio_file.save(temp_orig_path)
        try:
            audio_segment = AudioSegment.from_file(temp_orig_path)
            audio_segment = audio_segment.set_channels(1).set_frame_rate(16000)
            audio_segment.export(temp_wav_path, format="wav")
            logging.info(f"Successfully converted {temp_orig_path} to {temp_wav_path}")
        except Exception as e:
            logging.error(f"Error converting audio format {ext} using pydub: {e}", exc_info=True)
            if ext == ".wav":
                 logging.warning("Conversion failed, trying original WAV file.")
                 temp_wav_path = temp_orig_path
            else:
                 raise Exception(f"Audio conversion failed: {e}")

        with sr.AudioFile(temp_wav_path) as source:
            logging.info(f"Recording audio from {temp_wav_path}")
            audio_data = recognizer.record(source)
            logging.info("Audio recorded, attempting recognition...")
            try:
                text = recognizer.recognize_google(audio_data, language=language)
                logging.info(f"Speech recognized (lang: {language}): {text}")
                return text, None
            except sr.UnknownValueError:
                logging.warning(f"Speech Recognition could not understand audio (lang: {language})")
                return None, "Speech Recognition could not understand audio"
            except sr.RequestError as e:
                logging.error(f"Could not request results from Google Speech Recognition service (lang: {language}); {e}")
                return None, f"Could not request results from Google Speech Recognition service; {e}"

    except Exception as e:
        logging.error(f"Error processing audio file {filename}: {e}", exc_info=True)
        return None, f"Error processing audio file: {e}"
    finally:
        # Cleanup temporary files
        if os.path.exists(temp_wav_path):
            try: os.remove(temp_wav_path)
            except OSError as e: logging.error(f"Error removing temp file {temp_wav_path}: {e}")
        if temp_orig_path != temp_wav_path and os.path.exists(temp_orig_path):
             try: os.remove(temp_orig_path)
             except OSError as e: logging.error(f"Error removing temp file {temp_orig_path}: {e}")


def text_to_speech(text, lang="ar"): # Removed output_file parameter
    """Converts text to speech using ElevenLabs and returns an in-memory audio file object."""
    voice_settings = {
        "ar": "a1KZUXKFVFDOb33I1uqr", # Replace with your actual Arabic voice ID
        "en": "tQ4MEZFJOzsahSEEZtHK"  # Replace with your actual English voice ID
        # Add other languages/voices as needed
    }

    voice_id = voice_settings.get(lang)
    if not voice_id:
        error_msg = f"Unsupported language/voice selected for TTS: {lang}"
        logging.error(error_msg)
        return None, error_msg # Return None for audio, error message

    try:
        logging.info(f"Requesting TTS from ElevenLabs for lang '{lang}' with voice ID '{voice_id}'")
        # The client.text_to_speech.convert returns a generator yielding bytes chunks
        audio_stream = client.text_to_speech.convert(
            text=text,
            voice_id=voice_id,
            model_id="eleven_multilingual_v2", # Or your preferred model
            output_format="mp3_44100_128" # Choose desired format
        )

        # Consume the generator and store bytes in memory
        audio_bytes = b"".join(audio_stream)

        if not audio_bytes:
             logging.error("ElevenLabs returned empty audio stream.")
             return None, "TTS service returned empty audio."

        # Wrap the bytes in a BytesIO object to make it file-like for send_file
        audio_fp = io.BytesIO(audio_bytes)
        audio_fp.seek(0) # Reset stream position to the beginning

        logging.info(f"TTS generation successful for lang '{lang}'. Size: {len(audio_bytes)} bytes.")
        return audio_fp, None # Return file-like object and None for error

    except Exception as e:
        logging.error(f"ElevenLabs TTS API error for lang '{lang}': {e}", exc_info=True)
        # You might want to check for specific API error types from the elevenlabs library
        return None, f"TTS API error: {e}" # Return None for audio, error object/message
# --- API Routes ---

@app.route('/api/start_chat', methods=['POST'])
def start_chat():
    """Starts a new chat session."""
    try:
        user_data = request.get_json()
        if not user_data:
            return jsonify({"error": "Request body must be JSON."}), 400
        if not user_data.get('language'):
            return jsonify({"error": "User data must include 'language' (e.g., 'en-US', 'ar-SA')."}), 400

        logging.info(f"Starting new chat session for language: {user_data.get('language')}")
        session_id = session_manager.create_session(user_data)
        return jsonify({
            "session_id": session_id,
            "message": "Chat session started."
        }), 201
    except Exception as e:
        logging.error(f"Error in /api/start_chat: {e}", exc_info=True)
        return jsonify({"error": "An internal server error occurred initiating chat."}), 500


@app.route('/api/chat/<session_id>', methods=['POST'])
def chat(session_id):
    """Handles chat interaction (text/audio in, text/audio out)."""
    if not gemini:
         logging.error(f"Gemini API not initialized. Cannot process chat for session {session_id}.")
         return jsonify({"error": "Chat service is unavailable due to configuration error."}), 503

    try:
        session = session_manager.get_session(session_id)
        if not session:
            logging.warning(f"Invalid session ID requested: {session_id}")
            return jsonify({"error": "Invalid session ID"}), 404

        user_data = session.get("user_data", {})
        user_language = user_data.get('language', 'en-US')
        base_user_language = user_language.split('-')[0]
        logging.info(f"Chat request for session {session_id}, lang: {user_language}")

        user_input_text = None
        input_error = None
        input_type = "unknown"

        # Check for audio input (form-data)
        if 'audio' in request.files:
            audio_file = request.files['audio']
            if audio_file and audio_file.filename:
                input_type = "audio"
                logging.info(f"Processing audio input for session {session_id}")
                user_input_text, input_error = speech_to_text(audio_file, language=user_language)
                if input_error:
                    logging.warning(f"STT Error for session {session_id} (lang: {user_language}): {input_error}")
            else:
                 if not request.is_json and not request.form.get('message'):
                     input_error = "Audio file part found but no file uploaded or filename missing."
                 logging.warning(f"Audio key present, but no valid file for session {session_id}")

        # Check for text input (JSON or form) if audio not processed or STT failed
        if user_input_text is None and not input_error:
            if request.is_json:
                try:
                    data = request.get_json()
                    if data and "message" in data:
                        user_input_text = data.get("message")
                        if user_input_text: input_type = "text"
                        else: input_error = "JSON received but 'message' field is empty."
                    elif input_type != "audio":
                         input_error = "Request is JSON but missing 'message' field."
                except json.JSONDecodeError:
                     input_error = "Invalid JSON format in request body."
            elif 'message' in request.form:
                 user_input_text = request.form.get('message')
                 if user_input_text: input_type = "text"
                 else: input_error = "Form data received but 'message' field is empty."

        # Final Input Validation
        if user_input_text is None:
             error_message = input_error if input_error else "Input required: Send JSON with 'message' or form-data with 'audio' file."
             logging.warning(f"No valid input found for session {session_id}: {error_message}")
             return jsonify({"error": error_message}), 400
        elif input_error and input_type == "audio":
             logging.warning(f"Proceeding for session {session_id} despite STT error: {input_error}")

        # --- Process with Gemini ---
        chat_history = session.get("chat_history", [])

        prompt = f"""
        **Instructions for the Language Model:**
        You are a real human friend to {user_data.get("name", "the user")}. Your goal is to provide natural, enjoyable conversations tailored to the user's personality, interests, and communication style. You are the same age as the user ({user_data.get("age_range", "unknown")} years old) and share similar interests. You also speak the same language as the user and use the same accent from their country.

        * **Speak ONLY in the user's specific language ({user_language}). Use phrasing and tone appropriate for that language and region.**
        * **Keep your responses casual, friendly, and natural—just like a real person talking.**
        * **Incorporate the user's interests smoothly into conversations.**
        * **Acknowledge their goals and support them in a realistic way.**
        * **Adapt to their personality, humor, and way of speaking.**
        * **Avoid sensitive or unethical topics.**
        * **Remember you are a true human.**

        **Important:** Ensure your speech feels natural and authentic, matching the user's cultural and linguistic background ({user_language}). Use chat history to maintain consistency. Avoid mentioning you are an AI or language model.

        **User Profile:**
        {json.dumps(user_data, indent=2)}

        **Chat History (Last ~10 exchanges):**
        {json.dumps(chat_history[-10:], indent=2)}

        **User Input (Type: {input_type}, Language: {user_language}):**
        {user_input_text}

        **Your Response (in {user_language}):**
        """

        logging.info(f"Generating Gemini report for session {session_id}")
        response_text = gemini.get_report(prompt)

        if not response_text or response_text.startswith("Error:"):
             logging.error(f"Gemini Error for session {session_id}: {response_text}")
             return jsonify({"error": "Failed to get response from language model."}), 500

        logging.info(f"Gemini response received for session {session_id}")
        session_manager.update_session_chat_history(session_id, user_input_text, response_text)

        # --- Determine Response Format ---
        response_format = request.args.get('format', 'text').lower()

        if response_format == 'audio':
            logging.info(f"Generating audio response (TTS) for session {session_id}, lang: {base_user_language}")
            audio_fp, tts_error = text_to_speech(response_text, lang=base_user_language)
            if tts_error:
                logging.error(f"TTS Error for session {session_id} (lang: {base_user_language}): {tts_error}")
                return jsonify({
                    "warning": f"Could not generate audio response: {tts_error}. Returning text instead.",
                    "response": response_text
                    }), 200
            else:
                logging.info(f"Sending audio response for session {session_id}")
                return send_file(audio_fp, mimetype='audio/mpeg', as_attachment=False)
        else:
            logging.info(f"Sending text response for session {session_id}")
            return jsonify({"response": response_text}), 200

    except Exception as e:
        logging.error(f"Unexpected error in /api/chat/{session_id}: {e}", exc_info=True)
        return jsonify({"error": "An internal server error occurred during chat processing."}), 500

@app.route('/api/translator/', methods=['POST'])
def do_translation():
    """Translates text or speech."""
    app.logger.info("--- Translator Endpoint Hit ---")

    try:
        input_text = None
        input_error = None
        target_lang = None
        source_lang = None
        input_type = "unknown"

        # --- Extract input data ---
        if request.is_json:
            try:
                data = request.get_json()
                app.logger.info(f"Translator | JSON Data: {data}")
                input_text = data.get('text')
                target_lang = data.get('target_lang')
                source_lang = data.get('source_lang')
                if input_text:
                    input_type = "text"
            except json.JSONDecodeError as e:
                app.logger.error(f"Translator | Invalid JSON: {e}")
                return jsonify({"error": "Invalid JSON format in request body."}), 400
        else:
            # Handle form-data
            app.logger.info(f"Translator | Form Data: {request.form}")
            app.logger.info(f"Translator | Files: {request.files}")

            target_lang = request.form.get('target_lang')
            source_lang = request.form.get('source_lang')

            if 'audio' in request.files:
                audio_file = request.files.get('audio')
                if audio_file and audio_file.filename:
                    input_type = "audio"
                    stt_lang_hint = source_lang or 'en-US'
                    app.logger.info(f"STT | Processing audio (lang hint: {stt_lang_hint})")
                    input_text, input_error = speech_to_text(audio_file, language=stt_lang_hint)
                    if input_error:
                        app.logger.warning(f"STT | Error: {input_error}")
                        return jsonify({"error": f"Audio processing failed: {input_error}"}), 400
                    app.logger.info(f"STT | Extracted Text: {input_text}")
                else:
                    input_error = "Audio file provided but no file uploaded or filename missing."
                    app.logger.warning(f"STT | {input_error}")

            if input_text is None and not input_error:
                form_text = request.form.get('text')
                if form_text:
                    input_text = form_text
                    input_type = "text"
                    app.logger.info(f"Translator | Using text from form: {input_text}")
                elif input_type != "audio":
                    input_error = "No text or audio provided in form-data."

        # --- Validate inputs ---
        app.logger.info(f"Translator | Inputs - Text: '{input_text}', Target: '{target_lang}', Source: '{source_lang}'")

        if not target_lang:
            return jsonify({"error": "'target_lang' is required in JSON or form data."}), 400

        if input_text is None:
            error_message = input_error or "Input required: JSON with 'text', or form-data with 'text' or 'audio'."
            return jsonify({"error": error_message}), 400

        # --- Perform translation ---
        try:
            base_source = source_lang.split('-')[0] if source_lang else None
            app.logger.info(f"Translate | Using source='{base_source}' and target='{target_lang}'")
            translator = GoogleTranslator(source=source_lang or 'auto', target=target_lang)
            translated_text = translator.translate(input_text)
            actual_src_lang = source_lang or "auto-detect"
            app.logger.info(f"Translate | Success | Output: '{translated_text[:100]}...'")
        except Exception as e:
            app.logger.error(f"Translate | Error: {e}", exc_info=True)
            return jsonify({"error": f"Translation failed: {e}"}), 500

        # --- Output format ---
        output_format = request.args.get('format', 'text').lower()

        if not isinstance(target_lang, str):
            app.logger.error(f"Internal Error: Invalid target_lang: {target_lang}")
            return jsonify({"error": "Internal error: Target language missing or invalid."}), 500

        base_target_lang = target_lang.split('-')[0].lower()

        if output_format == 'audio':
            app.logger.info(f"TTS | Generating audio for language: {base_target_lang}")
            if translated_text is None:
                return jsonify({"error": "Internal error: Translation result is missing."}), 500

            audio_fp, tts_error = text_to_speech(translated_text, lang=base_target_lang)
            if tts_error:
                app.logger.warning(f"TTS | Error: {tts_error}")
                return jsonify({
                    "warning": f"Audio generation failed: {tts_error}. Returning text instead.",
                    "translated_text": translated_text,
                    "source_language_detected": actual_src_lang
                }), 200
            else:
                app.logger.info("TTS | Sending audio file.")
                return send_file(audio_fp, mimetype='audio/mpeg', as_attachment=False)

        # --- Return JSON response ---
        return jsonify({
            "translated_text": translated_text,
            "source_language_detected": actual_src_lang
        }), 200

    except Exception as e:
        app.logger.error(f"Translator | Unexpected Error: {e}", exc_info=True)
        return jsonify({"error": "Internal server error occurred."}), 500

@app.route('/api/link_classifier/', methods=['POST'])
def predict_url_safety():
    data = request.get_json()
    url = data.get('url')
    
    if not url:
        return jsonify({'error': 'URL is missing'}), 400

    model = joblib.load('./weights/rf_model.pkl')
    features = extract_features(url)
    features = np.array(features).reshape(1, -1)  # ensure it's 2D
    pred = model.predict(features)[0]  # Make sure this returns a 2D array
    label = 'Safe' if pred == 1 else 'Unsafe'

    m2_label = gemini.get_report(f"I will send you a link. Respond with only one word: safe or unsafe. No explanation, no punctuation, no newline—just the word,  link : {url} ")

    if label == m2_label:
        return jsonify({'label': label})
    else:
        return jsonify({'label': m2_label.strip()})



if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s %(threadName)s : %(message)s')
    # Ensure Flask's logger uses the configured settings
    # app.logger is already configured by Flask to use logging if basicConfig is called before app is run.
    # To be explicit, you could do: app.logger.handlers = logging.getLogger().handlers; app.logger.setLevel(logging.INFO)

    host = os.environ.get('FLASK_RUN_HOST', '127.0.0.1')
    port = int(os.environ.get('FLASK_RUN_PORT', 5000))
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() in ['true', '1', 't']

    logging.info(f"Starting Flask server on {host}:{port} (Debug: {debug_mode})")
    app.run(host=host, port=port, debug=debug_mode)

