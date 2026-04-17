from vector_store.vector_db import VectorDB
from utils.logging import setup_logger

logger = setup_logger("retriever")

def retrieve_context(
    query: str,
    vector_db: VectorDB,
    top_k: int = 3,
    where: dict | None = None,
    *,
    oversample_factor: int = 2,
    min_chunk_chars: int = 40,
):
    """
    Retrieves relevant chunks with simple deduplication and filtering.

    Chroma doesn't expose server-side aggregations; we keep retrieval lightweight:
    - oversample to allow dedupe without shrinking results too much
    - filter out tiny chunks
    - dedupe by document text (best-effort)
    """
    candidate_k = max(top_k, 1) * max(1, oversample_factor)
    candidate_k = min(candidate_k, 12)
    print(f"DEBUG: retriever.retrieve_context top_k={top_k}, candidate_k={candidate_k}, where={where}")
    results = vector_db.search(query, top_k=candidate_k, where=where)

    # Chroma returns lists of lists. Since we only submit 1 query, we take the 0th element.
    documents = results.get("documents", [[]])[0] or []
    metadata = results.get("metadatas", [[]])[0] or []
    ids = results.get("ids", [[]])[0] or []
    distances = results.get("distances", [[]])[0] or []

    seen_text = set()
    contexts: list[str] = []
    sources = set()
    chunks = []

    for doc, meta, doc_id, dist in zip(documents, metadata, ids, distances):
        if not doc:
            continue
        if len(doc) < min_chunk_chars:
            continue
        key = doc.strip()
        if key in seen_text:
            continue
        seen_text.add(key)

        src = meta.get("source") if isinstance(meta, dict) else None
        if src:
            sources.add(src)
        contexts.append(doc)
        chunks.append({"id": doc_id, "text": doc, "source": src, "distance": dist})

        if len(contexts) >= top_k:
            break

    logger.info(f"Retrieved {len(contexts)} chunks from {len(sources)} sources")
    return {
        "context_str": "\\n---\\n".join(contexts),
        "sources": list(sources),
        "chunks": chunks,
    }
