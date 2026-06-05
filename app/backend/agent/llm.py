# Compatibility wrapper pointing to agents/llm.py.
from app.agents.llm import client, chat, chat_json, chat_stream

__all__ = ["client", "chat", "chat_json", "chat_stream"]
