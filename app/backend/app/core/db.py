# Database engines and a safe read-only query helper.
from sqlalchemy import create_engine, text

from app.core.config import settings

# App engine: read/write. Used for schema introspection and writing usage logs.
app_engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)

# Read-only engine: connects as the chatbot_ro user. All generated SQL runs here.
readonly_engine = create_engine(settings.DATABASE_URL_READONLY, pool_pre_ping=True)


def run_readonly_sql(sql, params=None, timeout_ms=5000):
    """Run a SELECT on the read-only engine and return (columns, rows).

    rows is a list of plain dicts. A per-statement timeout protects the DB
    from slow generated queries.
    """
    with readonly_engine.connect() as conn:
        # Limit how long any single statement may run.
        # SET does not accept bind parameters, so inline the integer (we control it).
        conn.execute(text(f"SET LOCAL statement_timeout = {int(timeout_ms)}"))
        result = conn.execute(text(sql), params or {})
        columns = list(result.keys())
        rows = [dict(row._mapping) for row in result.fetchall()]
    return columns, rows


def run_app_sql(sql, params=None):
    """Run a statement on the app (read/write) engine. Used for introspection/logging."""
    with app_engine.begin() as conn:
        result = conn.execute(text(sql), params or {})
        if result.returns_rows:
            columns = list(result.keys())
            rows = [dict(row._mapping) for row in result.fetchall()]
            return columns, rows
        return [], []
