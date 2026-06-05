# FastAPI app exposing the chatbot over HTTP (SSE streaming + a blocking endpoint).
import json
import decimal
import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from agent import graph

app = FastAPI(title="Real Estate AI Chatbot")

# Allow the frontend dev server to call us.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"


@app.get("/health")
def health():
    return {"status": "ok"}


class _Encoder(json.JSONEncoder):
    """Handle types that come back from PostgreSQL but aren't JSON-native."""
    def default(self, obj):
        if isinstance(obj, decimal.Decimal):
            return float(obj)
        if isinstance(obj, (datetime.date, datetime.datetime)):
            return obj.isoformat()
        return super().default(obj)


def _sse(event):
    """Format one event dict as a Server-Sent Events 'data:' line."""
    return f"data: {json.dumps(event, cls=_Encoder)}\n\n"


@app.post("/chat")
def chat(req: ChatRequest):
    """Stream the answer as SSE: one meta, many tokens, then done."""
    def event_stream():
        for event in graph.answer_stream(req.session_id, req.message):
            yield _sse(event)

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.post("/chat/once")
def chat_once(req: ChatRequest):
    """Blocking answer as plain JSON, handy for tests and eval."""
    result = graph.answer(req.session_id, req.message)
    payload = {
        "answer": result["answer"],
        "intent": result["intent"],
        "sql": result["sql"],
        "sources": result["sources"],
        "row_count": result["row_count"],
        "columns": result["columns"],
        "rows": result["rows"],
        "latency_ms": result["latency_ms"],
    }
    return JSONResponse(content=json.loads(json.dumps(payload, cls=_Encoder)))
