# Real Estate AI Chatbot — Backend

A FastAPI backend where the LLM decides how to answer each question. Three dynamic
answer paths (no hardcoding): **nl2sql**, **rag**, **recommend**, plus **smalltalk**.

## How it works

1. **memory.rewrite** — turns a follow-up into a standalone question using session history.
2. **router.route** — the LLM classifies intent (`nl2sql` / `rag` / `recommend` / `smalltalk`).
3. Dispatch:
   - **nl2sql** — the LLM writes a fresh SELECT from the live introspected schema
     (real columns + real DISTINCT values for low-cardinality text columns), it is
     validated by `sql_guard`, run on the read-only engine, and the rows are summarized.
   - **rag** — the question is embedded locally (fastembed `bge-small-en-v1.5`, 384d),
     pgvector finds the top 3 docs, and the LLM answers only from that context with citations.
   - **recommend** — the LLM extracts criteria, generates a filtered SELECT over
     `properties`, results are ranked by closeness to budget, and the top matches explained.
4. Every answer is logged to `ai_usage_logs`.

No keyword routing, no hardcoded SQL, no hardcoded enum values, no LangChain/LangGraph.

## Environment variables (read from `../.env`)

- `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_CHAT_MODEL` — OpenAI-compatible chat model.
- `EMBED_MODEL` — local fastembed model (`BAAI/bge-small-en-v1.5`).
- `DATABASE_URL` — read/write engine (introspection + logging).
- `DATABASE_URL_READONLY` — read-only engine (runs all generated SQL).

## Run locally

```bash
cd app/backend
python -m venv .venv && .venv\Scripts\activate    # Windows
pip install -r requirements.txt

# After the DB is up and seeded, embed the knowledge base once:
python -m ingest.embed_kb

# Start the API:
uvicorn main:app --host 0.0.0.0 --port 8000

# Quick checks:
python eval.py          # runs all 10 sample questions
pytest                  # integration tests (skip if DB/LLM unreachable)
```

## Run via Docker

The image is built by the root `docker-compose`. Inside compose the DB host is `db`
(the compose file overrides `DATABASE_URL*`). Standalone:

```bash
docker build -t realestate-backend app/backend
docker run -p 8000:8000 --env-file .env realestate-backend
```

## Endpoints

- `GET /health` -> `{"status":"ok"}`
- `POST /chat` body `{message, session_id}` -> `text/event-stream` (SSE).
- `POST /chat/once` body `{message, session_id}` ->
  `{answer, intent, sql, sources, row_count, latency_ms}`.

## SSE event contract (`/chat`)

Each event is written as `data: <json>\n\n`:

- `{"type":"meta","intent":"...","sql":<string|null>,"sources":[{"title":...,"category":...}],"row_count":<int|null>}`
- `{"type":"token","text":"..."}` (repeated)
- `{"type":"done","latency_ms":<int>}`
- `{"type":"error","message":"..."}` (followed by a `done`)

Exactly one `meta` is emitted first, then tokens, then `done` (or `error` then `done`).
