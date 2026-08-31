"""The persistent economic event graph and its resolution interfaces."""

from __future__ import annotations

from .graph import EventGraph, IntegrationResult
from .resolution import (
    ACTION_CONTRADICT,
    ACTION_NEW,
    ACTION_REINFORCE,
    ACTION_RESOLVE,
    ACTION_WEAKEN,
    DefaultEntityResolver,
    DefaultEventResolver,
    EntityResolution,
    EntityResolver,
    EventMatch,
    EventResolver,
)

__all__ = [
    "ACTION_CONTRADICT",
    "ACTION_NEW",
    "ACTION_REINFORCE",
    "ACTION_RESOLVE",
    "ACTION_WEAKEN",
    "DefaultEntityResolver",
    "DefaultEventResolver",
    "EntityResolution",
    "EntityResolver",
    "EventGraph",
    "EventMatch",
    "EventResolver",
    "IntegrationResult",
]
