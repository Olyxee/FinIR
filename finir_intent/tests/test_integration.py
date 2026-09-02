"""End-to-end proof: a baseline-generated intent executes against the *real* FinIR
runtime -- no execution logic is duplicated in this package.

Also runs the full evaluation suite once and asserts floors on the "core" (curated,
in-distribution) examples, so a regression in the baseline's supported phrasing is
caught by ``pytest`` and not just by manually reading eval/results/latest.json.
"""

from __future__ import annotations

import sys
from pathlib import Path

from finir.intent import execute_intent

WORKSTREAM_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKSTREAM_ROOT / "eval"))
sys.path.insert(0, str(WORKSTREAM_ROOT / "src"))

from evaluate import evaluate, load_dataset  # noqa: E402
from finir_intent import build_reference_model, compile_intent  # noqa: E402

DATASET = WORKSTREAM_ROOT / "intentbench" / "examples" / "intentbench_v1.jsonl"


def test_valid_relative_change_executes_against_the_real_runtime() -> None:
    model = build_reference_model()
    envelope = compile_intent("Increase COGS by 4%.")
    result = model.apply_intent(envelope)  # the real FinancialModel, not a mock
    base = model.evaluate()
    assert float(result["ebitda"]) != float(base["ebitda"])  # cogs actually moved downstream


def test_valid_multi_operation_executes_simultaneously() -> None:
    model = build_reference_model()
    envelope = compile_intent(
        "Revenue falls 8%, COGS rises 3%, and extend payment terms to 60 days."
    )
    execution = execute_intent(model, envelope)
    assert execution.status == "valid"
    assert execution.result is not None


def test_valid_scenario_executes_and_returns_one_result_per_scenario() -> None:
    model = build_reference_model()
    envelope = compile_intent(
        "Base scenario: no changes. Upside scenario: revenue grows 10%. "
        "Downside scenario: revenue falls 8% and COGS rises 5%."
    )
    execution = execute_intent(model, envelope)
    assert execution.scenario_results is not None
    assert set(execution.scenario_results) == {"base", "upside", "downside"}


def test_ambiguous_and_unsupported_are_refused_by_the_real_runtime() -> None:
    model = build_reference_model()
    for text in ("Improve margins next year.", "Acquire our largest competitor."):
        envelope = compile_intent(text)
        try:
            model.apply_intent(envelope)
            raise AssertionError(f"{text!r} should not have executed")
        except Exception as exc:  # IntentValidationError
            assert type(exc).__name__ == "IntentValidationError"


def test_structurally_valid_but_semantically_wrong_intents_are_rejected_at_execution() -> None:
    """The NL layer must faithfully transcribe -- never 'fix' -- a currency/unit
    mismatch; the *runtime* is what rejects it (docs/intent-contract.md)."""
    model = build_reference_model()
    envelope = compile_intent("Increase revenue by USD 2,000,000.")
    assert envelope["status"] == "valid"  # structurally valid: no guessing/correcting here
    try:
        model.apply_intent(envelope)
        raise AssertionError("currency mismatch should have been rejected at execution")
    except Exception as exc:
        assert type(exc).__name__ == "IntentValidationError"


def test_intentbench_core_floor() -> None:
    """Regression gate on the curated ('core') subset -- the 'stress' subset is
    expected to expose real, documented baseline limitations and is intentionally
    excluded from this floor (see MODEL_CARD.md 'known limitations')."""
    examples = load_dataset(DATASET)
    report = evaluate(examples)
    core = report["metrics"]["by_difficulty"]["core"]
    assert core["schema_validity_rate"] == 1.0
    assert core["status_accuracy"] == 1.0
    assert report["metrics"]["schema_validity_rate"] == 1.0  # true for ALL examples, incl. stress
