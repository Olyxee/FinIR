# Benchmark

EIF ships an open benchmark format and a set of synthetic scenarios so anyone can
measure the framework reproducibly.

## Case format

A case is a directory:

```
case/
  case.json                       # id, title, synthetic flag, evidence_date, tags
  evidence/                       # the multimodal evidence EIF ingests
    supplier_email.txt
    purchase_orders.csv
  labels/
    economic_event.json           # gold EconomicEvent labels
    realized_outcome.json         # what actually happened (optional)
    traditional_detection.json    # when structured data would flag it (optional)
```

All shipped cases are marked `"synthetic": true`.

## Shipped scenarios

`eif benchmark generate` writes eight canonical cases: supplier price increase,
customer revenue contraction, project delay / cost overrun, inventory
accumulation, contract obligation, operational capacity issue, a conflicting
evidence case, and a benign non-material case (precision test).

Generate seeded numeric variants for larger studies:

```bash
eif benchmark generate benchmarks/cases --variants 5 --seed 1234
```

## Running

```bash
eif benchmark run --cases benchmarks/cases            # EIF condition
eif benchmark run --cases benchmarks/cases --baseline # structured-only
eif benchmark report --cases benchmarks/cases         # baseline vs EIF table
eif benchmark run --cases benchmarks/cases --json     # machine-readable
```

Programmatically:

```python
from eif.benchmark import run_suite, render_suite_text
from eif.config import Config
print(render_suite_text(run_suite("benchmarks/cases", config=Config())))
```

Each case runs in an isolated in-memory repository; runs are deterministic.

## What it measures

Detection (precision/recall/F1), impact error (vs label and vs realized outcome),
interval coverage, ESLT, and confidence calibration. The **baseline** condition
restricts evidence to structured/tabular files, isolating the value of the extra
modalities.

## Adding your own case

Create a directory under `benchmarks/cases/` following the format above. Keep data
synthetic and label it as such. Real, appropriately anonymized cases are welcome
via PR — see [extending.md](extending.md) and
[../research/experiment_001.md](../research/experiment_001.md).
