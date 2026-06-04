import logging
from config import (
    LLM_PROVIDER, OLLAMA_MODEL, OLLAMA_URL,
    HF_TOKEN, HF_MODEL, LLM_MAX_TOKENS, LLM_TEMPERATURE,
)

log = logging.getLogger(__name__)

_chat = None


def get_chat():
    global _chat
    if _chat is not None:
        return _chat

    if LLM_PROVIDER == "ollama":
        from langchain_ollama import ChatOllama
        log.info(f"Using Ollama: {OLLAMA_MODEL} at {OLLAMA_URL}")
        _chat = ChatOllama(
            model=OLLAMA_MODEL,
            base_url=OLLAMA_URL,
            temperature=LLM_TEMPERATURE,
            num_predict=LLM_MAX_TOKENS,
        )

    elif LLM_PROVIDER == "huggingface":
        if not HF_TOKEN:
            raise ValueError("HUGGINGFACEHUB_API_TOKEN not set in .env")
        from langchain_huggingface import HuggingFaceEndpoint, ChatHuggingFace
        log.info(f"Using HuggingFace: {HF_MODEL}")
        endpoint = HuggingFaceEndpoint(
            repo_id=HF_MODEL,
            task="text-generation",
            max_new_tokens=LLM_MAX_TOKENS,
            temperature=LLM_TEMPERATURE,
            do_sample=LLM_TEMPERATURE > 0,
            repetition_penalty=1.03,
            huggingfacehub_api_token=HF_TOKEN,
        )
        _chat = ChatHuggingFace(llm=endpoint)

    else:
        raise ValueError(f"Unknown LLM_PROVIDER: {LLM_PROVIDER}")

    log.info("LLM ready")
    return _chat
