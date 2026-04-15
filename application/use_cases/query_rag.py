from rag.query_analyzer import analyze_query
from rag.retriever import retrieve_context
from rag.prompt_builder import build_prompt
from rag.generator import generate_answer
from vector_store.vector_db import VectorDB

class RagPipeline:
    def __init__(self, vector_db: VectorDB = None):
        self.vector_db = vector_db or VectorDB()

    def run(self, query: str) -> str:
        """
        Runs the RAG pipeline and returns the generated answer.
        """
        query_type, target_file = analyze_query(query)
        
        where_filter = None
        if query_type == "file_specific_query" and target_file:
            if self.vector_db.has_file(target_file):
                where_filter = {"file_name": target_file}

        retrieval_data = retrieve_context(query, self.vector_db, top_k=3, where=where_filter)
        context_str = retrieval_data["context_str"]
        
        prompt = build_prompt(query, context_str)
        answer = generate_answer(prompt)
        
        return answer
