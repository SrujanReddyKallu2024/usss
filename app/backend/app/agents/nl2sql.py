from app.agents.llm import chat, chat_json
from app.core.db import run_readonly_sql
from app.services.schema_introspect import get_allowed_tables, get_schema_string
from app.core.sql_guard import SqlGuardError, clean_sql

MAX_RETRIES = 2

SQL_SYSTEM = """You write PostgreSQL SELECT queries for a real estate database.
Rules:
- Use ONLY the tables and columns from the schema given.
- Use the real column VALUES shown in [values: ...] (do not invent enum values).
- Output a SINGLE read-only SELECT statement. No INSERT/UPDATE/DELETE/DDL.
- Prefer explicit JOINs using the foreign keys provided.
- Always reply with strict JSON: {"sql": "<the select>"}."""


def _build_sql_prompt(question, schema, error=None, bad_sql=None):
    user = f"Database schema:\n{schema}\n\nQuestion: {question}"
    if error and bad_sql:
        user += (
            f"\n\nYour previous SQL failed:\n{bad_sql}\n\n"
            f"Error:\n{error}\n\nFix it and return corrected JSON."
        )
    return [
        {"role": "system", "content": SQL_SYSTEM},
        {"role": "user", "content": user},
    ]


def generate_and_run(question):
    """Generate SQL, validate, run (with self-correction), return result dict.

    Returns {sql, columns, rows, row_count, tokens}.
    Raises the last error if it never succeeds.
    """
    schema = get_schema_string()
    allowed = get_allowed_tables()
    total_tokens = 0
    error = None
    raw_sql = None

    for attempt in range(MAX_RETRIES + 1):
        messages = _build_sql_prompt(question, schema, error, raw_sql)
        data, tokens = chat_json(messages)
        total_tokens += tokens
        raw_sql = data.get("sql", "")
        try:
            safe_sql = clean_sql(raw_sql, allowed)
            columns, rows = run_readonly_sql(safe_sql)
            return {
                "sql": safe_sql,
                "columns": columns,
                "rows": rows,
                "row_count": len(rows),
                "tokens": total_tokens,
            }
        except (SqlGuardError, Exception) as e:
            error = str(e)

    raise RuntimeError(f"Could not produce working SQL: {error}")


EXPLAIN_SYSTEM = (
    "You explain SQL query results to a real estate manager in clear, concise "
    "plain English. Summarize the data; do not invent numbers. When stating how "
    "many records matched, always use the given total count, not the sample size."
)


def _explain_messages(question, columns, rows):
    """Build the prompt for turning rows into a plain-English answer."""
    total = len(rows)
    preview = rows[:30]
    body = {"columns": columns, "sample_rows": preview}
    return [
        {"role": "system", "content": EXPLAIN_SYSTEM},
        {"role": "user", "content":
            f"Question: {question}\n\n"
            f"The query returned {total} row(s) in total. "
            f"Below is a sample of up to 30 of them.\n"
            f"Data (JSON): {body}\n\n"
            f"Give a short, direct answer. Use {total} as the total count if asked how many."},
    ]


def explain_rows(question, columns, rows):
    """Turn query rows into a short plain-English answer. Returns (text, tokens)."""
    text, tokens = chat(_explain_messages(question, columns, rows), temperature=0.3)
    return text, tokens


def build_messages_for_stream(question, columns, rows):
    """Same prompt as explain_rows but returned for streaming the answer."""
    return _explain_messages(question, columns, rows)
