from fastembed import TextEmbedding

from app.core.config import settings

_model = None


def get_model():
    """Load the embedding model once and reuse it."""
    global _model
    if _model is None:
        _model = TextEmbedding(model_name=settings.EMBED_MODEL)
    return _model


def embed_text(text):
    """Embed a single string and return a list of floats (384 dims)."""
    model = get_model()
    vectors = list(model.embed([text]))
    return vectors[0].tolist()


def embed_many(texts):
    """Embed a list of strings, returning a list of float lists."""
    model = get_model()
    return [v.tolist() for v in model.embed(texts)]
