import json
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from config import CSV_DIR, DATA_DIR

STORE_PATH = DATA_DIR / "vectorstore.json"

vectorizer = None
doc_embeddings = None
documents = None


def setup():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    path = CSV_DIR / "knowledge_base_documents.csv"
    df = pd.read_csv(str(path))

    docs = []
    for _, row in df.iterrows():
        docs.append({
            "title": row["title"],
            "category": row["category"],
            "content": row["content"],
            "text": f"{row['title']}. {row['content']}",
        })

    texts = [d["text"] for d in docs]

    tfidf = TfidfVectorizer(stop_words="english", max_features=5000)
    matrix = tfidf.fit_transform(texts)

    store = {
        "documents": docs,
        "vocabulary": {k: int(v) for k, v in tfidf.vocabulary_.items()},
        "idf": tfidf.idf_.tolist(),
        "matrix": matrix.toarray().tolist(),
    }

    with open(str(STORE_PATH), "w") as f:
        json.dump(store, f)

    print(f"  ✓ Vector store: {len(docs)} documents indexed")
    print(f"  Vector store ready → {STORE_PATH}")


def load():
    global vectorizer, doc_embeddings, documents

    if documents is not None:
        return

    with open(str(STORE_PATH), "r") as f:
        store = json.load(f)

    documents = store["documents"]
    doc_embeddings = np.array(store["matrix"])

    vectorizer = TfidfVectorizer(stop_words="english", max_features=5000)
    vectorizer.vocabulary_ = {k: int(v) for k, v in store["vocabulary"].items()}
    vectorizer.idf_ = np.array(store["idf"])
    vectorizer._tfidf._idf_diag = None


def search(query, k=3):
    load()

    texts = [d["text"] for d in documents]
    all_texts = texts + [query]

    tfidf = TfidfVectorizer(stop_words="english", max_features=5000)
    matrix = tfidf.fit_transform(all_texts)

    query_vec = matrix[-1]
    doc_vecs = matrix[:-1]

    scores = cosine_similarity(query_vec, doc_vecs).flatten()
    top_indices = scores.argsort()[::-1][:k]

    results = []
    for idx in top_indices:
        if scores[idx] > 0.0:
            results.append({
                "title": documents[idx]["title"],
                "category": documents[idx]["category"],
                "content": documents[idx]["content"],
                "score": float(scores[idx]),
            })

    return results


if __name__ == "__main__":
    print("Building vector store from knowledge base...")
    setup()
    print("\nTest search: 'late payment'")
    results = search("late payment")
    for r in results:
        print(f"  {r['score']:.3f} — {r['title']}")
