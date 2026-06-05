# Simple in-memory per-session chat history with follow-up rewriting.
from agent.llm import chat

# session_id -> list of {"role", "content"} turns. Capped per session.
_history = {}
MAX_TURNS = 10

REWRITE_SYSTEM = """Given the conversation so far and a new user message, decide
whether the new message is a FOLLOW-UP that refers to prior context (e.g. "show me
their emails", "sort them by price", "what about Dallas?") or a STANDALONE question
that makes sense on its own.

- If the new message is a FOLLOW-UP: rewrite it into a single standalone question
  that incorporates only the necessary prior context.
- If the new message is ALREADY STANDALONE (a complete question on a new topic):
  return it EXACTLY as-is. Do NOT inject filters or details from earlier turns.

Return ONLY the rewritten (or unchanged) question, nothing else."""


def get_history(session_id):
    """Return the stored turns for a session (newest last)."""
    return _history.get(session_id, [])


def add_turn(session_id, role, content):
    """Append a turn and trim old ones."""
    turns = _history.setdefault(session_id, [])
    turns.append({"role": role, "content": content})
    # Keep only the most recent turns.
    if len(turns) > MAX_TURNS:
        del turns[:-MAX_TURNS]


def rewrite(session_id, message):
    """Rewrite a follow-up into a standalone question if there's prior history.

    Returns (standalone_question, tokens_used). Stores the user turn.
    """
    history = get_history(session_id)
    tokens = 0
    standalone = message

    if history:
        # Show the model the recent conversation plus the new message.
        convo = "\n".join(f"{t['role']}: {t['content']}" for t in history)
        messages = [
            {"role": "system", "content": REWRITE_SYSTEM},
            {"role": "user", "content":
                f"Conversation:\n{convo}\n\nNew message: {message}\n\nStandalone question:"},
        ]
        try:
            text_out, tokens = chat(messages, temperature=0.0)
            if text_out and text_out.strip():
                standalone = text_out.strip()
        except Exception:
            # If rewrite fails, just use the original message.
            standalone = message

    # Record the user's original message in history.
    add_turn(session_id, "user", message)
    return standalone, tokens
