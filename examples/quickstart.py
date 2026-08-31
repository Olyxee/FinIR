"""EIF quick-start: supplier price-increase scenario (end to end).

Runs entirely offline with the deterministic default provider — no API keys.

    python examples/quickstart.py
"""

from __future__ import annotations

import json
from pathlib import Path

from eif import EIF
from eif.config import Config

HERE = Path(__file__).parent
DATA = HERE / "data"


def main() -> None:
    # Fully local: SQLite in-memory + deterministic mock provider.
    config = Config()
    config.storage.database_url = "memory"
    config.logging.level = "ERROR"

    eif = EIF(config)

    result = eif.analyze(
        [
            str(DATA / "supplier_email.txt"),
            str(DATA / "master_agreement.txt"),
            str(DATA / "purchase_history.csv"),
        ]
    )

    print(f"Analyzed {len(result.evidence)} pieces of evidence "
          f"-> {len(result.observations)} observations -> {len(result.events)} events\n")

    for event in result.events:
        impact = event.primary_impact()
        print(f"• {event.event_type}  [{event.status}, {event.materiality}]")
        print(f"  title:        {event.title}")
        print(f"  confidence:   {event.confidence.score:.2f}")
        print(f"  effective_at: {event.effective_at:%Y-%m-%d}" if event.effective_at else "  effective_at: —")
        print(f"  entities:     {[f'{e.entity_type}:{e.name}' for e in event.entities]}")
        if impact:
            est = impact.estimate
            print(
                f"  impact:       {impact.metric} {impact.direction} "
                f"{est.point:,.0f} {est.unit}  (range {est.lower:,.0f}–{est.upper:,.0f}, "
                f"conf {est.confidence:.2f})"
            )
            for calc in impact.provenance.calculations:
                print(f"  calculation:  {calc.expression}  {calc.inputs} = {calc.result:,.0f}")
        print()

    # Machine-readable output — the whole point of EIF.
    primary = result.material_events()[0]
    print("Machine-readable event (abridged):")
    print(
        json.dumps(
            {
                "event_type": primary.event_type,
                "status": primary.status,
                "confidence": round(primary.confidence.score, 2),
                "effective_at": primary.effective_at.date().isoformat() if primary.effective_at else None,
                "impacts": [
                    {
                        "metric": i.metric,
                        "direction": i.direction,
                        "estimate": round(i.estimate.point),
                        "currency": i.estimate.unit,
                    }
                    for i in primary.impacts
                ],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
