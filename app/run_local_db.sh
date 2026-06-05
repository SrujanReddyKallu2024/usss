#!/usr/bin/env bash
# Bring up a fully local PostgreSQL (no Docker) using the conda 'recli' env,
# create the database, load the schema + CSVs. Safe to re-run.
set -e

CONDA="/c/Users/sruja/miniconda3/envs/recli/Library/bin"
PGDATA="/d/c/usssssssss/app/.pgdata"
PORT=5432
HERE="/d/c/usssssssss/app/data"

export PATH="$CONDA:$PATH"
export PGPORT=$PORT

# 1. Initialise the data directory once (superuser = postgres, trust auth locally).
if [ ! -f "$PGDATA/PG_VERSION" ]; then
  echo "initdb..."
  "$CONDA/initdb.exe" -D "$PGDATA" -U postgres --auth=trust --encoding=UTF8 >/dev/null
fi

# 2. Start the server (if not already running).
"$CONDA/pg_ctl.exe" -D "$PGDATA" -o "-p $PORT" -l "$PGDATA/server.log" -w start || true

# 3. Create the database (ignore error if it already exists).
"$CONDA/createdb.exe" -U postgres -p $PORT real_estate 2>/dev/null || echo "database already exists"

# 4. Schema (tables + read-only role) and data load.
"$CONDA/psql.exe" -U postgres -p $PORT -d real_estate -f "$HERE/init/01_schema.sql" || true
"$CONDA/psql.exe" -U postgres -p $PORT -d real_estate -f "$HERE/load_local.sql"

# 5. Quick row-count check.
"$CONDA/psql.exe" -U postgres -p $PORT -d real_estate -c \
  "SELECT 'properties' t, count(*) FROM properties UNION ALL
   SELECT 'tenants', count(*) FROM tenants UNION ALL
   SELECT 'payments', count(*) FROM payments UNION ALL
   SELECT 'kb_docs', count(*) FROM knowledge_base_documents;"

echo "Local DB is up on port $PORT."
