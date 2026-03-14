from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
from ingestion.embedding_pipeline import ingest_folder
from vector_store.vector_db import VectorDB
from rag.retriever import retrieve_context
from rag.prompt_builder import build_prompt
from rag.generator import generate_answer
from rag.query_analyzer import analyze_query
from utils.logging import setup_logger

logger = setup_logger("chat_routes")
router = APIRouter()
vector_db = VectorDB()

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
def scan_folder_endpoint(req: ScanRequest):
    """
    Endpoint to trigger folder scanning and indexing.
    """
    logger.info(f"Received request to scan folder: {req.folder_path}")
    result = ingest_folder(req.folder_path, vector_db)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

@router.post("/query", response_model=QueryResponse)
def query_endpoint(req: QueryRequest):
    """
    Endpoint to ask questions based on indexed documents.
    """
    print(f"DEBUG: Processing query endpoint for: {req.query}")
    logger.info(f"Received query: {req.query}")
    
    # 1. Check if it is a file-specific query
    query_type, target_file = analyze_query(req.query)
    
    where_filter = None
    if query_type == "file_specific_query" and target_file:
        # Validate that the file exists in the index
        if not vector_db.has_file(target_file):
            return QueryResponse(
                answer=f"File '{target_file}' is not indexed. Please run folder scan.",
                source_file=target_file,
                relevant_chunks=[]
            )
        where_filter = {"file_name": target_file}
    
    # 2. Retrieve
    print(f"DEBUG: Calling retrieve_context with target_file={target_file}")
    retrieval_data = retrieve_context(req.query, vector_db, top_k=req.top_k, where=where_filter)
    context_str = retrieval_data["context_str"]
    sources = retrieval_data["sources"]
    print(f"DEBUG: Retrieved {len(sources)} sources")
    
    # 3. Build prompt
    prompt = build_prompt(req.query, context_str)
    
    # 4. Generate answer
    print("DEBUG: Calling generate_answer")
    answer = generate_answer(prompt)
    print("DEBUG: Received answer from generator")
    
    return QueryResponse(
        answer=answer, 
        source_file=target_file if query_type == "file_specific_query" else (sources[0] if sources else None),
        relevant_chunks=context_str.split("\\n---\\n") if context_str else []
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
