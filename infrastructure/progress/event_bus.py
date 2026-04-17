from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List


@dataclass(frozen=True)
class ProgressEvent:
    """
    A generic event emitted by background jobs.
    The ProgressManager is responsible for turning these into per-job state.
    """

    job_id: str
    payload: Dict[str, Any]


class EventBus:
    """
    Tiny in-process pub/sub bus.

    Publishers (indexing, background jobs) emit ProgressEvent objects.
    The ProgressManager subscribes and broadcasts updates to WebSocket clients.
    """

    def __init__(self) -> None:
        self._subscribers: List[Callable[[ProgressEvent], None]] = []

    def subscribe(self, handler: Callable[[ProgressEvent], None]) -> None:
        self._subscribers.append(handler)

    def publish(self, event: ProgressEvent) -> None:
        for handler in list(self._subscribers):
            handler(event)

