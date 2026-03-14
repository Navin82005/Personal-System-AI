from rag.query_analyzer import SUPPORTED_EXTENSIONS
import os
from ingestion.folder_scanner import scan_folder
from ingestion.document_loader import load_text_from_file
from ingestion.chunking import split_text
from vector_store.vector_db import VectorDB
from config import settings
from utils.logging import setup_logger
from datetime import datetime

logger = setup_logger("embedding_pipeline")

def ingest_folder(folder_path: str, vector_db: VectorDB):
    logger.info(f"Starting ingestion for folder: {folder_path}")
    
    try:
        files = list(scan_folder(folder_path, SUPPORTED_EXTENSIONS))
    except Exception as e:
        logger.error(f"Error scanning folder {folder_path}: {e}")
        return {"error": str(e)}

    logger.info(f"Found {len(files)} files to process.")
    
    processed_files = 0
    failed_files = 0
    
    for file_path in files:
        try:
            # Check if file has already been ingested by looking at DB sources
            # To support re-indexing, we could also delete old chunks before adding them.
            # Keeping it simple for the initial version.
            text = load_text_from_file(file_path)
            if not text:
                logger.warning(f"No text extracted from {file_path}")
                failed_files += 1
                continue
                
            metadata = get_file_metadata(file_path)
            chunks = split_text(
                text, 
                metadata, 
                chunk_size=settings.default_chunk_size, 
                overlap=settings.default_chunk_overlap
            )
            
            vector_db.add_chunks(chunks, source=file_path)
            processed_files += 1
            
        except Exception as e:
            logger.error(f"Failed to process {file_path}: {e}")
            failed_files += 1

    return {
        "status": "success",
        "total_files_found": len(files),
        "processed_files": processed_files,
        "failed_files": failed_files
    }


def get_file_metadata(file_path: str):
    stat = os.stat(file_path)

    metadata = {
        "file_name": os.path.basename(file_path),
        "file_path": os.path.abspath(file_path),
        "created_at": f"{datetime.fromtimestamp(stat.st_ctime)}",
        "updated_at": f"{datetime.fromtimestamp(stat.st_mtime)}",
        "size_bytes": stat.st_size
    }

    return metadata