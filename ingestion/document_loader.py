import os
import pdfplumber
import docx
from typing import Optional
from rag.query_analyzer import SUPPORTED_EXTENSIONS

def load_text_from_file(file_path: str) -> Optional[str]:
    """
    Extracts text from a given file path based on its extension.
    Supports PDF, DOCX, and all other text-based files defined in SUPPORTED_EXTENSIONS.
    """
    ext = os.path.splitext(file_path)[1].lower()
    
    if ext not in SUPPORTED_EXTENSIONS:
        return None
        
    if ext == ".pdf":
        return _load_pdf(file_path)
    elif ext == ".docx":
        return _load_docx(file_path)
    else:
        # Fallback to plain text for everything else (.txt, .md, .py, .yaml, etc.)
        return _load_text(file_path)

def _load_pdf(file_path: str) -> str:
    text = []
    try:
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text.append(page_text)
    except Exception as e:
        print(f"Error reading PDF {file_path}: {e}")
    return "\\n".join(text)

def _load_docx(file_path: str) -> str:
    try:
        doc = docx.Document(file_path)
        return "\\n".join([para.text for para in doc.paragraphs])
    except Exception as e:
        print(f"Error reading DOCX {file_path}: {e}")
        return ""

def _load_text(file_path: str) -> str:
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        print(f"Error reading text {file_path}: {e}")
        return ""
