"""End-to-end company model (item 44).

Builds a small operating + working-capital model, runs several what-if scenarios,
and prints what was recomputed vs. reused, the cache stats, the chosen backend, and
latency. Everything runs on CPU with no optional dependencies.

    python examples/company_model/run.py
"""

from __future__ import annotations

import time

import numpy as np

from finir import FinancialModel


def build() -> FinancialModel:
    m = FinancialModel(name="company")
    m.input("revenue", 500_000_000, currency="ZAR")
    m.input("cogs", 300_000_000, currency="ZAR")
    m.input("opex", 120_000_000, currency="ZAR")
    m.input("receivable_days", 30, type="days")
    m.input("payable_days", 45, type="days")
    m.input("inventory", 50_000_000, currency="ZAR")

    m.define("gross_profit", "revenue - cogs")
    m.define("gross_margin", "gross_profit / revenue", output=True)
    m.define("ebitda", "gross_profit - opex", output=True)
    m.define("receivables", "receivables(revenue, receivable_days)")
    m.define("payables", "payables(cogs, payable_days)")
    m.define("working_capital", "working_capital(receivables, inventory, payables)", output=True)
    return m


def _show(label: str, result) -> None:
    print(f"\n{label}")
    print(f"  ebitda          = R{float(result['ebitda']):,.0f}")
    print(f"  gross_margin    = {float(result['gross_margin']):.3f}")
    print(f"  working_capital = R{float(result['working_capital']):,.0f}")
    print(f"  recomputed={sorted(result.recomputed)}")
    print(f"  reused    ={sorted(result.reused)}")


def main() -> None:
    m = build()
    print("FinIR company model — incremental scenarios\n" + "=" * 46)

    base = m.evaluate()
    _show("BASE", base)

    _show("Scenario 1 — COGS +4%", m.what_if(cogs="+4%"))
    _show("Scenario 2 — Revenue -8%", m.what_if(revenue="-8%"))
    _show("Scenario 3 — payment terms 30 -> 60 days", m.what_if(receivable_days="30d->60d"))
    _show(
        "Scenario 4 — all combined",
        m.what_if(cogs="+4%", revenue="-8%", receivable_days="30d->60d"),
    )

    # Scenario 5 — a 100k-scenario grid over COGS (vectorized).
    t0 = time.perf_counter()
    grid = m.run_scenarios(cogs=np.linspace(300_000_000, 400_000_000, 100_000))
    dt = time.perf_counter() - t0
    print("\nScenario 5 — 100,000-scenario COGS grid (vectorized)")
    print(
        f"  ebitda range    = R{float(grid['ebitda'].min()):,.0f} .. R{float(grid['ebitda'].max()):,.0f}"
    )
    print(f"  backend         = {grid.stats.backend}")
    print(f"  scenario_size   = {grid.stats.scenario_size:,}")
    print(f"  latency         = {dt * 1000:.1f} ms  (~{100_000 / dt:,.0f} scenarios/s)")

    print("\nCache stats:", m.cache_stats())


if __name__ == "__main__":
    main()
