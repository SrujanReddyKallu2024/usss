# Real Estate AI Chatbot

A production-style, local AI chatbot for real estate management. It allows users to ask natural-language questions and dynamically routes them to query the database (NL2SQL), search policy documents (RAG), recommend listings, or carry out smalltalk.

---

## Architecture Overview

```
                   +------------------------+
                   |  Frontend (Next.js)    |
                   |  Port 3000             |
                   +-----------+------------+
                               |
                               | POST /chat (SSE Stream)
                               v
                   +------------------------+
                   |  Backend (FastAPI)     |
                   |  Port 8000             |
                   +-----------+------------+
                               |
         +---------------------+---------------------+
         | (Operational Queries)                     | (Policy Docs)
         v                                           v
+--------+---------------+                  +--------+---------------+
|  PostgreSQL Database   |                  |  FastEmbed (Local NLP)  |
|  Port 5432             |                  |  384-dim Embeddings    |
+------------------------+                  +------------------------+
```

---

## Folder Structure

```
.
├── backend/
│   ├── app/                    # Production codebase
│   │   ├── api/                # FastAPI router endpoints
│   │   ├── core/               # Database, configuration, security, and logging
│   │   ├── services/           # Embeddings, schema cache, and Hybrid RAG
│   │   └── agents/             # Chat graph, intent routing, memory, SQL/recommender logic
│   ├── ingest/                 # Document ingestion script
│   ├── tests/                  # Integration test suite
│   ├── main.py                 # FastAPI app entrypoint wrapper
│   ├── eval.py                 # Evaluation suite
│   └── requirements.txt        # Python dependencies
├── frontend/                   # Next.js 14 Web application
├── data/                       # Initial database schema, seed CSVs, and load scripts
└── run_local_db.sh             # Shell script to boot the PostgreSQL database
```

---

## How to Run (Step-by-Step)

### 1. Database Setup
Boot the local PostgreSQL database and load the schema and properties/tenants seed data:
```bash
./run_local_db.sh
```

### 2. Backend Setup
1. Open a new terminal in the `backend/` directory.
2. Initialize embeddings for the policy documents:
   ```bash
   ./.venv/Scripts/python.exe -m ingest.embed_kb
   ```
3. Run the FastAPI development server:
   ```bash
   ./.venv/Scripts/python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
   ```

### 3. Frontend Setup
1. Open a new terminal in the `frontend/` directory.
2. Run the Next.js development server:
   ```bash
   npm run dev
   ```
3. Open **[http://localhost:3000](http://localhost:3000)** in your browser and start chatting!

---

## Verification & Testing

To run the full test suite and verify that all agents (NL2SQL, RAG, recommendations) are functioning correctly:
```bash
cd backend
./.venv/Scripts/python.exe -m pytest
```

To run a quick evaluation report printing out latency and accuracy stats:
```bash
cd backend
./.venv/Scripts/python.exe eval.py
```
