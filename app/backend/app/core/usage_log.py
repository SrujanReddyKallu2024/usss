import json

from sqlalchemy import text

from app.core.db import app_engine


def log_usage(session_id, intent, user_prompt, ai_response, sql_text=None,
              sources=None, tokens_used=0, latency_ms=0, status="ok",
              error_message=None):
    """Insert a usage log row. Swallows any error so logging can't break the chat."""
    try:
        sources_text = json.dumps(sources) if sources else None
        with app_engine.begin() as conn:
            conn.execute(text(
                """
                INSERT INTO ai_usage_logs
                    (session_id, intent, user_prompt, ai_response, sql_text,
                     sources, tokens_used, latency_ms, status, error_message)
                VALUES
                    (:session_id, :intent, :user_prompt, :ai_response, :sql_text,
                     :sources, :tokens_used, :latency_ms, :status, :error_message)
                """
            ), {
                "session_id": session_id,
                "intent": intent,
                "user_prompt": user_prompt,
                "ai_response": ai_response,
                "sql_text": sql_text,
                "sources": sources_text,
                "tokens_used": tokens_used,
                "latency_ms": latency_ms,
                "status": status,
                "error_message": error_message,
            })
    except Exception as e:
        print(f"[usage_log] failed to write log: {e}")
