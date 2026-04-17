import os
import sqlite3
from typing import Any, Dict, List, Optional, Tuple

from config import settings


class IndexMetadataStore:
    """
    Small SQLite sidecar for per-file index metadata.

    Chroma doesn't expose SQL-style aggregations, so we persist per-source rollups at
    ingest time to power fast "Insights" endpoints.
    """

    def __init__(self, db_path: Optional[str] = None):
        if db_path:
            self.db_path = db_path
            os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
        else:
            base_dir = settings.vector_db_path
            # Ensure the directory exists (Chroma PersistentClient will also create it,
            # but we want the insights DB to be robust even if called first).
            os.makedirs(base_dir, exist_ok=True)
            self.db_path = os.path.join(base_dir, "insights.sqlite3")
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS indexed_files (
                  source TEXT PRIMARY KEY,
                  file_name TEXT,
                  file_path TEXT,
                  file_ext TEXT,
                  file_type TEXT,
                  size_bytes INTEGER,
                  chunks_count INTEGER,
                  indexed_at TEXT
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_indexed_at ON indexed_files(indexed_at)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_file_type ON indexed_files(file_type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_size_bytes ON indexed_files(size_bytes)")

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS db_summary (
                  key TEXT PRIMARY KEY,
                  summary_json TEXT NOT NULL,
                  updated_at REAL NOT NULL
                )
                """
            )

    def upsert_indexed_file(
        self,
        *,
        source: str,
        file_name: Optional[str],
        file_path: Optional[str],
        file_ext: Optional[str],
        file_type: Optional[str],
        size_bytes: Optional[int],
        indexed_at: Optional[str],
        chunks_count: int,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO indexed_files (
                  source, file_name, file_path, file_ext, file_type, size_bytes, chunks_count, indexed_at
                ) VALUES (
                  :source, :file_name, :file_path, :file_ext, :file_type, :size_bytes, :chunks_count, :indexed_at
                )
                ON CONFLICT(source) DO UPDATE SET
                  file_name=excluded.file_name,
                  file_path=excluded.file_path,
                  file_ext=excluded.file_ext,
                  file_type=excluded.file_type,
                  size_bytes=excluded.size_bytes,
                  chunks_count=excluded.chunks_count,
                  indexed_at=excluded.indexed_at
                """,
                {
                    "source": source,
                    "file_name": file_name,
                    "file_path": file_path,
                    "file_ext": file_ext,
                    "file_type": file_type,
                    "size_bytes": size_bytes,
                    "chunks_count": chunks_count,
                    "indexed_at": indexed_at,
                },
            )

    def is_empty(self) -> bool:
        with self._connect() as conn:
            row = conn.execute("SELECT COUNT(1) AS c FROM indexed_files").fetchone()
            return int(row["c"]) == 0

    def summary(self) -> Dict[str, Any]:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT
                  COUNT(1) AS total_files,
                  COALESCE(SUM(chunks_count), 0) AS total_chunks,
                  MAX(indexed_at) AS last_indexed_at
                FROM indexed_files
                """
            ).fetchone()
            return {
                "total_files": int(row["total_files"]),
                "total_chunks": int(row["total_chunks"]),
                "last_indexed_at": row["last_indexed_at"],
            }

    def content_distribution_counts(self) -> Dict[str, int]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT COALESCE(file_type, 'others') AS file_type, COUNT(1) AS c FROM indexed_files GROUP BY file_type"
            ).fetchall()
            counts = {r["file_type"]: int(r["c"]) for r in rows}
            # Normalize to the required keys.
            return {
                "pdf": counts.get("pdf", 0),
                "code": counts.get("code", 0),
                "text": counts.get("text", 0),
                "others": counts.get("others", 0),
            }

    def recent_files(self, limit: int = 10) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT file_name, file_type, indexed_at
                FROM indexed_files
                ORDER BY indexed_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
            return [
                {
                    "file_name": r["file_name"],
                    "file_type": r["file_type"] or "others",
                    "indexed_at": r["indexed_at"],
                }
                for r in rows
            ]

    def size_distribution(self) -> Dict[str, int]:
        """
        Bucket files by size. Buckets are intentionally simple to avoid chart libs.
        """
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT
                  CASE
                    WHEN size_bytes IS NULL THEN 'unknown'
                    WHEN size_bytes < 100 * 1024 THEN 'lt_100kb'
                    WHEN size_bytes < 1024 * 1024 THEN '100kb_1mb'
                    WHEN size_bytes < 10 * 1024 * 1024 THEN '1mb_10mb'
                    ELSE 'gt_10mb'
                  END AS bucket,
                  COUNT(1) AS c
                FROM indexed_files
                GROUP BY bucket
                """
            ).fetchall()
            counts = {r["bucket"]: int(r["c"]) for r in rows}
            return {
                "lt_100kb": counts.get("lt_100kb", 0),
                "100kb_1mb": counts.get("100kb_1mb", 0),
                "1mb_10mb": counts.get("1mb_10mb", 0),
                "gt_10mb": counts.get("gt_10mb", 0),
                "unknown": counts.get("unknown", 0),
            }

    def get_db_summary(self, *, max_age_seconds: int = 300) -> Optional[Dict[str, Any]]:
        import json
        import time

        with self._connect() as conn:
            row = conn.execute("SELECT summary_json, updated_at FROM db_summary WHERE key='db_summary'").fetchone()
            if not row:
                return None
            if (time.time() - float(row["updated_at"])) > max_age_seconds:
                return None
            try:
                return json.loads(row["summary_json"])
            except Exception:
                return None

    def set_db_summary(self, summary: Dict[str, Any]) -> None:
        import json
        import time

        with self._connect() as conn:
            conn.execute(
                "INSERT INTO db_summary(key, summary_json, updated_at) VALUES('db_summary', ?, ?) "
                "ON CONFLICT(key) DO UPDATE SET summary_json=excluded.summary_json, updated_at=excluded.updated_at",
                (json.dumps(summary), time.time()),
            )

    def compute_db_summary(self) -> Dict[str, Any]:
        """
        Lightweight snapshot used for meta DB queries.
        """
        return {
            "summary": self.summary(),
            "content_distribution": self.content_distribution_counts(),
            "size_distribution": self.size_distribution(),
            "recent_files": self.recent_files(limit=10),
        }

    def sample_sources_by_type(self, file_type: str, limit: int = 2) -> List[str]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT source FROM indexed_files WHERE file_type = ? ORDER BY indexed_at DESC LIMIT ?",
                (file_type, limit),
            ).fetchall()
            return [r["source"] for r in rows]
