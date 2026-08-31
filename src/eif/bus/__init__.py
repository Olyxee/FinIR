"""Event bus abstraction and in-process implementation."""

from __future__ import annotations

from .base import (
    TOPIC_EVENT_DETECTED,
    TOPIC_EVENT_UPDATED,
    TOPIC_EVIDENCE,
    TOPIC_OUTCOME,
    EventBus,
    Handler,
)
from .inprocess import InProcessEventBus

__all__ = [
    "TOPIC_EVENT_DETECTED",
    "TOPIC_EVENT_UPDATED",
    "TOPIC_EVIDENCE",
    "TOPIC_OUTCOME",
    "EventBus",
    "Handler",
    "InProcessEventBus",
]
