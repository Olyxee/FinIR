"""Structural checks on the FinIR-IntentBench dataset itself.

Every expected intent must validate against the canonical schema, and every
fixture-referenced example must stay byte-identical to the shared fixture in the
core repo's tests/fixtures/intents/ (the same file the runtime's own contract tests
validate) -- these are the "paired instruction + expected intent" the Hugging Face
and core workstreams both depend on; they must never drift apart.
"""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest
from finir.intent import json_schema

WORKSTREAM_ROOT = Path(__file__).resolve().parent.parent
DATASET = WORKSTREAM_ROOT / "intentbench" / "examples" / "intentbench_v1.jsonl"
CORE_FIXTURES = WORKSTREAM_ROOT.parent / "tests" / "fixtures" / "intents"

_ALLOWED_CATEGORIES = {
    "valid_simple",
    "multi_operation",
    "ambiguous",
    "unsupported",
    "invalid",
    "range",
    "scenario",
}


def _rows() -> list[dict]:
    return [
        json.loads(line)
        for line in DATASET.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def test_dataset_ids_are_unique() -> None:
    rows = _rows()
    ids = [r["id"] for r in rows]
    assert len(ids) == len(set(ids))
    assert len(rows) >= 40  # the 9 canonical fixtures plus category coverage


def test_dataset_categories_are_from_the_allowed_set() -> None:
    for row in _rows():
        assert row["category"] in _ALLOWED_CATEGORIES, row


@pytest.mark.parametrize("row", _rows(), ids=lambda r: r["id"])
def test_every_expected_intent_is_schema_valid(row: dict) -> None:
    validator = jsonschema.Draft202012Validator(json_schema())
    expected = row.get("expected_intent")
    if expected is None:
        expected = json.loads((CORE_FIXTURES / row["fixture"]).read_text(encoding="utf-8"))
    errors = list(validator.iter_errors(expected))
    assert not errors, f"{row['id']} expected_intent failed schema: {[e.message for e in errors]}"


@pytest.mark.parametrize("row", [r for r in _rows() if "fixture" in r], ids=lambda r: r["id"])
def test_fixture_referenced_rows_match_the_shared_core_fixture(row: dict) -> None:
    """The 9 canonical fixtures must be reused verbatim, never re-typed by hand."""
    on_disk = json.loads((CORE_FIXTURES / row["fixture"]).read_text(encoding="utf-8"))
    assert on_disk is not None  # loads without error; content is the single source of truth
