import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.chat_routes import router as chat_router
from api.livekit_routes import router as livekit_router
from api.insights_routes import router as insights_router
from api.progress_routes import router as progress_router
from api.voice_routes import router as voice_router
from infrastructure.progress.global_progress import init_progress_system
from utils.logging import setup_logger

# Ensure a baseline global logging config (uvicorn may override formatting, but we want logs enabled).
logging.basicConfig(level=logging.INFO)

logger = setup_logger("main")

app = FastAPI(title="Personal System AI", version="0.1.0")

# Allow frontend dev server to make cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router)
app.include_router(livekit_router)
app.include_router(insights_router)
app.include_router(progress_router)
app.include_router(voice_router)


@app.on_event("startup")
async def _startup():
    init_progress_system()

@app.get("/")
def root():
    return {"message": "Welcome to Personal System AI API"}

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting up Personal System AI API...")
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
