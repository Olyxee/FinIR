"""SQLAlchemy-backed persistence for EIF (SQLite in dev, PostgreSQL in prod)."""

from __future__ import annotations

from .repository import SqlRepository

__all__ = ["SqlRepository"]
