from fastapi import APIRouter

from utils.logging import setup_logger
from vector_store.vector_db import VectorDB
from vector_store.index_metadata_store import IndexMetadataStore

logger = setup_logger("insights_routes")
router = APIRouter()

vector_db = VectorDB()
metadata_store = IndexMetadataStore()


def _backfill_if_needed() -> None:
    """
    Older indexes may not have a populated insights sidecar DB.
    If it's empty, backfill best-effort from Chroma metadatas.
    """
    if not metadata_store.is_empty():
        return

    try:
        data = vector_db.collection.get(include=["metadatas"])
        metadatas = data.get("metadatas", []) or []
        if not metadatas:
            return

        def categorize_file_type(file_ext: str) -> str:
            file_ext = (file_ext or "").lower()
            if file_ext == ".pdf":
                return "pdf"
            if file_ext in {".py", ".java", ".json", ".yaml", ".yml", ".env", ".lock"}:
                return "code"
            if file_ext in {".txt", ".md", ".docx"}:
                return "text"
            return "others"

        # Aggregate per-source chunk counts + keep one representative metadata dict.
        per_source = {}
        for meta in metadatas:
            if not meta:
                continue
            source = meta.get("source") or meta.get("file_path")
            if not source:
                continue
            entry = per_source.get(source)
            if not entry:
                per_source[source] = {"meta": meta, "chunks": 1}
            else:
                entry["chunks"] += 1

        for source, entry in per_source.items():
            meta = entry["meta"] or {}
            file_path = meta.get("file_path") or source
            file_name = meta.get("file_name")
            file_ext = meta.get("file_ext")
            if not file_ext and file_name and "." in file_name:
                file_ext = "." + file_name.split(".")[-1]
            file_type = meta.get("file_type") or categorize_file_type(file_ext)
            size_bytes = meta.get("size_bytes")
            indexed_at = meta.get("indexed_at") or meta.get("updated_at") or meta.get("created_at")
            metadata_store.upsert_indexed_file(
                source=source,
                file_name=file_name,
                file_path=file_path,
                file_ext=file_ext,
                file_type=file_type,
                size_bytes=size_bytes,
                indexed_at=indexed_at,
                chunks_count=int(entry["chunks"]),
            )
        logger.info(f"Backfilled insights metadata for {len(per_source)} sources")
    except Exception as e:
        logger.warning(f"Insights backfill failed: {e}")


@router.get("/insights/summary")
def insights_summary():
    _backfill_if_needed()
    return metadata_store.summary()


@router.get("/insights/content-distribution")
def insights_content_distribution():
    _backfill_if_needed()
    return {"file_types": metadata_store.content_distribution_counts()}


@router.get("/insights/recent-files")
def insights_recent_files(limit: int = 10):
    _backfill_if_needed()
    return metadata_store.recent_files(limit=limit)


@router.get("/insights/size-distribution")
def insights_size_distribution():
    _backfill_if_needed()
    return {"size_buckets": metadata_store.size_distribution()}
