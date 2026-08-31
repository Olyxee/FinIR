"""Rendering of benchmark results to dict / plain text."""

from __future__ import annotations

from .runner import SuiteResult


def suite_to_dict(suite: SuiteResult) -> dict:
    return {
        "condition": suite.condition,
        "cases": len(suite.cases),
        "detection": suite.detection().as_dict(),
        "impact_vs_label": suite.impact().as_dict(),
        "impact_vs_realized": suite.realized().as_dict(),
        "eslt": suite.eslt().as_dict(),
        "confidence_calibration_ece": suite.calibration(),
        "per_case": [
            {
                "case_id": c.case_id,
                "title": c.title,
                "detection": c.detection.as_dict(),
                "impact": c.impact.as_dict(),
                "eslt_days": (round(c.eslt_record.lead_time_days, 2) if c.eslt_record else None),
            }
            for c in suite.cases
        ],
    }


def render_suite_text(suite: SuiteResult) -> str:
    d = suite_to_dict(suite)
    det = d["detection"]
    imp = d["impact_vs_label"]
    realized = d["impact_vs_realized"]
    eslt = d["eslt"]
    lines = [
        f"EIF Benchmark Report — condition: {suite.condition}",
        "=" * 52,
        f"cases: {d['cases']}",
        "",
        "Detection:",
        f"  precision={det['precision']}  recall={det['recall']}  f1={det['f1']}",
        f"  tp={det['tp']} fp={det['fp']} fn={det['fn']}  fpr={det['false_positive_rate']}",
        "",
        "Impact vs label (reproduces intended deterministic estimate):",
        f"  n={imp['n']}  MAE={imp['mae']}  MAPE={imp['mape']}  interval_coverage={imp['interval_coverage']}",
        "",
        "Impact vs realized outcome (honest estimate accuracy):",
        f"  n={realized['n']}  MAE={realized['mae']}  MAPE={realized['mape']}",
        "",
        "ESLT (Economic Signal Lead Time, days):",
        f"  n={eslt['n']}  mean={eslt['mean_days']}  median={eslt['median_days']}",
        f"  min={eslt['min_days']}  max={eslt['max_days']}  positive_fraction={eslt['positive_fraction']}",
        f"  95% CI=[{eslt['ci95_low']}, {eslt['ci95_high']}]",
        "",
        f"Confidence calibration (ECE): {d['confidence_calibration_ece']}",
        "",
        "Per-case:",
    ]
    for c in d["per_case"]:
        cd = c["detection"]
        lines.append(
            f"  - {c['case_id']}: f1={cd['f1']} tp={cd['tp']} fp={cd['fp']} fn={cd['fn']} "
            f"impact_mae={c['impact']['mae']} eslt_days={c['eslt_days']}"
        )
    return "\n".join(lines)


def render_comparison_text(baseline: SuiteResult, eif: SuiteResult) -> str:
    b = suite_to_dict(baseline)
    e = suite_to_dict(eif)
    lines = [
        "EIF Research Comparison — baseline (structured-only) vs EIF (multimodal)",
        "=" * 72,
        f"{'metric':<28}{'baseline':>18}{'eif':>18}",
        "-" * 64,
        _row("detection.f1", b["detection"]["f1"], e["detection"]["f1"]),
        _row("detection.recall", b["detection"]["recall"], e["detection"]["recall"]),
        _row("detection.precision", b["detection"]["precision"], e["detection"]["precision"]),
        _row(
            "impact.mae_vs_realized", b["impact_vs_realized"]["mae"], e["impact_vs_realized"]["mae"]
        ),
        _row(
            "impact.mape_vs_realized",
            b["impact_vs_realized"]["mape"],
            e["impact_vs_realized"]["mape"],
        ),
        _row(
            "impact.coverage_vs_label",
            b["impact_vs_label"]["interval_coverage"],
            e["impact_vs_label"]["interval_coverage"],
        ),
        _row("eslt.mean_days", b["eslt"]["mean_days"], e["eslt"]["mean_days"]),
        _row("eslt.median_days", b["eslt"]["median_days"], e["eslt"]["median_days"]),
        _row("eslt.n", b["eslt"]["n"], e["eslt"]["n"]),
    ]
    return "\n".join(lines)


def _row(name: str, b, e) -> str:
    return f"{name:<28}{b!s:>18}{e!s:>18}"
