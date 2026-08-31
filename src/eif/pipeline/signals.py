"""Deterministic signal extraction helpers.

Pure, well-tested functions that pull structured signals out of text: monetary
amounts, percentages, durations, directions, dates, entity mentions, and money
columns in rendered tables. These carry no model dependency, which is what lets
EIF do its arithmetic deterministically and reproducibly.

The functions are intentionally conservative: they prefer to extract nothing over
guessing, so downstream estimates are never fabricated from thin air.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime

from dateutil import parser as dateparser

from ..domain.enums import Direction

# --------------------------------------------------------------------------- money
# Matches R4.2m, ZAR 42,000,000, $1.8m, R850k, 500 000, USD 1.2bn, etc.
_CURRENCY_SYMBOLS = {"R": "ZAR", "$": "USD", "€": "EUR", "£": "GBP"}
_SCALE = {"k": 1_000, "m": 1_000_000, "mn": 1_000_000, "bn": 1_000_000_000, "b": 1_000_000_000}

# Case-sensitive on purpose: a lowercase 'r' inside a word (e.g. "December")
# must not be read as the ZAR symbol 'R'. The scale suffix must attach directly
# to the number and be followed by a non-letter, so "R2,000,000 becomes" does not
# read the 'b' of "becomes" as "billion".
_MONEY_RE = re.compile(
    r"""
    (?<![A-Za-z0-9])
    (?P<code>ZAR|USD|EUR|GBP|R|\$|€|£)?      # optional currency code/symbol
    \s?
    (?P<num>\d{1,3}(?:[ ,]\d{3})+|\d+(?:\.\d+)?)  # 1,234,567 | 42 | 4.2
    (?P<scale>bn|mn|BN|MN|[kmbKMB])?          # optional scale suffix, no space
    (?![A-Za-z])
    """,
    re.VERBOSE,
)

_PERCENT_RE = re.compile(r"(?P<num>\d+(?:\.\d+)?)\s?%")
_DURATION_RE = re.compile(
    r"(?P<num>\d+(?:\.\d+)?)\s?(?P<unit>day|days|week|weeks|month|months)\b", re.IGNORECASE
)

_INCREASE_WORDS = ("increase", "rise", "raise", "up ", "higher", "grow", "expand", "surge", "more")
_DECREASE_WORDS = (
    "decrease",
    "reduce",
    "cut",
    "drop",
    "lower",
    "decline",
    "down ",
    "less",
    "fall",
    "shrink",
)


@dataclass
class MoneyHit:
    value: float
    currency: str | None
    context: str  # a short label inferred from nearby words (spend/revenue/penalty/...)
    span: tuple[int, int]


def parse_money(text: str) -> list[MoneyHit]:
    """Extract monetary amounts with an inferred context label."""
    hits: list[MoneyHit] = []
    for m in _MONEY_RE.finditer(text):
        code = m.group("code")
        num_raw = m.group("num")
        scale = (m.group("scale") or "").lower()
        # Skip bare small integers with no currency/scale (likely counts, not money).
        if not code and not scale:
            continue
        value = float(num_raw.replace(",", "").replace(" ", ""))
        if scale:
            value *= _SCALE.get(scale, 1)
        currency = None
        if code:
            currency = _CURRENCY_SYMBOLS.get(code, code.upper())
        context = _context_label(text, m.start())
        hits.append(MoneyHit(value=value, currency=currency, context=context, span=m.span()))
    return hits


# Labeled amounts without a currency symbol, e.g. `"annual_spend": 42000000` or
# `annual spend of 42,000,000`. Requires a financial keyword immediately before
# the number and a reasonably large magnitude to avoid matching ids/years.
_LABELED_AMOUNT_RE = re.compile(
    r"(?P<label>spend|revenue|sales|cost|budget|penalty|obligation|inventory|"
    r"receivable|payable|amount|value|fee)[\"']?\s*[:=]?\s*[\"']?"
    r"(?P<num>\d{1,3}(?:[ ,]\d{3})+|\d{4,})(?:\.\d+)?",
    re.IGNORECASE,
)
_LABELED_MIN = 10_000.0


def parse_labeled_amounts(text: str) -> list[MoneyHit]:
    """Extract labeled numeric amounts that lack an explicit currency symbol."""
    hits: list[MoneyHit] = []
    for m in _LABELED_AMOUNT_RE.finditer(text):
        raw = m.group("num").replace(",", "").replace(" ", "")
        try:
            value = float(raw)
        except ValueError:
            continue
        if value < _LABELED_MIN:
            continue
        hits.append(
            MoneyHit(value=value, currency=None, context=m.group("label").lower(), span=m.span())
        )
    return hits


def _context_label(text: str, pos: int) -> str:
    window = text[max(0, pos - 40) : pos + 40].lower()
    for label in (
        "spend",
        "revenue",
        "sales",
        "penalty",
        "obligation",
        "cost",
        "budget",
        "inventory",
        "receivable",
        "payable",
        "fee",
        "value",
    ):
        if label in window:
            return label
    return "amount"


def parse_percentages(text: str) -> list[float]:
    return [float(m.group("num")) for m in _PERCENT_RE.finditer(text)]


def parse_durations_days(text: str) -> list[float]:
    days: list[float] = []
    for m in _DURATION_RE.finditer(text):
        num = float(m.group("num"))
        unit = m.group("unit").lower()
        if unit.startswith("week"):
            num *= 7
        elif unit.startswith("month"):
            num *= 30
        days.append(num)
    return days


def infer_direction(text: str) -> Direction:
    low = f" {text.lower()} "
    inc = any(w in low for w in _INCREASE_WORDS)
    dec = any(w in low for w in _DECREASE_WORDS)
    if inc and not dec:
        return Direction.INCREASE
    if dec and not inc:
        return Direction.DECREASE
    if inc and dec:
        return Direction.UNKNOWN
    return Direction.NEUTRAL


# --------------------------------------------------------------------------- dates
_MONTHS = [
    "january",
    "february",
    "march",
    "april",
    "may",
    "june",
    "july",
    "august",
    "september",
    "october",
    "november",
    "december",
]
# \b word boundaries prevent "on" from matching inside words like "precision".
_EFFECTIVE_RE = re.compile(
    r"\b(?:effective(?:\s+from)?|starting|as of|beginning|with effect from)\b\s+"
    r"(?P<date>\d{0,2}\s*[A-Za-z]{3,9}\s+\d{4}|\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
    re.IGNORECASE,
)
_REL_MONTHS_RE = re.compile(r"in\s+(?P<num>\d+|two|three|four|five|six)\s+months?", re.IGNORECASE)
_WORD_NUM = {"two": 2, "three": 3, "four": 4, "five": 5, "six": 6}


def parse_effective_date(text: str, *, reference: datetime | None = None) -> datetime | None:
    """Best-effort extraction of an effective/start date from text.

    Handles absolute dates ("effective 1 November 2026") and simple relative
    phrases ("in two months") anchored to ``reference``.
    """
    ref = reference or datetime.utcnow()
    ref = ref.replace(hour=0, minute=0, second=0, microsecond=0)

    rel = _REL_MONTHS_RE.search(text)
    if rel:
        raw = rel.group("num").lower()
        months = _WORD_NUM.get(raw)
        if months is None and raw.isdigit():
            months = int(raw)
        if months is not None:
            month_index = ref.month - 1 + months
            year = ref.year + month_index // 12
            month = month_index % 12 + 1
            return ref.replace(
                year=year, month=month, day=1, hour=0, minute=0, second=0, microsecond=0
            )

    for m in _EFFECTIVE_RE.finditer(text):
        candidate = m.group("date").strip().rstrip(".,")
        if not any(mon in candidate.lower() for mon in _MONTHS) and not re.search(r"\d", candidate):
            continue
        try:
            parsed = dateparser.parse(candidate, default=ref.replace(day=1), fuzzy=True)
        except (ValueError, OverflowError):
            continue
        if parsed is not None:
            return parsed
    return None


# --------------------------------------------------------------------------- entities
@dataclass
class EntityMention:
    entity_type: str
    name: str
    role: str
    span: tuple[int, int] = (0, 0)


_ENTITY_PATTERNS: tuple[tuple[str, str, re.Pattern[str]], ...] = (
    (
        "supplier",
        "supplier",
        re.compile(r"\b[Ss]upplier[:\s]\s*([A-Z][\w&.\- ]{1,40}?)(?=[\s,.;:]|$)"),
    ),
    (
        "customer",
        "customer",
        re.compile(r"\b[Cc]ustomer[:\s]\s*([A-Z][\w&.\- ]{1,40}?)(?=[\s,.;:]|$)"),
    ),
    (
        "project",
        "project",
        re.compile(r"\b[Pp]roject[:\s]\s*([A-Z][\w&.\- ]{1,40}?)(?=[\s,.;:]|$)"),
    ),
    ("product", "affected_product", re.compile(r"\b(SKU[-\s]?[A-Z0-9]+)\b")),
    ("contract", "contract", re.compile(r"\b[Cc]ontract\s+(?:no\.?\s*)?([A-Z0-9][\w\-/]{1,30})")),
    (
        "order",
        "order",
        re.compile(r"\b(?:PO|order)\s+(?:no\.?\s*)?([A-Z0-9][\w\-/]{1,30})", re.IGNORECASE),
    ),
)


def extract_entities(text: str) -> list[EntityMention]:
    """Extract entity mentions via conservative surface patterns."""
    mentions: list[EntityMention] = []
    seen: set[tuple[str, str]] = set()
    for entity_type, role, pattern in _ENTITY_PATTERNS:
        for m in pattern.finditer(text):
            name = m.group(1).strip().rstrip(".,;:")
            name = re.split(r"\s+(?:will|has|is|announced|of|and)\b", name)[0].strip()
            if len(name) < 2:
                continue
            key = (entity_type, name.lower())
            if key in seen:
                continue
            seen.add(key)
            mentions.append(EntityMention(entity_type, name, role, m.span()))
    return mentions


# --------------------------------------------------------------------------- tables
_NUMERIC_COL_HINTS = (
    "amount",
    "spend",
    "total",
    "value",
    "cost",
    "price",
    "revenue",
    "qty",
    "quantity",
)


@dataclass
class TableSummary:
    row_count: int = 0
    column_sums: dict[str, float] = field(default_factory=dict)
    headers: list[str] = field(default_factory=list)


def summarize_pipe_table(text: str) -> TableSummary | None:
    """Summarize a pipe-rendered table (as produced by the CSV/Excel connectors).

    Returns per-column sums for columns whose header suggests a numeric money/qty
    value. Used to derive figures like annual spend deterministically.
    """
    lines = [ln for ln in text.splitlines() if "|" in ln]
    if len(lines) < 2:
        return None
    headers = [h.strip() for h in lines[0].split("|")]
    data_lines = [ln for ln in lines[1:] if set(ln.strip()) != {"-", " ", "|"}]
    summary = TableSummary(headers=headers)
    sums: dict[str, float] = {}
    count = 0
    for ln in data_lines:
        cells = [c.strip() for c in ln.split("|")]
        if len(cells) != len(headers):
            continue
        count += 1
        for header, cell in zip(headers, cells, strict=False):
            hl = header.lower()
            if any(hint in hl for hint in _NUMERIC_COL_HINTS):
                val = _to_number(cell)
                if val is not None:
                    sums[header] = sums.get(header, 0.0) + val
    summary.row_count = count
    summary.column_sums = sums
    return summary


def _to_number(cell: str) -> float | None:
    cleaned = re.sub(r"[^\d.\-]", "", cell.replace(",", ""))
    if cleaned in ("", "-", ".", "-."):
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None
