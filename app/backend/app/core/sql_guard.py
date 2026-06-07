import sqlglot
from sqlglot import expressions as exp

MAX_LIMIT = 200


class SqlGuardError(Exception):
    """Raised when generated SQL is unsafe or invalid."""
    pass


def clean_sql(sql, allowed_tables):
    """Check that sql is a single safe SELECT and return cleaned SQL.

    Rules: one statement, SELECT only, no DML/DDL, only allowed tables,
    and a LIMIT no larger than MAX_LIMIT (injected if missing).
    Raises SqlGuardError on any violation.
    """
    if not sql or not sql.strip():
        raise SqlGuardError("Empty SQL.")

    try:
        statements = sqlglot.parse(sql, read="postgres")
    except Exception as e:
        raise SqlGuardError(f"Could not parse SQL: {e}")

    statements = [s for s in statements if s is not None]
    if len(statements) != 1:
        raise SqlGuardError("Only a single SQL statement is allowed.")

    tree = statements[0]

    if not isinstance(tree, (exp.Select, exp.Subquery, exp.Union)):
        raise SqlGuardError("Only SELECT statements are allowed.")

    forbidden = (
        exp.Insert, exp.Update, exp.Delete, exp.Drop, exp.Create,
        exp.Alter, exp.TruncateTable, exp.Command, exp.Merge,
    )
    for node in tree.walk():
        if isinstance(node, forbidden):
            raise SqlGuardError("Only read-only SELECT queries are allowed.")

    allowed_lower = {t.lower() for t in allowed_tables}
    for table in tree.find_all(exp.Table):
        name = table.name
        if name and name.lower() not in allowed_lower:
            raise SqlGuardError(f"Table '{name}' is not allowed.")

    limit_node = tree.args.get("limit") if isinstance(tree, exp.Select) else None
    if isinstance(tree, exp.Select):
        if limit_node is None:
            tree.limit(MAX_LIMIT, copy=False)
        else:
            try:
                current = int(limit_node.expression.this)
                if current > MAX_LIMIT:
                    tree.limit(MAX_LIMIT, copy=False)
            except (ValueError, AttributeError):
                tree.limit(MAX_LIMIT, copy=False)
    else:
        tree = exp.select("*").from_(tree.subquery("guarded")).limit(MAX_LIMIT)

    return tree.sql(dialect="postgres")
