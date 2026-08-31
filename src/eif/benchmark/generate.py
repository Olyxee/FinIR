"""Synthetic benchmark data generator.

Materializes a set of realistic-but-synthetic benchmark cases on disk. Every case
is labeled ``"synthetic": true``. The eight canonical scenarios are deterministic;
``generate_variants`` additionally produces seeded numeric variants for larger
studies. Nothing here fabricates *results* — it fabricates *inputs* and *labels*
so the pipeline can be measured honestly.

Run via the CLI (``eif benchmark generate``) or directly::

    python -m eif.benchmark.generate benchmarks/cases
"""

from __future__ import annotations

import json
import random
import sys
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class CaseSpec:
    case_id: str
    title: str
    description: str
    evidence_date: str
    evidence: dict[str, str]
    gold_events: list[dict]
    realized: dict | None = None
    traditional: dict | None = None
    tags: list[str] = field(default_factory=list)


def _supplier_price_increase() -> CaseSpec:
    email = (
        "From: accounts@abcsupplies.example\n"
        "Subject: Notice of price increase\n\n"
        "Dear valued customer,\n\n"
        "Please be advised that Supplier ABC will implement a 10% price increase "
        "across all components in SKU-A, effective 1 November 2026. This adjustment "
        "reflects rising input and logistics costs.\n\n"
        "Regards,\nABC Supplies Accounts Team\n"
    )
    contract = (
        "MASTER SUPPLY AGREEMENT (extract)\n"
        "Supplier: ABC Supplies (Pty) Ltd\n"
        "Affected products: SKU-A precision components.\n"
        "Current unit pricing is fixed until the effective date of any notified change.\n"
    )
    pos = (
        "po_number,date,supplier,product,amount\n"
        "PO-2026-01,2026-01-20,ABC,SKU-A,10500000\n"
        "PO-2026-02,2026-04-20,ABC,SKU-A,10500000\n"
        "PO-2026-03,2026-07-20,ABC,SKU-A,10500000\n"
        "PO-2026-04,2026-10-20,ABC,SKU-A,10500000\n"
    )
    return CaseSpec(
        case_id="supplier_price_increase",
        title="Supplier announces a future 10% price increase",
        description="Email + contract + purchase history imply a COGS increase before it hits the ledger.",
        evidence_date="2026-09-03",
        evidence={
            "supplier_email.txt": email,
            "master_agreement.txt": contract,
            "purchase_orders.csv": pos,
        },
        gold_events=[
            {
                "event_type": "supplier_price_change",
                "entity_names": ["ABC"],
                "metric": "cost_of_goods_sold",
                "impact_value": 4200000,
                "currency": "ZAR",
                "materiality": "material",
            }
        ],
        realized={
            "occurred": True,
            "realized_at": "2026-11-15",
            "realized_metrics": {"cost_of_goods_sold": 3980000},
            "currency": "ZAR",
        },
        traditional={"detected_at": "2026-10-21", "source": "accounts-payable variance review"},
        tags=["cost", "multimodal-advantage"],
    )


def _customer_revenue_contraction() -> CaseSpec:
    transcript = (
        "Call transcript — Account review with Customer XYZ\n"
        "XYZ: Given our own demand softening, we expect to reduce orders by 20% "
        "starting next quarter. We wanted to give you early notice.\n"
        "Rep: Understood, thank you for flagging it early.\n"
    )
    revenue = "customer,period,annual_revenue\nXYZ,2026,9000000\n"
    return CaseSpec(
        case_id="customer_revenue_contraction",
        title="Customer signals a 20% order reduction",
        description="A call reveals revenue contraction long before invoicing reflects it.",
        evidence_date="2026-09-10",
        evidence={
            "account_call_transcript.txt": transcript,
            "customer_revenue.csv": revenue,
        },
        gold_events=[
            {
                "event_type": "customer_contraction",
                "entity_names": ["XYZ"],
                "metric": "revenue",
                "impact_value": 1800000,
                "currency": "ZAR",
                "materiality": "material",
            }
        ],
        realized={
            "occurred": True,
            "realized_at": "2027-01-31",
            "realized_metrics": {"revenue": 1700000},
            "currency": "ZAR",
        },
        traditional={"detected_at": "2027-01-15", "source": "quarterly revenue actuals"},
        tags=["revenue", "multimodal-advantage"],
    )


def _project_delay_cost_overrun() -> CaseSpec:
    notes = (
        "Project Alpha — steering committee notes\n"
        "The integration workstream is behind schedule. Project Alpha is now expected "
        "to be delayed by 3 weeks. Finance estimates this delay could add between "
        "R850,000 and R1,100,000 in additional cost due to extended contractor time.\n"
    )
    budget = "workstream,budget\nintegration,6000000\nrollout,2500000\n"
    return CaseSpec(
        case_id="project_delay_cost_overrun",
        title="Project delay implies a cost overrun",
        description="Meeting notes quantify a delay-driven cost range ahead of any budget actuals.",
        evidence_date="2026-09-05",
        evidence={
            "steering_notes.txt": notes,
            "project_budget.csv": budget,
        },
        gold_events=[
            {
                "event_type": "project_delay",
                "entity_names": ["Alpha"],
                "metric": "operating_expenses",
                "impact_value": 975000,
                "currency": "ZAR",
                "materiality": "material",
            }
        ],
        realized={
            "occurred": True,
            "realized_at": "2026-12-01",
            "realized_metrics": {"operating_expenses": 1020000},
            "currency": "ZAR",
        },
        traditional={"detected_at": "2026-11-10", "source": "project cost actuals"},
        tags=["operations"],
    )


def _inventory_accumulation() -> CaseSpec:
    ops = (
        "Operations note — Warehouse 2\n"
        "Inventory for SKU-A has been accumulating; stock levels are up 15% over the "
        "last six weeks with no matching sales increase. Holding value is climbing.\n"
    )
    ts = (
        "week,product,inventory_value\n"
        "W1,SKU-A,8000000\n"
        "W2,SKU-A,8200000\n"
        "W3,SKU-A,8500000\n"
        "W4,SKU-A,8800000\n"
        "W5,SKU-A,9000000\n"
        "W6,SKU-A,9200000\n"
    )
    return CaseSpec(
        case_id="inventory_accumulation",
        title="Inventory accumulating faster than sales",
        description="An operations note plus a stock time-series flag working-capital pressure.",
        evidence_date="2026-09-12",
        evidence={
            "operations_note.txt": ops,
            "inventory_timeseries.csv": ts,
        },
        gold_events=[
            {
                "event_type": "inventory_accumulation",
                "entity_names": ["SKU-A"],
                "metric": "inventory_value",
                "materiality": "material",
            }
        ],
        realized={"occurred": True, "realized_at": "2026-11-01", "realized_metrics": {}},
        traditional={"detected_at": "2026-10-25", "source": "month-end inventory report"},
        tags=["operations", "structured-detectable"],
    )


def _contract_obligation() -> CaseSpec:
    contract = (
        "SERVICE AGREEMENT — obligations summary\n"
        "The customer has a committed minimum spend obligation. A shortfall penalty of "
        "R2,000,000 becomes payable if minimum volumes are not met by 31 December 2026.\n"
    )
    payables = "account,period,amount\nservice-fees,2026,4000000\n"
    return CaseSpec(
        case_id="contract_obligation",
        title="Upcoming contractual obligation",
        description="A contract clause creates a future payable not yet in the ledger.",
        evidence_date="2026-09-01",
        evidence={
            "service_agreement.txt": contract,
            "payables.csv": payables,
        },
        gold_events=[
            {
                "event_type": "contract_obligation",
                "entity_names": [],
                "metric": "operating_expenses",
                "impact_value": 2000000,
                "currency": "ZAR",
                "materiality": "material",
            }
        ],
        realized={
            "occurred": True,
            "realized_at": "2026-12-31",
            "realized_metrics": {"operating_expenses": 2000000},
            "currency": "ZAR",
        },
        traditional={"detected_at": "2026-12-20", "source": "period-end accrual"},
        tags=["liquidity"],
    )


def _operational_capacity_issue() -> CaseSpec:
    report = (
        "Maintenance report — Line 3\n"
        "Recurring downtime has reduced effective capacity by 15%. Throughput is "
        "constrained and is expected to reduce output value by approximately "
        "R1,200,000 this quarter until repairs are completed.\n"
    )
    throughput = "line,week,throughput_units\nline-3,W1,10000\nline-3,W2,9800\nline-3,W3,8600\n"
    return CaseSpec(
        case_id="operational_capacity_issue",
        title="Operational capacity constraint",
        description="A maintenance report signals a capacity/throughput constraint.",
        evidence_date="2026-09-08",
        evidence={
            "maintenance_report.txt": report,
            "throughput.csv": throughput,
        },
        gold_events=[
            {
                "event_type": "capacity_change",
                "entity_names": [],
                "metric": "revenue",
                "impact_value": 1200000,
                "currency": "ZAR",
                "materiality": "material",
            }
        ],
        realized={
            "occurred": True,
            "realized_at": "2026-10-15",
            "realized_metrics": {"revenue": 1150000},
            "currency": "ZAR",
        },
        traditional={"detected_at": "2026-10-05", "source": "production output variance"},
        tags=["operations"],
    )


def _conflicting_evidence() -> CaseSpec:
    email1 = (
        "From: sales@abcsupplies.example\n"
        "Subject: Upcoming pricing change\n\n"
        "Supplier ABC intends to increase prices by 8% on SKU-A from 1 October 2026.\n"
    )
    email2 = (
        "From: sales@abcsupplies.example\n"
        "Subject: Update: pricing on hold\n\n"
        "Following your feedback, Supplier ABC will hold current prices and will not "
        "increase pricing on SKU-A at this time.\n"
    )
    pos = "po_number,supplier,product,amount\nPO-A,ABC,SKU-A,20000000\nPO-B,ABC,SKU-A,20000000\n"
    return CaseSpec(
        case_id="conflicting_evidence",
        title="Conflicting supplier pricing signals",
        description="A later message contradicts an earlier price-increase notice; the graph must reconcile.",
        evidence_date="2026-09-02",
        evidence={
            "email_1_increase.txt": email1,
            "email_2_hold.txt": email2,
            "purchase_orders.csv": pos,
        },
        gold_events=[
            {
                "event_type": "supplier_price_change",
                "entity_names": ["ABC"],
                "metric": "cost_of_goods_sold",
                "materiality": "material",
            }
        ],
        realized={"occurred": False, "realized_at": "2026-10-05", "realized_metrics": {}},
        traditional=None,
        tags=["conflict"],
    )


def _benign_non_material() -> CaseSpec:
    note = (
        "Supplier note\n"
        "Supplier ABC will apply a minor 0.5% price adjustment on SKU-A next month. "
        "Spend on this line is small.\n"
    )
    pos = "po_number,supplier,product,amount\nPO-1,ABC,SKU-A,60000\nPO-2,ABC,SKU-A,40000\n"
    return CaseSpec(
        case_id="benign_non_material",
        title="Benign, non-material price tweak",
        description="A tiny price change on tiny spend should NOT be flagged as material (precision test).",
        evidence_date="2026-09-04",
        evidence={
            "supplier_note.txt": note,
            "purchase_orders.csv": pos,
        },
        gold_events=[],  # no material event expected
        realized={"occurred": True, "realized_at": "2026-10-01", "realized_metrics": {}},
        traditional=None,
        tags=["non-material", "precision"],
    )


CANONICAL_BUILDERS = (
    _supplier_price_increase,
    _customer_revenue_contraction,
    _project_delay_cost_overrun,
    _inventory_accumulation,
    _contract_obligation,
    _operational_capacity_issue,
    _conflicting_evidence,
    _benign_non_material,
)


def write_case(root: Path, spec: CaseSpec) -> Path:
    case_dir = root / spec.case_id
    (case_dir / "evidence").mkdir(parents=True, exist_ok=True)
    (case_dir / "labels").mkdir(parents=True, exist_ok=True)

    meta = {
        "id": spec.case_id,
        "title": spec.title,
        "description": spec.description,
        "synthetic": True,
        "evidence_date": spec.evidence_date,
        "tags": spec.tags,
    }
    (case_dir / "case.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

    for name, content in spec.evidence.items():
        (case_dir / "evidence" / name).write_text(content, encoding="utf-8")

    (case_dir / "labels" / "economic_event.json").write_text(
        json.dumps({"events": spec.gold_events}, indent=2), encoding="utf-8"
    )
    if spec.realized is not None:
        (case_dir / "labels" / "realized_outcome.json").write_text(
            json.dumps(spec.realized, indent=2), encoding="utf-8"
        )
    if spec.traditional is not None:
        (case_dir / "labels" / "traditional_detection.json").write_text(
            json.dumps(spec.traditional, indent=2), encoding="utf-8"
        )
    return case_dir


def generate_canonical(root: str | Path) -> list[Path]:
    """Write the eight canonical synthetic cases under ``root``."""
    root = Path(root)
    return [write_case(root, builder()) for builder in CANONICAL_BUILDERS]


def generate_variants(root: str | Path, *, n: int = 3, seed: int = 1234) -> list[Path]:
    """Write ``n`` seeded numeric variants of the supplier-price case."""
    rng = random.Random(seed)
    root = Path(root)
    written: list[Path] = []
    for i in range(n):
        pct = rng.choice([5, 6, 7, 8, 9, 10, 12])
        unit_spend = rng.choice([2, 3, 4, 5]) * 1_000_000
        annual = unit_spend * 4
        exposure = annual * pct / 100
        spec = _supplier_price_increase()
        spec.case_id = f"variant_supplier_{i + 1:02d}"
        spec.title = f"[variant] Supplier price increase {pct}%"
        spec.evidence = {
            "supplier_email.txt": (
                f"Supplier ABC will implement a {pct}% price increase on SKU-A, "
                "effective 1 November 2026.\n"
            ),
            "purchase_orders.csv": (
                "po_number,supplier,product,amount\n"
                + "\n".join(f"PO-{j},ABC,SKU-A,{unit_spend}" for j in range(1, 5))
                + "\n"
            ),
        }
        spec.gold_events = [
            {
                "event_type": "supplier_price_change",
                "entity_names": ["ABC"],
                "metric": "cost_of_goods_sold",
                "impact_value": exposure,
                "currency": "ZAR",
                "materiality": "material" if exposure >= 500000 else "non_material",
            }
        ]
        written.append(write_case(root, spec))
    return written


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    root = argv[0] if argv else "benchmarks/cases"
    paths = generate_canonical(root)
    print(f"Wrote {len(paths)} canonical synthetic cases to {root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
