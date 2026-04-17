import os
import tempfile
import unittest
from datetime import datetime, timedelta

from vector_store.index_metadata_store import IndexMetadataStore


class TestIndexMetadataStore(unittest.TestCase):
    def test_summary_distribution_recent_and_size(self):
        with tempfile.TemporaryDirectory() as td:
            db_path = os.path.join(td, "insights.sqlite3")
            store = IndexMetadataStore(db_path=db_path)

            now = datetime.now()
            store.upsert_indexed_file(
                source="/tmp/a.pdf",
                file_name="a.pdf",
                file_path="/tmp/a.pdf",
                file_ext=".pdf",
                file_type="pdf",
                size_bytes=50 * 1024,
                indexed_at=(now - timedelta(minutes=2)).isoformat(),
                chunks_count=12,
            )
            store.upsert_indexed_file(
                source="/tmp/b.py",
                file_name="b.py",
                file_path="/tmp/b.py",
                file_ext=".py",
                file_type="code",
                size_bytes=2 * 1024 * 1024,
                indexed_at=(now - timedelta(minutes=1)).isoformat(),
                chunks_count=7,
            )
            store.upsert_indexed_file(
                source="/tmp/c.txt",
                file_name="c.txt",
                file_path="/tmp/c.txt",
                file_ext=".txt",
                file_type="text",
                size_bytes=20 * 1024 * 1024,
                indexed_at=now.isoformat(),
                chunks_count=3,
            )

            summary = store.summary()
            self.assertEqual(summary["total_files"], 3)
            self.assertEqual(summary["total_chunks"], 22)
            self.assertIsNotNone(summary["last_indexed_at"])

            dist = store.content_distribution_counts()
            self.assertEqual(dist["pdf"], 1)
            self.assertEqual(dist["code"], 1)
            self.assertEqual(dist["text"], 1)
            self.assertEqual(dist["others"], 0)

            recent = store.recent_files(limit=2)
            self.assertEqual(len(recent), 2)
            self.assertEqual(recent[0]["file_name"], "c.txt")
            self.assertEqual(recent[1]["file_name"], "b.py")

            sizes = store.size_distribution()
            self.assertEqual(sizes["lt_100kb"], 1)
            self.assertEqual(sizes["1mb_10mb"], 1)
            self.assertEqual(sizes["gt_10mb"], 1)


if __name__ == "__main__":
    unittest.main()

