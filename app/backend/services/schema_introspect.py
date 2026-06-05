# Introspect the live database so the LLM always sees the real schema and values.
from sqlalchemy import text

from db import app_engine

# Cache the built schema string and the table allowlist in memory.
_schema_cache = None
_allowed_tables = None

# How many distinct values a text column may have before we still list them.
DISTINCT_LIMIT = 25


def _load_tables(conn):
    """Return {table_name: [(column, type), ...]} for the public schema."""
    rows = conn.execute(text(
        """
        SELECT table_name, column_name, data_type
        FROM information_schema.columns
        WHERE table_schema = 'public'
        ORDER BY table_name, ordinal_position
        """
    )).fetchall()
    tables = {}
    for table_name, column_name, data_type in rows:
        tables.setdefault(table_name, []).append((column_name, data_type))
    return tables


def _load_foreign_keys(conn):
    """Return a list of 'child.col -> parent.col' strings."""
    rows = conn.execute(text(
        """
        SELECT
            tc.table_name AS child_table,
            kcu.column_name AS child_col,
            ccu.table_name AS parent_table,
            ccu.column_name AS parent_col
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
            ON tc.constraint_name = kcu.constraint_name
        JOIN information_schema.constraint_column_usage ccu
            ON tc.constraint_name = ccu.constraint_name
        WHERE tc.constraint_type = 'FOREIGN KEY'
            AND tc.table_schema = 'public'
        """
    )).fetchall()
    return [f"{r[0]}.{r[1]} -> {r[2]}.{r[3]}" for r in rows]


def _load_distinct_values(conn, table, column):
    """Return distinct values of a text column if there are few of them, else None."""
    # Count distinct values first; only list when the column is low cardinality.
    count = conn.execute(text(
        f'SELECT COUNT(DISTINCT "{column}") FROM "{table}"'
    )).scalar()
    if count is None or count == 0 or count > DISTINCT_LIMIT:
        return None
    values = conn.execute(text(
        f'SELECT DISTINCT "{column}" FROM "{table}" '
        f'WHERE "{column}" IS NOT NULL ORDER BY 1'
    )).fetchall()
    return [str(v[0]) for v in values]


def _is_text_type(data_type):
    return data_type in ("character varying", "varchar", "text", "character")


def build_schema_string():
    """Introspect the DB and return a compact schema description for prompts."""
    global _schema_cache, _allowed_tables
    with app_engine.connect() as conn:
        tables = _load_tables(conn)
        foreign_keys = _load_foreign_keys(conn)

        lines = []
        for table_name, columns in tables.items():
            col_parts = []
            for column_name, data_type in columns:
                part = f"{column_name} {data_type}"
                # For low-cardinality text columns, show the real values.
                if _is_text_type(data_type):
                    distinct = _load_distinct_values(conn, table_name, column_name)
                    if distinct:
                        joined = ", ".join(distinct)
                        part += f" [values: {joined}]"
                col_parts.append(part)
            lines.append(f"TABLE {table_name}:\n  " + "\n  ".join(col_parts))

        schema_text = "\n\n".join(lines)
        if foreign_keys:
            schema_text += "\n\nFOREIGN KEYS:\n  " + "\n  ".join(foreign_keys)

    _schema_cache = schema_text
    _allowed_tables = list(tables.keys())
    return schema_text


def get_schema_string():
    """Return the cached schema string, building it once on first use."""
    global _schema_cache
    if _schema_cache is None:
        build_schema_string()
    return _schema_cache


def get_allowed_tables():
    """Return the list of table names the generated SQL is allowed to touch."""
    global _allowed_tables
    if _allowed_tables is None:
        build_schema_string()
    return _allowed_tables


def refresh_schema():
    """Force a fresh introspection on the next call."""
    global _schema_cache, _allowed_tables
    _schema_cache = None
    _allowed_tables = None
    return build_schema_string()
