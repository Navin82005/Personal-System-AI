from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from infrastructure.progress.event_bus import ProgressEvent


@dataclass
class CancelToken:
    cancelled: bool = False

    def cancel(self) -> None:
        self.cancelled = True


@dataclass
class ProgressState:
    job_id: str
    status: str = "idle"
    message: str = ""
    current_file: Optional[str] = None
    processed_files: int = 0
    total_files: int = 0
    file_chunks_done: int = 0
    file_chunks_total: int = 0
    progress_percentage: int = 0
    logs: List[Dict[str, Any]] = field(default_factory=list)
    started_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    error: Optional[str] = None

    def to_payload(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "progress_percentage": self.progress_percentage,
            "current_file": self.current_file,
            "processed_files": self.processed_files,
            "total_files": self.total_files,
            "status": self.status,
            "message": self.message,
            "file_chunks_done": self.file_chunks_done,
            "file_chunks_total": self.file_chunks_total,
            "logs": self.logs,
            "updated_at": self.updated_at,
            "started_at": self.started_at,
            "error": self.error,
        }


class ProgressManager:
    """
    Holds per-job progress state and broadcasts to subscribers (WebSocket clients).
    """

    def __init__(self) -> None:
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._jobs: Dict[str, ProgressState] = {}
        self._cancel_tokens: Dict[str, CancelToken] = {}
        self._subscribers: Dict[str, Set[asyncio.Queue]] = {}
        self._tasks: Dict[str, asyncio.Task] = {}

    def init_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    def create_job(self) -> tuple[str, CancelToken]:
        job_id = uuid.uuid4().hex
        token = CancelToken()
        self._cancel_tokens[job_id] = token
        self._jobs[job_id] = ProgressState(job_id=job_id, status="idle", message="Job created")
        return job_id, token

    def get_cancel_token(self, job_id: str) -> Optional[CancelToken]:
        return self._cancel_tokens.get(job_id)

    def get_state(self, job_id: str) -> Optional[ProgressState]:
        return self._jobs.get(job_id)

    def attach_task(self, job_id: str, task: asyncio.Task) -> None:
        self._tasks[job_id] = task

    def cancel(self, job_id: str) -> bool:
        token = self._cancel_tokens.get(job_id)
        if not token:
            return False
        token.cancel()
        self._set_state_threadsafe(job_id, {"status": "cancelled", "message": "Cancelled"})
        return True

    def handle_event(self, event: ProgressEvent) -> None:
        """
        EventBus subscriber. Safe to call from any thread.
        """
        self._set_state_threadsafe(event.job_id, event.payload)

    def _set_state_threadsafe(self, job_id: str, payload: Dict[str, Any]) -> None:
        if not self._loop:
            # During import/startup before loop is available.
            self._apply_update(job_id, payload)
            return
        self._loop.call_soon_threadsafe(lambda: self._apply_update(job_id, payload))

    def _apply_update(self, job_id: str, payload: Dict[str, Any]) -> None:
        st = self._jobs.get(job_id)
        if not st:
            st = ProgressState(job_id=job_id)
            self._jobs[job_id] = st

        # Merge fields
        for k, v in payload.items():
            if hasattr(st, k):
                setattr(st, k, v)

        st.updated_at = time.time()

        msg = payload.get("message")
        if msg:
            st.logs.append({"ts": st.updated_at, "message": str(msg), "status": st.status})
            if len(st.logs) > 80:
                st.logs = st.logs[-80:]

        if payload.get("error"):
            st.error = str(payload.get("error"))

        # Compute job percent. If chunk info present, include partial progress for current file.
        denom = max(st.total_files, 0)
        if denom <= 0:
            st.progress_percentage = 0 if st.status not in {"completed"} else 100
        else:
            partial = 0.0
            if st.file_chunks_total and st.file_chunks_done:
                partial = min(st.file_chunks_done / max(st.file_chunks_total, 1), 1.0)
            done = min(st.processed_files, denom)
            pct = int(round(((done + partial) / denom) * 100))
            st.progress_percentage = max(0, min(100, pct))

        if st.status == "completed":
            st.progress_percentage = 100

        # Broadcast
        queues = self._subscribers.get(job_id, set())
        if queues:
            payload_out = st.to_payload()
            for q in list(queues):
                try:
                    q.put_nowait(payload_out)
                except Exception:
                    # Drop broken subscribers.
                    queues.discard(q)

    def subscribe(self, job_id: str) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=200)
        self._subscribers.setdefault(job_id, set()).add(q)
        # Send snapshot immediately
        st = self._jobs.get(job_id)
        if st:
            q.put_nowait(st.to_payload())
        return q

    def unsubscribe(self, job_id: str, q: asyncio.Queue) -> None:
        subs = self._subscribers.get(job_id)
        if not subs:
            return
        subs.discard(q)
        if not subs:
            self._subscribers.pop(job_id, None)
