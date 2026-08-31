"""Benchmark runner.

Runs each case through EIF in an isolated in-memory repository and computes
detection, impact, and ESLT metrics against the case labels. Supports an
evidence-modality filter so the same harness can run the research experiment's
two conditions:

* **baseline** — structured/tabular evidence only (CSV/Excel/JSON);
* **eif** — the full multimodal evidence set.

The runner is deterministic: same cases + same config -> same results.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from ..config import Config
from ..domain import EconomicEvent
from ..evaluation.eslt import ESLTRecord, ESLTSummary, compute_eslt
from ..evaluation.metrics import (
    DetectionMetrics,
    ImpactMetrics,
    MatchResult,
    calibration_error,
    impact_metrics,
    match_events,
)
from ..facade import EIF
from .model import BenchmarkCase, load_suite

# Evidence file suffixes considered "structured" for the baseline condition.
STRUCTURED_SUFFIXES = {".csv", ".tsv", ".xlsx", ".xlsm", ".json"}


@dataclass
class CaseResult:
    case_id: str
    title: str
    condition: str
    predicted: list[EconomicEvent]
    match: MatchResult
    impact: ImpactMetrics
    eslt_record: ESLTRecord | None = None
    # Honest estimate-vs-actual error: predicted point vs realized outcome value.
    realized_n: int = 0
    realized_abs_error_sum: float = 0.0
    realized_abs_pct_error_sum: float = 0.0

    @property
    def detection(self) -> DetectionMetrics:
        return self.match.detection

    @property
    def realized_mae(self) -> float | None:
        return self.realized_abs_error_sum / self.realized_n if self.realized_n else None

    @property
    def realized_mape(self) -> float | None:
        return self.realized_abs_pct_error_sum / self.realized_n if self.realized_n else None


@dataclass
class SuiteResult:
    condition: str
    cases: list[CaseResult] = field(default_factory=list)

    def detection(self) -> DetectionMetrics:
        agg = DetectionMetrics()
        for c in self.cases:
            d = c.detection
            agg.tp += d.tp
            agg.fp += d.fp
            agg.fn += d.fn
        return agg

    def impact(self) -> ImpactMetrics:
        maes, mapes, covs, weights = [], [], [], []
        for c in self.cases:
            if c.impact.n:
                maes.append((c.impact.mae or 0) * c.impact.n)
                if c.impact.mape is not None:
                    mapes.append(c.impact.mape * c.impact.n)
                if c.impact.interval_coverage is not None:
                    covs.append(c.impact.interval_coverage * c.impact.n)
                weights.append(c.impact.n)
        total = sum(weights)
        if not total:
            return ImpactMetrics()
        return ImpactMetrics(
            n=total,
            mae=sum(maes) / total if maes else None,
            mape=sum(mapes) / total if mapes else None,
            interval_coverage=sum(covs) / total if covs else None,
        )

    def eslt(self) -> ESLTSummary:
        records = [c.eslt_record for c in self.cases if c.eslt_record is not None]
        return compute_eslt(records)

    def realized(self) -> ImpactMetrics:
        n = sum(c.realized_n for c in self.cases)
        if not n:
            return ImpactMetrics()
        ae = sum(c.realized_abs_error_sum for c in self.cases)
        ape = sum(c.realized_abs_pct_error_sum for c in self.cases)
        return ImpactMetrics(n=n, mae=ae / n, mape=ape / n, interval_coverage=None)

    def calibration(self) -> float:
        confidences: list[float] = []
        correct: list[bool] = []
        for c in self.cases:
            matched_pred = {p.predicted.id for p in c.match.matched}
            for ev in c.predicted:
                confidences.append(ev.confidence.score)
                correct.append(ev.id in matched_pred)
        return calibration_error(confidences, correct)


def run_case(
    case: BenchmarkCase,
    *,
    config: Config | None = None,
    condition: str = "eif",
    structured_only: bool = False,
) -> CaseResult:
    """Run one case and score it. Uses an isolated in-memory repository."""
    cfg = config.model_copy(deep=True) if config else Config()
    cfg.storage.database_url = "memory"
    cfg.logging.level = "ERROR"

    eif = EIF(cfg)
    files = case.evidence_files()
    if structured_only:
        files = [f for f in files if f.suffix.lower() in STRUCTURED_SUFFIXES]

    evidence = eif.load_evidence([str(f) for f in files])
    # Stamp the case date so detection time reflects evidence availability, not now.
    for ev in evidence:
        if case.evidence_date is not None and ev.created_at is None:
            ev.created_at = case.evidence_date
    result = eif.pipeline.process_evidence(evidence)
    predicted = result.events

    # Score detection over *material* predictions: non-material events are stored
    # but are not "alarms", so they must not count as false positives.
    scored = [e for e in predicted if str(e.materiality) == "material"]
    match = match_events(scored, case.gold_events)
    impact = impact_metrics(match.matched)

    eslt_record = _eslt_for_case(case, match)
    realized_n, realized_ae, realized_ape = _realized_error(case, match)
    eif.close()
    return CaseResult(
        case_id=case.case_id,
        title=case.title,
        condition=condition,
        predicted=predicted,
        match=match,
        impact=impact,
        eslt_record=eslt_record,
        realized_n=realized_n,
        realized_abs_error_sum=realized_ae,
        realized_abs_pct_error_sum=realized_ape,
    )


def run_suite(
    root: str | Path,
    *,
    config: Config | None = None,
    condition: str = "eif",
    structured_only: bool = False,
) -> SuiteResult:
    """Run every case under ``root`` and aggregate results."""
    suite = SuiteResult(condition=condition)
    for case in load_suite(root):
        suite.cases.append(
            run_case(case, config=config, condition=condition, structured_only=structured_only)
        )
    return suite


def _realized_error(case: BenchmarkCase, match: MatchResult) -> tuple[int, float, float]:
    """Sum absolute and absolute-percentage error of estimates vs realized outcomes."""
    if case.realized is None or not case.realized.realized_metrics:
        return 0, 0.0, 0.0
    n = 0
    ae = 0.0
    ape = 0.0
    for pair in match.matched:
        impact = pair.predicted.primary_impact()
        if impact is None:
            continue
        actual = case.realized.realized_metrics.get(impact.metric)
        if actual is None:
            continue
        predicted_value = abs(impact.estimate.point)
        actual_value = abs(actual)
        n += 1
        ae += abs(predicted_value - actual_value)
        if actual_value:
            ape += abs(predicted_value - actual_value) / actual_value
    return n, ae, ape


def _eslt_for_case(case: BenchmarkCase, match: MatchResult) -> ESLTRecord | None:
    if case.traditional is None or case.traditional.detected_at is None:
        return None
    if not match.matched:
        return None
    # Use the earliest matched EIF event as the detection time.
    earliest = min(match.matched, key=lambda p: p.predicted.detected_at).predicted
    return ESLTRecord(
        event_id=earliest.id,
        event_type=earliest.event_type,
        eif_detected_at=earliest.detected_at,
        traditional_detected_at=case.traditional.detected_at,
        traditional_source=case.traditional.source,
    )
