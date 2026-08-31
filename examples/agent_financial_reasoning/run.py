"""AI-agent financial reasoning over FinIR (item 26).

Flow:  natural-language request -> structured intent -> FinIR mutation ->
incremental execution -> result. No live LLM is required — a deterministic
MockIntentCompiler stands in for the language model. Real LLM-backed compilers can
implement the same IntentCompiler interface behind extras.

    python examples/agent_financial_reasoning/run.py
"""

from __future__ import annotations

from finir import FinancialModel, MockIntentCompiler


def build() -> FinancialModel:
    m = FinancialModel(name="agent_demo")
    m.input("revenue", 500_000_000, currency="ZAR")
    m.input("cogs", 300_000_000, currency="ZAR")
    m.input("opex", 120_000_000, currency="ZAR")
    m.define("gross_profit", "revenue - cogs")
    m.define("gross_margin", "gross_profit / revenue", output=True)
    m.define("ebitda", "gross_profit - opex", output=True)
    return m


def main() -> None:
    model = build()
    compiler = MockIntentCompiler()
    model.evaluate()  # warm the base

    print("Agent reasoning over FinIR (model interprets, runtime computes)\n" + "=" * 60)
    requests = [
        "What happens if supplier costs increase by 7%?",
        "And if revenue grows 5%?",
        "What if we reduce opex by 10%?",
    ]
    for text in requests:
        intent = compiler.compile(text)  # LLM layer: text -> structured intent
        result = model.apply_intent(intent)  # runtime: execute the intent incrementally
        print(f'\nAgent: "{text}"')
        print(f"  intent   -> {intent}")
        print(f"  ebitda    = R{float(result['ebitda']):,.0f}")
        print(f"  margin    = {float(result['gross_margin']):.3f}")
        print(f"  recomputed={sorted(result.recomputed)}  reused={sorted(result.reused)}")

    print("\nThe agent never generated arbitrary Python — it emitted structured intent,")
    print("and FinIR executed it deterministically, recomputing only affected nodes.")
    print("cache stats:", model.cache_stats())


if __name__ == "__main__":
    main()
