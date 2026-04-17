from __future__ import annotations

import re
from dataclasses import dataclass

from rag.query_analyzer import analyze_query


@dataclass(frozen=True)
class ClassificationResult:
    category: str
    confidence_score: float


class QueryClassifierService:
    """
    Fast heuristic classifier.

    We avoid LLM calls here to keep latency low; classification is "good enough"
    for selecting retrieval strategy, and enhancement can refine vague queries.
    """

    _greeting_re = re.compile(r"^\s*(hi|hello|hey|yo|bye|goodbye|thanks|thank you)\b", re.I)
    _general_chat_re = re.compile(
        r"\b(who are you|what can you do|help me|how do you work|what is this)\b", re.I
    )
    _rag_context_re = re.compile(
        r"\b(indexed|documents|document|database|db|vector|chroma|knowledge base|corpus|embeddings)\b",
        re.I,
    )
    _summary_re = re.compile(r"\b(summarize|summary|overview|what is in)\b", re.I)
    _meta_db_re = re.compile(
        r"\b(what data do you contain|what do you contain|what is stored|what kind of information|"
        r"what's in (the )?(db|database)|summarize my (uploaded|indexed) (documents|files)|"
        r"summarize my documents|what documents are indexed|list (the )?indexed (documents|files))\b",
        re.I,
    )
    _vague_re = re.compile(r"\b(it|this|that|those|them)\b", re.I)
    _vague_verb_re = re.compile(r"^\s*(explain|summarize|tell me about|describe)\b", re.I)
    _out_of_scope_re = re.compile(
        r"\b(send email|book|buy|purchase|call|text|sms|delete file|remove file|edit file)\b", re.I
    )

    def __init__(self, *, cache_size: int = 256):
        self._cache_size = cache_size
        self._cache: dict[str, ClassificationResult] = {}

    def classify(self, query: str) -> ClassificationResult:
        q = (query or "").strip()
        if q in self._cache:
            return self._cache[q]
        if not q:
            res = ClassificationResult(category="VAGUE_QUERY", confidence_score=0.6)
            return res

        if self._greeting_re.search(q):
            res = ClassificationResult(category="GREETING", confidence_score=0.95)
            return self._set_cache(q, res)

        if self._general_chat_re.search(q):
            res = ClassificationResult(category="GENERAL_CHAT", confidence_score=0.85)
            return self._set_cache(q, res)

        if self._out_of_scope_re.search(q):
            res = ClassificationResult(category="OUT_OF_SCOPE", confidence_score=0.8)
            return self._set_cache(q, res)

        if self._meta_db_re.search(q):
            res = ClassificationResult(category="META_DB_QUERY", confidence_score=0.85)
            return self._set_cache(q, res)

        query_type, target_file = analyze_query(q)
        if query_type == "file_specific_query" and target_file:
            res = ClassificationResult(category="SPECIFIC_RAG_QUERY", confidence_score=0.9)
            return self._set_cache(q, res)

        # Vague: short + deictic/pronoun language.
        words = q.split()
        if (len(words) <= 4 and self._vague_re.search(q)) or (
            self._vague_verb_re.search(q) and self._vague_re.search(q)
        ):
            res = ClassificationResult(category="VAGUE_QUERY", confidence_score=0.75)
            return self._set_cache(q, res)

        # RAG-context: about "the documents / the db".
        if self._summary_re.search(q) and self._rag_context_re.search(q):
            res = ClassificationResult(category="RAG_CONTEXT_QUERY", confidence_score=0.85)
            return self._set_cache(q, res)

        # Generic "what's in the db" without explicit keywords.
        if self._summary_re.search(q) and len(words) <= 6:
            res = ClassificationResult(category="RAG_CONTEXT_QUERY", confidence_score=0.7)
            return self._set_cache(q, res)

        # If it looks like a question and not system-ops/out-of-scope, assume it's a specific RAG query.
        if "?" in q or len(words) >= 5:
            res = ClassificationResult(category="SPECIFIC_RAG_QUERY", confidence_score=0.6)
            return self._set_cache(q, res)

        res = ClassificationResult(category="GENERAL_CHAT", confidence_score=0.55)
        return self._set_cache(q, res)

    def _set_cache(self, q: str, res: ClassificationResult) -> ClassificationResult:
        if self._cache_size <= 0:
            return res
        if len(self._cache) >= self._cache_size:
            # FIFO-ish: pop the first key
            try:
                self._cache.pop(next(iter(self._cache)))
            except Exception:
                self._cache.clear()
        self._cache[q] = res
        return res
