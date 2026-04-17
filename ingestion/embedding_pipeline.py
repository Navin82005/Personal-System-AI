from rag.query_analyzer import SUPPORTED_EXTENSIONS
import os
from ingestion.folder_scanner import scan_folder
from ingestion.document_loader import load_text_from_file
from ingestion.chunking import split_text
from vector_store.vector_db import VectorDB
from config import settings
from utils.logging import setup_logger
from datetime import datetime
from vector_store.index_metadata_store import IndexMetadataStore
from infrastructure.progress.event_bus import ProgressEvent
from infrastructure.progress.global_progress import progress_event_bus

logger = setup_logger("embedding_pipeline")

def ingest_folder(
    folder_path: str,
    vector_db: VectorDB,
    *,
    job_id: str | None = None,
    cancel_token=None,
):
    logger.info(f"Starting ingestion for folder: {folder_path}")
    metadata_store = IndexMetadataStore()

    def emit(payload: dict):
        if not job_id:
            return
        progress_event_bus.publish(ProgressEvent(job_id=job_id, payload=payload))
    
    try:
        emit({"status": "scanning", "message": f"Scanning folder: {folder_path}"})
        files = list(scan_folder(folder_path, SUPPORTED_EXTENSIONS))
    except Exception as e:
        logger.error(f"Error scanning folder {folder_path}: {e}")
        emit({"status": "error", "error": str(e), "message": f"Scan failed: {e}"})
        return {"error": str(e)}

    logger.info(f"Found {len(files)} files to process.")
    emit({"total_files": len(files), "processed_files": 0, "status": "processing", "message": f"Found {len(files)} files"})
    
    processed_files = 0
    failed_files = 0
    
    for file_path in files:
        try:
            if cancel_token and getattr(cancel_token, "cancelled", False):
                emit({"status": "cancelled", "message": "Cancelled"})
                break
            # Check if file has already been ingested by looking at DB sources
            # To support re-indexing, we could also delete old chunks before adding them.
            # Keeping it simple for the initial version.
            text = load_text_from_file(file_path)
            if not text:
                logger.warning(f"No text extracted from {file_path}")
                failed_files += 1
                emit({"message": f"Skipped (no text): {file_path}"})
                continue
                
            metadata = get_file_metadata(file_path)
            emit(
                {
                    "current_file": metadata.get("file_name") or file_path,
                    "status": "processing",
                    "file_chunks_done": 0,
                    "file_chunks_total": 0,
                    "message": f"Processing {metadata.get('file_name') or file_path}",
                }
            )
            chunks = split_text(
                text, 
                metadata, 
                chunk_size=settings.default_chunk_size, 
                overlap=settings.default_chunk_overlap
            )

            # Throttle chunk updates to avoid spamming the UI.
            total_chunks = len(chunks)
            emit({"file_chunks_done": 0, "file_chunks_total": total_chunks})
            last_sent = {"n": 0}
            step = max(1, total_chunks // 20) if total_chunks else 1

            def progress_cb(update: dict):
                # Called from vector_db loop.
                if "file_chunks_done" in update and total_chunks:
                    done = int(update["file_chunks_done"])
                    if done != total_chunks and (done - last_sent["n"]) < step:
                        return
                    last_sent["n"] = done
                    emit(
                        {
                            "status": "embedding",
                            "file_chunks_done": done,
                            "file_chunks_total": total_chunks,
                            "message": f"Generating embeddings ({done}/{total_chunks})",
                        }
                    )
                    return
                emit(update)

            vector_db.add_chunks(
                chunks,
                source=file_path,
                progress_cb=progress_cb,
                should_cancel=(lambda: bool(cancel_token and getattr(cancel_token, "cancelled", False))),
            )
            # Keep an aggregated per-file record for fast "Insights" queries.
            metadata_store.upsert_indexed_file(
                source=file_path,
                file_name=metadata.get("file_name"),
                file_path=metadata.get("file_path"),
                file_ext=metadata.get("file_ext"),
                file_type=metadata.get("file_type"),
                size_bytes=metadata.get("size_bytes"),
                indexed_at=metadata.get("indexed_at"),
                chunks_count=len(chunks),
            )
            processed_files += 1
            emit(
                {
                    "processed_files": processed_files,
                    "status": "processing",
                    "file_chunks_done": 0,
                    "file_chunks_total": 0,
                    "message": f"Indexed {metadata.get('file_name') or file_path}",
                }
            )
            
        except Exception as e:
            if str(e) == "cancelled":
                emit({"status": "cancelled", "message": "Cancelled"})
                break
            logger.error(f"Failed to process {file_path}: {e}")
            failed_files += 1
            emit({"status": "processing", "message": f"Failed: {file_path}"})

    if cancel_token and getattr(cancel_token, "cancelled", False):
        return {
            "status": "cancelled",
            "total_files_found": len(files),
            "processed_files": processed_files,
            "failed_files": failed_files,
        }

    # Update the snapshot cache for meta DB queries.
    try:
        metadata_store.set_db_summary(metadata_store.compute_db_summary())
    except Exception:
        pass

    emit(
        {
            "status": "completed",
            "message": f"Indexing completed (processed: {processed_files}, failed: {failed_files})",
            "file_chunks_done": 0,
            "file_chunks_total": 0,
        }
    )
    return {
        "status": "success",
        "total_files_found": len(files),
        "processed_files": processed_files,
        "failed_files": failed_files
    }


def get_file_metadata(file_path: str):
    stat = os.stat(file_path)
    _, ext = os.path.splitext(file_path)
    ext = (ext or "").lower()

    def categorize_file_type(file_ext: str) -> str:
        if file_ext == ".pdf":
            return "pdf"
        if file_ext in {".py", ".java", ".json", ".yaml", ".yml", ".env", ".lock"}:
            return "code"
        if file_ext in {".txt", ".md", ".docx"}:
            return "text"
        return "others"

    metadata = {
        "file_name": os.path.basename(file_path),
        "source_name": os.path.basename(file_path),
        "file_path": os.path.abspath(file_path),
        "file_ext": ext,
        "file_type": categorize_file_type(ext),
        "created_at": f"{datetime.fromtimestamp(stat.st_ctime)}",
        "updated_at": f"{datetime.fromtimestamp(stat.st_mtime)}",
        "size_bytes": stat.st_size,
        # When the index operation ran (not the file's mtime).
        "indexed_at": datetime.now().isoformat()
    }

    return metadata
