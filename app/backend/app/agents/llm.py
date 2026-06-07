import json
import time

from openai import OpenAI

from app.core.config import settings

client = OpenAI(base_url=settings.LLM_BASE_URL, api_key=settings.LLM_API_KEY)

MAX_TRIES = 4
BACKOFF_SECONDS = [2, 4, 8]


def _create(**kwargs):
    """Call the model with simple exponential-backoff retries on transient errors."""
    last_error = None
    for attempt in range(MAX_TRIES):
        try:
            return client.chat.completions.create(**kwargs)
        except Exception as e:
            last_error = e
            text = str(e).lower()
            transient = any(s in text for s in
                            ["429", "rate", "timeout", "timed out", "503", "502", "overloaded", "connection"])
            if attempt < MAX_TRIES - 1 and transient:
                time.sleep(BACKOFF_SECONDS[attempt])
                continue
            raise
    raise last_error


def chat(messages, temperature=0.2, force_json=False):
    """Call the chat model and return (text, tokens_used)."""
    kwargs = {
        "model": settings.LLM_CHAT_MODEL,
        "messages": messages,
        "temperature": temperature,
    }
    if force_json:
        kwargs["response_format"] = {"type": "json_object"}
    response = _create(**kwargs)
    text = response.choices[0].message.content or ""
    tokens = 0
    if response.usage:
        tokens = response.usage.total_tokens or 0
    return text, tokens


def chat_json(messages, temperature=0.0):
    """Call the model expecting JSON and return (parsed_dict, tokens_used)."""
    text, tokens = chat(messages, temperature=temperature, force_json=True)
    data = _parse_json(text)
    return data, tokens


def chat_stream(messages, temperature=0.3):
    """Stream the model answer. Yields text chunks; returns nothing."""
    stream = _create(
        model=settings.LLM_CHAT_MODEL,
        messages=messages,
        temperature=temperature,
        stream=True,
    )
    for chunk in stream:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta
        if delta and delta.content:
            yield delta.content


def _parse_json(text):
    """Best-effort JSON parse that tolerates code fences or extra prose."""
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
        text = text.strip()
    try:
        return json.loads(text)
    except Exception:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start:end + 1])
            except Exception:
                pass
    return {}
