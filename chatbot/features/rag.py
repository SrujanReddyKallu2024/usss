import logging
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from core.llm import get_chat
import vectorstore as vs

log = logging.getLogger(__name__)

ANSWER_PROMPT = ChatPromptTemplate.from_messages([
    ("system",
     "You are a Real Estate ERP policy assistant.\n"
     "Answer the question using ONLY the provided documents.\n"
     "If the answer is not in the documents, say so clearly.\n"
     "Be concise and professional. Cite which document you used."),
    ("human",
     "Policy Documents:\n{context}\n\n"
     "Question: {question}"),
])


def ask(question):
    chat = get_chat()
    parser = StrOutputParser()

    results = vs.search(question, k=3)
    log.info(f"RAG search returned {len(results)} docs for: {question[:50]}")

    if not results:
        return {
            "answer": "I couldn't find relevant policy documents for that question.",
            "sources": [],
            "route": "rag",
        }

    context = "\n\n---\n\n".join(
        f"📄 {r['title']} (Category: {r['category']})\n{r['content']}"
        for r in results
    )

    sources = list(set(r["title"] for r in results))

    chain = ANSWER_PROMPT | chat | parser
    answer = chain.invoke({"context": context, "question": question})

    log.info(f"RAG sources used: {sources}")

    return {
        "answer": answer,
        "sources": sources,
        "route": "rag",
    }
