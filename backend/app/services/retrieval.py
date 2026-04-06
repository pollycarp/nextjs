"""
Retrieval service — Phase 2.

Embeds a query and performs cosine similarity search in ChromaDB.
"""

from app.services.ingestion import get_collection, embed_texts


def retrieve_chunks(
    query: str,
    top_k: int = 5,
    doc_id: str | None = None,
) -> list[dict]:
    """
    Return top-k chunks relevant to *query*.
    Each chunk: {text, filename, page, score, doc_id}
    """
    collection = get_collection()
    count = collection.count()
    if count == 0:
        return []

    actual_k = min(top_k, count)
    query_embedding = embed_texts([query])[0]

    where = {"doc_id": doc_id} if doc_id else None

    try:
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=actual_k,
            where=where,
            include=["documents", "metadatas", "distances"],
        )
    except Exception:
        return []

    chunks = []
    for text, meta, distance in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        # ChromaDB cosine distance → similarity score
        score = round(1.0 - distance, 4)
        chunks.append(
            {
                "text": text,
                "filename": meta.get("filename", "unknown"),
                "page": meta.get("page", "1"),
                "score": score,
                "doc_id": meta.get("doc_id", ""),
            }
        )

    return chunks
