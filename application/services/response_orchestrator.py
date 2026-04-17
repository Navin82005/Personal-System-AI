from __future__ import annotations

from dataclasses import dataclass

from application.services.query_classifier_service import QueryClassifierService
from application.services.query_enhancer_service import QueryEnhancerService
from application.services.meta_context_service import MetaContextService
from application.services.retrieval_strategy_service import RetrievalStrategyService
from rag.generator import generate_answer
from rag.prompt_builder import build_chat_prompt, build_meta_prompt, build_prompt
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
        self.meta_context = MetaContextService()

    def handle_user_query(self, query: str, *, client_top_k: int | None = None) -> OrchestratorResult:
        classification = self.classifier.classify(query)
        enhancement = self.enhancer.enhance(query, classification.category)

        # ----------------------------------------
        # STEP 0: Meta DB Queries (holistic DB understanding)
        # ----------------------------------------
        if classification.category == "META_DB_QUERY":
            meta = self.meta_context.build_meta_context(vector_db=self.vector_db, excerpt_per_type=2)
            if not meta.has_any_data:
                return OrchestratorResult(
                    answer=(
                        "It looks like your indexed database is empty (or has no readable chunks yet). "
                        "Use the Indexing tab to scan a folder, then ask again."
                    ),
                    used_rag=False,
                    category=classification.category,
                    enhanced_query=enhancement.enhanced_query,
                    sources=[],
                    relevant_chunks=[],
                )

            prompt = build_meta_prompt(query, meta.text)
            answer = generate_answer(prompt) or ""
            return OrchestratorResult(
                answer=answer,
                used_rag=True,
                category=classification.category,
                enhanced_query=enhancement.enhanced_query,
                sources=[],
                relevant_chunks=[],
            )

        # ----------------------------------------
        # STEP 1: Clarification Handling
        # ----------------------------------------
        if enhancement.needs_clarification:
            return OrchestratorResult(
                answer=(
                    "What should I use as the reference for “this/it”? "
                    "If you mean your indexed documents, share a topic or a specific file name (e.g., report.pdf)."
                ),
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

        if decision.missing_target_file:
            return OrchestratorResult(
                answer=(
                    f"File '{decision.missing_target_file}' is not indexed. "
                    "Use the Indexing tab to scan a folder, then try again."
                ),
                used_rag=True,
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
        # STEP 5: Intent-aware fallback
        # ----------------------------------------
        if not context_str.strip():
            meta = self.meta_context.build_meta_context(vector_db=self.vector_db, excerpt_per_type=1)
            if meta.has_any_data:
                prompt = build_meta_prompt(
                    user_query=(
                        "The user asked a question but retrieval found no close matches. "
                        "Provide a short summary of what is indexed and suggest how to refine the query: "
                        + query
                    ),
                    meta_context=meta.text,
                )
                answer = generate_answer(prompt) or ""
            else:
                prompt = build_chat_prompt(query)
                answer = generate_answer(prompt) or ""
            return OrchestratorResult(
                answer=answer,
                used_rag=meta.has_any_data,
                category=classification.category,
                enhanced_query=enhancement.enhanced_query,
                sources=[],
                relevant_chunks=[],
            )

        # ----------------------------------------
        # STEP 6: Response generation
        # ----------------------------------------
        prompt = build_prompt(enhancement.enhanced_query, context_str)
        answer = generate_answer(prompt) or ""

        # Guardrail: if the model still answers "I don't know" despite having context,
        # retry with a more explicit instruction to summarize what *is* present.
        normalized = answer.strip().lower()
        if context_str.strip() and (normalized == "i don't know." or normalized == "i don't know" or normalized.startswith("i don't know")):
            retry_prompt = (
                prompt
                + "\n\nIMPORTANT: Do not respond with 'I don't know'. If you can't answer the question directly, "
                "summarize the most relevant information present in the context and explain how it relates."
            )
            answer = generate_answer(retry_prompt) or answer

        return OrchestratorResult(
            answer=answer,
            used_rag=True,
            category=classification.category,
            enhanced_query=enhancement.enhanced_query,
            sources=sources,
            relevant_chunks=[c.get("text", "") for c in chunks if c.get("text")],
        )
