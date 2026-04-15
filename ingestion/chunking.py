from typing import List
from dataclasses import dataclass
from langchain_text_splitters import RecursiveCharacterTextSplitter

@dataclass
class DocumentChunk:
    text: str
    metadata: dict

def split_text(text: str, metadata: dict, chunk_size: int = 500, overlap: int = 100) -> List[DocumentChunk]:
    """
    Splits text into chunks of `chunk_size` characters with an `overlap`.
    Uses langchain-text-splitters RecursiveCharacterTextSplitter.
    """
    if not text:
        return []
        
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=overlap,
        length_function=len,
        is_separator_regex=False,
    )
    
    chunks = text_splitter.split_text(text)
    return [DocumentChunk(text=chunk, metadata=metadata) for chunk in chunks]
