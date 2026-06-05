# Embed all knowledge base documents and store the vectors. Run: python -m ingest.embed_kb
from sqlalchemy import bindparam, text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.types import Float

from app.services.embeddings import embed_text
from app.core.db import app_engine


def run():
    """Load every KB doc, embed title+content, and UPDATE the embedding column."""
    with app_engine.connect() as conn:
        rows = conn.execute(text(
            "SELECT document_id, title, content FROM knowledge_base_documents ORDER BY document_id"
        )).fetchall()

    total = len(rows)
    print(f"Embedding {total} knowledge base documents...")

    # The embedding column is a float array, so we bind a plain Python list.
    update = text(
        "UPDATE knowledge_base_documents SET embedding = :vec WHERE document_id = :id"
    ).bindparams(bindparam("vec", type_=ARRAY(Float)))

    for i, row in enumerate(rows, start=1):
        doc_id, title, content = row[0], row[1] or "", row[2] or ""
        vector = embed_text(f"{title} {content}")
        with app_engine.begin() as conn:
            conn.execute(update, {"vec": vector, "id": doc_id})
        print(f"  [{i}/{total}] embedded document {doc_id}: {title}")

    print("Done.")


if __name__ == "__main__":
    run()
