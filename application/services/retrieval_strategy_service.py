from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

from rag.query_analyzer import analyze_query

if TYPE_CHECKING:
    from vector_store.vector_db import VectorDB


class _VectorDBLike(Protocol):
    def has_file(self, filename: str) -> bool: ...


@dataclass(frozen=True)
class RetrievalDecision:
    use_rag: bool
    top_k: int
    where_filter: dict | None
    missing_target_file: str | None = None


class RetrievalStrategyService:
    def __init__(self, *, max_top_k: int = 8):
        self.max_top_k = max_top_k

    def decide(
        self,
        *,
        category: str,
        query: str,
        vector_db: _VectorDBLike,
        needs_clarification: bool = False,
        client_top_k: int | None = None,
    ) -> RetrievalDecision:
        if needs_clarification:
            return RetrievalDecision(use_rag=False, top_k=0, where_filter=None)

        if category in {"GREETING", "GENERAL_CHAT", "OUT_OF_SCOPE"}:
            return RetrievalDecision(use_rag=False, top_k=0, where_filter=None)

        # Map categories to baseline top_k.
        if category == "RAG_CONTEXT_QUERY":
            top_k = 7
        elif category == "META_DB_QUERY":
            # Meta queries use a separate context builder; keep RAG enabled but allow the orchestrator
            # to swap retrieval mode. Use a larger cap for meta sampling.
            top_k = 12
        elif category == "SPECIFIC_RAG_QUERY":
            top_k = 4
        elif category == "VAGUE_QUERY":
            top_k = 6
        else:
            top_k = 4

        if client_top_k is not None:
            # Treat the client hint as an upper bound to protect latency.
            try:
                top_k = min(top_k, int(client_top_k))
            except Exception:
                pass

        cap = 20 if category == "META_DB_QUERY" else self.max_top_k
        top_k = max(3, min(cap, top_k))

        # File-specific filter if present and indexed.
        where_filter = None
        missing_target_file = None
        query_type, target_file = analyze_query(query)
        if query_type == "file_specific_query" and target_file:
            if vector_db.has_file(target_file):
                where_filter = {"file_name": target_file}
            else:
                missing_target_file = target_file

        return RetrievalDecision(
            use_rag=True,
            top_k=top_k,
            where_filter=where_filter,
            missing_target_file=missing_target_file,
        )
