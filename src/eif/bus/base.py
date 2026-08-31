"""Event bus abstraction for streaming / event-driven evidence ingestion.

EIF ships an in-process bus so continuous ingestion works out of the box with no
infrastructure. The interface is deliberately minimal so production adapters
(Kafka, Redis Streams, NATS, cloud queues) can implement it without changing
callers. Those adapters are intentionally *not* bundled — they would add heavy,
optional dependencies — but the interface below is their contract.
"""

from __future__ import annotations

import abc
from collections.abc import Callable
from typing import Any

Handler = Callable[[str, Any], None]


class EventBus(abc.ABC):
    """Publish/subscribe interface for internal events."""

    @abc.abstractmethod
    def publish(self, topic: str, message: Any) -> None: ...

    @abc.abstractmethod
    def subscribe(self, topic: str, handler: Handler) -> None: ...

    @abc.abstractmethod
    def unsubscribe(self, topic: str, handler: Handler) -> None: ...


# Well-known topics used by the framework.
TOPIC_EVIDENCE = "evidence.received"
TOPIC_EVENT_DETECTED = "event.detected"
TOPIC_EVENT_UPDATED = "event.updated"
TOPIC_OUTCOME = "outcome.recorded"
