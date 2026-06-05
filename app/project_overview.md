# Real Estate AI Chatbot — End-to-End Project Overview

## What This Is

A **production-style AI chatbot** for real estate management. The user asks natural-language questions in a chat UI and the backend intelligently decides *how* to answer — by writing SQL, searching policy documents, recommending properties, or just having a conversation. Everything runs **100% locally** with a pluggable LLM provider (OpenAI SDK compatible: NVIDIA NIM, OpenAI, HuggingFace).

---

## High-Level Architecture

```
Browser (Next.js)
    │  HTTP POST /chat  (SSE stream)
    ▼
FastAPI Backend  (port 8000)
    │
    ├─ agent/graph.py  ← Orchestrator
    │       │
    │       ├─ memory.py     → Rewrites follow-ups into standalone questions
    │       ├─ router.py     → LLM classifies intent (4 choices)
    │       │
    │       ├─ nl2sql.py     → generates + runs SQL, explains rows
    │       ├─ recommend.py  → extracts criteria, generates + runs SQL, ranks
    │       ├─ rag.py        → semantic search over KB docs → LLM answer
    │       └─ (smalltalk)   → direct LLM call
    │
    ├─ services/
    │   ├─ schema_introspect.py  → live DB schema for prompts (cached)
    │   ├─ sql_guard.py          → validates/sanitises LLM SQL (sqlglot)
    │   └─ usage_log.py          → logs every AI turn to ai_usage_logs
    │
    └─ db.py  → two SQLAlchemy engines: app (r/w) + chatbot_ro (read-only)

PostgreSQL 16  (port 5432, db: real_estate)
    ├─ properties, tenants, leases, payments, leads
    ├─ crm_activities, maintenance_requests
    ├─ knowledge_base_documents  (+ 384-dim float[] embedding)
    └─ ai_usage_logs
```

---

## Layer-by-Layer Breakdown

### 1. Database — `data/`

| File | Purpose |
|---|---|
| [01_schema.sql](file:///d:/c/usssssssss/app/data/init/01_schema.sql) | Creates all 9 tables, indexes, and the `chatbot_ro` read-only role |
| [02_load.sql](file:///d:/c/usssssssss/app/data/init/02_load.sql) | Points `\copy` commands at the CSVs in `data/csv/` |
| [run_local_db.sh](file:///d:/c/usssssssss/app/run_local_db.sh) | Shell script that starts Postgres via conda and loads data |

**Key design decision:** Generated SQL runs as `chatbot_ro` (SELECT-only Postgres role) so the LLM can never mutate the database, even if it tries.

**Tables:**
- `properties` — listings with city, bedrooms, rent, status, lat/lon
- `tenants` — tenant info + credit score
- `leases` — links tenant ↔ property, dates, status
- `payments` — due/paid dates, amounts, `days_late`
- `leads` — CRM prospects with preferences and budget
- `crm_activities` — follow-up activities per lead
- `maintenance_requests` — property issues with priority + cost
- `knowledge_base_documents` — policy docs with `embedding double precision[]`
- `ai_usage_logs` — one row per chatbot answer (session, intent, SQL, tokens, latency)

---

### 2. Backend — `backend/`

#### Entry point: [main.py](file:///d:/c/usssssssss/app/backend/main.py)

FastAPI app with two chat endpoints:

| Endpoint | Behaviour |
|---|---|
| `POST /chat` | **Streaming SSE** — emits `meta → token… → done` events |
| `POST /chat/once` | **Blocking JSON** — returns full answer at once (used by eval.py) |
| `GET /health` | Health check |

CORS allows `http://localhost:3000` only.

---

#### Config: [config.py](file:///d:/c/usssssssss/app/backend/config.py)

Pydantic-settings class. Reads from `../.env` (one level above `app/`). Key vars:

```
LLM_BASE_URL        # e.g. https://integrate.api.nvidia.com/v1
LLM_API_KEY         # provider key
LLM_CHAT_MODEL      # e.g. meta/llama-3.3-70b-instruct
EMBED_MODEL         # BAAI/bge-small-en-v1.5 (local fastembed)
DATABASE_URL        # app (r/w) connection
DATABASE_URL_READONLY  # chatbot_ro connection
```

Swapping LLM providers requires **only `.env` changes** — no code changes.

---

#### Database: [db.py](file:///d:/c/usssssssss/app/backend/db.py)

Two SQLAlchemy engines:
- `app_engine` — r/w, used for schema introspection and writing usage logs
- `readonly_engine` — SELECT-only (`chatbot_ro` user), used for all LLM-generated queries with a **5-second statement timeout** for safety

---

#### LLM Client: [agent/llm.py](file:///d:/c/usssssssss/app/backend/agent/llm.py)

Thin wrapper over the OpenAI SDK:
- `chat()` — blocking, returns `(text, tokens_used)`
- `chat_json()` — forces `response_format: json_object`, parses result
- `chat_stream()` — yields text chunks for SSE streaming
- Exponential backoff retry (up to 4 tries) on rate-limits, timeouts, 5xx errors

---

#### Embeddings: [agent/embeddings.py](file:///d:/c/usssssssss/app/backend/agent/embeddings.py)

Uses **fastembed** (`BAAI/bge-small-en-v1.5`) running **locally**. Produces 384-dim float vectors. Singleton model instance loaded once and reused. No external embedding API call needed.

---

#### Orchestrator: [agent/graph.py](file:///d:/c/usssssssss/app/backend/agent/graph.py)

The "brain" — called by both endpoints. The pipeline is:

```
1. memory.rewrite()     → turn follow-ups into standalone questions
2. router.route()       → classify intent with LLM
3. dispatch by intent:
   nl2sql   → nl2sql.generate_and_run() → nl2sql.explain_rows()
   recommend → recommend.generate_and_run() → recommend.explain()
   rag       → rag.retrieve() → rag.answer_rag()
   smalltalk → direct LLM call
4. memory.add_turn()   → save assistant reply to session history
5. usage_log.log_usage() → write ai_usage_logs row
```

For **streaming**, the same steps happen but after data is fetched, the answer text is streamed token-by-token via `chat_stream()`.

**SSE event contract:**
```
{ type: "meta",  intent, sql, sources, row_count, columns, rows }  ← first
{ type: "token", text: "..." }                                      ← many
{ type: "done",  latency_ms: 1234 }                                 ← last
{ type: "error", message: "..." }                                   ← on failure
```

---

#### Router: [agent/router.py](file:///d:/c/usssssssss/app/backend/agent/router.py)

Sends the question to the LLM with a system prompt listing all four intents. Expects strict JSON `{"intent": "..."}`. Falls back to `nl2sql` if the response is invalid.

**Intents:**
| Intent | Trigger |
|---|---|
| `nl2sql` | Data questions — tenants, payments, leases, analytics |
| `rag` | Policy/process questions — answered from KB documents |
| `recommend` | Property recommendations matching user criteria |
| `smalltalk` | Greetings, vague messages, chit-chat |

---

#### Memory: [agent/memory.py](file:///d:/c/usssssssss/app/backend/agent/memory.py)

- In-memory dict keyed by `session_id` (survives backend restart _not_ guaranteed)
- Stores last 10 turns per session
- On each new message: if there's history, asks the LLM to rewrite the follow-up as a standalone question (so "show me their emails" after "which tenants are overdue" works correctly)

---

#### NL2SQL: [agent/nl2sql.py](file:///d:/c/usssssssss/app/backend/agent/nl2sql.py)

1. Fetches live schema string from `schema_introspect` (cached)
2. Asks LLM for SQL → JSON `{"sql": "..."}`
3. Validates + sanitises via `sql_guard.clean_sql()`
4. Runs on `readonly_engine` with 5 s timeout
5. On failure, feeds the error back to the LLM and retries up to **2 more times** (self-correction loop)
6. Calls `explain_rows()` to turn raw data into a plain-English summary

---

#### Recommend: [agent/recommend.py](file:///d:/c/usssssssss/app/backend/agent/recommend.py)

1. Calls LLM to extract structured criteria: `{city, bedrooms, max_budget, property_type}`
2. Builds a SQL prompt using those criteria + live schema
3. Same guard/run/retry loop as NL2SQL
4. Post-processes: ranks results by closeness to `max_budget` (cheapest within budget first)
5. Calls `explain()` to write a friendly recommendation paragraph

---

#### RAG: [agent/rag.py](file:///d:/c/usssssssss/app/backend/agent/rag.py)

1. Embeds the question with fastembed
2. Fetches all `knowledge_base_documents` where `embedding IS NOT NULL`
3. Scores with **cosine similarity in Python (numpy)** — no pgvector needed
4. Takes top-3 docs, builds context string
5. LLM answers using ONLY those docs (grounded answer with source attribution)

---

#### Schema Introspector: [services/schema_introspect.py](file:///d:/c/usssssssss/app/backend/services/schema_introspect.py)

- Reads `information_schema.columns` and foreign keys on startup
- For low-cardinality text columns (≤25 distinct values), lists the actual values inline so the LLM uses correct enum values (e.g. `status [values: active, expired, pending]`)
- Result is **cached in memory** — no repeated DB roundtrips
- `refresh_schema()` forces a re-introspection

---

#### SQL Guard: [services/sql_guard.py](file:///d:/c/usssssssss/app/backend/services/sql_guard.py)

Validates LLM SQL before it runs:
- Parses with **sqlglot** (postgres dialect)
- Rejects: multiple statements, non-SELECT, INSERT/UPDATE/DELETE/DDL nodes, tables not in allowlist
- Enforces `LIMIT 200` (injects if missing, caps if too high)
- Returns clean SQL or raises `SqlGuardError` (which triggers the retry loop)

---

#### Usage Logger: [services/usage_log.py](file:///d:/c/usssssssss/app/backend/services/usage_log.py)

Writes one row to `ai_usage_logs` per answer. Fields: session_id, intent, user_prompt, ai_response, sql_text, sources (JSON), tokens_used, latency_ms, status, error_message. **Silently swallows all errors** — logging never breaks a chat response.

---

#### Knowledge Base Ingest: [ingest/embed_kb.py](file:///d:/c/usssssssss/app/backend/ingest/embed_kb.py)

One-off script (run once before first use). Reads all `knowledge_base_documents` rows, embeds `title + content` with fastembed, and UPDATEs the `embedding` column. Run via:
```bash
python -m ingest.embed_kb
```

---

### 3. Frontend — `frontend/`

**Stack:** Next.js 14, TypeScript, Tailwind CSS, shadcn/ui, Zustand

#### Pages & Layout
| File | Role |
|---|---|
| [app/layout.tsx](file:///d:/c/usssssssss/app/frontend/app/layout.tsx) | Root layout with ThemeProvider |
| [app/page.tsx](file:///d:/c/usssssssss/app/frontend/app/page.tsx) | Main chat page — header, scrollable message list, composer footer |
| [app/globals.css](file:///d:/c/usssssssss/app/frontend/app/globals.css) | Global styles + typing caret animation |

#### State Management: [store/chat-store.ts](file:///d:/c/usssssssss/app/frontend/store/chat-store.ts)

Zustand store. Key state:
- `messages: ChatMessage[]` — full conversation
- `sending: boolean` — disables input while streaming
- `sessionId` — stored in `localStorage`, persists across page reloads

`sendMessage()` flow:
1. Appends user message + empty assistant message with `streaming: true`
2. Calls `streamChat()` from `lib/chat-client.ts`
3. On `meta` event → fills in intent/sql/sources/rows on the assistant message
4. On `token` events → appends text to the assistant message in real-time
5. On `done` → sets `latencyMs`, clears `streaming`
6. On `error` → sets the error field

#### API Client: [lib/chat-client.ts](file:///d:/c/usssssssss/app/frontend/lib/chat-client.ts)

Uses `fetch()` + `ReadableStream` to manually parse SSE (`data: <json>` lines). Buffers partial lines across chunks — robust against chunked TCP delivery.

#### Components

| Component | Role |
|---|---|
| [composer.tsx](file:///d:/c/usssssssss/app/frontend/components/composer.tsx) | Textarea input + send button, Enter to send, Shift+Enter for newline |
| [message-bubble.tsx](file:///d:/c/usssssssss/app/frontend/components/message-bubble.tsx) | User (right, primary color) and assistant (left, card) messages; shows intent badge, streaming caret, error state |
| [details-panel.tsx](file:///d:/c/usssssssss/app/frontend/components/details-panel.tsx) | "Show details" collapsible under AI answers — shows SQL or sources |
| [sql-block.tsx](file:///d:/c/usssssssss/app/frontend/components/sql-block.tsx) | Syntax-highlighted SQL display |
| [data-table.tsx](file:///d:/c/usssssssss/app/frontend/components/data-table.tsx) | Renders query result rows as a scrollable table |
| [intent-badge.tsx](file:///d:/c/usssssssss/app/frontend/components/intent-badge.tsx) | Coloured pill showing `nl2sql` / `rag` / `recommend` / `smalltalk` |
| [suggestions.tsx](file:///d:/c/usssssssss/app/frontend/components/suggestions.tsx) | Starter question chips shown when chat is empty |
| [theme-toggle.tsx](file:///d:/c/usssssssss/app/frontend/components/theme-toggle.tsx) | Dark/light mode toggle |

---

## Request Lifecycle — Full End-to-End Trace

```
User types "Which tenants have overdue payments?" → hits Enter

1. [Frontend] Composer calls store.sendMessage()
2. [Frontend] Zustand appends user msg + empty streaming assistant msg
3. [Frontend] chat-client.ts: POST /chat { message, session_id }
4. [Backend] main.py: streams graph.answer_stream()
5. [Backend] memory.rewrite() → no prior history → question unchanged
6. [Backend] router.route() → LLM returns {"intent": "nl2sql"}
7. [Backend] nl2sql.generate_and_run():
     a. schema_introspect.get_schema_string() → "TABLE payments: ... [values: overdue, paid, pending]"
     b. LLM writes SQL → {"sql": "SELECT t.tenant_name, p.amount_due ... WHERE p.status = 'overdue'"}
     c. sql_guard.clean_sql() → validates, injects LIMIT 200
     d. run_readonly_sql() on chatbot_ro engine with 5s timeout → rows
8. [Backend] yield meta event { intent:"nl2sql", sql:"...", columns:[...], rows:[...] }
9. [Backend] nl2sql.build_messages_for_stream() → prompt to explain rows
10.[Backend] chat_stream() → yield token events as LLM responds
11.[Backend] yield done event { latency_ms: 1234 }
12.[Backend] memory.add_turn() → save assistant reply
13.[Backend] usage_log.log_usage() → write to ai_usage_logs
14.[Frontend] meta event → store patches assistant msg with intent/sql/rows
15.[Frontend] token events → text appends in real-time, UI rerenders
16.[Frontend] done event → streaming:false, latency shown, input re-enabled
17.[Frontend] User clicks "Show details" → DetailsPanel shows SQL + data table
```

---

## Security Design

| Threat | Mitigation |
|---|---|
| SQL injection via LLM | `sql_guard.py` parses AST, rejects non-SELECT and unknown tables |
| Data mutation | `chatbot_ro` Postgres role has SELECT-only grants |
| Runaway queries | 5-second statement timeout per query |
| Oversized results | `LIMIT 200` enforced by sql_guard, frontend shows top 50 |
| LLM hallucinating table names | Schema introspection gives exact allowlist; guard rejects others |
| LLM making up enum values | Schema includes real distinct values inline (e.g. `[values: overdue, paid]`) |

---

## Evaluation: [eval.py](file:///d:/c/usssssssss/app/backend/eval.py)

Runs 10 sample questions against `POST /chat/once`, prints a results table with intent, row count, latency, and a preview of the answer. Good for smoke-testing after LLM provider changes.

```bash
cd backend
./.venv/Scripts/python.exe eval.py
```

---

## Key Dependency Versions

| Package | Role |
|---|---|
| `fastapi` + `uvicorn` | Backend web server |
| `openai` | LLM client (any compatible provider) |
| `fastembed` | Local embedding model (no API key needed) |
| `sqlalchemy` + `psycopg` | DB access |
| `sqlglot` | SQL AST parsing for the guard |
| `pydantic-settings` | .env-based config |
| `numpy` | Cosine similarity for RAG |
| `next` 14 | Frontend framework |
| `zustand` | Frontend state management |
| `shadcn/ui` + `tailwind` | Frontend component library + styling |

---

## Extension Points

- **LLM provider**: edit `.env` only — no code changes needed
- **Add knowledge base docs**: insert rows into `knowledge_base_documents`, re-run `embed_kb.py`
- **Add DB tables**: they appear automatically in the next schema introspection (cache invalidated on restart)
- **Scale RAG**: swap the Python cosine similarity for pgvector if the KB grows large
- **Add streaming to eval**: `eval.py` already uses the blocking `/chat/once` endpoint
- **Docker**: `docker-compose.yml` is ready; just needs a healthy Docker engine
