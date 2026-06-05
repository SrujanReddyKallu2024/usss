# Compatibility wrapper pointing to core/sql_guard.py.
from app.core.sql_guard import SqlGuardError, clean_sql

__all__ = ["SqlGuardError", "clean_sql"]
