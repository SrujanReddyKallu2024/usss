# Upgraded Hybrid RAG Service.
# Implements semantic and full-text keyword search merged via Reciprocal Rank Fusion (RRF).
import numpy as np
from sqlalchemy import text

from app.core.db import app_engine
from app.services.embeddings import embed_text
from app.agents.llm import chat

TOP_K = 3
RAG_SYSTEM = """You answer real estate policy questions using ONLY the provided
context documents. If the answer is not in the context, say you don't have that
policy. Be concise and do not invent details."""


def _cosine_similarity(v1, v2):
    v1 = np.asarray(v1, dtype=float)
    v2 = np.asarray(v2, dtype=float)
    norm = np.linalg.norm(v1) * np.linalg.norm(v2)
    return float(np.dot(v1, v2) / norm) if norm > 0 else 0.0


def retrieve(query, limit=TOP_K, semantic_weight=0.7, keyword_weight=0.3, context_window=0):
    query_vector = embed_text(query)
    try:
        with app_engine.connect() as conn:
            rows = conn.execute(text(
                "SELECT document_id, title, category, content, embedding "
                "FROM knowledge_base_documents WHERE embedding IS NOT NULL"
            )).fetchall()
    except Exception as e:
        print(f"RAG DB error: {e}")
        return []

    semantic_list = []
    for row in rows:
        score = _cosine_similarity(query_vector, row[4])
        semantic_list.append((score, {
            "id": row[0],
            "title": row[1],
            "category": row[2],
            "content": row[3],
            "embedding": row[4],
            "chunk_index": 0,
            "total_chunks": 1
        }))
    
    semantic_list.sort(key=lambda x: x[0], reverse=True)
    semantic_docs = [item[1] for item in semantic_list]

    keyword_docs = []
    try:
        with app_engine.connect() as conn:
            keyword_rows = conn.execute(text(
                """
                SELECT document_id, title, category, content, embedding,
                       ts_rank(to_tsvector('english', coalesce(title, '') || ' ' || coalesce(content, '')), plainto_tsquery('english', :query)) as rank
                FROM knowledge_base_documents
                WHERE to_tsvector('english', coalesce(title, '') || ' ' || coalesce(content, '')) @@ plainto_tsquery('english', :query)
                ORDER BY rank DESC
                """
            ), {"query": query}).fetchall()
            
            for row in keyword_rows:
                keyword_docs.append({
                    "id": row[0],
                    "title": row[1],
                    "category": row[2],
                    "content": row[3],
                    "embedding": row[4],
                    "keyword_rank": row[5],
                    "chunk_index": 0,
                    "total_chunks": 1
                })
    except Exception:
        # FTS parsing fails on special characters; fall back to semantic search
        pass

    # Reciprocal Rank Fusion (RRF)
    k = 60
    rrf_scores = {}
    docs_by_id = {}

    for rank, doc in enumerate(semantic_docs, start=1):
        doc_id = doc["id"]
        rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + semantic_weight / (k + rank)
        docs_by_id[doc_id] = doc

    for rank, doc in enumerate(keyword_docs, start=1):
        doc_id = doc["id"]
        rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + keyword_weight / (k + rank)
        if doc_id not in docs_by_id:
            docs_by_id[doc_id] = doc

    ranked_ids = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)
    results = [docs_by_id[doc_id] for doc_id in ranked_ids[:limit]]

    if context_window > 0 and results:
        results = _add_context(results, context_window)

    return results


def _add_context(docs, window):
    enriched = []
    for doc in docs:
        doc_id = doc["id"]
        title = doc["title"]
        
        try:
            with app_engine.connect() as conn:
                columns = conn.execute(text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_schema = 'public' AND table_name = 'knowledge_base_documents' "
                    "AND column_name IN ('chunk_index', 'total_chunks')"
                )).fetchall()
                col_names = {r[0] for r in columns}
                
                if "chunk_index" in col_names and "total_chunks" in col_names:
                    info = conn.execute(text(
                        "SELECT chunk_index, total_chunks FROM knowledge_base_documents WHERE document_id = :id"
                    ), {"id": doc_id}).fetchone()
                    
                    if info:
                        idx, total = info[0], info[1]
                        start = max(0, idx - window)
                        end = min(total - 1, idx + window)
                        
                        chunks = conn.execute(text(
                            "SELECT content FROM knowledge_base_documents "
                            "WHERE title = :title AND chunk_index BETWEEN :start AND :end "
                            "ORDER BY chunk_index"
                        ), {"title": title, "start": start, "end": end}).fetchall()
                        
                        if chunks:
                            doc = {**doc, "content": "\n\n".join([c[0] for c in chunks])}
        except Exception:
            pass
        
        enriched.append(doc)
    return enriched


def build_messages(question, docs):
    context = ""
    for d in docs:
        context += f"Title: {d['title']}\nCategory: {d['category']}\n{d['content']}\n\n---\n\n"
    
    if not context:
        context = "(no documents found)"
        
    return [
        {"role": "system", "content": RAG_SYSTEM},
        {"role": "user", "content": f"Context documents:\n{context}\n\nQuestion: {question}"},
    ]


def answer_rag(question):
    docs = retrieve(question)
    sources = [{"title": d["title"], "category": d["category"]} for d in docs]
    messages = build_messages(question, docs)
    answer, tokens = chat(messages, temperature=0.2)
    return answer, sources, tokens
