from vector_store.vector_db import VectorDB
from application.services.response_orchestrator import ResponseOrchestrator

class RagPipeline:
    def __init__(self, vector_db: VectorDB = None):
        self.vector_db = vector_db or VectorDB()
        self.orchestrator = ResponseOrchestrator(vector_db=self.vector_db)

    def run(self, query: str) -> str:
        """
        Runs the full query understanding + retrieval + generation pipeline.
        """
        return self.orchestrator.handle_user_query(query).answer
