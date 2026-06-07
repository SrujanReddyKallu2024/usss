#!/usr/bin/env bash
# Bring up a local PostgreSQL in Docker, then load the schema + sample CSVs.
# Requires only Docker (no local Postgres install). Safe to re-run.
set -euo pipefail

# Don't let Git Bash / MSYS rewrite the container-side paths (/csv, /sql, ...).
export MSYS_NO_PATHCONV=1

CONTAINER=realestate_db
IMAGE=pgvector/pgvector:pg16
VOLUME=realestate_pgdata
PORT=5432
DB=real_estate

# Directory of this script (…/app). Use a Windows-style path on Git Bash so the
# Docker bind mounts resolve correctly; fall back to POSIX pwd elsewhere.
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && { pwd -W 2>/dev/null || pwd; })"
DATA="$HERE/data"

# 1. Start the database container (reuse it if it already exists).
if [ -n "$(docker ps -q -f name="^${CONTAINER}$")" ]; then
  echo "Container ${CONTAINER} already running."
elif [ -n "$(docker ps -aq -f name="^${CONTAINER}$")" ]; then
  echo "Starting existing container ${CONTAINER}..."
  docker start "$CONTAINER" >/dev/null
else
  echo "Creating container ${CONTAINER} (image ${IMAGE})..."
  docker run -d --name "$CONTAINER" \
    -e POSTGRES_USER=postgres \
    -e POSTGRES_PASSWORD=postgres \
    -e POSTGRES_DB="$DB" \
    -p "${PORT}:5432" \
    -v "${VOLUME}:/var/lib/postgresql/data" \
    -v "${DATA}/csv:/csv:ro" \
    -v "${DATA}/init:/sql:ro" \
    "$IMAGE" >/dev/null
fi

# 2. Wait until Postgres is accepting connections.
echo -n "Waiting for Postgres"
until docker exec "$CONTAINER" pg_isready -U postgres -d "$DB" >/dev/null 2>&1; do
  echo -n "."
  sleep 1
done
echo " ready."

# 3. Apply schema (tables + read-only chatbot_ro role) and load the CSVs.
#    Both scripts are idempotent — 01_schema.sql drops everything first.
docker exec "$CONTAINER" psql -v ON_ERROR_STOP=1 -U postgres -d "$DB" -f /sql/01_schema.sql
docker exec "$CONTAINER" psql -v ON_ERROR_STOP=1 -U postgres -d "$DB" -f /sql/02_load.sql

# 4. Quick row-count sanity check.
docker exec "$CONTAINER" psql -U postgres -d "$DB" -c \
  "SELECT 'properties' AS t, count(*) FROM properties UNION ALL
   SELECT 'tenants',  count(*) FROM tenants  UNION ALL
   SELECT 'payments', count(*) FROM payments UNION ALL
   SELECT 'kb_docs',  count(*) FROM knowledge_base_documents;"

echo "Local DB is up on port ${PORT} (container: ${CONTAINER})."
