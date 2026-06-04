import logging
import sqlite3
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_community.utilities import SQLDatabase
from core.llm import get_chat
from config import DB_URI, DB_PATH

log = logging.getLogger(__name__)

_db = None


def get_db():
    global _db
    if _db is None:
        _db = SQLDatabase.from_uri(DB_URI, sample_rows_in_table_info=3)
        log.info("SQLDatabase connected")
    return _db


GENERATE_SQL = ChatPromptTemplate.from_messages([
    ("system",
     "You are a SQL expert for a Real Estate ERP system running on SQLite.\n\n"
     "Database schema:\n{schema}\n\n"
     "Rules:\n"
     "- Write ONLY a SELECT query — never INSERT, UPDATE, DELETE, DROP\n"
     "- Use SQLite syntax — no PostgreSQL features\n"
     "- Return ONLY the raw SQL, no markdown, no explanation, no backticks\n"
     "- Use LIKE with % for text matching\n"
     "- For dates use date() and strftime() functions\n"
     "- Limit to 25 rows unless user asks for all\n"
     "- Use JOINs when data spans multiple tables\n"
     "- Use descriptive column aliases for readability"),
    ("human", "{question}"),
])

FORMAT_ANSWER = ChatPromptTemplate.from_messages([
    ("system",
     "You are a Real Estate assistant. Explain SQL results in plain English.\n"
     "Be concise. Use bullet points for lists. Highlight key numbers.\n"
     "If no results found, say so politely and suggest how to rephrase."),
    ("human",
     "Question: {question}\n"
     "SQL used: {sql}\n"
     "Results:\n{results}"),
])

BLOCKED_WORDS = {"INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "TRUNCATE"}


def clean_sql(raw):
    sql = raw.strip()
    for tag in ["```sql", "```SQL", "```", "SQLQuery:", "sql"]:
        sql = sql.replace(tag, "")
    sql = sql.strip().rstrip(";").strip()
    if "\n" in sql:
        lines = [l for l in sql.split("\n") if not l.strip().startswith("--")]
        sql = "\n".join(lines)
    return sql


def is_safe(sql):
    tokens = sql.upper().split()
    return not any(word in BLOCKED_WORDS for word in tokens)


def execute(sql):
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(sql)
    columns = [desc[0] for desc in cursor.description] if cursor.description else []
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return columns, rows


def format_table(columns, rows, max_rows=25):
    if not rows:
        return "No results found."
    lines = [" | ".join(columns)]
    lines.append(" | ".join("---" for _ in columns))
    for row in rows[:max_rows]:
        lines.append(" | ".join(str(row.get(c, "")) for c in columns))
    if len(rows) > max_rows:
        lines.append(f"... and {len(rows) - max_rows} more rows")
    return "\n".join(lines)


def ask(question):
    db = get_db()
    chat = get_chat()
    parser = StrOutputParser()

    schema = db.get_table_info()

    sql_chain = GENERATE_SQL | chat | parser
    raw_sql = sql_chain.invoke({"schema": schema, "question": question})
    sql = clean_sql(raw_sql)

    log.info(f"NL2SQL generated: {sql}")

    if not is_safe(sql):
        return {
            "answer": "I can only run read-only queries for safety.",
            "sql": sql, "route": "nl2sql",
        }

    try:
        columns, rows = execute(sql)
        results_text = format_table(columns, rows)
        log.info(f"NL2SQL returned {len(rows)} rows")
    except Exception as e:
        log.error(f"SQL execution failed: {e}")
        return {
            "answer": f"The query didn't work: {e}. Try rephrasing your question.",
            "sql": sql, "route": "nl2sql",
        }

    answer_chain = FORMAT_ANSWER | chat | parser
    answer = answer_chain.invoke({
        "question": question,
        "sql": sql,
        "results": results_text[:2000],
    })

    return {
        "answer": answer,
        "sql": sql,
        "results": results_text[:1000],
        "route": "nl2sql",
    }
