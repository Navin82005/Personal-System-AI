import asyncio
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from application.services.response_orchestrator import ResponseOrchestrator
from application.services.voice_session_service import VoiceSessionConfig, VoiceSessionService
from infrastructure.stt.whisper_service import WhisperService
from infrastructure.tts.coqui_tts_service import CoquiTTSService
from vector_store.vector_db import VectorDB


router = APIRouter()

_sessions: dict[str, VoiceSessionService] = {}
_tasks: dict[str, asyncio.Task] = {}

# Heavy dependencies: keep singletons to avoid reloading models for each room.
_vector_db = VectorDB()
_orchestrator = ResponseOrchestrator(vector_db=_vector_db)
_stt = WhisperService(model_size="tiny")
_tts = None  # lazy-init Coqui (can be slow / large)


class StartVoiceSessionRequest(BaseModel):
    room_name: str


class StopVoiceSessionRequest(BaseModel):
    room_name: str


@router.post("/voice/session/start")
async def start_voice_session(req: StartVoiceSessionRequest):
    """
    Starts (or reuses) a backend LiveKit voice agent for a given room.
    """
    room = req.room_name.strip()
    if not room:
        raise HTTPException(status_code=400, detail="room_name is required")

    if room in _tasks and not _tasks[room].done():
        return {"status": "running", "room_name": room}

    global _tts
    if _tts is None:
        _tts = CoquiTTSService()

    svc = VoiceSessionService(stt=_stt, tts=_tts, orchestrator=_orchestrator)
    cfg = VoiceSessionConfig(room_name=room)

    _sessions[room] = svc
    _tasks[room] = asyncio.create_task(svc.start_session(cfg))
    return {"status": "started", "room_name": room}


@router.post("/voice/session/stop")
async def stop_voice_session(req: StopVoiceSessionRequest):
    room = req.room_name.strip()
    svc = _sessions.get(room)
    if not svc:
        raise HTTPException(status_code=404, detail="No such voice session")
    await svc.stop_session()
    return {"status": "stopping", "room_name": room}
