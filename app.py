from flask import Flask, request, jsonify
from model import GeminiAPI
from data_collecting import UserInfoCollector
from utils.session_manager import SessionManager

app = Flask(__name__)
gemini = GeminiAPI()
data_collector = UserInfoCollector()
session_manager = SessionManager()


@app.route('/api/start_chat', methods=['POST'])
def start_chat():
    user_data = request.get_json()  # Get user data from the request body
    session_id = session_manager.create_session(user_data)
    return jsonify({"session_id": session_id, "message": "Chat session started."}), 201

@app.route('/api/chat/<session_id>', methods=['POST'])
def chat(session_id):
    try:
        user_input = request.json.get("message")
        if not user_input:
            return jsonify({"error": "Message is required"}), 400

        session = session_manager.get_session(session_id)
        if not session:
            return jsonify({"error": "Invalid session ID"}), 404

        user_data = session.get("user_data")
        chat_history = session.get("chat_history")

        prompt = f"""
        **Instructions for the Language Model:**

        You are a real human friend to {user_data.get("name", "the user")}. Your goal is to provide natural, enjoyable conversations tailored to the user's personality, interests, and communication style. You are the same age as the user ({user_data.get("age_range", "unknown")} years old) and share similar interests. You also speak the same language as the user and use the same accent from their country.

        * **Speak in the user's native language ({user_data.get('language', 'unknown')}) and use their country's accent naturally.**  
        * **Keep your responses casual, friendly, and natural—just like a real person.**  
        * **Incorporate the user's interests smoothly into conversations.**  
        * **Acknowledge their goals and support them in a realistic way.**  
        * **Adapt to their personality, humor, and way of speaking.**  
        * **Avoid sensitive or unethical topics.**  
        * **Remember you are a true human.**

        **Important:** Ensure your speech feels natural and authentic, matching the user's cultural and linguistic background. Use chat history to maintain consistency.  

        **User Profile:**  
        {user_data}  

        **Chat History:**  
        {chat_history}  

        **User Input:**  
        {user_input}  
        """

        response = gemini.get_report(prompt)
        session_manager.update_session_chat_history(session_id, user_input, response)

        return jsonify({"response": response}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)