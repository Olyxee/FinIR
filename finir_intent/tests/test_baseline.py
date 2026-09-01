"""Unit tests for the FinIR-Intent baseline compiler.

These check the interpretation layer in isolation: every emitted envelope must
structurally validate against the *canonical* schema owned by the core ``finir``
package (never a locally redefined one), and the never-do rules from
docs/huggingface-intent-handoff.md must hold (never invent a number, never guess
between conflicting operations, never emit period scoping or other unknown fields).
"""

from __future__ import annotations

import jsonschema
import pytest
from finir.intent import json_schema

from finir_intent import BaselineIntentCompiler, compile_intent

_VALIDATOR = jsonschema.Draft202012Validator(json_schema())


def _assert_schema_valid(envelope: dict) -> None:
    errors = list(_VALIDATOR.iter_errors(envelope))
    assert not errors, f"envelope failed the canonical schema: {[e.message for e in errors]}"


@pytest.mark.parametrize(
    "text",
    [
        "Increase COGS by 4%.",
        "Increase opex by R5,000,000.",
        "Extend payment terms to 60 days.",
        "Revenue falls 8%, COGS rises 3%, and extend payment terms to 60 days.",
        "Improve margins next year.",
        "Acquire our largest competitor.",
        "Increase revenue by USD 2,000,000.",
        "Set COGS to 60 days.",
        "Sweep COGS from 300,000,000 to 400,000,000 in 100 steps.",
        "Base scenario: no changes. Upside scenario: revenue grows 10%.",
    ],
)
def test_every_prediction_is_schema_valid(text: str) -> None:
    _assert_schema_valid(compile_intent(text))


def test_relative_change_is_multiplicative_and_signed_correctly() -> None:
    env = compile_intent("Increase COGS by 4%.")
    assert env["status"] == "valid"
    op = env["operations"][0]
    assert op == {"operation": "relative_change", "target": "cogs", "value": 0.04}


def test_down_word_flips_sign() -> None:
    env = compile_intent("Revenue falls 8%.")
    assert env["operations"][0]["value"] == -0.08


def test_absolute_change_carries_currency_only_when_stated() -> None:
    env = compile_intent("Increase opex by R5,000,000.")
    op = env["operations"][0]
    assert op["operation"] == "absolute_change"
    assert op["currency"] == "ZAR"
    assert "unit" not in op  # matches docs/intent-contract.md: currency alone, no redundant unit


def test_set_days() -> None:
    env = compile_intent("Extend payment terms to 60 days.")
    assert env["operations"][0] == {
        "operation": "set",
        "target": "payment_terms",
        "value": 60.0,
        "unit": "days",
    }


def test_dollar_sign_is_recognized_as_usd() -> None:
    env = compile_intent("Increase revenue by $2,000,000.")
    assert env["operations"][0]["currency"] == "USD"


def test_scenario_with_an_unparseable_body_falls_back_to_ambiguous_whole_instruction() -> None:
    # A scenario clause the parser can't confidently resolve must not produce a
    # partial/wrong scenario -- the whole instruction should fall back to ambiguous.
    env = compile_intent("Base scenario: no changes. Wildcard scenario: something vague happens.")
    assert env["status"] == "ambiguous"
    assert "scenarios" not in env


def test_set_percentage_is_absolute_not_relative() -> None:
    # "set X to N%" means new = N%, not a relative_change -- see docs/intent-contract.md.
    env = compile_intent("Set the interest rate to 8%.")
    assert env["operations"][0] == {
        "operation": "set",
        "target": "interest_rate",
        "value": 0.08,
        "unit": "percentage",
    }


def test_vague_language_never_invents_a_number() -> None:
    for text in (
        "Improve margins next year.",
        "Sales should grow significantly.",
        "Reduce costs a little.",
    ):
        env = compile_intent(text)
        assert env["status"] == "ambiguous"
        assert env["operations"] == []
        assert "value" not in str(env)  # no numeric field anywhere


def test_unsupported_is_distinct_from_ambiguous() -> None:
    env = compile_intent("Acquire our largest competitor.")
    assert env["status"] == "unsupported"
    assert env["operations"] == []


def test_conflicting_duplicate_targets_are_ambiguous_not_guessed() -> None:
    env = compile_intent("Increase revenue by 5% and also cut revenue by 10%.")
    assert env["status"] == "ambiguous"
    assert env["operations"] == []


def test_never_emits_period_scoping_or_unknown_fields() -> None:
    # docs/huggingface-intent-handoff.md: "Never add fields the runtime does not
    # consume (e.g. period scoping)."
    texts = [
        "Increase COGS by 4%.",
        "Increase revenue monthly by 5%.",
        "Extend payment terms to 60 days.",
    ]
    for text in texts:
        env = compile_intent(text)
        assert "period" not in env
        for op in env.get("operations", []):
            assert "period" not in op
        for sc in env.get("scenarios", []):
            for op in sc.get("operations", []):
                assert "period" not in op


def test_range_is_the_sole_operation() -> None:
    env = compile_intent("Sweep COGS from 300,000,000 to 400,000,000 in 100 steps.")
    assert env["status"] == "valid"
    assert len(env["operations"]) == 1
    op = env["operations"][0]
    assert op["operation"] == "range"
    assert op["min"] == 300_000_000.0
    assert op["max"] == 400_000_000.0
    assert op["steps"] == 100
    assert "value" not in op


def test_scenarios_are_mutually_exclusive_with_operations() -> None:
    env = compile_intent(
        "Base scenario: no changes. Upside scenario: revenue grows 10%. "
        "Downside scenario: revenue falls 8% and COGS rises 5%."
    )
    assert env["status"] == "valid"
    assert "scenarios" in env
    assert "operations" not in env
    names = [s["name"] for s in env["scenarios"]]
    assert names == ["base", "upside", "downside"]


def test_baseline_compiler_implements_the_core_intent_compiler_interface() -> None:
    compiler = BaselineIntentCompiler()
    env = compiler.compile("Increase COGS by 4%.")
    _assert_schema_valid(env)
    assert env["status"] == "valid"


# ---------------------------------------------------------------------- regression
# Word-level direction/unsupported matching must use word boundaries. A naive
# substring check false-positives constantly on ordinary English: "up" inside
# "supplier"/"group", "merge" inside "emergency", "sue" inside "issue". These
# regressions were found in review and must never come back.
def test_direction_word_does_not_false_positive_inside_supplier() -> None:
    env = compile_intent("Reduce supplier costs by 10%.")
    assert env["operations"][0] == {
        "operation": "relative_change",
        "target": "cogs",
        "value": -0.10,
    }


def test_direction_word_does_not_false_positive_inside_group() -> None:
    env = compile_intent("Decrease cogs for this group by 4%.")
    assert env["operations"][0]["value"] == -0.04


def test_unsupported_word_does_not_false_positive_inside_emergency() -> None:
    env = compile_intent("This is an emergent risk; increase cash by R1,000,000.")
    assert env["status"] == "valid"
    assert env["operations"][0]["operation"] == "absolute_change"


def test_unsupported_word_does_not_false_positive_inside_issue() -> None:
    env = compile_intent("We have a cash flow issue and need to increase cash by R2,000,000.")
    assert env["status"] == "valid"


def test_unsupported_word_still_catches_inflected_forms() -> None:
    for text in (
        "The company was acquired by a competitor.",
        "We are hiring new staff and increasing opex by 5%.",
        "The company filed for bankruptcy.",
        "We are being sued by a former supplier.",
    ):
        assert compile_intent(text)["status"] == "unsupported", text


def test_set_to_percent_on_a_non_percentage_target_is_ambiguous_not_guessed() -> None:
    # "set opex to 45%" must not be silently reinterpreted as "increase opex by
    # 45%" (relative_change) -- that invents a meaning the instruction never
    # stated. opex is money-typed, not percentage-typed; refuse rather than guess.
    env = compile_intent("Set opex to 45%.")
    assert env["status"] == "ambiguous"
    assert env["operations"] == []


# --------------------------------------------------------------------------
# Four previously-documented "stress" limitations, now fixed with targeted
# additions (spelled-out numbers via a fixed number-word vocabulary, one new
# target alias, and a widened -- but still keyword-anchored -- range pattern).
def test_spelled_out_percent_is_parsed() -> None:
    env = compile_intent("Bump top line up five percent.")
    assert env == {
        "schema_version": "1.0",
        "status": "valid",
        "operations": [{"operation": "relative_change", "target": "revenue", "value": 0.05}],
    }


def test_supplier_invoices_alias_resolves_to_accounts_payable() -> None:
    env = compile_intent("Our supplier invoices should be paid down by R1,000,000.")
    assert env["operations"][0] == {
        "operation": "absolute_change",
        "target": "accounts_payable",
        "value": -1000000.0,
        "currency": "ZAR",
    }


def test_range_with_explore_between_and_points_phrasing() -> None:
    env = compile_intent("Explore COGS between 300,000,000 and 400,000,000 across 100 points.")
    assert env["operations"][0] == {
        "operation": "range",
        "target": "cogs",
        "min": 300_000_000.0,
        "max": 400_000_000.0,
        "steps": 100,
    }


def test_spelled_out_money_amount_with_rand_currency() -> None:
    env = compile_intent("Increase opex by five million rand.")
    assert env["operations"][0] == {
        "operation": "absolute_change",
        "target": "opex",
        "value": 5_000_000.0,
        "currency": "ZAR",
    }


def test_spelled_out_percent_does_not_reintroduce_the_set_to_percent_bug() -> None:
    # The word-number path must respect the same "set X to <percent>" guard as
    # the digit path -- must not become relative_change for a money target.
    env = compile_intent("Set opex to five percent.")
    assert env["status"] == "ambiguous"
    assert env["operations"] == []
