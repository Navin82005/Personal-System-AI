from __future__ import annotations

from dataclasses import dataclass

from vector_store.index_metadata_store import IndexMetadataStore
from vector_store.vector_db import VectorDB


@dataclass(frozen=True)
class MetaContext:
    text: str
    has_any_data: bool


class MetaContextService:
    """
    Generates a "DB-level" context for meta queries.

    Uses:
    - fast SQLite snapshot (db_summary)
    - representative chunk excerpts sampled across file types
    """

    def __init__(self, *, metadata_store: IndexMetadataStore | None = None):
        self.metadata_store = metadata_store or IndexMetadataStore()

    def build_meta_context(self, *, vector_db: VectorDB, excerpt_per_type: int = 2) -> MetaContext:
        cached = self.metadata_store.get_db_summary(max_age_seconds=300)
        if not cached:
            cached = self.metadata_store.compute_db_summary()
            try:
                self.metadata_store.set_db_summary(cached)
            except Exception:
                pass

        summary = cached.get("summary", {}) or {}
        total_files = int(summary.get("total_files") or 0)
        total_chunks = int(summary.get("total_chunks") or 0)
        last_indexed_at = summary.get("last_indexed_at") or None

        dist = cached.get("content_distribution", {}) or {}
        recent = cached.get("recent_files", []) or []

        excerpts: list[str] = []

        # Prefer per-type sampling via sqlite sources to reduce Chroma reads.
        for file_type in ["pdf", "code", "text", "others"]:
            sources = self.metadata_store.sample_sources_by_type(file_type, limit=excerpt_per_type)
            for src in sources:
                try:
                    chunks = vector_db.chunks_for_source(src, limit=1)
                except Exception:
                    chunks = []
                if not chunks:
                    continue
                meta = chunks[0].get("metadata") or {}
                file_name = meta.get("file_name") or meta.get("source_name") or src
                text = (chunks[0].get("text") or "").strip().replace("\n", " ")
                if len(text) > 320:
                    text = text[:320] + "…"
                excerpts.append(f"- [{file_type}] {file_name}: {text}")

        # If still empty but DB has chunks, sample some chunks directly.
        if not excerpts and total_chunks > 0:
            count = vector_db.count()
            if count > 0:
                offsets = [0, max(count // 3, 0), max((2 * count) // 3, 0)]
                for off in offsets:
                    for row in vector_db.sample_chunks(limit=10, offset=off):
                        meta = row.get("metadata") or {}
                        file_name = meta.get("file_name") or meta.get("source_name") or meta.get("source") or "unknown"
                        file_type = meta.get("file_type") or "unknown"
                        text = (row.get("text") or "").strip().replace("\n", " ")
                        if len(text) > 240:
                            text = text[:240] + "…"
                        excerpts.append(f"- [{file_type}] {file_name}: {text}")
                        if len(excerpts) >= 12:
                            break
                    if len(excerpts) >= 12:
                        break

        dist_lines = [
            f"- pdf: {int(dist.get('pdf') or 0)}",
            f"- code: {int(dist.get('code') or 0)}",
            f"- text: {int(dist.get('text') or 0)}",
            f"- others: {int(dist.get('others') or 0)}",
        ]
        recent_lines = []
        for r in recent[:8]:
            recent_lines.append(
                f"- {r.get('file_name') or '—'} ({(r.get('file_type') or 'others')}) @ {r.get('indexed_at') or '—'}"
            )

        meta_text = "\n".join(
            [
                "DB Snapshot:",
                f"- total_files: {total_files}",
                f"- total_chunks: {total_chunks}",
                f"- last_indexed_at: {last_indexed_at or '—'}",
                "",
                "File Type Distribution (counts):",
                *dist_lines,
                "",
                "Recent Indexed Files:",
                *(recent_lines or ["- —"]),
                "",
                "Representative Excerpts:",
                *(excerpts or ["- —"]),
            ]
        )

        return MetaContext(text=meta_text, has_any_data=(total_chunks > 0 or total_files > 0))

