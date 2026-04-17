from __future__ import annotations

import asyncio

from infrastructure.progress.event_bus import EventBus
from infrastructure.progress.progress_manager import ProgressManager


progress_event_bus = EventBus()
progress_manager = ProgressManager()


def init_progress_system() -> None:
    """
    Must be called from within FastAPI startup (event loop is running).
    """
    loop = asyncio.get_running_loop()
    progress_manager.init_loop(loop)
    progress_event_bus.subscribe(progress_manager.handle_event)

