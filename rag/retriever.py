from vector_store.vector_db import VectorDB
from utils.logging import setup_logger

logger = setup_logger("retriever")

def retrieve_context(query: str, vector_db: VectorDB, top_k: int = 3, where: dict = None):
    print(f"DEBUG: retriever.retrieve_context top_k={top_k}, where={where}")
    results = vector_db.search(query, top_k=top_k, where=where)
    
    contexts = []
    sources = set()
    
    # Chroma returns lists of lists. Since we only submit 1 query, we take the 0th element.
    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    
    for doc, meta in zip(documents, metadatas):
        contexts.append(doc)
        if meta and "source" in meta:
            sources.add(meta["source"])
            
    logger.info(f"Retrieved {len(contexts)} chunks from {len(sources)} sources")
    return {
        "context_str": "\\n---\\n".join(contexts),
        "sources": list(sources)
    }
