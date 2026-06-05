# Compatibility wrapper pointing to services/schema_introspect.py.
from app.services.schema_introspect import build_schema_string, get_schema_string, get_allowed_tables, refresh_schema

__all__ = ["build_schema_string", "get_schema_string", "get_allowed_tables", "refresh_schema"]
