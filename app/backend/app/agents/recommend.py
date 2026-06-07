from app.agents.llm import chat, chat_json
from app.core.db import run_readonly_sql
from app.services.schema_introspect import get_allowed_tables, get_schema_string
from app.core.sql_guard import SqlGuardError, clean_sql

MAX_RETRIES = 2

CRITERIA_SYSTEM = """Extract property search criteria from the user's message.
Return strict JSON with these keys (use null when not mentioned):
{"city": <string|null>, "bedrooms": <int|null>,
 "max_budget": <number|null>, "property_type": <string|null>}."""

SQL_SYSTEM = """You write a single PostgreSQL SELECT over the properties table to
find matching listings. Use ONLY columns from the schema and the real values shown
in [values: ...]. Only return AVAILABLE properties (use ILIKE '%available%' on the
status column so the filter is case-insensitive). Apply the given criteria as WHERE
filters (skip null ones). Select useful columns including monthly_rent.
Reply strict JSON: {"sql": "<select>"}."""


def extract_criteria(question):
    """Ask the LLM for structured search criteria. Returns (dict, tokens)."""
    messages = [
        {"role": "system", "content": CRITERIA_SYSTEM},
        {"role": "user", "content": question},
    ]
    data, tokens = chat_json(messages)
    return data, tokens


def _build_sql_prompt(question, criteria, schema, error=None, bad_sql=None):
    user = (
        f"Database schema:\n{schema}\n\n"
        f"Criteria (JSON): {criteria}\n\nUser message: {question}"
    )
    if error and bad_sql:
        user += f"\n\nPrevious SQL failed:\n{bad_sql}\nError:\n{error}\nFix it."
    return [
        {"role": "system", "content": SQL_SYSTEM},
        {"role": "user", "content": user},
    ]


def _rank_by_budget(rows, max_budget):
    """Rank rows by closeness to the budget (cheapest-within-budget first)."""
    if max_budget is None:
        return rows

    def score(row):
        rent = row.get("monthly_rent")
        if rent is None:
            return float("inf")
        rent = float(rent)
        if rent <= max_budget:
            return max_budget - rent
        return float("inf") - 1 + rent

    return sorted(rows, key=score)


def generate_and_run(question):
    """Extract criteria, build/run SQL with self-correction, rank by budget.

    Returns {sql, columns, rows, row_count, criteria, tokens}.
    """
    schema = get_schema_string()
    allowed = get_allowed_tables()
    criteria, total_tokens = extract_criteria(question)
    max_budget = criteria.get("max_budget")
    error = None
    raw_sql = None

    for attempt in range(MAX_RETRIES + 1):
        messages = _build_sql_prompt(question, criteria, schema, error, raw_sql)
        data, tokens = chat_json(messages)
        total_tokens += tokens
        raw_sql = data.get("sql", "")
        try:
            safe_sql = clean_sql(raw_sql, allowed)
            columns, rows = run_readonly_sql(safe_sql)
            ranked = _rank_by_budget(rows, max_budget)
            return {
                "sql": safe_sql,
                "columns": columns,
                "rows": ranked,
                "row_count": len(ranked),
                "criteria": criteria,
                "tokens": total_tokens,
            }
        except (SqlGuardError, Exception) as e:
            error = str(e)

    raise RuntimeError(f"Could not produce working SQL: {error}")


def build_messages_for_stream(question, columns, rows, criteria):
    """Messages to explain the top recommendations (used for streaming)."""
    top = rows[:5]
    body = {"columns": columns, "matches": top, "criteria": criteria,
            "total_matches": len(rows)}
    return [
        {"role": "system", "content":
            "You are a real estate advisor. Recommend the top matching properties "
            "to the user and briefly explain why each fits their criteria and budget."},
        {"role": "user", "content":
            f"Request: {question}\n\nMatches (JSON): {body}\n\n"
            "Recommend the best options in a short, friendly answer."},
    ]


def explain(question, columns, rows, criteria):
    """Non-streaming explanation of the recommendations. Returns (text, tokens)."""
    messages = build_messages_for_stream(question, columns, rows, criteria)
    text_out, tokens = chat(messages, temperature=0.3)
    return text_out, tokens
