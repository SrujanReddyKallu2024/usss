# Real Estate AI Chatbot — How to Run

A production-style chatbot where the AI decides how to answer every question:
- **NL2SQL** — writes SQL against the live database (no hardcoded queries)
- **RAG** — answers policy questions from the knowledge base (with sources)
- **Recommendation** — suggests properties matching a request
- **Smalltalk** — greetings / steering

Everything runs **locally**. The LLM is reached through the OpenAI SDK pointed at a
configurable endpoint (currently NVIDIA NIM, free). Swapping providers is env-only.

---

## What's already running
If this was just set up for you, three things are live:
- **Database**: local PostgreSQL 16 on port 5432 (conda env `recli`)
- **Backend API**: http://localhost:8000  (docs at /docs)
- **Frontend chat**: http://localhost:3000   <-- open this in your browser

Just open **http://localhost:3000** and start chatting.

---

## Start everything from scratch (e.g. after a reboot)

Open Git Bash in `D:\c\usssssssss\app`.

### 1. Database
```bash
bash run_local_db.sh           # starts Postgres, loads data (safe to re-run)
```

### 2. Backend (new terminal)
```bash
cd backend
./.venv/Scripts/python.exe -m ingest.embed_kb        # only needed once (fills doc vectors)
./.venv/Scripts/python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

### 3. Frontend (new terminal)
```bash
cd frontend
npm run dev                    # serves http://localhost:3000
```

---

## Try these questions
- Which tenants have overdue payments?
- Show leases expiring in the next 60 days
- What is total paid revenue this month?
- Recommend 2 bedroom properties in Austin under 2000
- What is the late payment policy?
- What is the lease renewal process?

Click **"Show details"** under any answer to see the exact SQL it wrote or the
policy sources it used.

---

## Switching the LLM provider (no code changes)
Edit `D:\c\usssssssss\.env`:
- **NVIDIA NIM (current):** `LLM_BASE_URL=https://integrate.api.nvidia.com/v1`, `LLM_CHAT_MODEL=meta/llama-3.3-70b-instruct`
- **OpenAI:** `LLM_BASE_URL=https://api.openai.com/v1`, `LLM_API_KEY=sk-...`, `LLM_CHAT_MODEL=gpt-4o`
- **Hugging Face:** `LLM_BASE_URL=https://router.huggingface.co/v1`, `LLM_API_KEY=hf_...`
Restart the backend after changing it.

For a snappier (slightly less accurate) demo, set `LLM_CHAT_MODEL=meta/llama-3.1-8b-instruct`.

---

## Check / test
```bash
cd backend
./.venv/Scripts/python.exe eval.py     # runs all 10 sample questions, prints a results table
```

## Docker option (when Docker is healthy)
A `docker-compose.yml` is included to run Postgres + backend in containers
(`docker compose up`). It was not used here because the local Docker engine was down,
so we run Postgres via conda instead — same schema and code.
