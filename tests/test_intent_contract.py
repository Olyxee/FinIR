"""FinIR Intent Contract tests: schema validity, fixtures, Python types, end-to-end.

These fixtures (tests/fixtures/intents/) are the shared integration surface for the
Hugging Face workstream. They must validate against schemas/finir-intent-v1.schema.json
and behave exactly as documented in docs/intent-contract.md.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from finir import FinancialModel
from finir.intent import (
    FinIRIntent,
    IntentStatus,
    IntentValidationError,
    OperationType,
    execute_intent,
    json_schema,
)
from finir.intent.schema import Operation

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = Path(__file__).resolve().parent / "fixtures" / "intents"
REPO_SCHEMA = ROOT / "schemas" / "finir-intent-v1.schema.json"


def _fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def _model() -> FinancialModel:
    m = FinancialModel()
    m.input("revenue", 500e6, currency="ZAR")
    m.input("cogs", 300e6, currency="ZAR")
    m.input("opex", 120e6, currency="ZAR")
    m.input("payment_terms", 30, type="days")
    m.define("gross_profit", "revenue - cogs")
    m.define("ebitda", "gross_profit - opex", output=True)
    m.define("gross_margin", "gross_profit / revenue", output=True)
    return m


# ------------------------------------------------------------------ schema artifact
def test_packaged_schema_matches_repo_schema():
    """The packaged schema and schemas/ copy must be byte-identical (no drift)."""
    packaged = json_schema()
    repo = json.loads(REPO_SCHEMA.read_text(encoding="utf-8"))
    assert packaged == repo


def test_schema_is_itself_valid():
    jsonschema = pytest.importorskip("jsonschema")
    jsonschema.Draft202012Validator.check_schema(json_schema())


def test_all_fixtures_are_structurally_valid_json_schema():
    jsonschema = pytest.importorskip("jsonschema")
    validator = jsonschema.Draft202012Validator(json_schema())
    for path in sorted(FIXTURES.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        errors = list(validator.iter_errors(payload))
        assert not errors, f"{path.name} failed schema: {errors[0].message if errors else ''}"


# ------------------------------------------------------------------ python types
def test_operation_change_specs():
    assert Operation(OperationType.RELATIVE_CHANGE, "cogs", value=0.04).change_spec() == {
        "relative": 0.04
    }
    assert Operation(OperationType.SET, "revenue", value=6e8).change_spec() == {"absolute": 6e8}
    assert Operation(OperationType.ABSOLUTE_CHANGE, "opex", value=5e6).change_spec() == {
        "delta": 5e6
    }


def test_from_obj_normalizes_legacy_single_op():
    intent = FinIRIntent.from_obj({"operation": "relative_change", "target": "cogs", "value": 0.04})
    assert intent.status == IntentStatus.VALID
    assert len(intent.operations) == 1 and intent.operations[0].target == "cogs"


def test_from_obj_normalizes_legacy_aliases():
    # 'change' -> relative_change, 'metric' -> target
    intent = FinIRIntent.from_obj({"operation": "change", "metric": "cogs", "value": 0.04})
    assert intent.operations[0].operation == OperationType.RELATIVE_CHANGE
    assert intent.operations[0].target == "cogs"


def test_duplicate_targets_rejected():
    with pytest.raises(IntentValidationError):
        FinIRIntent.from_obj(
            {
                "schema_version": "1.0",
                "status": "valid",
                "operations": [
                    {"operation": "set", "target": "revenue", "value": 1},
                    {"operation": "set", "target": "revenue", "value": 2},
                ],
            }
        )


def test_nonvalid_with_operations_rejected():
    with pytest.raises(IntentValidationError):
        FinIRIntent.from_obj(
            {
                "schema_version": "1.0",
                "status": "ambiguous",
                "operations": [{"operation": "set", "target": "revenue", "value": 1}],
            }
        )


def test_to_dict_roundtrip():
    payload = _fixture("valid_multi_operation.json")
    intent = FinIRIntent.from_obj(payload)
    again = FinIRIntent.from_obj(intent.to_dict())
    assert again.to_dict() == intent.to_dict()


# ------------------------------------------------------------------ end-to-end (valid)
def test_e2e_relative_change():
    r = _model().apply_intent(_fixture("valid_relative_change.json"))
    assert round(float(r["ebitda"])) == round(500e6 - 300e6 * 1.04 - 120e6)


def test_e2e_absolute_change():
    r = _model().apply_intent(_fixture("valid_absolute_change.json"))
    assert round(float(r["ebitda"])) == round(500e6 - 300e6 - (120e6 + 5e6))


def test_e2e_set_days():
    m = _model()
    r = m.apply_intent(_fixture("valid_set_days.json"))
    # payment_terms is not in the income-statement outputs; execution must still succeed.
    assert "ebitda" in r


def test_e2e_multi_operation_simultaneous():
    r = _model().apply_intent(_fixture("valid_multi_operation.json"))
    # revenue -8% and cogs +3%, simultaneously against the base.
    assert round(float(r["ebitda"])) == round(500e6 * 0.92 - 300e6 * 1.03 - 120e6)


def test_e2e_scenarios():
    results = _model().apply_intent(_fixture("valid_scenario.json"))
    assert set(results) == {"base", "upside", "downside"}
    assert round(float(results["base"]["ebitda"])) == 80_000_000
    assert round(float(results["upside"]["ebitda"])) == 130_000_000


# ------------------------------------------------------------------ end-to-end (rejected)
def test_e2e_ambiguous_refused():
    with pytest.raises(IntentValidationError):
        _model().apply_intent(_fixture("ambiguous_missing_value.json"))


def test_e2e_unsupported_refused():
    with pytest.raises(IntentValidationError):
        _model().apply_intent(_fixture("unsupported_operation.json"))


def test_e2e_invalid_currency_refused():
    # Structurally valid, semantically invalid (USD on a money[ZAR] target).
    with pytest.raises(IntentValidationError):
        _model().apply_intent(_fixture("invalid_currency.json"))


def test_e2e_invalid_type_refused():
    # 'days' unit on a money target.
    with pytest.raises(IntentValidationError):
        _model().apply_intent(_fixture("invalid_type.json"))


def test_unknown_target_refused():
    with pytest.raises(IntentValidationError):
        execute_intent(
            _model(),
            {
                "schema_version": "1.0",
                "status": "valid",
                "operations": [{"operation": "set", "target": "nonexistent", "value": 1}],
            },
        )
