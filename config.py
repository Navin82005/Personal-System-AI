import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    groq_api_key: str = os.getenv("GROQ_API_KEY", "")
    embedding_model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    vector_db_path: str = "./chroma_db"
    default_chunk_size: int = 500
    default_chunk_overlap: int = 100
    
    # LiveKit and TTS APIs
    livekit_url: str = os.getenv("LIVEKIT_URL", "")
    livekit_api_key: str = os.getenv("LIVEKIT_API_KEY", "")
    livekit_api_secret: str = os.getenv("LIVEKIT_API_SECRET", "")
    fish_audio_api_key: str = os.getenv("FISH_AUDIO_API_KEY", "")
    nvidia_api_key: str = os.getenv("NVIDIA_NIM_API_KEY", "")
    
    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
