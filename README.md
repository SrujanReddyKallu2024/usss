# Real Estate AI Chatbot

A production-style, fully local AI chatbot for real estate management. Ask
natural-language questions and the backend decides *how* to answer — by writing
SQL against the live database (**NL2SQL**), searching policy documents (**RAG**),
recommending listings (**recommend**), or just chatting (**smalltalk**).

No keyword routing, no hardcoded SQL, no hardcoded enum values — the LLM does the
deciding, guarded by a read-only DB role and a SQL validator.

- **Frontend:** Next.js 14 chat UI (port 3000)
- **Backend:** FastAPI with SSE streaming (port 8000)
- **Database:** PostgreSQL 16 (port 5432)
- **LLM:** any OpenAI-compatible provider (NVIDIA NIM, OpenAI, Hugging Face) — swappable via `.env` only
- **Embeddings:** `fastembed` (`BAAI/bge-small-en-v1.5`), 384-dim, runs locally — no API key

> The full layout and end-to-end request flow are documented in
> [ARCHITECTURE.md](ARCHITECTURE.md).

---

## Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL 16 (the helper script boots a local instance via a conda `recli` env;
  any local Postgres on port 5432 also works)

---

## 1. Configure the environment

Create `app/.env` (read by the backend; the LLM provider is set here):

```ini
LLM_BASE_URL=https://integrate.api.nvidia.com/v1
LLM_API_KEY=your-key-here
LLM_CHAT_MODEL=meta/llama-3.3-70b-instruct

EMBED_MODEL=BAAI/bge-small-en-v1.5

DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/real_estate
DATABASE_URL_READONLY=postgresql+psycopg://chatbot_ro:readonly@localhost:5432/real_estate
```

Switching providers is config-only — no code changes:

| Provider     | `LLM_BASE_URL`                          | `LLM_CHAT_MODEL` (example)        |
|--------------|------------------------------------------|-----------------------------------|
| NVIDIA NIM   | `https://integrate.api.nvidia.com/v1`    | `meta/llama-3.3-70b-instruct`     |
| OpenAI       | `https://api.openai.com/v1`              | `gpt-4o`                          |
| Hugging Face | `https://router.huggingface.co/v1`       | `Qwen/Qwen2.5-Coder-32B-Instruct` |

---

## 2. Database

Boot Postgres and load the schema + seed CSVs (safe to re-run):

```bash
cd app
bash run_local_db.sh
```

This creates the `real_estate` database, all tables, the read-only `chatbot_ro`
role, and loads the CSVs from `app/data/csv/`.

---

## 3. Backend

```bash
cd app/backend
python -m venv .venv
.venv\Scripts\activate            # Windows  (use: source .venv/bin/activate on macOS/Linux)
pip install -r requirements.txt

# One-time: embed the knowledge-base documents for RAG.
python -m ingest.embed_kb

# Start the API (docs at http://localhost:8000/docs).
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

---

## 4. Frontend

```bash
cd app/frontend
npm install
npm run dev
```

Open **http://localhost:3000** and start chatting.

---

## Try these questions

- Which tenants have overdue payments?
- Show leases expiring in the next 60 days
- What is total paid revenue this month?
- Recommend 2 bedroom properties in Austin under 2000
- What is the late payment policy?

Click **"Show details"** under any answer to see the exact SQL it ran or the
policy sources it cited.

---

## Testing

```bash
cd app/backend
python eval.py     # runs the sample questions and prints a results table
pytest             # integration tests (skip cleanly if DB/LLM are unreachable)
```

---

## Docker (optional)

`app/docker-compose.yml` runs Postgres + backend in containers:

```bash
cd app
docker compose up
```
