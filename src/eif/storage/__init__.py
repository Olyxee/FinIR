"""Persistence layer: repository interface, in-memory + SQL backends."""

from __future__ import annotations

from ..config import Config, StorageConfig
from .base import (
    EntityQuery,
    EventQuery,
    Page,
    Repository,
    RepositoryStats,
)
from .memory import MemoryRepository

__all__ = [
    "EntityQuery",
    "EventQuery",
    "MemoryRepository",
    "Page",
    "Repository",
    "RepositoryStats",
    "open_repository",
]


def open_repository(config: Config | StorageConfig | str | None = None) -> Repository:
    """Open a repository from config.

    * ``None`` or ``"memory"`` / ``"memory://"`` -> in-memory repository.
    * any SQLAlchemy URL (e.g. ``sqlite:///./eif.db``, ``postgresql+psycopg://...``)
      -> :class:`~eif.storage.sql.repository.SqlRepository` with schema created.
    """
    if config is None:
        return MemoryRepository()

    if isinstance(config, Config):
        url = config.storage.database_url
        echo = config.storage.echo_sql
    elif isinstance(config, StorageConfig):
        url = config.database_url
        echo = config.echo_sql
    else:
        url = config
        echo = False

    if url in ("memory", "memory://", ":memory:"):
        return MemoryRepository()

    from .sql import SqlRepository

    repo = SqlRepository(url, echo=echo)
    repo.init_schema()
    return repo
