class MemoryManager:

    def __init__(self):
        self.sessions = {}

    def get_history(self, session_id):
        return self.sessions.get(session_id, [])

    def append(self, session_id, user, assistant):
        self.sessions.setdefault(session_id, []).append({
            "user": user,
            "assistant": assistant
        })

        # Sliding window
        if len(self.sessions[session_id]) > 10:
            self.sessions[session_id] = self.sessions[session_id][-10:]
