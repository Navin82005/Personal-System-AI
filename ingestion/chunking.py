from typing import List
from dataclasses import dataclass

@dataclass
class DocumentChunk:
    text: str
    metadata: dict

def split_text(text: str, metadata: dict, chunk_size: int = 500, overlap: int = 100) -> List[DocumentChunk]:
    """
    Splits text into chunks of `chunk_size` characters with an `overlap`.
    Uses simple character splitting as requested, which can be improved to semantic split later.
    """
    chunks = []
    if not text:
        return chunks
        
    start = 0
    text_length = len(text)
    
    while start < text_length:
        end = min(start + chunk_size, text_length)
        chunk_text = text[start:end]
        chunks.append(DocumentChunk(text=chunk_text, metadata=metadata))
        
        # Move the start forward by chunk_size - overlap
        start += (chunk_size - overlap)
        
        if start >= text_length:
            break
            
    return chunks
