# Compatibility wrapper pointing to services/rag.py.
from app.services.rag import retrieve, build_messages, answer_rag

__all__ = ["retrieve", "build_messages", "answer_rag"]
