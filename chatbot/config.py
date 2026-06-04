import core.ssl_fix  # noqa: F401 — must be first
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
CSV_DIR = BASE_DIR.parent

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3.5:9b")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")

HF_TOKEN = os.getenv("HUGGINGFACEHUB_API_TOKEN", "")
HF_MODEL = os.getenv("HF_MODEL", "mistralai/Mistral-7B-Instruct-v0.3")

LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.1"))
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "1024"))

DB_PATH = DATA_DIR / "erp.db"
DB_URI = f"sqlite:///{DATA_DIR / 'erp.db'}"
VECTORSTORE_PATH = DATA_DIR / "vectorstore.json"

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
