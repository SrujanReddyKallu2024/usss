# Orchestrator: rewrite -> route -> dispatch -> answer (blocking and streaming).
import time

from agent import memory, nl2sql, rag, recommend, router
from agent.llm import chat, chat_stream
from services.usage_log import log_usage

SMALLTALK_SYSTEM = """You are a friendly real estate assistant. Reply briefly to
greetings, thanks, or vague messages, and gently steer the user toward asking
about properties, tenants, payments, leases, or company policies."""


def _smalltalk_messages(question):
    return [
        {"role": "system", "content": SMALLTALK_SYSTEM},
        {"role": "user", "content": question},
    ]


def answer(session_id, message):
    """Blocking answer. Returns a result dict and writes a usage log."""
    start = time.time()
    result = {
        "answer": "", "intent": None, "sql": None, "sources": [],
        "row_count": None, "columns": [], "rows": [],
        "latency_ms": 0, "tokens": 0, "status": "ok", "error": None,
    }
    tokens = 0
    try:
        # 1. Rewrite follow-ups into a standalone question.
        question, t = memory.rewrite(session_id, message)
        tokens += t

        # 2. Route to an intent with the LLM.
        intent, t = router.route(question)
        tokens += t
        result["intent"] = intent

        # 3. Dispatch.
        if intent == "nl2sql":
            run = nl2sql.generate_and_run(question)
            tokens += run["tokens"]
            result["sql"] = run["sql"]
            result["row_count"] = run["row_count"]
            result["columns"] = run["columns"]
            result["rows"] = [list(r.values()) for r in run["rows"][:50]]
            text_out, t = nl2sql.explain_rows(question, run["columns"], run["rows"])
            tokens += t
            result["answer"] = text_out

        elif intent == "recommend":
            run = recommend.generate_and_run(question)
            tokens += run["tokens"]
            result["sql"] = run["sql"]
            result["row_count"] = run["row_count"]
            result["columns"] = run["columns"]
            result["rows"] = [list(r.values()) for r in run["rows"][:50]]
            text_out, t = recommend.explain(
                question, run["columns"], run["rows"], run["criteria"])
            tokens += t
            result["answer"] = text_out

        elif intent == "rag":
            text_out, sources, t = rag.answer_rag(question)
            tokens += t
            result["answer"] = text_out
            result["sources"] = sources

        else:  # smalltalk
            text_out, t = chat(_smalltalk_messages(question), temperature=0.5)
            tokens += t
            result["answer"] = text_out

        # Record the assistant turn for memory.
        memory.add_turn(session_id, "assistant", result["answer"])

    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
        result["answer"] = "Sorry, I ran into an error answering that."

    result["tokens"] = tokens
    result["latency_ms"] = int((time.time() - start) * 1000)

    # Log the usage row (never breaks the response).
    log_usage(
        session_id=session_id, intent=result["intent"],
        user_prompt=message, ai_response=result["answer"],
        sql_text=result["sql"], sources=result["sources"],
        tokens_used=result["tokens"], latency_ms=result["latency_ms"],
        status=result["status"], error_message=result["error"],
    )
    return result


def answer_stream(session_id, message):
    """Streaming generator. Yields meta, token..., done (or error then done)."""
    start = time.time()
    intent = None
    sql = None
    sources = []
    row_count = None
    tokens = 0
    collected = []
    status = "ok"
    error = None

    try:
        # Rewrite + route (these are quick, before we stream).
        question, t = memory.rewrite(session_id, message)
        tokens += t
        intent, t = router.route(question)
        tokens += t

        # Prepare the streaming prompt depending on intent.
        table_columns = []
        table_rows = []

        if intent == "nl2sql":
            run = nl2sql.generate_and_run(question)
            tokens += run["tokens"]
            sql = run["sql"]
            row_count = run["row_count"]
            table_columns = run["columns"]
            table_rows = run["rows"]
            stream_messages = nl2sql.build_messages_for_stream(
                question, run["columns"], run["rows"])

        elif intent == "recommend":
            run = recommend.generate_and_run(question)
            tokens += run["tokens"]
            sql = run["sql"]
            row_count = run["row_count"]
            table_columns = run["columns"]
            table_rows = run["rows"]
            stream_messages = recommend.build_messages_for_stream(
                question, run["columns"], run["rows"], run["criteria"])

        elif intent == "rag":
            docs = rag.retrieve(question)
            sources = [{"title": d["title"], "category": d["category"]} for d in docs]
            stream_messages = rag.build_messages(question, docs)

        else:  # smalltalk
            stream_messages = _smalltalk_messages(question)

        # Emit meta first (include first 50 rows so the UI can render a table).
        yield {"type": "meta", "intent": intent, "sql": sql,
               "sources": sources, "row_count": row_count,
               "columns": table_columns,
               "rows": [list(r.values()) if isinstance(r, dict) else list(r) for r in table_rows[:50]]}

        # Stream the answer tokens.
        for chunk in chat_stream(stream_messages):
            collected.append(chunk)
            yield {"type": "token", "text": chunk}

    except Exception as e:
        status = "error"
        error = str(e)
        # If we never sent meta, send one now so the contract holds.
        yield {"type": "meta", "intent": intent, "sql": sql,
               "sources": sources, "row_count": row_count,
               "columns": [], "rows": []}
        yield {"type": "error", "message": str(e)}

    latency_ms = int((time.time() - start) * 1000)
    answer_text = "".join(collected)

    # Save memory + log usage.
    if status == "ok":
        memory.add_turn(session_id, "assistant", answer_text)
    log_usage(
        session_id=session_id, intent=intent, user_prompt=message,
        ai_response=answer_text, sql_text=sql, sources=sources,
        tokens_used=tokens, latency_ms=latency_ms,
        status=status, error_message=error,
    )

    yield {"type": "done", "latency_ms": latency_ms}
