import os
from typing import List, Iterator

def scan_folder(folder_path: str, supported_extensions: List[str] = None) -> Iterator[str]:
    """
    Scans a folder recursively and yields absolute paths of files 
    that match supported extensions.
    """
    if supported_extensions is None:
        supported_extensions = [".pdf", ".txt", ".docx", ".md"]
    
    # Normalize extensions to lowercase
    supported_extensions = [ext.lower() for ext in supported_extensions]

    if not os.path.isdir(folder_path):
        raise ValueError(f"Path is not a valid directory: {folder_path}")

    for root, _, files in os.walk(folder_path):
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext in supported_extensions:
                yield os.path.abspath(os.path.join(root, file))
