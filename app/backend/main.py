# Compatibility wrapper pointing to the restructured app logic.
from app.api.endpoints import app, ChatRequest, health, chat, chat_once

__all__ = ["app", "ChatRequest", "health", "chat", "chat_once"]
