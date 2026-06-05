# Compatibility wrapper pointing to services/embeddings.py.
from app.services.embeddings import get_model, embed_text, embed_many

__all__ = ["get_model", "embed_text", "embed_many"]
