"""In-process event bus implementation (synchronous, thread-safe)."""

from __future__ import annotations

import threading
from collections import defaultdict

from ..logging import get_logger
from .base import EventBus, Handler


class InProcessEventBus(EventBus):
    """A simple synchronous pub/sub bus.

    Handlers run in the caller's thread. Exceptions in one handler are logged and
    do not prevent other handlers from running, so a single bad subscriber cannot
    stall ingestion.
    """

    def __init__(self) -> None:
        self._subscribers: dict[str, list[Handler]] = defaultdict(list)
        self._lock = threading.RLock()
        self._log = get_logger("bus")

    def publish(self, topic: str, message: object) -> None:
        with self._lock:
            handlers = list(self._subscribers.get(topic, ()))
        for handler in handlers:
            try:
                handler(topic, message)
            except Exception as exc:
                self._log.error("bus.handler_error", extra={"topic": topic, "error": str(exc)})

    def subscribe(self, topic: str, handler: Handler) -> None:
        with self._lock:
            self._subscribers[topic].append(handler)

    def unsubscribe(self, topic: str, handler: Handler) -> None:
        with self._lock:
            if handler in self._subscribers.get(topic, []):
                self._subscribers[topic].remove(handler)
