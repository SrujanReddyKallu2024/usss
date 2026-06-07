import time

from app.agents import memory, nl2sql, recommend, router
from app.services import rag
from app.agents.llm import chat, chat_stream
from app.core.usage_log import log_usage

SMALLTALK_SYSTEM = """You are a friendly real estate assistant. Reply briefly to
greetings, thanks, or vague messages, and gently steer the user toward asking
about properties, tenants, payments, leases, or company policies."""


def _smalltalk_messages(question):
    return [
        {"role": "system", "content": SMALLTALK_SYSTEM},
        {"role": "user", "content": question},
    ]


def answer(session_id, message):
    start_time = time.time()
    res = {
        "answer": "", "intent": None, "sql": None, "sources": [],
        "row_count": None, "columns": [], "rows": [],
        "latency_ms": 0, "tokens": 0, "status": "ok", "error": None,
    }
    total_tokens = 0
    try:
        question, tokens = memory.rewrite(session_id, message)
        total_tokens += tokens

        intent, tokens = router.route(question)
        total_tokens += tokens
        res["intent"] = intent

        if intent == "nl2sql":
            data = nl2sql.generate_and_run(question)
            total_tokens += data["tokens"]
            res["sql"] = data["sql"]
            res["row_count"] = data["row_count"]
            res["columns"] = data["columns"]
            res["rows"] = [list(r.values()) for r in data["rows"][:50]]
            
            summary, tokens = nl2sql.explain_rows(question, data["columns"], data["rows"])
            total_tokens += tokens
            res["answer"] = summary

        elif intent == "recommend":
            data = recommend.generate_and_run(question)
            total_tokens += data["tokens"]
            res["sql"] = data["sql"]
            res["row_count"] = data["row_count"]
            res["columns"] = data["columns"]
            res["rows"] = [list(r.values()) for r in data["rows"][:50]]
            
            summary, tokens = recommend.explain(
                question, data["columns"], data["rows"], data["criteria"])
            total_tokens += tokens
            res["answer"] = summary

        elif intent == "rag":
            summary, sources, tokens = rag.answer_rag(question)
            total_tokens += tokens
            res["answer"] = summary
            res["sources"] = sources

        else:
            summary, tokens = chat(_smalltalk_messages(question), temperature=0.5)
            total_tokens += tokens
            res["answer"] = summary

        memory.add_turn(session_id, "assistant", res["answer"])

    except Exception as e:
        res["status"] = "error"
        res["error"] = str(e)
        res["answer"] = "Sorry, I ran into an error answering that."

    res["tokens"] = total_tokens
    res["latency_ms"] = int((time.time() - start_time) * 1000)

    log_usage(
        session_id=session_id, intent=res["intent"],
        user_prompt=message, ai_response=res["answer"],
        sql_text=res["sql"], sources=res["sources"],
        tokens_used=res["tokens"], latency_ms=res["latency_ms"],
        status=res["status"], error_message=res["error"],
    )
    return res


def answer_stream(session_id, message):
    start_time = time.time()
    intent = None
    sql = None
    sources = []
    row_count = None
    total_tokens = 0
    token_list = []
    status = "ok"
    error = None

    try:
        question, tokens = memory.rewrite(session_id, message)
        total_tokens += tokens
        intent, tokens = router.route(question)
        total_tokens += tokens

        cols = []
        rows = []

        if intent == "nl2sql":
            data = nl2sql.generate_and_run(question)
            total_tokens += data["tokens"]
            sql = data["sql"]
            row_count = data["row_count"]
            cols = data["columns"]
            rows = data["rows"]
            stream_messages = nl2sql.build_messages_for_stream(question, cols, rows)

        elif intent == "recommend":
            data = recommend.generate_and_run(question)
            total_tokens += data["tokens"]
            sql = data["sql"]
            row_count = data["row_count"]
            cols = data["columns"]
            rows = data["rows"]
            stream_messages = recommend.build_messages_for_stream(
                question, cols, rows, data["criteria"])

        elif intent == "rag":
            docs = rag.retrieve(question)
            sources = [{"title": d["title"], "category": d["category"]} for d in docs]
            stream_messages = rag.build_messages(question, docs)

        else:
            stream_messages = _smalltalk_messages(question)

        yield {"type": "meta", "intent": intent, "sql": sql,
               "sources": sources, "row_count": row_count,
               "columns": cols,
               "rows": [list(r.values()) if isinstance(r, dict) else list(r) for r in rows[:50]]}

        for chunk in chat_stream(stream_messages):
            token_list.append(chunk)
            yield {"type": "token", "text": chunk}

    except Exception as e:
        status = "error"
        error = str(e)
        yield {"type": "meta", "intent": intent, "sql": sql,
               "sources": sources, "row_count": row_count,
               "columns": [], "rows": []}
        yield {"type": "error", "message": str(e)}

    latency = int((time.time() - start_time) * 1000)
    full_answer = "".join(token_list)

    if status == "ok":
        memory.add_turn(session_id, "assistant", full_answer)
        
    log_usage(
        session_id=session_id, intent=intent, user_prompt=message,
        ai_response=full_answer, sql_text=sql, sources=sources,
        tokens_used=total_tokens, latency_ms=latency,
        status=status, error_message=error,
    )

    yield {"type": "done", "latency_ms": latency}
