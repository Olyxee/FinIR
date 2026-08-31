"""Benchmark case model and the open benchmark format.

A benchmark case is a directory::

    case/
      case.json                         # metadata (id, title, synthetic flag, date)
      evidence/                         # the multimodal evidence EIF ingests
        supplier_email.txt
        purchase_orders.csv
      labels/
        economic_event.json            # gold EconomicEvent labels
        realized_outcome.json          # what actually happened (optional)
        traditional_detection.json     # when structured data would flag it (optional)

All shipped cases are clearly marked ``"synthetic": true``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from dateutil import parser as dateparser

from ..evaluation.metrics import GoldEvent
from ..exceptions import EIFError


@dataclass
class RealizedLabel:
    occurred: bool = True
    realized_at: datetime | None = None
    realized_metrics: dict[str, float] = field(default_factory=dict)
    currency: str | None = None


@dataclass
class TraditionalLabel:
    detected_at: datetime | None = None
    source: str | None = None


@dataclass
class BenchmarkCase:
    case_id: str
    title: str
    path: Path
    description: str = ""
    synthetic: bool = True
    evidence_date: datetime | None = None
    gold_events: list[GoldEvent] = field(default_factory=list)
    realized: RealizedLabel | None = None
    traditional: TraditionalLabel | None = None

    @property
    def evidence_dir(self) -> Path:
        return self.path / "evidence"

    def evidence_files(self) -> list[Path]:
        if not self.evidence_dir.is_dir():
            return []
        return sorted(p for p in self.evidence_dir.glob("*") if p.is_file())


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    dt = dateparser.parse(value)
    if dt is not None and dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt


def load_case(path: str | Path) -> BenchmarkCase:
    """Load a single benchmark case directory."""
    path = Path(path)
    meta_file = path / "case.json"
    if not meta_file.is_file():
        raise EIFError(f"Benchmark case missing case.json: {path}")
    meta = json.loads(meta_file.read_text(encoding="utf-8"))

    labels_dir = path / "labels"
    gold_events = _load_gold_events(labels_dir / "economic_event.json")
    realized = _load_realized(labels_dir / "realized_outcome.json")
    traditional = _load_traditional(labels_dir / "traditional_detection.json")

    return BenchmarkCase(
        case_id=meta.get("id", path.name),
        title=meta.get("title", path.name),
        description=meta.get("description", ""),
        synthetic=meta.get("synthetic", True),
        evidence_date=_parse_dt(meta.get("evidence_date")),
        gold_events=gold_events,
        realized=realized,
        traditional=traditional,
        path=path,
    )


def load_suite(root: str | Path) -> list[BenchmarkCase]:
    """Load all benchmark cases under ``root`` (each subdir with a case.json)."""
    root = Path(root)
    cases: list[BenchmarkCase] = []
    for meta_file in sorted(root.glob("**/case.json")):
        cases.append(load_case(meta_file.parent))
    return cases


def _load_gold_events(path: Path) -> list[GoldEvent]:
    if not path.is_file():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    events = data.get("events", data) if isinstance(data, dict) else data
    return [GoldEvent.model_validate(e) for e in events]


def _load_realized(path: Path) -> RealizedLabel | None:
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return RealizedLabel(
        occurred=data.get("occurred", True),
        realized_at=_parse_dt(data.get("realized_at")),
        realized_metrics=data.get("realized_metrics", {}),
        currency=data.get("currency"),
    )


def _load_traditional(path: Path) -> TraditionalLabel | None:
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return TraditionalLabel(
        detected_at=_parse_dt(data.get("detected_at")),
        source=data.get("source"),
    )
