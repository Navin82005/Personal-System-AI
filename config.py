import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    groq_api_key: str = os.getenv("GROQ_API_KEY", "")
    embedding_model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    vector_db_path: str = "./chroma_db"
    default_chunk_size: int = 500
    default_chunk_overlap: int = 100
    
    class Config:
        env_file = ".env"

settings = Settings()
