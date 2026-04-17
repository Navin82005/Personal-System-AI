import unittest

from application.services.query_classifier_service import QueryClassifierService
from application.services.retrieval_strategy_service import RetrievalStrategyService


class _FakeVectorDB:
    def has_file(self, filename: str) -> bool:
        return filename == "architecture_notes.md"


class TestQueryUnderstanding(unittest.TestCase):
    def test_classify_greeting(self):
        c = QueryClassifierService().classify("hello there")
        self.assertEqual(c.category, "GREETING")

    def test_classify_rag_context(self):
        c = QueryClassifierService().classify("summarize the indexed documents")
        self.assertEqual(c.category, "RAG_CONTEXT_QUERY")

    def test_classify_meta_db(self):
        c = QueryClassifierService().classify("What data do you contain?")
        self.assertEqual(c.category, "META_DB_QUERY")

    def test_classify_specific_file(self):
        c = QueryClassifierService().classify("what does it say in architecture_notes.md?")
        self.assertEqual(c.category, "SPECIFIC_RAG_QUERY")

    def test_strategy_top_k(self):
        s = RetrievalStrategyService(max_top_k=8)
        d = s.decide(category="RAG_CONTEXT_QUERY", query="summarize indexed documents", vector_db=_FakeVectorDB())
        self.assertTrue(d.use_rag)
        self.assertGreaterEqual(d.top_k, 6)


if __name__ == "__main__":
    unittest.main()
