import logging
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from core.llm import get_chat

log = logging.getLogger(__name__)

CLASSIFY_PROMPT = ChatPromptTemplate.from_messages([
    ("system",
     "You are an intent classifier for a Real Estate ERP system. "
     "Classify the user's question into exactly ONE category.\n\n"
     "Categories:\n"
     "- DATA — questions about properties, tenants, leases, payments, leads, "
     "maintenance requests, CRM activities, numbers, lists, counts, totals, "
     "comparisons, recommendations, risk analysis, forecasting, revenue\n"
     "- POLICY — questions about company rules, procedures, policies, guidelines, "
     "processes, late payment rules, lease renewal process, move-in checklist, "
     "pet policy, noise policy, insurance, eviction process\n"
     "- GENERAL — greetings, help requests, thanks, or anything not about "
     "real estate data or company policies\n\n"
     "Respond with ONLY the category name. Nothing else."),
    ("human", "{question}"),
])

classify_chain = None


def get_chain():
    global classify_chain
    if classify_chain is not None:
        return classify_chain
    classify_chain = CLASSIFY_PROMPT | get_chat() | StrOutputParser()
    return classify_chain


def classify(question):
    try:
        chain = get_chain()
        result = chain.invoke({"question": question})
        category = result.strip().upper()
        log.info(f"Router: '{question[:50]}...' → {category}")

        if "DATA" in category:
            return "nl2sql"
        elif "POLICY" in category:
            return "rag"
        else:
            return "general"

    except Exception as e:
        log.warning(f"Router LLM failed, using fallback: {e}")
        return _fallback_classify(question)


def _fallback_classify(question):
    q = question.lower()
    policy_hints = ["policy", "procedure", "process", "rule", "guideline",
                    "eviction", "inspection", "move-in", "move in"]
    for kw in policy_hints:
        if kw in q:
            return "rag"

    data_hints = ["property", "tenant", "lease", "payment", "lead",
                  "maintenance", "how many", "show", "list", "count",
                  "total", "average", "which", "rent", "available"]
    for kw in data_hints:
        if kw in q:
            return "nl2sql"

    return "general"
