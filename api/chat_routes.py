import asyncio
from fastapi import APIRouter, HTTPException, UploadFile
from pydantic import BaseModel
from typing import List
from ingestion.embedding_pipeline import ingest_folder
from vector_store.vector_db import VectorDB
from utils.logging import setup_logger
from application.services.response_orchestrator import ResponseOrchestrator

from application.use_cases.voice_query import VoiceQueryUseCase
from application.use_cases.query_rag import RagPipeline
from infrastructure.stt.whisper_service import WhisperService
from infrastructure.tts.coqui_tts_service import CoquiTTSService
from infrastructure.progress.global_progress import progress_manager

logger = setup_logger("chat_routes")
router = APIRouter()
vector_db = VectorDB()
orchestrator = ResponseOrchestrator(vector_db=vector_db)

# Initialize Voice Query services
rag_pipeline = RagPipeline(vector_db)
whisper_stt = WhisperService()
coqui_tts = CoquiTTSService()
voice_use_case = VoiceQueryUseCase(stt=whisper_stt, tts=coqui_tts, rag=rag_pipeline)


class ScanRequest(BaseModel):
    folder_path: str

class QueryRequest(BaseModel):
    query: str
    top_k: int = 3

class QueryResponse(BaseModel):
    answer: str
    source_file: str | None = None
    relevant_chunks: List[str] = []

@router.post("/scan-folder")
async def scan_folder_endpoint(req: ScanRequest):
    """
    Endpoint to trigger folder scanning and indexing.
    """
    logger.info(f"Received request to scan folder: {req.folder_path}")
    job_id, token = progress_manager.create_job()

    async def runner():
        # Run the blocking pipeline off the event loop.
        return await asyncio.to_thread(ingest_folder, req.folder_path, vector_db, job_id=job_id, cancel_token=token)

    task = asyncio.create_task(runner())
    progress_manager.attach_task(job_id, task)
    return {"job_id": job_id}

@router.post("/query", response_model=QueryResponse)
def query_endpoint(req: QueryRequest):
    """
    Endpoint to ask questions based on indexed documents.
    """
    logger.info(f"Received query: {req.query}")

    result = orchestrator.handle_user_query(req.query, client_top_k=req.top_k)
    source_file = result.sources[0] if result.sources else None
    return QueryResponse(
        answer=result.answer,
        source_file=source_file,
        relevant_chunks=result.relevant_chunks,
    )

@router.get("/documents")
def list_documents():
    """
    Endpoint to list all indexed document sources and their metadata.
    """
    sources = vector_db.get_all_sources()
    metadata_map = vector_db.get_all_metadata()
    
    documents = []
    for source in sources:
        documents.append({
            "source": source,
            "metadata": metadata_map.get(source, {})
        })
        
    return {"documents": documents, "total_count": len(sources)}

@router.post("/voice-query")
async def voice_query(audio: UploadFile):
    """
    Endpoint to handle voice queries (Speech-to-Text -> RAG -> Text-to-Speech)
    """
    logger.info("Received voice query request")
    audio_bytes = await audio.read()
    
    result = voice_use_case.execute(audio_bytes)
    
    return {
        "query": result["query"],
        "answer": result["answer"]
    }
