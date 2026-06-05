# Compatibility wrapper pointing to agents/recommend.py.
from app.agents.recommend import extract_criteria, generate_and_run, build_messages_for_stream, explain

__all__ = ["extract_criteria", "generate_and_run", "build_messages_for_stream", "explain"]
