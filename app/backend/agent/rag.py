# Answer policy questions from knowledge_base_documents using semantic search.
# Embeddings are stored as plain float arrays; we rank them in Python with numpy
# (only 8 docs, so this is fast and needs no database extension).
import numpy as np
from sqlalchemy import text

from agent.embeddings import embed_text
from agent.llm import chat
from db import app_engine

TOP_K = 3

RAG_SYSTEM = """You answer real estate policy questions using ONLY the provided
context documents. If the answer is not in the context, say you don't have that
policy. Be concise and do not invent details."""


def _cosine(a, b):
    """Cosine similarity between two vectors."""
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)


def retrieve(question):
    """Embed the question and return the top matching docs as a list of dicts."""
    qvec = embed_text(question)
    with app_engine.connect() as conn:
        rows = conn.execute(text(
            "SELECT title, category, content, embedding "
            "FROM knowledge_base_documents WHERE embedding IS NOT NULL"
        )).fetchall()

    # Score every document, keep the closest ones.
    scored = []
    for r in rows:
        score = _cosine(qvec, r[3])
        scored.append((score, {"title": r[0], "category": r[1], "content": r[2]}))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [doc for _, doc in scored[:TOP_K]]


def _build_context(docs):
    parts = []
    for d in docs:
        parts.append(f"Title: {d['title']}\nCategory: {d['category']}\n{d['content']}")
    return "\n\n---\n\n".join(parts)


def build_messages(question, docs):
    """Build the chat messages for answering from retrieved context."""
    context = _build_context(docs) if docs else "(no documents found)"
    return [
        {"role": "system", "content": RAG_SYSTEM},
        {"role": "user", "content":
            f"Context documents:\n{context}\n\nQuestion: {question}"},
    ]


def answer_rag(question):
    """Full non-streaming RAG answer. Returns (text, sources, tokens)."""
    docs = retrieve(question)
    sources = [{"title": d["title"], "category": d["category"]} for d in docs]
    messages = build_messages(question, docs)
    text_out, tokens = chat(messages, temperature=0.2)
    return text_out, sources, tokens
