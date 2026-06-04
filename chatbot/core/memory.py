import logging
from collections import defaultdict
from langchain_core.messages import HumanMessage, AIMessage

log = logging.getLogger(__name__)

MAX_HISTORY = 10


class ConversationMemory:
    def __init__(self):
        self.sessions = defaultdict(list)

    def add_user_message(self, session_id, content):
        self.sessions[session_id].append(HumanMessage(content=content))
        self._trim(session_id)

    def add_ai_message(self, session_id, content):
        self.sessions[session_id].append(AIMessage(content=content))
        self._trim(session_id)

    def get_messages(self, session_id):
        return self.sessions.get(session_id, [])

    def get_context_string(self, session_id):
        messages = self.get_messages(session_id)
        if not messages:
            return ""
        lines = []
        for msg in messages[-6:]:
            role = "User" if isinstance(msg, HumanMessage) else "Assistant"
            lines.append(f"{role}: {msg.content}")
        return "\n".join(lines)

    def clear(self, session_id):
        self.sessions[session_id] = []
        log.info(f"Cleared memory for session {session_id[:8]}")

    def _trim(self, session_id):
        if len(self.sessions[session_id]) > MAX_HISTORY * 2:
            self.sessions[session_id] = self.sessions[session_id][-(MAX_HISTORY * 2):]


memory = ConversationMemory()
