# Architecture & Code Flow

How the Real Estate AI Chatbot is laid out and what happens end-to-end on every
question. For setup/run instructions see [README.md](README.md).

---

## High-level architecture

```
Browser (Next.js, :3000)
    │  POST /chat  (Server-Sent Events stream)
    ▼
FastAPI backend (:8000)
    │
    ├─ app/agents/graph.py   ← orchestrator
    │      ├─ memory.py      → rewrites follow-ups into standalone questions
    │      ├─ router.py      → LLM classifies intent (4 choices)
    │      ├─ nl2sql.py      → generates + runs SQL, explains rows
    │      ├─ recommend.py   → extracts criteria, generates + runs SQL, ranks
    │      └─ (smalltalk)    → direct LLM call
    │
    ├─ app/services/
    │      ├─ rag.py                 → semantic search over KB docs → grounded answer
    │      ├─ embeddings.py          → local fastembed model (384-dim)
    │      └─ schema_introspect.py   → live DB schema for prompts (cached)
    │
    └─ app/core/
           ├─ db.py          → two SQLAlchemy engines: app (r/w) + chatbot_ro (read-only)
           ├─ sql_guard.py   → validates / sanitises LLM SQL (sqlglot)
           ├─ usage_log.py   → logs every AI turn to ai_usage_logs
           └─ config.py      → pydantic-settings, reads .env

PostgreSQL 16 (:5432, db: real_estate)
    ├─ properties, tenants, leases, payments, leads
    ├─ crm_activities, maintenance_requests
    ├─ knowledge_base_documents  (+ 384-dim float[] embedding)
    └─ ai_usage_logs
```

---

## Folder structure

```
.
├── README.md                       # Setup & run guide
├── ARCHITECTURE.md                 # This file
├── chatbot/                        # Standalone legacy prototype (not part of the main app)
└── app/
    ├── docker-compose.yml          # Postgres + backend containers
    ├── run_local_db.sh             # Boots local Postgres, loads schema + CSVs
    │
    ├── backend/
    │   ├── main.py                 # FastAPI entrypoint (wrapper → app.api.endpoints)
    │   ├── eval.py                 # Runs the sample questions, prints a results table
    │   ├── requirements.txt
    │   ├── Dockerfile
    │   ├── app/                    # ── The backend package ──
    │   │   ├── api/
    │   │   │   └── endpoints.py     # /health, /chat (SSE), /chat/once (JSON)
    │   │   ├── agents/
    │   │   │   ├── graph.py         # Orchestrator for all four intents
    │   │   │   ├── router.py        # LLM intent classification
    │   │   │   ├── memory.py        # Per-session history + follow-up rewriting
    │   │   │   ├── nl2sql.py        # NL → SQL generation, run, explain
    │   │   │   ├── recommend.py     # Criteria extraction + ranked recommendations
    │   │   │   └── llm.py           # OpenAI-SDK wrapper (chat / chat_json / chat_stream)
    │   │   ├── services/
    │   │   │   ├── rag.py           # Retrieval-augmented generation over KB docs
    │   │   │   ├── embeddings.py    # Local fastembed embedding model
    │   │   │   └── schema_introspect.py  # Cached live DB schema string
    │   │   └── core/
    │   │       ├── db.py            # r/w + read-only SQLAlchemy engines
    │   │       ├── sql_guard.py     # SQL AST validation (sqlglot)
    │   │       ├── usage_log.py     # Writes ai_usage_logs rows
    │   │       └── config.py        # Settings from .env
    │   ├── ingest/
    │   │   └── embed_kb.py          # One-off: embed knowledge-base documents
    │   └── tests/
    │       └── test_features.py     # Integration tests (skip if DB/LLM unreachable)
    │
    ├── frontend/                    # Next.js 14 + TypeScript + Tailwind + shadcn/ui
    │   ├── app/                     # page.tsx (chat), layout.tsx, globals.css
    │   ├── components/              # message-bubble, composer, details-panel, etc.
    │   ├── lib/                     # chat-client.ts (SSE parser), types.ts
    │   └── store/                   # chat-store.ts (Zustand state)
    │
    └── data/
        ├── csv/                     # Seed data (properties, tenants, payments, …)
        └── init/                    # 01_schema.sql, 02_load.sql
```

---

## Backend modules

### Entry point — `backend/main.py` → `app/api/endpoints.py`

`main.py` is a thin wrapper that re-exports the FastAPI `app` from
`app.api.endpoints`. The endpoints:

| Endpoint        | Behaviour                                                     |
|-----------------|--------------------------------------------------------------|
| `POST /chat`     | **Streaming SSE** — emits `meta → token… → done` events     |
| `POST /chat/once`| **Blocking JSON** — full answer at once (used by `eval.py`) |
| `GET /health`    | Health check                                                 |

CORS allows `http://localhost:3000` only.

### Config — `app/core/config.py`

Pydantic-settings class reading `.env`. Key vars: `LLM_BASE_URL`, `LLM_API_KEY`,
`LLM_CHAT_MODEL`, `EMBED_MODEL`, `DATABASE_URL`, `DATABASE_URL_READONLY`.
Swapping LLM providers is `.env`-only.

### Database — `app/core/db.py`

Two SQLAlchemy engines:
- `app_engine` — read/write, used for schema introspection and writing usage logs.
- read-only engine — `chatbot_ro` role, runs **all** LLM-generated SQL with a
  **5-second statement timeout**.

### LLM client — `app/agents/llm.py`

Thin wrapper over the OpenAI SDK with exponential-backoff retry (rate limits,
timeouts, 5xx): `chat()` (blocking, returns text + token count), `chat_json()`
(forces JSON output), `chat_stream()` (yields chunks for SSE).

### Orchestrator — `app/agents/graph.py`

The brain, called by both endpoints:

```
1. memory.rewrite()       → turn follow-ups into standalone questions
2. router.route()         → classify intent with the LLM
3. dispatch by intent:
     nl2sql    → nl2sql.generate_and_run() → explain rows
     recommend → recommend.generate_and_run() → rank → explain
     rag       → rag.retrieve() → rag.answer_rag()
     smalltalk → direct LLM call
4. memory.add_turn()      → save assistant reply to session history
5. usage_log.log_usage()  → write an ai_usage_logs row
```

For streaming, the same steps run, then the answer is streamed token-by-token.

### Router — `app/agents/router.py`

Sends the question to the LLM with a system prompt listing the four intents,
expects strict JSON `{"intent": "..."}`, falls back to `nl2sql` if invalid.

| Intent      | Trigger                                                      |
|-------------|-------------------------------------------------------------|
| `nl2sql`    | Data questions — tenants, payments, leases, analytics       |
| `rag`       | Policy / process questions — answered from KB documents     |
| `recommend` | Property recommendations matching user criteria             |
| `smalltalk` | Greetings, vague messages, chit-chat                        |

### Memory — `app/agents/memory.py`

In-memory dict keyed by `session_id` (last ~10 turns; not persisted across
restarts). When history exists, the LLM rewrites a follow-up into a standalone
question so "show me their emails" after "which tenants are overdue" still works.

### NL2SQL — `app/agents/nl2sql.py`

1. Fetch the live schema string from `schema_introspect` (cached).
2. Ask the LLM for SQL → JSON `{"sql": "..."}`.
3. Validate + sanitise via `sql_guard.clean_sql()`.
4. Run on the read-only engine (5s timeout).
5. On failure, feed the error back to the LLM and retry up to 2 more times
   (self-correction loop).
6. Summarise the rows into plain English.

### Recommend — `app/agents/recommend.py`

Extracts structured criteria (`city`, `bedrooms`, `max_budget`,
`property_type`), builds + runs SQL with the same guard/retry loop, then ranks
results by closeness to budget and writes a recommendation paragraph.

### RAG — `app/services/rag.py`

1. Embed the question with fastembed.
2. Load `knowledge_base_documents` with non-null embeddings.
3. Score with cosine similarity (numpy) and take the top 3.
4. The LLM answers using only those docs, with source attribution.

### Embeddings — `app/services/embeddings.py`

`fastembed` (`BAAI/bge-small-en-v1.5`) running locally; 384-dim vectors; model
loaded once and reused. No external embedding API.

### Schema introspector — `app/services/schema_introspect.py`

Reads `information_schema.columns` + foreign keys. For low-cardinality text
columns (≤25 distinct values), lists the real values inline so the LLM uses
correct enums (e.g. `status [values: active, expired, pending]`). Cached in
memory; `refresh_schema()` forces a reload.

### SQL guard — `app/core/sql_guard.py`

Parses SQL with **sqlglot** (postgres dialect) and rejects: multiple statements,
non-SELECT queries, INSERT/UPDATE/DELETE/DDL, and tables not in the allowlist.
Enforces `LIMIT 200`. Raises `SqlGuardError` (which triggers the retry loop).

### Usage logger — `app/core/usage_log.py`

Writes one `ai_usage_logs` row per answer (session, intent, prompt, response,
SQL, sources, tokens, latency, status). Swallows its own errors so logging never
breaks a response.

### KB ingest — `backend/ingest/embed_kb.py`

One-off script: reads each KB document, embeds `title + content`, and UPDATEs the
`embedding` column. Run with `python -m ingest.embed_kb`.

---

## End-to-end request flow

Example: *"Which tenants have overdue payments?"*

```
[Frontend] composer.tsx → store.sendMessage()
[Frontend] chat-store.ts appends a user msg + an empty streaming assistant msg
[Frontend] chat-client.ts: POST /chat { message, session_id }

[Backend]  endpoints.py streams graph.answer_stream()
[Backend]  memory.rewrite()  → no prior history → question unchanged
[Backend]  router.route()    → LLM returns {"intent": "nl2sql"}
[Backend]  nl2sql.generate_and_run():
              schema_introspect.get_schema_string()  (cached)
              LLM writes SQL → {"sql": "SELECT ... WHERE p.status = 'overdue'"}
              sql_guard.clean_sql()  → validates, injects LIMIT 200
              read-only engine runs it (5s timeout) → rows
[Backend]  yield meta event { intent, sql, columns, rows, row_count }
[Backend]  chat_stream() → yield token events as the LLM explains the rows
[Backend]  yield done event { latency_ms }
[Backend]  memory.add_turn() + usage_log.log_usage()

[Frontend] meta event   → patch assistant msg with intent / sql / rows
[Frontend] token events → append text in real time
[Frontend] done event   → stop streaming, show latency, re-enable input
[Frontend] "Show details" → details-panel.tsx shows the SQL + data table
```

### SSE event contract (`/chat`)

Each event is written as `data: <json>\n\n`, in this order:

```
{ "type": "meta",  "intent": ..., "sql": <string|null>, "sources": [...], "row_count": <int|null>, "columns": [...], "rows": [...] }   ← exactly one, first
{ "type": "token", "text": "..." }                                                                                                     ← repeated
{ "type": "done",  "latency_ms": <int> }                                                                                               ← last
{ "type": "error", "message": "..." }                                                                                                  ← on failure, followed by done
```

---

## Security design

| Threat                          | Mitigation                                                        |
|---------------------------------|-------------------------------------------------------------------|
| SQL injection via the LLM       | `sql_guard.py` parses the AST, rejects non-SELECT / unknown tables |
| Data mutation                   | `chatbot_ro` Postgres role has SELECT-only grants                 |
| Runaway queries                 | 5-second statement timeout per query                              |
| Oversized results               | `LIMIT 200` enforced by the guard                                 |
| Hallucinated table names        | Schema introspection provides the exact allowlist                 |
| Made-up enum values             | Schema includes real distinct values inline (`[values: ...]`)     |

---

## Frontend

**Stack:** Next.js 14 (App Router), TypeScript, Tailwind CSS, shadcn/ui, Zustand.

- `app/page.tsx` — chat page (header, scrollable message list, composer).
- `store/chat-store.ts` — Zustand state: `messages`, `sending`, `sessionId`
  (persisted in `localStorage`). `sendMessage()` drives the SSE lifecycle.
- `lib/chat-client.ts` — manual SSE parser over `fetch` + `ReadableStream`,
  buffering partial lines across chunks.
- `components/` — `message-bubble`, `composer`, `details-panel`, `sql-block`,
  `data-table`, `intent-badge`, `suggestions`, `theme-toggle`.

---

## Extension points

- **LLM provider** — edit `.env` only.
- **Add KB docs** — insert rows into `knowledge_base_documents`, re-run `embed_kb`.
- **Add DB tables** — picked up on the next schema introspection (cache clears on restart).
- **Scale RAG** — swap the numpy cosine similarity for pgvector if the KB grows large.
```
