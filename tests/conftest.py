"""Shared pytest fixtures."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from eif.config import Config
from eif.facade import EIF
from eif.storage import open_repository


@pytest.fixture
def config() -> Config:
    cfg = Config()
    cfg.storage.database_url = "memory"
    cfg.logging.level = "ERROR"
    return cfg


@pytest.fixture
def memory_repo():
    return open_repository("memory")


@pytest.fixture
def eif(config: Config) -> EIF:
    instance = EIF(config)
    yield instance
    instance.close()


@pytest.fixture
def supplier_case(tmp_path: Path) -> list[str]:
    """Write the canonical supplier scenario and return the file paths."""
    email = tmp_path / "supplier_email.txt"
    email.write_text(
        "Supplier ABC will implement a 10% price increase on SKU-A, effective 1 November 2026.",
        encoding="utf-8",
    )
    csv = tmp_path / "purchase_history.csv"
    csv.write_text(
        "po_number,supplier,product,amount\n"
        "PO-1,ABC,SKU-A,10500000\n"
        "PO-2,ABC,SKU-A,10500000\n"
        "PO-3,ABC,SKU-A,10500000\n"
        "PO-4,ABC,SKU-A,10500000\n",
        encoding="utf-8",
    )
    return [str(email), str(csv)]


@pytest.fixture
def utc_now() -> datetime:
    return datetime.now(UTC)
