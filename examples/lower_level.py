"""Lower-level EIF API: drive the pipeline stages directly.

Shows how the connector -> extractor -> pipeline layers compose, for callers who
want more control than the ``EIF`` facade offers.

    python examples/lower_level.py
"""

from __future__ import annotations

from pathlib import Path

from eif.config import Config
from eif.connectors import default_registry
from eif.pipeline import EIFPipeline
from eif.storage import open_repository

DATA = Path(__file__).parent / "data"


def main() -> None:
    config = Config()
    repo = open_repository("memory")

    # 1. Load evidence with the connector registry.
    registry = default_registry()
    evidence = registry.load_many(
        [str(DATA / "supplier_email.txt"), str(DATA / "purchase_history.csv")]
    )
    print(f"Loaded {len(evidence)} evidence objects")

    # 2. Run the pipeline (extraction -> events -> impact -> graph).
    pipeline = EIFPipeline(repo, config=config)
    result = pipeline.process_evidence(evidence)

    # 3. Inspect the resulting graph.
    for event in repo.list_events().items:
        impact = event.primary_impact()
        print(f"{event.event_type}: {impact.metric if impact else 'no impact'} "
              f"{round(impact.estimate.point) if impact else ''}")

    print(f"\nRepository stats: {repo.stats()}")


if __name__ == "__main__":
    main()
