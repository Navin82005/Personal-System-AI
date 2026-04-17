import asyncio
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect

from infrastructure.progress.global_progress import progress_manager


router = APIRouter()


@router.get("/progress/{job_id}")
def get_progress(job_id: str):
    st = progress_manager.get_state(job_id)
    if not st:
        raise HTTPException(status_code=404, detail="Unknown job_id")
    return st.to_payload()


@router.post("/progress/{job_id}/cancel")
def cancel_progress(job_id: str):
    ok = progress_manager.cancel(job_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Unknown job_id")
    return {"status": "cancelled", "job_id": job_id}


@router.websocket("/ws/progress/{job_id}")
async def ws_progress(websocket: WebSocket, job_id: str):
    await websocket.accept()
    q = progress_manager.subscribe(job_id)
    try:
        while True:
            payload = await q.get()
            await websocket.send_json(payload)
    except WebSocketDisconnect:
        pass
    except Exception:
        # Connection may break mid-send. Treat as disconnect.
        pass
    finally:
        progress_manager.unsubscribe(job_id, q)

