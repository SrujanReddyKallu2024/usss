# Compatibility wrapper pointing to agents/nl2sql.py.
from app.agents.nl2sql import generate_and_run, explain_rows, build_messages_for_stream

__all__ = ["generate_and_run", "explain_rows", "build_messages_for_stream"]
