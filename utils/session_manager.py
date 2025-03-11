import uuid

class SessionManager:
    def __init__(self):
        self.sessions = {}

    def create_session(self, user_data):
        session_id = str(uuid.uuid4())
        self.sessions[session_id] = {"user_data": user_data, "chat_history": []}
        return session_id

    def get_session(self, session_id):
        return self.sessions.get(session_id)


    def update_session_chat_history(self, session_id, message, response):
        session = self.get_session(session_id)
        if session:
            session["chat_history"].append({"user": message, "bot": response})
            self.sessions[session_id] = session #update session


    def delete_session(self, session_id): #optional , use when you want to end the session 
        if session_id in self.sessions:
            del self.sessions[session_id]