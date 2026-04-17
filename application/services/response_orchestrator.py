from __future__ import annotations

from dataclasses import dataclass

from application.services.query_classifier_service import QueryClassifierService
from application.services.query_enhancer_service import QueryEnhancerService
from application.services.retrieval_strategy_service import RetrievalStrategyService
from rag.generator import generate_answer
from rag.prompt_builder import build_chat_prompt, build_prompt
from rag.retriever import retrieve_context
from vector_store.vector_db import VectorDB


@dataclass(frozen=True)
class OrchestratorResult:
    answer: str
    used_rag: bool
    category: str
    enhanced_query: str
    sources: list[str]
    relevant_chunks: list[str]


class ResponseOrchestrator:
    """
    Single entry point: classify -> enhance (if needed) -> decide retrieval -> retrieve -> respond.
    """

    def __init__(
        self,
        *,
        vector_db: VectorDB | None = None,
        classifier: QueryClassifierService | None = None,
        enhancer: QueryEnhancerService | None = None,
        strategy: RetrievalStrategyService | None = None,
    ):
        self.vector_db = vector_db or VectorDB()
        self.classifier = classifier or QueryClassifierService()
        self.enhancer = enhancer or QueryEnhancerService()
        self.strategy = strategy or RetrievalStrategyService()

    def handle_user_query(self, query: str, *, client_top_k: int | None = None) -> OrchestratorResult:
        classification = self.classifier.classify(query)
        enhancement = self.enhancer.enhance(query, classification.category)

        # ----------------------------------------
        # STEP 1: Clarification Handling
        # ----------------------------------------
        if enhancement.needs_clarification:
            return OrchestratorResult(
                answer="Could you clarify what you are referring to?",
                used_rag=False,
                category=classification.category,
                enhanced_query=enhancement.enhanced_query,
                sources=[],
                relevant_chunks=[],
            )

        # ----------------------------------------
        # STEP 2: Strategy Decision
        # ----------------------------------------
        decision = self.strategy.decide(
            category=classification.category,
            query=enhancement.enhanced_query,
            vector_db=self.vector_db,
            needs_clarification=False,
            client_top_k=client_top_k,
        )

        # ----------------------------------------
        # STEP 3: Non-RAG Flow
        # ----------------------------------------
        if not decision.use_rag:
            prompt = build_chat_prompt(query)
            answer = generate_answer(prompt) or ""
            return OrchestratorResult(
                answer=answer,
                used_rag=False,
                category=classification.category,
                enhanced_query=enhancement.enhanced_query,
                sources=[],
                relevant_chunks=[],
            )

        # ----------------------------------------
        # STEP 4: PRIMARY RETRIEVAL
        # ----------------------------------------
        retrieval = retrieve_context(
            enhancement.enhanced_query,
            self.vector_db,
            top_k=decision.top_k,
            where=decision.where_filter,
        )

        context_str = retrieval.get("context_str") or ""
        sources = retrieval.get("sources") or []
        chunks = retrieval.get("chunks") or []

        # ----------------------------------------
        # STEP 5: META QUERY HANDLING (NEW)
        # ----------------------------------------
        if classification.category == "META_DB_QUERY":
            # Broader retrieval for meta understanding
            meta_retrieval = retrieve_context(
                enhancement.enhanced_query,
                self.vector_db,
                top_k=15,  # wider context
            )

            context_str = meta_retrieval.get("context_str") or context_str
            sources = meta_retrieval.get("sources") or sources
            chunks = meta_retrieval.get("chunks") or chunks

        # ----------------------------------------
        # STEP 6: RETRY WITH RELAXED SEARCH (NEW)
        # ----------------------------------------
        if not context_str.strip():
            retry_retrieval = retrieve_context(
                enhancement.enhanced_query,
                self.vector_db,
                top_k=10,
                where=None,  # remove filters
            )

            context_str = retry_retrieval.get("context_str") or ""
            sources = retry_retrieval.get("sources") or []
            chunks = retry_retrieval.get("chunks") or []

        # ----------------------------------------
        # STEP 7: SOFT FALLBACK (IMPORTANT FIX)
        # ----------------------------------------
        if not context_str.strip():
            prompt = build_chat_prompt(
                f"{query}\n\nIf no exact data is found, provide a general helpful answer based on system capabilities."
            )
            answer = generate_answer(prompt) or ""

            return OrchestratorResult(
                answer=answer,
                used_rag=False,
                category=classification.category,
                enhanced_query=enhancement.enhanced_query,
                sources=[],
                relevant_chunks=[],
            )

        # ----------------------------------------
        # STEP 8: RESPONSE GENERATION (IMPROVED PROMPT)
        # ----------------------------------------
        prompt = build_prompt(
            enhancement.enhanced_query,
            context_str + "\n\nYou may summarize or infer high-level meaning from the context. Do not strictly require exact matches.",
        )

        answer = generate_answer(prompt) or ""

        return OrchestratorResult(
            answer=answer,
            used_rag=True,
            category=classification.category,
            enhanced_query=enhancement.enhanced_query,
            sources=sources,
            relevant_chunks=[c.get("text", "") for c in chunks if c.get("text")],
        )