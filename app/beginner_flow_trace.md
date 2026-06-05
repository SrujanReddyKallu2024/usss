# Beginner's Guide: What Happens When You Type "list all properties above $2000 rent"

> Follow this like a story. Every numbered step is a real thing that happens, in order.

---

## Step 0 — Before You Even Type Anything (One-time setup)

Before the chatbot can answer anything, two things must already be running:

### The Database (PostgreSQL)
You ran `bash run_local_db.sh` once. That script:
1. Created a Postgres database called `real_estate`
2. Ran `data/init/01_schema.sql` → created tables like `properties`, `tenants`, `payments`
3. Loaded CSV files (your actual data) into those tables
4. Created a special read-only user called `chatbot_ro` that can only SELECT, never INSERT/UPDATE/DELETE

Right now the `properties` table looks like this inside Postgres:

```
property_id | property_name       | city    | monthly_rent | bedrooms | status
------------+---------------------+---------+--------------+----------+--------
1           | Sunset Apartments   | Austin  | 2500.00      | 2        | available
2           | Oak Street House    | Dallas  | 1800.00      | 3        | available
3           | Maple Tower         | Houston | 3200.00      | 1        | available
...
```

### The Backend (FastAPI)
You ran `uvicorn main:app --port 8000`. This Python server is now waiting for requests.

### The Frontend (Next.js)
You ran `npm run dev`. This is the browser UI running at http://localhost:3000.

---

## Step 1 — You Type in the Browser

You open http://localhost:3000, see the chat box, and type:

```
list all properties above $2000 rent
```

Then press **Enter**.

**File involved:** `frontend/components/composer.tsx`

This component captures your keypress and calls:
```typescript
store.sendMessage("list all properties above $2000 rent")
```

---

## Step 2 — Frontend Creates Two Messages Instantly

**File:** `frontend/store/chat-store.ts`

The `sendMessage()` function runs immediately and does two things:

1. Creates a **user message** and adds it to the list → you see your own message appear on the right side of the screen (in blue)

2. Creates an **empty assistant message** with `streaming: true` → you see "Thinking..." appear on the left side with a blinking cursor

The chat now shows:
```
[You]       list all properties above $2000 rent
[Bot]       Thinking...  ▌
```

---

## Step 3 — Frontend Sends HTTP Request to Backend

**File:** `frontend/lib/chat-client.ts`

The frontend immediately sends a POST request:

```
POST http://localhost:8000/chat
Body: {
  "message": "list all properties above $2000 rent",
  "session_id": "abc-123-xyz"   ← stored in your browser's localStorage
}
```

The connection stays **open** — it's a streaming connection (Server-Sent Events / SSE). Think of it like a radio station: the backend keeps broadcasting, the frontend keeps listening.

---

## Step 4 — Backend Receives the Request

**File:** `backend/main.py` (line 38)

```python
@app.post("/chat")
def chat(req: ChatRequest):
    def event_stream():
        for event in graph.answer_stream(req.session_id, req.message):
            yield _sse(event)
    return StreamingResponse(event_stream(), media_type="text/event-stream")
```

`main.py` doesn't do the thinking itself. It immediately hands off to `graph.answer_stream()` and streams back whatever it produces.

---

## Step 5 — Memory Check (Is this a follow-up question?)

**File:** `backend/agent/memory.py`

```python
question, tokens = memory.rewrite(session_id, message)
```

The memory module asks: *"Has this session_id asked anything before?"*

- If **no prior history** (your first question): the question stays as-is → `"list all properties above $2000 rent"`
- If **yes there's history** (e.g. you previously asked "show me Austin properties" and now say "sort them by price"): the LLM rewrites the follow-up into a standalone question → `"Sort Austin properties by price"`

**Where is this history stored?**
In a Python dictionary in memory (RAM), keyed by session_id:
```python
_history = {
    "abc-123-xyz": [
        {"role": "user", "content": "list all properties above $2000 rent"},
        {"role": "assistant", "content": "Here are the properties..."}
    ]
}
```
It's **not in the database**. If you restart the backend, history is gone. It keeps only the last 10 turns.

---

## Step 6 — The Router Decides: What Kind of Question Is This?

**File:** `backend/agent/router.py`

This calls the LLM (your configured model — e.g. Llama-3.3-70B on NVIDIA NIM) with a special prompt:

```
SYSTEM: You are the router for a real estate assistant.
        Classify the question into one of:
        - "nl2sql": questions about database data
        - "rag": questions about policies/documents
        - "recommend": property recommendations
        - "smalltalk": greetings/chit-chat
        Reply with strict JSON only: {"intent": "<one of the four>"}

USER: list all properties above $2000 rent
```

The LLM responds:
```json
{"intent": "nl2sql"}
```

> ℹ️ **Why nl2sql?** Because this is asking for data from the database, not a policy doc, not a recommendation with criteria matching — it's a straight data query.

---

## Step 7 — Schema Is Fetched (or Loaded from Cache)

**File:** `backend/services/schema_introspect.py`

Before the LLM can write SQL, it needs to know what tables and columns exist.

```python
schema = get_schema_string()
```

**First time this runs:**
- Connects to Postgres (as the `postgres` app user)
- Reads `information_schema.columns` → gets all table names and column names
- For text columns with few distinct values (≤25), it also queries for those values
- Builds a string like this:

```
TABLE properties:
  property_id integer
  property_name character varying
  property_type character varying [values: apartment, house, condo, townhouse]
  city character varying [values: Austin, Dallas, Houston, Phoenix, Seattle]
  address text
  monthly_rent numeric
  status character varying [values: available, rented, maintenance]
  bedrooms integer
  bathrooms numeric
  sqft integer
  amenities text
  latitude numeric
  longitude numeric
  created_at timestamp

TABLE tenants:
  tenant_id integer
  ...

FOREIGN KEYS:
  leases.tenant_id -> tenants.tenant_id
  leases.property_id -> properties.property_id
  ...
```

**Caching:** This is stored in a Python variable `_schema_cache`. Every subsequent call skips the DB query and returns the cached string instantly. It's only refreshed if you call `refresh_schema()` or restart the server.

---

## Step 8 — LLM Writes the SQL

**File:** `backend/agent/nl2sql.py` (the `generate_and_run()` function)

The code calls the LLM again with this prompt:

```
SYSTEM: You write PostgreSQL SELECT queries for a real estate database.
        Rules:
        - Use ONLY the tables and columns from the schema given.
        - Use the real column VALUES shown in [values: ...]
        - Output a SINGLE read-only SELECT statement. No INSERT/UPDATE/DELETE/DDL.
        - Always reply with strict JSON: {"sql": "<the select>"}

USER: Database schema:
      TABLE properties:
        property_id integer
        property_name character varying
        monthly_rent numeric
        status character varying [values: available, rented, maintenance]
        ...

      Question: list all properties above $2000 rent
```

The LLM responds:
```json
{
  "sql": "SELECT property_name, city, monthly_rent, bedrooms, status FROM properties WHERE monthly_rent > 2000 ORDER BY monthly_rent"
}
```

---

## Step 9 — SQL Guard Checks the SQL

**File:** `backend/services/sql_guard.py`

This is a **safety check** before anything runs. It uses a library called `sqlglot` to parse the SQL into a tree and check:

| Check | What it does |
|---|---|
| Is it one statement? | Rejects `SELECT ...; DROP TABLE ...` |
| Is the top node a SELECT? | Rejects INSERT, UPDATE, DELETE, DDL |
| Are all tables in the allowlist? | Rejects made-up table names |
| Does it have a LIMIT? | Injects `LIMIT 200` if missing |

For our SQL:
```sql
SELECT property_name, city, monthly_rent, bedrooms, status 
FROM properties 
WHERE monthly_rent > 2000 
ORDER BY monthly_rent
```

✅ All checks pass. The guard adds `LIMIT 200` since there's none:
```sql
SELECT property_name, city, monthly_rent, bedrooms, status 
FROM properties 
WHERE monthly_rent > 2000 
ORDER BY monthly_rent 
LIMIT 200
```

---

## Step 10 — SQL Is Executed on the Database

**File:** `backend/db.py` (the `run_readonly_sql()` function)

```python
columns, rows = run_readonly_sql(safe_sql)
```

This connects to Postgres as the **`chatbot_ro` user** (read-only role). It first sets a timeout:

```sql
SET LOCAL statement_timeout = 5000  -- 5 seconds max
```

Then runs your SQL. Postgres executes it and returns:

```
columns: ["property_name", "city", "monthly_rent", "bedrooms", "status"]
rows: [
  {"property_name": "Maple Tower",     "city": "Houston", "monthly_rent": 3200, "bedrooms": 1, "status": "available"},
  {"property_name": "Sunset Apts",     "city": "Austin",  "monthly_rent": 2500, "bedrooms": 2, "status": "available"},
  {"property_name": "Lakeside Condos", "city": "Seattle", "monthly_rent": 2200, "bedrooms": 3, "status": "rented"},
]
```

> **What if SQL fails?** The error message is fed back to the LLM ("Your previous SQL failed: ...Fix it.") and it retries up to 2 more times. This is the **self-correction loop**.

---

## Step 11 — Backend Sends the First Event to the Frontend (meta)

**File:** `backend/agent/graph.py`

Before streaming the text answer, the backend immediately sends a **meta event** to the frontend:

```json
{
  "type": "meta",
  "intent": "nl2sql",
  "sql": "SELECT property_name, city, monthly_rent... LIMIT 200",
  "sources": [],
  "row_count": 3,
  "columns": ["property_name", "city", "monthly_rent", "bedrooms", "status"],
  "rows": [
    ["Maple Tower", "Houston", 3200, 1, "available"],
    ["Sunset Apts", "Austin", 2500, 2, "available"],
    ["Lakeside Condos", "Seattle", 2200, 3, "rented"]
  ]
}
```

The frontend receives this immediately. The store patches the assistant message:
```
intent = "nl2sql"
sql = "SELECT ..."
rows = [[...], [...], [...]]
```

The UI now shows the **intent badge** "nl2sql" above the message.

---

## Step 12 — LLM Streams the Text Answer

**File:** `backend/agent/nl2sql.py` (`build_messages_for_stream()`) → `backend/agent/llm.py` (`chat_stream()`)

Now the backend builds another LLM call — this time to *explain the rows in plain English*:

```
SYSTEM: You explain SQL query results to a real estate manager in clear, 
        concise plain English. Summarize the data; do not invent numbers.

USER: Question: list all properties above $2000 rent

      The query returned 3 row(s) in total. Below is a sample of up to 30.
      Data: {"columns": [...], "sample_rows": [...]}

      Give a short, direct answer.
```

The LLM's response streams back **token by token** (word by word). For each chunk, the backend sends:

```json
{ "type": "token", "text": "Here" }
{ "type": "token", "text": " are" }
{ "type": "token", "text": " the" }
{ "type": "token", "text": " 3" }
{ "type": "token", "text": " properties..." }
```

---

## Step 13 — Frontend Appends Each Token in Real-Time

**File:** `frontend/store/chat-store.ts`

```typescript
case "token":
    appendToken(event.text);  // adds the chunk to message.text
    break;
```

So the user sees the answer **appear word by word** in the chat bubble, just like ChatGPT.

---

## Step 14 — Backend Sends the Done Event

```json
{ "type": "done", "latency_ms": 2341 }
```

The frontend:
- Sets `streaming: false` (removes the blinking cursor)
- Shows `2341 ms` below the message
- Re-enables the input box

---

## Step 15 — Backend Saves to Memory and Logs

**File:** `backend/agent/memory.py`
```python
memory.add_turn(session_id, "assistant", answer_text)
```
The assistant's full answer is added to the in-memory history dict.

**File:** `backend/services/usage_log.py`
```python
log_usage(session_id, intent="nl2sql", user_prompt="list all...", 
          ai_response="Here are the 3 properties...", sql_text="SELECT...", 
          tokens_used=450, latency_ms=2341, status="ok")
```
This writes one row to the `ai_usage_logs` table in Postgres. You can query it later to see what the bot did and how long it took.

---

## Step 16 — What the User Sees at the End

```
[You]    list all properties above $2000 rent

[🤖 nl2sql]
         Here are the 3 properties with a monthly rent above $2000:
         - Maple Tower (Houston) — $3,200/mo, 1 bed, available
         - Sunset Apartments (Austin) — $2,500/mo, 2 bed, available
         - Lakeside Condos (Seattle) — $2,200/mo, 3 bed, rented

         [Show details ▼]     ← click this to see the SQL + data table

         2341 ms
```

Clicking "Show details":
- Shows the exact SQL that was written and run
- Shows the raw data table with columns and rows

---

## Now — What About Embeddings & Vectors?

> ❗ Embeddings are **NOT used** for this question. They're only used for **RAG** (policy questions).

But here's how they work for something like "What is the late payment policy?":

### What is an embedding?
A vector = a list of 384 numbers that represents the *meaning* of a sentence.

```
"late payment policy"  →  [0.023, -0.142, 0.891, 0.034, ...]  (384 numbers)
"overdue rent fee"     →  [0.031, -0.138, 0.884, 0.029, ...]  (very similar!)
"bedrooms in Austin"   →  [0.821, 0.342, -0.211, 0.654, ...]  (very different)
```

Similar meaning = similar numbers = small "angle" between vectors (high cosine similarity).

### Where are vectors stored?

In the `knowledge_base_documents` table in Postgres:

```sql
CREATE TABLE knowledge_base_documents (
    document_id INT,
    title VARCHAR(200),
    category VARCHAR(80),
    content TEXT,
    embedding double precision[]   -- 384 numbers stored right here in Postgres
);
```

No special vector database needed. Just a normal array column.

### How do vectors get INTO the database?

You ran this once:
```bash
python -m ingest.embed_kb
```

**File:** `backend/ingest/embed_kb.py`

This script:
1. Reads every row from `knowledge_base_documents` (the text content)
2. For each doc, calls `embed_text(title + content)`
3. `embed_text` runs the **fastembed** model locally on your CPU → produces 384 numbers
4. UPDATEs the `embedding` column in Postgres with those numbers

No internet needed. The model (`BAAI/bge-small-en-v1.5`) runs 100% on your machine.

### How does RAG search work?

**File:** `backend/agent/rag.py`

When you ask "What is the late payment policy?":

1. Embed your question → 384 numbers
2. Load ALL documents + their embeddings from Postgres
3. For each document, compute **cosine similarity** between your question vector and the document vector (using numpy in Python)
4. Sort by similarity score, take top 3
5. Put those 3 document contents into the LLM prompt
6. LLM answers using only those docs

```
Your question vector:   [0.023, -0.142, 0.891, ...]
Doc 1 "Late Fees":      [0.031, -0.138, 0.884, ...]  → similarity: 0.97 ✅ TOP MATCH
Doc 2 "Lease Renewal":  [0.412,  0.221, 0.123, ...]  → similarity: 0.34 ❌
Doc 3 "Maintenance":    [0.654,  0.099, 0.021, ...]  → similarity: 0.21 ❌
```

---

## Summary: Every File Involved for "list all properties above $2000 rent"

```
You type in browser
    │
    ▼ frontend/components/composer.tsx         ← captures Enter key
    ▼ frontend/store/chat-store.ts             ← adds messages to UI state
    ▼ frontend/lib/chat-client.ts              ← sends POST /chat to backend
    │
    ▼ backend/main.py                          ← receives request, starts streaming
    ▼ backend/agent/graph.py                   ← orchestrates everything
    ▼ backend/agent/memory.py                  ← checks/rewrites follow-ups
    ▼ backend/agent/router.py + llm.py         ← LLM decides: "nl2sql"
    ▼ backend/services/schema_introspect.py    ← gets table/column info (cached)
    ▼ backend/agent/nl2sql.py + llm.py         ← LLM writes SQL
    ▼ backend/services/sql_guard.py            ← validates SQL is safe
    ▼ backend/db.py                            ← runs SQL on Postgres (chatbot_ro)
    ▼ backend/agent/graph.py                   ← sends meta event (SQL + rows)
    ▼ backend/agent/nl2sql.py + llm.py         ← LLM streams text explanation
    ▼ backend/agent/memory.py                  ← saves answer to session history
    ▼ backend/services/usage_log.py            ← writes log row to ai_usage_logs
    │
    ▼ frontend/store/chat-store.ts             ← receives meta → patches message
    ▼ frontend/store/chat-store.ts             ← receives tokens → appends text live
    ▼ frontend/components/message-bubble.tsx   ← renders the message
    ▼ frontend/components/details-panel.tsx    ← "Show details" → shows SQL + table
```

