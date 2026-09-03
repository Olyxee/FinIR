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
from finir_intent import build_reference_model, compile_intent  # type: ignore[attr-defined]  # noqa: E402, I001

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


def _pct(n: int, d: int) -> float | None:
    return round(n / d, 4) if d else None


def _aggregate(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute the full metric suite over any subset of per-example records.

    Every op-level count is carried on the record itself, so overall / core / stress
    are scored by exactly the same code path -- no metric can drift between subsets.
    """
    n = len(records)
    op_total = sum(r["op_total"] for r in records)
    op_correct = sum(r["op_correct"] for r in records)
    target_correct = sum(r["target_correct"] for r in records)
    value_total = sum(r["value_total"] for r in records)
    value_correct = sum(r["value_correct"] for r in records)
    unit_correct = sum(r["unit_correct"] for r in records)
    currency_correct = sum(r["currency_correct"] for r in records)

    tp = sum(1 for r in records if r["exp_nonexec"] and r["pred_nonexec"])
    fp = sum(1 for r in records if not r["exp_nonexec"] and r["pred_nonexec"])
    fn = sum(1 for r in records if r["exp_nonexec"] and not r["pred_nonexec"])
    tn = sum(1 for r in records if not r["exp_nonexec"] and not r["pred_nonexec"])
    precision = _pct(tp, tp + fp)
    recall = _pct(tp, tp + fn)
    # 0.0 precision/recall are valid values, not "missing": test `is not None`.
    f1 = None
    if precision is not None and recall is not None and (precision + recall) > 0:
        f1 = round(2 * precision * recall / (precision + recall), 4)

    multi = [r for r in records if r["category"] == "multi_operation"]
    scenario = [r for r in records if r["category"] == "scenario"]
    executable = [r for r in records if r["exec_executable"]]
    exec_ok = [r for r in executable if r["exec_note"] == "executed"]
    sem = [r for r in records if r["expects_semantic_reject"]]
    sem_ok = [r for r in sem if r["exec_note"] == "semantically_rejected"]

    return {
        "n_examples": n,
        "schema_validity_rate": _pct(sum(r["schema_valid"] for r in records), n),
        "status_accuracy": _pct(sum(r["status_ok"] for r in records), n),
        "operation_accuracy": _pct(op_correct, op_total),
        "target_accuracy": _pct(target_correct, op_total),
        "value_accuracy": _pct(value_correct, value_total),
        "unit_accuracy": _pct(unit_correct, value_total),
        "currency_accuracy": _pct(currency_correct, value_total),
        "ambiguity_handling": {
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "tn": tn,
        },
        "multi_operation_accuracy": _pct(sum(r["exact_match"] for r in multi), len(multi)),
        "scenario_accuracy": _pct(sum(r["exact_match"] for r in scenario), len(scenario)),
        "runtime_execution_success_rate": _pct(len(exec_ok), len(executable)),
        "semantic_rejection_correctness": _pct(len(sem_ok), len(sem)),
    }


# ---------------------------------------------------------------------------- scoring
def evaluate(examples: list[dict[str, Any]], *, verbose: bool = False) -> dict[str, Any]:
    schema = json_schema()
    validator = jsonschema.Draft202012Validator(schema)
    ref_model = build_reference_model()

    per_example: list[dict[str, Any]] = []
    status_confusion: Counter[tuple[str, str]] = Counter()

    for ex in examples:
        text = ex["text"]
        expected = ex["expected_intent"]
        predicted = compile_intent(text)

        schema_errors = sorted(validator.iter_errors(predicted), key=str)
        is_schema_valid = not schema_errors

        status_confusion[(expected["status"], predicted["status"])] += 1
        status_ok = predicted["status"] == expected["status"]

        exp_nonexec = expected["status"] in ("ambiguous", "unsupported", "invalid")
        pred_nonexec = predicted["status"] in ("ambiguous", "unsupported", "invalid")

        exp_flat = _flatten_ops(expected) if expected["status"] == "valid" else {}
        pred_flat = _flatten_ops(predicted) if predicted["status"] == "valid" else {}

        op_total = op_correct = target_correct = 0
        value_total = value_correct = unit_correct = currency_correct = 0
        for key, exp_op in exp_flat.items():
            op_total += 1
            pred_op = pred_flat.get(key)
            if pred_op is None:
                continue
            target_correct += 1
            if pred_op.get("operation") == exp_op.get("operation"):
                op_correct += 1
                value_total += 1
                value_correct += int(_values_match(exp_op, pred_op))
                unit_correct += int(exp_op.get("unit") == pred_op.get("unit"))
                currency_correct += int(exp_op.get("currency") == pred_op.get("currency"))

        # exact match (all keys present, every op/value/unit correct) -- used for
        # both multi-operation and scenario categories.
        exact_match = (
            status_ok
            and pred_flat.keys() == exp_flat.keys()
            and op_correct == len(exp_flat)
            and all(
                _values_match(exp_flat[k], pred_flat[k])
                and exp_flat[k].get("unit") == pred_flat[k].get("unit")
                for k in exp_flat
            )
        )

        expects_semantic_reject = ex.get("execution_expectation") == "semantic_reject"
        # "executable" = a schema-valid prediction the contract marks runnable that
        # is NOT expected to be a semantic reject (so success is the right outcome).
        exec_executable = (
            is_schema_valid and predicted["status"] == "valid" and not expects_semantic_reject
        )

        exec_note = None
        if is_schema_valid:
            try:
                FinIRIntent.from_obj(predicted)  # structural re-check via core Python types
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
                # -- fields the aggregator consumes (subset-scored uniformly) --
                "exp_nonexec": exp_nonexec,
                "pred_nonexec": pred_nonexec,
                "op_total": op_total,
                "op_correct": op_correct,
                "target_correct": target_correct,
                "value_total": value_total,
                "value_correct": value_correct,
                "unit_correct": unit_correct,
                "currency_correct": currency_correct,
                "exact_match": exact_match,
                "exec_executable": exec_executable,
                "expects_semantic_reject": expects_semantic_reject,
                "exec_note": exec_note,
            }
        )
        if verbose:
            mark = "OK " if status_ok else "FAIL"
            print(f"[{mark}] {ex['id']:<35} exec={exec_note}")

    metrics: dict[str, Any] = {"overall": _aggregate(per_example)}
    metrics["by_difficulty"] = {
        difficulty: _aggregate([e for e in per_example if e["difficulty"] == difficulty])
        for difficulty in sorted({e["difficulty"] for e in per_example})
    }
    metrics["status_confusion_matrix"] = {
        f"{exp}->{pred}": c for (exp, pred), c in sorted(status_confusion.items())
    }

    # keep the flat top-level metric keys too, for backward compatibility with any
    # tooling / tests that read report["metrics"]["status_accuracy"] directly.
    for k, v in metrics["overall"].items():
        metrics.setdefault(k, v)

    # trim the aggregator-only bookkeeping fields out of the persisted per-example list
    _internal = {
        "exp_nonexec",
        "pred_nonexec",
        "op_total",
        "op_correct",
        "target_correct",
        "value_total",
        "value_correct",
        "unit_correct",
        "currency_correct",
        "exact_match",
        "exec_executable",
        "expects_semantic_reject",
        "exec_note",
    }
    clean_examples = [{k: v for k, v in r.items() if k not in _internal} for r in per_example]
    return {"metrics": metrics, "examples": clean_examples}


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
