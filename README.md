# API Documentation:
# Imortant Note : only sported langs are "ar" and "en"
### Start New Chat Session

## Endpoint: `/api/start_chat`

**Method:** `POST`

**Description:**
Initiates a new chat session. This endpoint requires the client to specify the desired language for the session via the request body. Upon successful creation, it returns a unique session ID that should be used for subsequent interactions within that chat session.

---

**Request:**

*   **Headers:**
    *   `Content-Type: application/json` (Required)

*   **Body (JSON):**
    *   Requires a JSON object containing user data, primarily the language.
    *   `language` (string, **required**): The BCP-47 language code for the desired chat language (e.g., `en-US`, `es-ES`, `ar-SA`, `fr-FR`).
    *   Other optional key-value pairs can be included in the JSON object. These will be captured as `user_data` and potentially used by the session manager during creation.

*   **Example Request Body:**
    ```json
        {
            "name": "Mohamed Ahmed",
            "age_range": "22-25",
            "gender": "Male",
            "location": "Cairo, Egypt",
            "language": "ar",
            "interests": [
                "football",
                "watching movies",
                "hanging out with friends",
                "listening to music"
            ],
            "favorites": [
                "koshari",
                "Umm Kulthum music",
                "Al Ahly football club"
            ],
            "goals": "Start my own business",
            "communication_style": "casual",
            "personality": "extroverted",
            "values": "Family, friendship, hard work",
            "life_situation": "University student",
            "relationship_status": "In a relationship",
            "challenges": "Finding a good job after graduation"
        }
    ```

---

**Responses:**

*   **Success Response (Code `201 Created`):**
    *   Indicates the chat session was successfully created.
    *   **Body (JSON):**
        *   `session_id` (string): A unique identifier for the newly created session.
        *   `message` (string): A confirmation message, typically "Chat session started.".

    *   **Example Success Response Body:**
        ```json
        {
          "session_id": "a1b2c3d4-e5f6-7890-g1h2-i3j4k5l6m7n8",
          "message": "Chat session started."
        }
        ```

*   **Error Response (Code `400 Bad Request`):**
    *   Indicates invalid input from the client.
    *   **Scenario 1:** Request body is not valid JSON or is missing.
        *   **Body (JSON):**
            ```json
            {
              "error": "Request body must be JSON."
            }
            ```
    *   **Scenario 2:** The required `language` field is missing in the JSON payload.
        *   **Body (JSON):**
            ```json
            {
              "error": "User data must include 'language' (e.g., 'en-US', 'ar-SA')."
            }
            ```

*   **Error Response (Code `500 Internal Server Error`):**
    *   Indicates an unexpected error occurred on the server while trying to create the session.
    *   **Body (JSON):**
        ```json
        {
          "error": "An internal server error occurred initiating chat."
        }
        ```

---

**Example Usage (curl):**

```bash
curl -X POST \
  http://<your_api_domain>/api/start_chat \
  -H 'Content-Type: application/json' \
  -d '{
    "language": "es-ES"
  }
  ```


## Chat Interaction

## Endpoint: `/api/chat/<session_id>`

**Method:** `POST`

**Description:**
Handles a single turn in an ongoing chat conversation identified by `session_id`. Accepts user input as either text (JSON or form data) or an audio file (multipart/form-data). Processes the input using the configured language model (Gemini), considering chat history and user profile data stored in the session. Returns the model's response as either text (JSON) or synthesized audio, based on the `format` query parameter.

---

**Path Parameters:**

*   `session_id` (string, **required**): The unique identifier for the chat session, obtained from the `/api/start_chat` endpoint. Included directly in the URL path.

---

**Query Parameters:**

*   `format` (string, *optional*): Specifies the desired format for the response.
    *   `text` (default): Returns the response as a JSON object containing the text.
    *   `audio`: Attempts to synthesize the response text into speech using Text-to-Speech (TTS) for the session's language and returns the audio file directly (e.g., `audio/mpeg`). If TTS fails, it may fall back to returning a text response with a warning.

---

**Request:**

*   **Headers:**
    *   `Content-Type`: Must match the body format.
        *   `application/json` (for text input via JSON)
        *   `application/x-www-form-urlencoded` (for text input via form data)
        *   `multipart/form-data` (required for audio file input)
*   **Body:** Contains the user's input for this turn. The endpoint prioritizes audio input if present.
    *   **Option 1: Audio Input (using `multipart/form-data`)**
        *   Include a file part named `audio`. The value should be the user's audio recording file.
        *   The server will attempt Speech-to-Text (STT) using the language specified when the session was created.
        *   *Example (conceptual form structure):*
            ```
            ------BoundaryString
            Content-Disposition: form-data; name="audio"; filename="user_speech.wav"
            Content-Type: audio/wav

            <binary audio data>
            ------BoundaryString--
            ```
    *   **Option 2: Text Input (using `application/json`)**
        *   Requires a JSON object with a `message` key containing the user's text input.
        *   *Example Request Body:*
            ```json
            {
              "message": "Hello, how are you doing today?"
            }
            ```
    *   **Option 3: Text Input (using `application/x-www-form-urlencoded`)**
        *   Requires a form field named `message` containing the user's text input.
        *   *Example Request Body (raw):*
            ```
            message=Hello%2C%20how%20are%20you%20doing%20today%3F
            ```
    *   **Input Priority:** The server checks for `audio` in `request.files` first. If found and valid, it's processed via STT. If no valid audio is found, it then checks for `message` in the JSON body or form data.

---

**Responses:**

*   **Success Response (Code `200 OK`):**
    *   Indicates the user input was successfully processed and a response was generated. The format depends on the `format` query parameter.
    *   **If `format=text` (or default):**
        *   **Headers:** `Content-Type: application/json`
        *   **Body (JSON):**
            *   `response` (string): The text response generated by the language model.
            *   `warning` (string, *optional*): May appear if `format=audio` was requested but TTS failed, indicating a fallback to text.
        *   *Example Text Response Body:*
            ```json
            {
              "response": "I'm doing great, thanks for asking! What's up?"
            }
            ```
        *   *Example Text Fallback Response Body (when audio failed):*
            ```json
            {
              "warning": "Could not generate audio response: <TTS Error Details>. Returning text instead.",
              "response": "I'm doing great, thanks for asking! What's up?"
            }
            ```
    *   **If `format=audio`:**
        *   **Headers:** `Content-Type: audio/mpeg` (or similar, depending on TTS output)
        *   **Body:** The raw binary audio data of the synthesized speech.

*   **Error Response (Code `400 Bad Request`):**
    *   Indicates invalid input from the client.
    *   **Possible Reasons:**
        *   No input provided (missing `audio` file and missing/empty `message` field).
        *   Invalid JSON format when `Content-Type` is `application/json`.
        *   `audio` key present in `multipart/form-data` but no actual file uploaded or filename missing.
        *   `message` field present (JSON or form) but value is empty.
    *   **Body (JSON):**
        ```json
        {
          "error": "<Specific error message explaining the input issue>"
          // e.g., "Input required: Send JSON with 'message' or form-data with 'audio' file."
          // e.g., "JSON received but 'message' field is empty."
          // e.g., "Audio file part found but no file uploaded or filename missing."
        }
        ```

*   **Error Response (Code `404 Not Found`):**
    *   Indicates the provided `session_id` does not correspond to an active session.
    *   **Body (JSON):**
        ```json
        {
          "error": "Invalid session ID"
        }
        ```

*   **Error Response (Code `500 Internal Server Error`):**
    *   Indicates an unexpected error occurred on the server during processing.
    *   **Possible Reasons:** Error communicating with the language model (Gemini), error during STT/TTS processing (that isn't handled by fallback), other unexpected exceptions.
    *   **Body (JSON):**
        ```json
        {
          "error": "An internal server error occurred during chat processing."
          // Or: "Failed to get response from language model."
        }
        ```

*   **Error Response (Code `503 Service Unavailable`):**
    *   Indicates the backend chat service (Gemini) is not initialized or unavailable.
    *   **Body (JSON):**
        ```json
        {
          "error": "Chat service is unavailable due to configuration error."
        }
        ```

---

**Example Usage (curl):**

1.  **Send text, get text response:**
    ```bash
    curl -X POST \
      http://<your_api_domain>/api/chat/<session_id_value> \
      -H 'Content-Type: application/json' \
      -d '{
        "message": "Tell me a joke."
      }'
    ```

2.  **Send text, get audio response:**
    ```bash
    curl -X POST \
      http://<your_api_domain>/api/chat/<session_id_value>?format=audio \
      -H 'Content-Type: application/json' \
      -d '{
        "message": "How is the weather today?"
      }' \
      --output response.mp3 # Save the audio output to a file
    ```

3.  **Send audio, get text response:**
    ```bash
    curl -X POST \
      http://<your_api_domain>/api/chat/<session_id_value> \
      -H 'Content-Type: multipart/form-data' \
      -F 'audio=@/path/to/your/speech.wav'
    ```

4.  **Send audio, get audio response:**
    ```bash
    curl -X POST \
      http://<your_api_domain>/api/chat/<session_id_value>?format=audio \
      -H 'Content-Type: multipart/form-data' \
      -F 'audio=@/path/to/your/speech.wav' \
      --output response.mp3 # Save the audio output to a file
    ```

*(Replace `<your_api_domain>`, `<session_id_value>`, and `/path/to/your/speech.wav` with actual values.)*


## Translator

## Endpoint: `/api/translator/`

**Method:** `POST`

**Description:**
Translates text or speech from a source language (can be auto-detected) to a specified target language. Accepts input as text (JSON or form data) or an audio file (multipart/form-data). Returns the translation as either text (JSON) or synthesized audio, based on the `format` query parameter.

---

**Query Parameters:**

*   `format` (string, *optional*): Specifies the desired format for the response.
    *   `text` (default): Returns the translation as a JSON object containing the text.
    *   `audio`: Attempts to synthesize the translated text into speech using Text-to-Speech (TTS) for the target language and returns the audio file directly (e.g., `audio/mpeg`). If TTS fails, it may fall back to returning a text response with a warning.

---

**Request:**

*   **Headers:**
    *   `Content-Type`: Must match the body format.
        *   `application/json` (for text input via JSON)
        *   `multipart/form-data` (required for audio file input, can also contain text fields)
        *   `application/x-www-form-urlencoded` (for text input via standard form)
*   **Body:** Contains the content to be translated and language parameters.
    *   **Option 1: JSON Input (`application/json`)**
        *   Requires a JSON object.
        *   `text` (string, **required**): The text content to translate.
        *   `target_lang` (string, **required**): The BCP-47 language code to translate *to* (e.g., `es-ES`, `fr-FR`, `ar`).
        *   `source_lang` (string, *optional*): The BCP-47 language code of the input `text`. If omitted or set to `'auto'`, the service will attempt to detect the language.
        *   *Example JSON Body:*
            ```json
            {
              "text": "Hello, world!",
              "target_lang": "es-ES",
              "source_lang": "en-US"
            }
            ```
            ```json
            {
              "text": "Bonjour le monde!",
              "target_lang": "en"
            }
            ```

    *   **Option 2: Form Data Input (`multipart/form-data` or `application/x-www-form-urlencoded`)**
        *   Must contain form fields.
        *   `target_lang` (string, **required**): The target language code.
        *   `source_lang` (string, *optional*): The source language code. If audio is provided, this acts as a hint for Speech-to-Text (STT). Defaults to 'auto' for text translation if omitted.
        *   **Must include *one* of the following:**
            *   `text` (string): The text content to translate.
            *   `audio` (file): An audio file part containing the speech to be translated. The server will perform STT first. Required if `text` is not provided. Use `multipart/form-data` for file uploads.
        *   **Input Priority:** If both `audio` file and `text` field are somehow present (e.g., in `multipart/form-data`), the `audio` file takes precedence. If audio processing fails or no audio file is validly uploaded, it looks for the `text` field.
        *   *Example Form Data (Conceptual, using `multipart/form-data` for audio):*
            ```
            ------BoundaryString
            Content-Disposition: form-data; name="target_lang"

            fr-FR
            ------BoundaryString
            Content-Disposition: form-data; name="source_lang"

            en-US
            ------BoundaryString
            Content-Disposition: form-data; name="audio"; filename="greeting.wav"
            Content-Type: audio/wav

            <binary audio data>
            ------BoundaryString--
            ```
        *   *Example Form Data (using `application/x-www-form-urlencoded` for text):*
            ```
            target_lang=ja&source_lang=en&text=How%20are%20you%3F
            ```

---

**Responses:**

*   **Success Response (Code `200 OK`):**
    *   Indicates the input was successfully processed and translated. The format depends on the `format` query parameter.
    *   **If `format=text` (or default):**
        *   **Headers:** `Content-Type: application/json`
        *   **Body (JSON):**
            *   `translated_text` (string): The translated text.
            *   `source_language_detected` (string): The source language used for translation (either the one provided or 'auto-detect').
            *   `warning` (string, *optional*): May appear if `format=audio` was requested but TTS failed, indicating a fallback to text (e.g., "Audio generation failed: <TTS Error Details>. Returning text instead.").
        *   *Example Text Response Body:*
            ```json
            {
              "translated_text": "Hola, mundo!",
              "source_language_detected": "en-US"
            }
            ```
            ```json
            {
              "translated_text": "Hello world!",
              "source_language_detected": "auto-detect"
            }
            ```
    *   **If `format=audio`:**
        *   **Headers:** `Content-Type: audio/mpeg` (or similar, depending on TTS output)
        *   **Body:** The raw binary audio data of the synthesized translated speech.

*   **Error Response (Code `400 Bad Request`):**
    *   Indicates invalid input from the client.
    *   **Possible Reasons:**
        *   Invalid JSON format.
        *   `target_lang` field is missing.
        *   Neither `text` nor `audio` input provided.
        *   `audio` key present in form-data but no valid file uploaded.
        *   Speech-to-Text (STT) process failed for the provided audio.
    *   **Body (JSON):**
        ```json
        {
          "error": "<Specific error message describing the input issue>"
          // e.g., "'target_lang' is required in JSON or form data."
          // e.g., "Input required: JSON with 'text', or form-data with 'text' or 'audio'."
          // e.g., "Audio processing failed: <STT Error Details>"
          // e.g., "Invalid JSON format in request body."
        }
        ```

*   **Error Response (Code `500 Internal Server Error`):**
    *   Indicates an unexpected error occurred on the server during processing.
    *   **Possible Reasons:** Error communicating with the translation service, error during TTS processing (if `format=audio` and not handled by fallback), other unexpected exceptions.
    *   **Body (JSON):**
        ```json
        {
          "error": "<Specific error message>"
          // e.g., "Translation failed: <Details>"
          // e.g., "Internal server error occurred."
          // e.g., "Internal error: Translation result is missing."
        }
        ```

---

**Example Usage (curl):**

1.  **Translate text (JSON input), get text response:**
    ```bash
    curl -X POST \
      http://<your_api_domain>/api/translator/ \
      -H 'Content-Type: application/json' \
      -d '{
        "text": "This is a test.",
        "target_lang": "de"
      }'
    ```

2.  **Translate text (JSON input), get audio response:**
    ```bash
    curl -X POST \
      http://<your_api_domain>/api/translator/?format=audio \
      -H 'Content-Type: application/json' \
      -d '{
        "text": "Translate this to French audio.",
        "target_lang": "fr-FR"
      }' \
      --output translated_speech.mp3 # Save the audio output
    ```

3.  **Translate audio (Form input), get text response:**
    ```bash
    curl -X POST \
      http://<your_api_domain>/api/translator/ \
      -F 'target_lang=es' \
      -F 'source_lang=en-US' \
      -F 'audio=@/path/to/your/english_audio.wav'
    ```

4.  **Translate audio (Form input), get audio response:**
    ```bash
    curl -X POST \
      http://<your_api_domain>/api/translator/?format=audio \
      -F 'target_lang=ja' \
      -F 'source_lang=en-GB' \
      -F 'audio=@/path/to/your/english_audio.mp3' \
      --output japanese_translation.mp3 # Save the audio output
    ```

*(Replace `<your_api_domain>` and `/path/to/your/...` with actual values.)*


## Link Classifier

## Endpoint: `/api/link_classifier/`

**Method:** `POST`

**Description:**
Classifies a given URL as either 'Safe' or 'Unsafe'. This endpoint utilizes both a pre-trained local machine learning model (`rf_model.pkl`) and a large language model (Gemini) to determine the safety status. If the predictions from both models differ, the Gemini prediction is prioritized.

---

**Request:**

*   **Headers:**
    *   `Content-Type: application/json` (Required)

*   **Body (JSON):**
    *   Requires a JSON object containing the URL to be classified.
    *   `url` (string, **required**): The full URL that needs to be checked for safety (e.g., `"https://www.google.com"`, `"http://example-malicious-site.com/phish"`).

*   **Example Request Body:**
    ```json
    {
      "url": "https://www.safe-example-site.org/index.html"
    }
    ```
    ```json
    {
      "url": "http://some-suspicious-link.xyz/login?id=123"
    }
    ```

---

**Responses:**

*   **Success Response (Code `200 OK`):**
    *   Indicates the URL was successfully processed and classified.
    *   **Body (JSON):**
        *   `label` (string): The classification result, either `"Safe"` or `"Unsafe"`.

    *   **Example Success Response Body (Safe):**
        ```json
        {
          "label": "Safe"
        }
        ```
    *   **Example Success Response Body (Unsafe):**
        ```json
        {
          "label": "Unsafe"
        }
        ```

*   **Error Response (Code `400 Bad Request`):**
    *   Indicates the required `url` field was missing from the JSON payload.
    *   **Body (JSON):**
        ```json
        {
          "error": "URL is missing"
        }
        ```

*   **Error Response (Code `500 Internal Server Error` - Implicit):**
    *   Although not explicitly coded with a `try...except` block wrapping the core logic in the provided snippet, errors during model loading (`joblib.load`), feature extraction (`extract_features`), model prediction (`model.predict`), or communication with the Gemini API could potentially result in a 500 Internal Server Error.
    *   The exact response body for a 500 error would depend on the Flask application's global error handling configuration. A typical response might be:
        ```json
        {
          "error": "An internal server error occurred."
        }
        ```

---

**Example Usage (curl):**

```bash
curl -X POST \
  http://<your_api_domain>/api/link_classifier/ \
  -H 'Content-Type: application/json' \
  -d '{
    "url": "https://github.com"
  }'
