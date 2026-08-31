"""Deterministic observation extractor.

Produces one :class:`Observation` per piece of evidence, aggregating the signals
found by :mod:`eif.pipeline.signals`: entity mentions, monetary amounts,
percentages, durations, an effective date, and representative claims. Every
measurement and claim is tied back to the evidence via a citation locator, so
provenance holds from the very first stage.

An optional :class:`LLMObservationExtractor` is provided for teams that want a
model to enrich extraction; it uses the provider only for interpretation and
still validates output against the typed schema. The deterministic extractor is
the default and requires no model.
"""

from __future__ import annotations

from ..domain import Claim, Confidence, EntityRef, Evidence, Measurement, Observation
from ..domain.enums import ExtractionMethod
from ..domain.provenance import Citation, Provenance
from ..utils.ids import entity_key
from .signals import (
    extract_entities,
    parse_durations_days,
    parse_effective_date,
    parse_labeled_amounts,
    parse_money,
    parse_percentages,
    summarize_pipe_table,
)
from .stages import ObservationExtractor

# Keywords that mark a sentence as economically salient -> becomes a claim.
_SIGNAL_KEYWORDS = (
    "price",
    "increase",
    "decrease",
    "reduce",
    "delay",
    "overrun",
    "inventory",
    "obligation",
    "penalty",
    "contract",
    "capacity",
    "shortage",
    "churn",
    "cancel",
    "expand",
    "risk",
    "spend",
    "revenue",
    "cost",
    "late",
    "default",
)


class DeterministicObservationExtractor(ObservationExtractor):
    """Rule-based, model-free observation extraction."""

    def extract(self, evidence: Evidence) -> list[Observation]:
        if evidence.content is None:
            return []
        text = evidence.content
        reference = evidence.effective_time

        entities = self._entities(text)
        measurements, citations = self._measurements(evidence, text)
        claims = self._claims(text)
        effective_at = parse_effective_date(text, reference=reference)

        if not (entities or measurements or claims):
            return []

        strength = self._evidence_strength(measurements, entities)
        provenance = Provenance(
            producer="DeterministicObservationExtractor",
            method=ExtractionMethod.DETERMINISTIC,
            citations=citations,
        )
        observation = Observation(
            evidence_ids=[evidence.id],
            observed_at=reference,
            effective_at=effective_at,
            entities=entities,
            claims=claims,
            measurements=measurements,
            extraction_method=ExtractionMethod.DETERMINISTIC,
            confidence=Confidence(score=strength, evidence_strength=strength),
            provenance=provenance,
        )
        return [observation]

    # -- helpers -------------------------------------------------------------
    def _entities(self, text: str) -> list[EntityRef]:
        refs: list[EntityRef] = []
        for mention in extract_entities(text):
            provisional_id = entity_key(mention.entity_type, mention.name)
            refs.append(
                EntityRef(
                    entity_id=provisional_id,
                    entity_type=mention.entity_type,
                    name=mention.name,
                    role=mention.role,
                )
            )
        return refs

    def _measurements(
        self, evidence: Evidence, text: str
    ) -> tuple[list[Measurement], list[Citation]]:
        measurements: list[Measurement] = []
        citations: list[Citation] = []

        for pct in parse_percentages(text):
            measurements.append(
                Measurement(name="percent", value=pct, unit="percent", basis="stated")
            )

        # Combine currency-marked and labeled (currency-less) amounts, de-duped by
        # (value, context) so the same figure isn't counted twice.
        seen_money: set[tuple[float, str]] = set()
        for hit in [*parse_money(text), *parse_labeled_amounts(text)]:
            key = (round(hit.value, 2), hit.context)
            if key in seen_money:
                continue
            seen_money.add(key)
            measurements.append(
                Measurement(
                    name="money",
                    value=hit.value,
                    unit=hit.currency or "unknown",
                    basis=hit.context,
                )
            )
        for days in parse_durations_days(text):
            measurements.append(
                Measurement(name="duration_days", value=days, unit="days", basis="stated")
            )

        table = summarize_pipe_table(text)
        if table is not None:
            for header, total in table.column_sums.items():
                measurements.append(
                    Measurement(name="table_sum", value=total, unit="unknown", basis=header)
                )
            if table.row_count:
                measurements.append(
                    Measurement(
                        name="row_count", value=float(table.row_count), unit="count", basis="table"
                    )
                )

        if measurements:
            citations.append(
                Citation(
                    evidence_id=evidence.id,
                    locator=f"{evidence.modality}:{evidence.source}",
                    snippet=text[:160],
                )
            )
        return measurements, citations

    def _claims(self, text: str) -> list[Claim]:
        claims: list[Claim] = []
        seen: set[str] = set()
        for raw in _split_sentences(text):
            sentence = raw.strip()
            low = sentence.lower()
            if len(sentence) < 8:
                continue
            if any(k in low for k in _SIGNAL_KEYWORDS):
                key = low[:80]
                if key not in seen:
                    seen.add(key)
                    claims.append(Claim(text=sentence[:280]))
            if len(claims) >= 8:
                break
        return claims

    @staticmethod
    def _evidence_strength(measurements: list[Measurement], entities: list[EntityRef]) -> float:
        score = 0.4
        if any(m.name == "percent" for m in measurements):
            score += 0.2
        if any(m.name in ("money", "table_sum") for m in measurements):
            score += 0.2
        if entities:
            score += 0.15
        return min(0.95, score)


def _split_sentences(text: str) -> list[str]:
    import re

    # Split on sentence terminators and newlines; keep it simple and deterministic.
    parts = re.split(r"(?<=[.!?])\s+|\n+", text)
    return [p for p in parts if p.strip()]


class LLMObservationExtractor(ObservationExtractor):
    """Optional model-assisted extractor.

    Uses an :class:`LLMProvider` to enrich the deterministic extraction with
    additional claims. The model never performs arithmetic; numeric measurements
    still come from the deterministic pass. Output is merged, not trusted blindly.
    """

    def __init__(self, provider, *, base: ObservationExtractor | None = None) -> None:
        self.provider = provider
        self.base = base or DeterministicObservationExtractor()

    def extract(self, evidence: Evidence) -> list[Observation]:
        observations = self.base.extract(evidence)
        if evidence.content is None:
            return observations
        prompt = (
            "Summarize the single most important economic claim in the text in one short "
            "sentence. Do not include numbers you are not certain about.\n\nTEXT:\n"
            + evidence.content[:2000]
        )
        try:
            summary = self.provider.complete(prompt, system="You extract economic claims.")
        except Exception:
            return observations
        if observations and summary.strip():
            obs = observations[0]
            obs.claims.append(Claim(text=summary.strip()[:280]))
            obs.model = getattr(self.provider, "model", None)
            obs.extraction_method = ExtractionMethod.HYBRID
        return observations
