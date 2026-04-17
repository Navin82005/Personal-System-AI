from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass


@dataclass(frozen=True)
class EnhancementResult:
    enhanced_query: str
    used_llm: bool
    needs_clarification: bool


class QueryEnhancerService:
    """
    Lightweight query enhancement.

    - Avoids LLM calls unless the query is ambiguous/vague and can be improved.
    - Never invents facts; only rewrites into a standalone retrieval-friendly form.
    """

    def __init__(self, *, model: str = "phi3:mini", ollama_url: str = "http://localhost:11434/api/chat"):
        self.model = model
        self.ollama_url = ollama_url

    def enhance(self, query: str, category: str) -> EnhancementResult:
        q = (query or "").strip()
        if not q:
            return EnhancementResult(enhanced_query="Summarize the indexed documents in the database.", used_llm=False, needs_clarification=False)

        # Fast templates for common vague cases.
        q_lower = q.lower().strip()
        if q_lower in {"summary", "summarize", "summarize it", "summarize this", "summarize that"}:
            return EnhancementResult(
                enhanced_query="Provide a concise summary of the indexed documents in the database.",
                used_llm=False,
                needs_clarification=False,
            )

        if q_lower in {"what is in the db", "what's in the db", "what is in the database", "what's in the database"}:
            return EnhancementResult(
                enhanced_query="List what content is indexed in the database and summarize the main themes.",
                used_llm=False,
                needs_clarification=False,
            )

        # If the query is vague but has no anchor, prefer clarification instead of risky enhancement.
        if category == "VAGUE_QUERY" and q_lower in {"explain this", "tell me about it", "tell me about this", "tell me about that", "explain it"}:
            return EnhancementResult(enhanced_query=q, used_llm=False, needs_clarification=True)

        # Only call LLM for VAGUE_QUERY / RAG_CONTEXT_QUERY where a rewrite can improve retrieval.
        if category not in {"VAGUE_QUERY", "RAG_CONTEXT_QUERY"}:
            return EnhancementResult(enhanced_query=q, used_llm=False, needs_clarification=False)

        # If it already mentions the index/db/docs, keep it (no need to spend an LLM call).
        if any(k in q_lower for k in ["indexed", "documents", "document", "database", "db", "vector", "chroma"]):
            return EnhancementResult(enhanced_query=q, used_llm=False, needs_clarification=False)

        # LLM rewrite: output only an enhanced query.
        prompt = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Rewrite the user query into a standalone, specific query suitable for retrieving information "
                        "from the user's indexed document database. Preserve intent. Do not invent details. "
                        "If the query is too ambiguous to rewrite safely, respond with exactly: NEEDS_CLARIFICATION"
                    ),
                },
                {"role": "user", "content": q},
            ],
            "stream": False,
            "options": {"temperature": 0.0},
        }

        try:
            req = urllib.request.Request(
                self.ollama_url,
                data=json.dumps(prompt).encode("utf-8"),
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                enhanced = (result.get("message", {}) or {}).get("content", "") or ""
                enhanced = enhanced.strip().strip('"')
                if enhanced == "NEEDS_CLARIFICATION":
                    return EnhancementResult(enhanced_query=q, used_llm=True, needs_clarification=True)
                if not enhanced:
                    return EnhancementResult(enhanced_query=q, used_llm=True, needs_clarification=False)
                return EnhancementResult(enhanced_query=enhanced, used_llm=True, needs_clarification=False)
        except Exception:
            # If enhancement fails, fall back to original query.
            return EnhancementResult(enhanced_query=q, used_llm=True, needs_clarification=False)

