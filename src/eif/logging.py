"""Structured logging for EIF.

Provides a lightweight structured logger with no hard dependency on a logging
framework. In ``json`` mode each record is a single JSON line carrying the
contextual fields EIF cares about (request/run id, event id, organization id,
stage, provider, model, latency). Context is bound per-call via keyword args or
via :func:`bind` for a scoped adapter.
"""

from __future__ import annotations

import json
import logging
import sys
import time
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

_CONFIGURED = False

# Reserved LogRecord attributes we must not treat as structured "extra" fields.
_RESERVED = set(logging.makeLogRecord({}).__dict__.keys()) | {"message", "asctime", "taskName"}


class JsonFormatter(logging.Formatter):
    """Format log records as single-line JSON objects."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(record.created)),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key not in _RESERVED and not key.startswith("_"):
                payload[key] = value
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure(level: str = "INFO", fmt: str = "json") -> None:
    """Configure the root ``eif`` logger. Idempotent."""
    global _CONFIGURED
    logger = logging.getLogger("eif")
    logger.setLevel(level.upper())
    logger.handlers.clear()
    handler = logging.StreamHandler(sys.stderr)
    if fmt == "json":
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    logger.addHandler(handler)
    logger.propagate = False
    _CONFIGURED = True


def get_logger(name: str = "eif", **context: Any) -> logging.LoggerAdapter:
    """Return a logger adapter that injects ``context`` into every record."""
    if not _CONFIGURED:
        configure()
    base = logging.getLogger(name if name.startswith("eif") else f"eif.{name}")
    return logging.LoggerAdapter(base, context)


def bind(adapter: logging.LoggerAdapter, **context: Any) -> logging.LoggerAdapter:
    """Return a new adapter with additional bound context."""
    merged = {**(adapter.extra or {}), **context}
    return logging.LoggerAdapter(adapter.logger, merged)


@contextmanager
def stage_timer(logger: logging.LoggerAdapter, stage: str, **context: Any) -> Iterator[None]:
    """Log stage start/end with latency in milliseconds."""
    start = time.perf_counter()
    logger.info("stage.start", extra={"stage": stage, **context})
    try:
        yield
    except Exception as exc:
        latency_ms = (time.perf_counter() - start) * 1000
        logger.error(
            "stage.error",
            extra={
                "stage": stage,
                "latency_ms": round(latency_ms, 2),
                "error": str(exc),
                **context,
            },
        )
        raise
    else:
        latency_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "stage.end", extra={"stage": stage, "latency_ms": round(latency_ms, 2), **context}
        )
