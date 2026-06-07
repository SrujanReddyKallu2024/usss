# Real Estate AI Chatbot

A simple, modern real estate chatbot application. It helps users query an operational database (via NL2SQL), retrieve company policies (via RAG), get property recommendations, or engage in smalltalk.

---

## Folder Structure

- **`frontend/`**: Next.js 14 Chat User Interface (running on port `3000`).
- **`backend/`**: FastAPI Server (running on port `8000`).
- **`data/`**: PostgreSQL database initialization files and CSV datasets.

---

## Setup & Running the App

### 1. Configuration
Create a `.env` file in the `app` folder (next to `docker-compose.yml` and `run_local_db.sh`):

```ini
LLM_BASE_URL=https://router.huggingface.co/v1
LLM_API_KEY=your_api_key_here
LLM_CHAT_MODEL=Qwen/Qwen2.5-Coder-32B-Instruct

EMBED_MODEL=BAAI/bge-small-en-v1.5

DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/real_estate
DATABASE_URL_READONLY=postgresql+psycopg://chatbot_ro:readonly@localhost:5432/real_estate
```

### 2. Database
Run the local database startup script:
```bash
# From the app/ directory
bash run_local_db.sh
```
This boots a PostgreSQL container, creates the database tables, configures a read-only user, and seeds the sample CSV files.

### 3. Backend Server
```bash
# From the app/backend directory
python -m venv .venv
.venv\Scripts\activate           # On Windows
# source .venv/bin/activate      # On macOS/Linux

pip install -r requirements.txt

# Run embedding ingestion for policy documents
python -m ingest.embed_kb

# Start the FastAPI backend
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

### 4. Frontend Chat UI
```bash
# From the app/frontend directory
npm install
npm run dev
```
Open **http://localhost:3000** in your browser.

---

## How Requests Flow End-to-End

### 1. The Initial Entry Point (Common to all requests)
1. **Frontend Input**: The user types a question and clicks send. The React UI (`frontend/app/page.tsx` & `frontend/components/composer.tsx`) invokes `sendMessage` in the chat store (`frontend/store/chat-store.ts`).
2. **API Request**: The store calls `streamChat` (`frontend/lib/chat-client.ts`), which posts the user query and session ID to the backend `/chat` endpoint.
3. **Backend API Route**: The FastAPI router (`backend/app/api/endpoints.py`) receives the request and calls `graph.answer_stream` (`backend/app/agents/graph.py`), returning a Server-Sent Events (SSE) stream.
4. **Memory Rewriting**: Inside `graph.py`, the orchestrator queries `memory.rewrite` (`backend/app/agents/memory.py`). If the message refers to past chat history (e.g., "how about Dallas?"), the LLM rewrites it to a standalone question (e.g., "Recommend properties in Dallas").
5. **Intent Routing**: The orchestrator asks `router.route` (`backend/app/agents/router.py`) to classify the question's intent. The LLM returns one of four categories: `nl2sql`, `rag`, `recommend`, or `smalltalk`.

---

### 2. The SQL Path (`nl2sql` or `recommend` intent)
If the user's intent is classified as database querying:
1. **Introspection**: The backend gets the live database schema from `schema_introspect.py` (`backend/app/services/schema_introspect.py`) so the LLM knows the current tables, column types, and allowed values.
2. **SQL Generation**: The query is sent to the LLM via `nl2sql.py` or `recommend.py` to produce a raw PostgreSQL SELECT statement.
3. **Security Check (SQL Guard)**: The raw SQL is validated by `clean_sql` (`backend/app/core/sql_guard.py`) using `sqlglot`. This ensures it is a single read-only `SELECT` query on allowed tables and caps/injects a `LIMIT` clause to avoid heavy DB load.
4. **Database Query**: The safe query is run against PostgreSQL via `run_readonly_sql` (`backend/app/core/db.py`) using a restricted read-only database user (`chatbot_ro`). If it fails, the error is fed back to the LLM to self-correct and try again.
5. **Table Rendering**: The orchestrator sends the intent, SQL statement, columns, and rows as a `meta` event down the stream. The frontend UI immediately renders the result inside an interactive `DataTable` component.
6. **Explanation**: The orchestrator asks the LLM to write a plain-English explanation of the database rows and streams it word-by-word to the chat bubble.
7. **Logging**: After the stream completes, the details (SQL query, latency, token count, status) are recorded in the `ai_usage_logs` table by `usage_log.py` (`backend/app/core/usage_log.py`).

---

### 3. The RAG Path (`rag` intent)
If the user asks a question about company policies or processes:
1. **Vector Embeddings**: The query is sent to `embeddings.py` (`backend/app/services/embeddings.py`), which creates a 384-dimensional vector locally using the `fastembed` library.
2. **Hybrid Retrieval**: In `rag.py` (`backend/app/services/rag.py`), the backend searches the `knowledge_base_documents` table:
   - **Semantic Search**: Compares cosine similarity between the query vector and document vectors.
   - **Full-Text Keyword Search**: Runs Postgres keyword search querying `ts_rank` matches.
   - **Reciprocal Rank Fusion (RRF)**: Merges the ranks of both searches to extract the top 3 most relevant policy pages.
3. **Citing Sources**: The orchestrator sends the list of selected policy source documents in a `meta` event. The UI displays them as clickable citation badges.
4. **Context Synthesis & Streaming**: The orchestrator builds a prompt containing the text contents of the retrieved documents and streams the LLM's synthesis word-by-word.
5. **Logging**: The transaction details are logged for administrative analytics.
