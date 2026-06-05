# Ask the LLM which answer path a question needs. No keyword rules here.
from app.agents.llm import chat_json

VALID_INTENTS = ["nl2sql", "rag", "recommend", "smalltalk"]

ROUTER_SYSTEM = """You are the router for a real estate assistant.
Classify the user's question into exactly one intent:

- "nl2sql": questions answered by querying the operational database
  (properties, tenants, leases, payments, leads, maintenance, analytics,
  totals, counts, risk, forecasting from historical data).
- "rag": questions about company POLICIES or PROCESSES answered from
  knowledge base documents (e.g. late payment policy, lease renewal process).
- "recommend": the user wants property RECOMMENDATIONS / suggestions that
  match criteria like city, bedrooms, budget, property type.
- "smalltalk": greetings, thanks, chit-chat, or vague messages needing
  clarification.

Reply with strict JSON only: {"intent": "<one of the four>"}."""


def route(question):
    """Return one of VALID_INTENTS for the question."""
    messages = [
        {"role": "system", "content": ROUTER_SYSTEM},
        {"role": "user", "content": question},
    ]
    data, tokens = chat_json(messages)
    intent = data.get("intent", "").strip().lower()
    if intent not in VALID_INTENTS:
        # Safe default: try a DB query.
        intent = "nl2sql"
    return intent, tokens
