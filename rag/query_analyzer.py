import re
from typing import Optional, Tuple
from utils.logging import setup_logger

logger = setup_logger("query_analyzer")

# Supported extensions to look for in a query
SUPPORTED_EXTENSIONS = [".pdf", ".txt", ".docx", ".md", ".py", ".json", ".env", ".yaml", ".yml", ".lock", ".java"]

def analyze_query(query: str) -> Tuple[str, Optional[str]]:
    """
    Analyzes a user query to determine if it is a global_query or file_specific_query.
    
    Returns:
        Tuple containing:
        - query_type (str): "global_query" or "file_specific_query"
        - target_file (Optional[str]): The extracted file name if file_specific, else None.
    """
    # Regex to find a word ending with one of the supported extensions
    # This regex looks for word characters optionally containing dots, dashes, or underscores,
    # ending with a string like '.pdf', case insensitive.
    ext_pattern = "|".join([re.escape(ext) for ext in SUPPORTED_EXTENSIONS])

    pattern = rf"\b([a-zA-Z0-9_\-\.]+(?:{ext_pattern}))\b"
    
    match = re.search(pattern, query, re.IGNORECASE)
    logger.debug(f"analyze_query match={bool(match)} pattern={pattern}")

    if match:
        file_name = match.group(1).strip()
        return "file_specific_query", file_name

    return "global_query", None
