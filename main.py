from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.chat_routes import router as chat_router
from api.livekit_routes import router as livekit_router
from utils.logging import setup_logger

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

@app.get("/")
def root():
    return {"message": "Welcome to Personal System AI API"}

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting up Personal System AI API...")
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
