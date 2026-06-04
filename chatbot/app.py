import uuid
import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import config
import db
import vectorstore as vs
from core.router import classify
from core.memory import memory

logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("app")


class ChatRequest(BaseModel):
    message: str
    session_id: str = ""


class ChatResponse(BaseModel):
    answer: str
    route: str
    session_id: str
    sql: str = ""
    sources: list = []
    time_ms: int = 0


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not config.DB_PATH.exists():
        log.info("Setting up database...")
        db.setup()
    else:
        log.info("Database exists")

    if not config.VECTORSTORE_PATH.exists():
        log.info("Building vector store...")
        vs.setup()
    else:
        log.info("Vector store exists")

    log.info("Server ready → http://localhost:8000")
    yield
    log.info("Server shutting down")


app = FastAPI(
    title="Real Estate AI Chatbot",
    version="2.0",
    description="Production-grade AI chatbot with NL2SQL and RAG",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

static_dir = config.BASE_DIR / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/")
async def home():
    return FileResponse(str(static_dir / "index.html"))


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "model": config.HF_MODEL,
        "version": "2.0",
    }


@app.post("/api/chat")
async def chat(req: ChatRequest):
    start = time.time()
    sid = req.session_id or str(uuid.uuid4())
    question = req.message.strip()

    if not question:
        return ChatResponse(answer="Please ask a question.", route="general", session_id=sid)

    log.info(f"[{sid[:8]}] Question: {question}")
    memory.add_user_message(sid, question)

    try:
        route = classify(question)
        log.info(f"[{sid[:8]}] Route: {route}")

        if route == "nl2sql":
            from features.nl2sql import ask
            result = ask(question)

        elif route == "rag":
            from features.rag import ask
            result = ask(question)

        else:
            from core.llm import get_chat
            from langchain_core.messages import HumanMessage, SystemMessage
            chat_llm = get_chat()
            history = memory.get_messages(sid)
            messages = [
                SystemMessage(content=(
                    "You are a helpful Real Estate ERP AI assistant. "
                    "You help with properties, tenants, leases, payments, "
                    "leads, maintenance, and company policies. "
                    "Be friendly, concise, and professional."
                )),
                *history[-4:],
                HumanMessage(content=question),
            ]
            response = chat_llm.invoke(messages)
            result = {"answer": response.content, "route": "general"}

        answer = result.get("answer", "I couldn't process that.")
        memory.add_ai_message(sid, answer)

        elapsed = int((time.time() - start) * 1000)
        log.info(f"[{sid[:8]}] Answered in {elapsed}ms via {route}")

        return ChatResponse(
            answer=answer,
            route=result.get("route", route),
            session_id=sid,
            sql=result.get("sql", ""),
            sources=result.get("sources", []),
            time_ms=elapsed,
        )

    except ValueError as e:
        log.error(f"Config error: {e}")
        return ChatResponse(answer=str(e), route="error", session_id=sid)

    except Exception as e:
        log.exception(f"Unexpected error: {e}")
        return ChatResponse(
            answer=f"Something went wrong: {e}",
            route="error",
            session_id=sid,
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
