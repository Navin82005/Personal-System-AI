from fastapi import FastAPI
from api.chat_routes import router as chat_router
from utils.logging import setup_logger

logger = setup_logger("main")

app = FastAPI(title="Personal System AI", version="0.1.0")

app.include_router(chat_router)

@app.get("/")
def root():
    return {"message": "Welcome to Personal System AI API"}

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting up Personal System AI API...")
    uvicorn.run("main:app", host="0.0.0.1", port=8000, reload=True)
