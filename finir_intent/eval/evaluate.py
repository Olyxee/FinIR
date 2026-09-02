#!/usr/bin/env python3
"""FinIR-IntentBench evaluation suite.

Reproducible, deterministic (no network, no LLM). Loads
``intentbench/examples/intentbench_v1.jsonl``, runs the FinIR-Intent baseline on every
instruction, checks the prediction against the *canonical* JSON Schema
(``finir.intent.json_schema()`` -- the core package's schema, never a local copy),
scores it against the paired expected intent, and -- for predictions the contract
says are executable -- actually executes them against a small reference
``FinancialModel`` via the real ``finir.intent.execute_intent`` to prove the
end-to-end path works. No number in this script's output is hand-typed; every
metric is computed from the run.

    python eval/evaluate.py
    python eval/evaluate.py --dataset intentbench/examples/intentbench_v1.jsonl --out eval/results/latest.json
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import jsonschema
from finir.intent import FinIRIntent, IntentValidationError, execute_intent, json_schema

HERE = Path(__file__).resolve().parent
WORKSTREAM_ROOT = HERE.parent
CORE_FIXTURES = WORKSTREAM_ROOT.parent / "tests" / "fixtures" / "intents"

sys.path.insert(0, str(WORKSTREAM_ROOT / "src"))
from finir_intent import build_reference_model, compile_intent  # noqa: E402

_TOL = 1e-9


# --------------------------------------------------------------------------- dataset
def load_dataset(path: Path) -> list[dict[str, Any]]:
    examples = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        if "fixture" in row:
            fixture_path = CORE_FIXTURES / row["fixture"]
            row["expected_intent"] = json.loads(fixture_path.read_text(encoding="utf-8"))
        examples.append(row)
    return examples


# ------------------------------------------------------------------ comparison utils
def _flatten_ops(intent: dict[str, Any]) -> dict[tuple[str | None, str], dict[str, Any]]:
    """Map (scenario_name_or_None, target) -> operation, for order-independent comparison.

    Operations within one list are "simultaneous" per the contract (order-independent);
    duplicate targets are themselves invalid, so this key is always unique for a
    structurally valid intent.
    """
    flat: dict[tuple[str | None, str], dict[str, Any]] = {}
    for op in intent.get("operations", []) or []:
        flat[(None, op["target"])] = op
    for sc in intent.get("scenarios", []) or []:
        for op in sc.get("operations", []):
            flat[(sc["name"], op["target"])] = op
    return flat


def _values_match(a: dict[str, Any], b: dict[str, Any]) -> bool:
    if a.get("operation") == "range":
        return all(
            a.get(f) is not None
            and b.get(f) is not None
            and math.isclose(a[f], b[f], rel_tol=_TOL, abs_tol=_TOL)
            for f in ("min", "max")
        ) and a.get("steps") == b.get("steps")
    av, bv = a.get("value"), b.get("value")
    if av is None or bv is None:
        return av == bv
    return math.isclose(av, bv, rel_tol=_TOL, abs_tol=_TOL)


# ---------------------------------------------------------------------------- scoring
def evaluate(examples: list[dict[str, Any]], *, verbose: bool = False) -> dict[str, Any]:
    schema = json_schema()
    validator = jsonschema.Draft202012Validator(schema)
    ref_model = build_reference_model()

    per_example: list[dict[str, Any]] = []
    status_confusion: Counter[tuple[str, str]] = Counter()

    op_total = op_correct = 0
    target_total = target_correct = 0
    value_total = value_correct = 0
    unit_total = unit_correct = 0
    currency_total = currency_correct = 0

    n_schema_valid = 0
    multi_op_examples = 0
    multi_op_exact = 0

    ambiguity_tp = ambiguity_fp = ambiguity_fn = ambiguity_tn = 0

    for ex in examples:
        text = ex["text"]
        expected = ex["expected_intent"]
        predicted = compile_intent(text)

        schema_errors = sorted(validator.iter_errors(predicted), key=str)
        is_schema_valid = not schema_errors
        n_schema_valid += int(is_schema_valid)

        status_confusion[(expected["status"], predicted["status"])] += 1
        status_ok = predicted["status"] == expected["status"]

        exp_nonexec = expected["status"] in ("ambiguous", "unsupported", "invalid")
        pred_nonexec = predicted["status"] in ("ambiguous", "unsupported", "invalid")
        if exp_nonexec and pred_nonexec:
            ambiguity_tp += 1
        elif exp_nonexec and not pred_nonexec:
            ambiguity_fn += 1
        elif not exp_nonexec and pred_nonexec:
            ambiguity_fp += 1
        else:
            ambiguity_tn += 1

        exp_flat = _flatten_ops(expected) if expected["status"] == "valid" else {}
        pred_flat = _flatten_ops(predicted) if predicted["status"] == "valid" else {}

        example_op_correct = 0
        for key, exp_op in exp_flat.items():
            op_total += 1
            target_total += 1
            pred_op = pred_flat.get(key)
            target_hit = pred_op is not None
            target_correct += int(target_hit)
            op_hit = target_hit and pred_op.get("operation") == exp_op.get("operation")
            op_correct += int(op_hit)
            example_op_correct += int(op_hit)
            if op_hit:
                value_total += 1
                value_correct += int(_values_match(exp_op, pred_op))
                unit_total += 1
                unit_correct += int(exp_op.get("unit") == pred_op.get("unit"))
                currency_total += 1
                currency_correct += int(exp_op.get("currency") == pred_op.get("currency"))

        is_multi = ex.get("category") == "multi_operation"
        if is_multi:
            multi_op_examples += 1
            exact = (
                status_ok
                and pred_flat.keys() == exp_flat.keys()
                and example_op_correct == len(exp_flat)
                and all(
                    _values_match(exp_flat[k], pred_flat[k])
                    and exp_flat[k].get("unit") == pred_flat[k].get("unit")
                    for k in exp_flat
                )
            )
            multi_op_exact += int(exact)

        # -- end-to-end execution proof (only meaningful for schema-valid predictions)
        exec_note = None
        if is_schema_valid:
            expects_semantic_reject = ex.get("execution_expectation") == "semantic_reject"
            try:
                FinIRIntent.from_obj(predicted)  # structural re-check via the core Python types
                if predicted["status"] == "valid":
                    execute_intent(ref_model, predicted)
                    exec_note = (
                        "executed"
                        if not expects_semantic_reject
                        else "executed_but_expected_semantic_reject"
                    )
                else:
                    try:
                        execute_intent(ref_model, predicted)
                        exec_note = "unexpectedly_executed_nonvalid_status"
                    except IntentValidationError:
                        exec_note = "correctly_refused_nonvalid_status"
            except IntentValidationError as exc:
                exec_note = (
                    "semantically_rejected"
                    if expects_semantic_reject
                    else f"unexpected_reject: {exc}"
                )

        per_example.append(
            {
                "id": ex["id"],
                "category": ex.get("category"),
                "difficulty": ex.get("difficulty", "core"),
                "text": text,
                "expected_status": expected["status"],
                "predicted_status": predicted["status"],
                "status_ok": status_ok,
                "schema_valid": is_schema_valid,
                "schema_errors": [e.message for e in schema_errors] if schema_errors else [],
                "predicted": predicted,
                "execution": exec_note,
            }
        )
        if verbose:
            mark = "OK " if status_ok else "FAIL"
            print(f"[{mark}] {ex['id']:<35} exec={exec_note}")

    def _pct(n: int, d: int) -> float | None:
        return round(n / d, 4) if d else None

    precision = _pct(ambiguity_tp, ambiguity_tp + ambiguity_fp)
    recall = _pct(ambiguity_tp, ambiguity_tp + ambiguity_fn)
    # NOTE: precision/recall of exactly 0.0 are valid values, not "missing" -- must
    # check `is not None`, not truthiness, or a genuine 0 gets silently misreported
    # as an undefined F1 instead of the mathematically correct 0.0.
    f1 = None
    if precision is not None and recall is not None and (precision + recall) > 0:
        f1 = round(2 * precision * recall / (precision + recall), 4)

    n = len(examples)
    metrics = {
        "n_examples": n,
        "schema_validity_rate": _pct(n_schema_valid, n),
        "status_accuracy": _pct(sum(1 for e in per_example if e["status_ok"]), n),
        "operation_accuracy": _pct(op_correct, op_total),
        "target_accuracy": _pct(target_correct, target_total),
        "value_accuracy": _pct(value_correct, value_total),
        "unit_accuracy": _pct(unit_correct, unit_total),
        "currency_accuracy_extra": _pct(currency_correct, currency_total),
        "ambiguity_handling": {
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "tp": ambiguity_tp,
            "fp": ambiguity_fp,
            "fn": ambiguity_fn,
            "tn": ambiguity_tn,
        },
        "multi_operation_accuracy": _pct(multi_op_exact, multi_op_examples),
        "status_confusion_matrix": {
            f"{exp}->{pred}": c for (exp, pred), c in sorted(status_confusion.items())
        },
    }

    # Break out core vs. stress (paraphrase / known-limitation) subsets for honesty.
    by_difficulty: dict[str, Any] = {}
    for difficulty in sorted({e["difficulty"] for e in per_example}):
        subset = [e for e in per_example if e["difficulty"] == difficulty]
        by_difficulty[difficulty] = {
            "n_examples": len(subset),
            "status_accuracy": _pct(sum(1 for e in subset if e["status_ok"]), len(subset)),
            "schema_validity_rate": _pct(sum(1 for e in subset if e["schema_valid"]), len(subset)),
        }
    metrics["by_difficulty"] = by_difficulty

    return {"metrics": metrics, "examples": per_example}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dataset",
        default=str(WORKSTREAM_ROOT / "intentbench" / "examples" / "intentbench_v1.jsonl"),
    )
    parser.add_argument("--out", default=str(HERE / "results" / "latest.json"))
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    examples = load_dataset(Path(args.dataset))
    report = evaluate(examples, verbose=args.verbose)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(json.dumps(report["metrics"], indent=2))
    print(f"\nFull per-example report written to {out_path}")


if __name__ == "__main__":
    main()
