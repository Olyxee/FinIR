"""FinIR-Intent baseline: a deterministic, rule-based NL -> FinIR Intent compiler.

This is the constrained structured-output baseline for the first milestone (see
docs/huggingface-intent-handoff.md in the FinIR repo). It is intentionally *not* a
trained model: a small, fully offline, dependency-free pattern matcher that emits
exactly the canonical envelope defined by ``finir.intent`` -- the same JSON Schema
and Python types the core runtime already validates and executes.

Design boundary (do not blur this):

* This module only *interprets* natural language into the canonical envelope.
* It never performs financial arithmetic beyond parsing a number out of text.
* It never invents a quantity for vague language -- that maps to ``ambiguous``.
* It never guesses which of several conflicting operations on the same target the
  user meant -- that also maps to ``ambiguous`` rather than silently picking one.
* Target names, units and the operation vocabulary are exactly the ones in
  ``finir.intent.schema`` / ``schemas/finir-intent-v1.schema.json``. No new fields,
  no alias resolution inside the contract -- alias resolution happens here, before
  the envelope is emitted, exactly as ``docs/intent-contract.md`` requires.

Supported phrasing is deliberately narrow and documented in MODEL_CARD.md. Natural
language outside these patterns correctly falls back to ``ambiguous`` (a target was
named but no parseable quantity was found) rather than being guessed.
"""

from __future__ import annotations

import re
from typing import Any

from finir.intent import SCHEMA_VERSION, IntentCompiler

# --------------------------------------------------------------------------- targets
# Canonical target -> the finance "kind" used to decide default unit/currency
# handling. This mirrors 1:1 the input types declared in
# finir_intent.reference_model.build_reference_model(), so every "valid" envelope
# this baseline emits is also executable end-to-end against that model.
_TARGET_KIND: dict[str, str] = {
    "revenue": "money",
    "cogs": "money",
    "opex": "money",
    "payment_terms": "days",
    "accounts_payable": "money",
    "inventory": "money",
    "capex": "money",
    "debt": "money",
    "interest_rate": "percentage",
    "cash": "money",
    "price": "money",
    "volume": "quantity",
}

# NL synonym -> canonical target (model input node name). This alias table lives
# entirely in the interpretation layer -- the runtime resolves no aliases
# (docs/intent-contract.md "Targets").
_TARGET_ALIASES: dict[str, str] = {
    "revenue": "revenue",
    "sales": "revenue",
    "top line": "revenue",
    "cogs": "cogs",
    "cost of goods sold": "cogs",
    "cost of goods": "cogs",
    "cost of sales": "cogs",
    "supplier cost": "cogs",
    "supplier costs": "cogs",
    "opex": "opex",
    "operating expenses": "opex",
    "operating expense": "opex",
    "operating costs": "opex",
    "payment terms": "payment_terms",
    "customer payment terms": "payment_terms",
    "receivable terms": "payment_terms",
    "credit terms": "payment_terms",
    "accounts payable": "accounts_payable",
    "trade payables": "accounts_payable",
    "payables balance": "accounts_payable",
    "amount owed to suppliers": "accounts_payable",
    "supplier invoices": "accounts_payable",
    "inventory levels": "inventory",
    "inventory": "inventory",
    "stock levels": "inventory",
    "stock": "inventory",
    "capital expenditure": "capex",
    "capital expenditures": "capex",
    "capital spending": "capex",
    "capex": "capex",
    "borrowings": "debt",
    "loan balance": "debt",
    "total debt": "debt",
    "debt": "debt",
    "interest rate": "interest_rate",
    "cost of debt": "interest_rate",
    "borrowing rate": "interest_rate",
    "cash balance": "cash",
    "cash on hand": "cash",
    "cash position": "cash",
    "cash": "cash",
    "unit price": "price",
    "selling price": "price",
    "sale price": "price",
    "price": "price",
    "sales volume": "volume",
    "unit volume": "volume",
    "units sold": "volume",
    "volume": "volume",
}
_SORTED_ALIASES = sorted(_TARGET_ALIASES, key=len, reverse=True)

_UP_WORDS = ("increase", "increases", "raise", "grow", "grows", "rise", "rises", "up", "higher", "extend")
_DOWN_WORDS = ("decrease", "decreases", "reduce", "reduces", "cut", "cuts", "lower", "drop", "drops", "down", "fall", "falls")
# Word-boundary matching is required here: naive substring checks on these short
# words false-positive constantly in ordinary English (e.g. "up" inside "supplier"
# or "group", "down" inside "downside", "cut" inside "circuit").
_UP_RE = re.compile(r"\b(?:" + "|".join(_UP_WORDS) + r")\b")
_DOWN_RE = re.compile(r"\b(?:" + "|".join(_DOWN_WORDS) + r")\b")

# Requests that are clear but cannot be expressed as a FinIR model mutation --
# distinct from "ambiguous" (right domain, missing quantity). See
# docs/intent-contract.md section 7 / docs/huggingface-intent-handoff.md section 7.
_UNSUPPORTED_WORDS = (
    "acquire",
    "acquires",
    "acquiring",
    "acquired",
    "acquisition",
    "acquisitions",
    "merge",
    "merges",
    "merging",
    "merged",
    "merger",
    "mergers",
    "hire",
    "hires",
    "hiring",
    "hired",
    "fire staff",
    "fire employees",
    "fired staff",
    "fired employees",
    "lay off",
    "laying off",
    "laid off",
    "layoff",
    "layoffs",
    "ipo",
    "go public",
    "going public",
    "buy back",
    "buying back",
    "bought back",
    "buyback",
    "buybacks",
    "share buyback",
    "litigation",
    "lawsuit",
    "lawsuits",
    "sue",
    "sues",
    "sued",
    "suing",
    "bankrupt",
    "bankruptcy",
    "restructure the board",
    "new ceo",
)
# Word-boundary matching: a naive substring check false-positives on ordinary
# English containing these as a fragment (e.g. "merge" inside "emergency", "sue"
# inside "issue", "fire" inside "fired up about revenue growth" is fine but "fire"
# bare must not match inside e.g. "firewall" or "fireside").
_UNSUPPORTED_RE = re.compile(r"\b(?:" + "|".join(re.escape(w) for w in _UNSUPPORTED_WORDS) + r")\b")

# Spelled-out cardinal numbers (deterministic, exact parsing of an unambiguous
# number phrase -- not a guess). Kept small and targeted: only the words needed to
# resolve a spelled-out number, never a general vocabulary.
_NUM_WORDS: dict[str, int] = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12,
    "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17,
    "eighteen": 18, "nineteen": 19, "twenty": 20, "thirty": 30, "forty": 40,
    "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90,
}
_NUM_SCALES: dict[str, int] = {"hundred": 100, "thousand": 1_000, "million": 1_000_000, "billion": 1_000_000_000}
_NUM_WORD_ALT = "|".join(sorted({*_NUM_WORDS, *_NUM_SCALES}, key=len, reverse=True))

_PCT_RE = re.compile(r"([+-]?\d+(?:\.\d+)?)\s*(?:%|\bpercent\b)")
# Only a phrase built entirely from recognized number/scale words is captured --
# deliberately not a generic "any words before percent" grab, which would swallow
# unrelated leading words (e.g. "up" in "bump ... up five percent").
_SPELLED_PCT_RE = re.compile(rf"\b((?:{_NUM_WORD_ALT})(?:[ -](?:{_NUM_WORD_ALT}))*)\s+percent\b", re.I)
_SPELLED_MONEY_RE = re.compile(
    rf"^((?:{_NUM_WORD_ALT})(?:[ -](?:{_NUM_WORD_ALT}))*)\s*(rand|rands|dollars?|zar|usd)?\s*\.?\s*$", re.I
)
_DAYS_RANGE_RE = re.compile(r"\b(\d+)\s*(?:to|->|→)\s*(\d+)\s*days?\b")
_DAYS_TO_RE = re.compile(r"\bto\s+(\d+)\s*days?\b")
_BY_RE = re.compile(r"\bby\s+(.+)$")
_TO_RE = re.compile(r"\bto\s+(.+)$")
_MONEY_AMOUNT_RE = re.compile(r"(r|zar|usd|\$)?\s*([\d]+(?:\.\d+)?)\s*(zar|usd)?", re.I)
_RANGE_RE = re.compile(
    r"\b(?:range|sweep|grid|scan|explore)\b.*?\b(?:from|between)\b\s*(?:r|zar|usd|\$)?\s*([\d.]+)"
    r"\s*(?:zar|usd)?\s*\b(?:to|and)\b\s*(?:r|zar|usd|\$)?\s*([\d.]+)\s*(?:zar|usd)?.*?\b(\d+)\s*(?:steps|points)\b",
    re.I | re.S,
)
_SCENARIO_SPLIT_RE = re.compile(r"([A-Za-z][A-Za-z ]{0,24}?)\s+scenario\s*:\s*", re.I)
_NO_CHANGE_BODY = {"no change", "no changes", "none", "base", "unchanged", "the base case", "base case"}


def _strip_thousands(text: str) -> str:
    """Remove thousand-separator commas from numbers (``5,000,000`` -> ``5000000``)."""
    return re.sub(r"(?<=\d),(?=\d{3}\b)", "", text)


def _amount(raw: str) -> float:
    return float(re.sub(r"[^\d.]", "", raw))


def _currency(*fragments: str | None) -> str | None:
    for frag in fragments:
        if not frag:
            continue
        low = frag.strip().lower()
        if low in ("r", "zar", "rand", "rands"):
            return "ZAR"
        if low in ("$", "usd", "dollar", "dollars"):
            return "USD"
    return None


def _words_to_number(phrase: str) -> float | None:
    """Convert a spelled-out cardinal number phrase (e.g. 'five million') to a
    float. Deterministic, exact parsing of an unambiguous number -- not a guess.
    Returns None if any token isn't a recognized number/scale word.
    """
    tokens = phrase.strip().lower().replace("-", " ").split()
    if not tokens:
        return None
    total = 0
    current = 0
    for t in tokens:
        if t == "and":
            continue
        if t in _NUM_WORDS:
            current += _NUM_WORDS[t]
        elif t in _NUM_SCALES:
            scale = _NUM_SCALES[t]
            if scale == 100:
                current = (current or 1) * scale
            else:
                total += (current or 1) * scale
                current = 0
        else:
            return None
    return float(total + current)


def _direction_sign(low: str) -> float:
    up = bool(_UP_RE.search(low))
    down = bool(_DOWN_RE.search(low))
    return -1.0 if (down and not up) else 1.0


def _find_target(low: str) -> str | None:
    for alias in _SORTED_ALIASES:
        if re.search(r"\b" + re.escape(alias) + r"\b", low):
            return _TARGET_ALIASES[alias]
    return None


def _split_clauses(text: str) -> list[str]:
    protected = _strip_thousands(text)
    parts = re.split(r"\s*;\s*|\s*,\s*(?=[A-Za-z])|\s+\band\b\s+", protected)
    clauses = []
    for p in parts:
        p = re.sub(r"^(and|then|also)\s+", "", p.strip(), flags=re.I).strip(" .")
        if p:
            clauses.append(p)
    return clauses


def _parse_clause(clause: str) -> tuple[dict[str, Any] | None, str | None]:
    """Parse one clause. Returns (operation, note); note is set only on failure."""
    low = clause.lower()
    target = _find_target(low)
    if target is None:
        return None, None
    kind = _TARGET_KIND.get(target, "money")

    m = _DAYS_RANGE_RE.search(low)
    if m:
        return {"operation": "set", "target": target, "value": _amount(m.group(2)), "unit": "days"}, None

    m = _DAYS_TO_RE.search(low)
    if m:
        return {"operation": "set", "target": target, "value": _amount(m.group(1)), "unit": "days"}, None

    # "set/reduce/... TARGET to N%" is an absolute set to that percentage level
    # (new = value), not a relative_change -- must be checked before the generic
    # relative-change percentage rule below.
    m_to = _TO_RE.search(low)
    if m_to:
        pct = _PCT_RE.match(m_to.group(1).strip())
        if pct and kind == "percentage":
            return (
                {"operation": "set", "target": target, "value": _amount(pct.group(1)) / 100.0, "unit": "percentage"},
                None,
            )
        if pct:
            # "set/change <non-percentage target> to N%" (e.g. "set opex to 45%") is
            # not a coherent instruction for this target's type -- refuse rather
            # than silently reinterpreting "to" as "by" (relative_change), which
            # would invent a meaning the user did not state.
            return None, "target_no_value"

    m = _PCT_RE.search(low)
    if m:
        value = _direction_sign(low) * _amount(m.group(1)) / 100.0
        return {"operation": "relative_change", "target": target, "value": value}, None

    m = _SPELLED_PCT_RE.search(low)
    if m:
        if m_to and _SPELLED_PCT_RE.match(m_to.group(1).strip()):
            # Same "set X to <percent>" guard as the digit case above -- a
            # spelled-out number must not bypass it.
            return None, "target_no_value"
        num = _words_to_number(m.group(1))
        if num is not None:
            value = _direction_sign(low) * num / 100.0
            return {"operation": "relative_change", "target": target, "value": value}, None

    m = _BY_RE.search(low)
    if m and kind == "money":
        amt_match = _MONEY_AMOUNT_RE.search(m.group(1))
        if amt_match and amt_match.group(2):
            amt = _amount(amt_match.group(2))
            sign = -1.0 if _direction_sign(low) < 0 else 1.0
            op: dict[str, Any] = {"operation": "absolute_change", "target": target, "value": sign * amt}
            ccy = _currency(amt_match.group(1), amt_match.group(3))
            if ccy:
                op["currency"] = ccy
            return op, None
        spelled = _SPELLED_MONEY_RE.match(m.group(1).strip())
        if spelled:
            num = _words_to_number(spelled.group(1))
            if num is not None:
                sign = -1.0 if _direction_sign(low) < 0 else 1.0
                op = {"operation": "absolute_change", "target": target, "value": sign * num}
                ccy = _currency(spelled.group(2))
                if ccy:
                    op["currency"] = ccy
                return op, None

    if m_to and kind in ("money", "days"):
        amt_match = _MONEY_AMOUNT_RE.search(m_to.group(1))
        if amt_match and amt_match.group(2):
            amt = _amount(amt_match.group(2))
            op = {"operation": "set", "target": target, "value": amt}
            if kind == "money":
                ccy = _currency(amt_match.group(1), amt_match.group(3))
                if ccy:
                    op["currency"] = ccy
            else:  # days, without the word "days" already matched above
                op["unit"] = "days"
            return op, None
    # kind == "quantity": a plain numeric "set ... to N" is left unhandled (unit
    # intentionally never guessed for quantity targets -- see MODEL_CARD.md "known
    # limitations": the runtime's semantic validator only accepts unit == 'scalar'
    # or no unit for Quantity-typed targets today).

    return None, "target_no_value"


def _envelope(status: str, *, operations: list[dict[str, Any]] | None = None, reason: str | None = None) -> dict[str, Any]:
    env: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "status": status, "operations": operations or []}
    if reason is not None:
        env["reason"] = reason
    return env


def _is_unsupported(low: str) -> bool:
    return bool(_UNSUPPORTED_RE.search(low))


def _try_parse_scenarios(text: str) -> dict[str, Any] | None:
    parts = _SCENARIO_SPLIT_RE.split(text)
    if len(parts) < 3:
        return None
    preamble = parts[0].strip(" .")
    if preamble and len(preamble.split()) > 8:
        return None

    scenarios: list[dict[str, Any]] = []
    for i in range(1, len(parts), 2):
        name = re.sub(r"\s+", "_", parts[i].strip().lower())
        body = parts[i + 1].strip(" .") if i + 1 < len(parts) else ""
        if not body or body.lower() in _NO_CHANGE_BODY:
            scenarios.append({"name": name, "operations": []})
            continue
        ops: list[dict[str, Any]] = []
        unparsed = False
        for clause in _split_clauses(body):
            op, _note = _parse_clause(clause)
            if op is not None:
                if op["operation"] == "range":
                    return None  # range is never valid inside a scenario
                ops.append(op)
            else:
                unparsed = True
        if unparsed and not ops:
            return None  # can't confidently build this scenario -> fall through to ambiguous
        targets = [o["target"] for o in ops]
        if len(targets) != len(set(targets)):
            return None
        scenarios.append({"name": name, "operations": ops})

    if len(scenarios) < 2:
        return None
    return {"schema_version": SCHEMA_VERSION, "status": "valid", "scenarios": scenarios}


def compile_intent(text: str) -> dict[str, Any]:
    """Compile one natural-language financial instruction into a canonical envelope.

    Always returns a dict that structurally validates against
    ``finir.intent.json_schema()`` (verify with
    ``finir.intent.FinIRIntent.from_obj`` before executing).
    """
    scenario_env = _try_parse_scenarios(text)
    if scenario_env is not None:
        return scenario_env

    low = text.lower()
    if _is_unsupported(low):
        return _envelope("unsupported", reason=f"request cannot be represented as a FinIR model mutation: {text!r}")

    range_match = _RANGE_RE.search(_strip_thousands(low))
    if range_match:
        target = _find_target(low)
        if target is not None:
            return _envelope(
                "valid",
                operations=[
                    {
                        "operation": "range",
                        "target": target,
                        "min": _amount(range_match.group(1)),
                        "max": _amount(range_match.group(2)),
                        "steps": int(range_match.group(3)),
                    }
                ],
            )

    ops: list[dict[str, Any]] = []
    saw_target_without_value = False
    for clause in _split_clauses(text):
        op, note = _parse_clause(clause)
        if op is not None:
            ops.append(op)
        elif note == "target_no_value":
            saw_target_without_value = True

    if not ops:
        if saw_target_without_value:
            return _envelope(
                "ambiguous",
                reason="a financial target was identified but no quantitative change was specified",
            )
        return _envelope("ambiguous", reason="no financial target or quantitative change was identified")

    targets = [o["target"] for o in ops]
    if len(targets) != len(set(targets)):
        return _envelope(
            "ambiguous",
            reason="conflicting operations on the same target were requested; cannot resolve unambiguously",
        )

    return _envelope("valid", operations=ops)


class BaselineIntentCompiler(IntentCompiler):
    """The FinIR-Intent baseline, implementing the core :class:`IntentCompiler` seam.

    Deterministic and fully offline -- no external LLM/API dependency. Emits exactly
    the canonical envelope; validation and execution are left entirely to
    ``finir.intent`` / ``FinancialModel.apply_intent`` (never duplicated here).
    """

    def compile(self, text: str) -> dict[str, Any]:
        return compile_intent(text)
