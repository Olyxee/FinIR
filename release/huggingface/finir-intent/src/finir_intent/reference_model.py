"""A small demo :class:`~finir.FinancialModel` spanning every FinIR-IntentBench target.

This is fixture data for the Hugging Face workstream's end-to-end proof and the
Space demo -- not a real company's financials. It exists so every target the
baseline compiler can name (see ``finir_intent.baseline._TARGET_KIND``) is a real
input the runtime can execute against. Built entirely from the public
``finir.FinancialModel`` API; it adds no new runtime behavior and duplicates no
execution logic.
"""

from __future__ import annotations

from finir import FinancialModel


def build_reference_model() -> FinancialModel:
    m = FinancialModel(name="finir_intent_reference")
    m.input("revenue", 500_000_000, currency="ZAR")
    m.input("cogs", 300_000_000, currency="ZAR")
    m.input("opex", 120_000_000, currency="ZAR")
    m.input("payment_terms", 30, type="days")
    m.input("accounts_payable", 40_000_000, currency="ZAR")
    m.input("inventory", 50_000_000, currency="ZAR")
    m.input("capex", 60_000_000, currency="ZAR")
    m.input("debt", 200_000_000, currency="ZAR")
    m.input("interest_rate", 0.09, type="percentage")
    m.input("cash", 80_000_000, currency="ZAR")
    m.input("price", 1_250, currency="ZAR")
    m.input("volume", 400_000, type="quantity[units]")

    m.define("gross_profit", "revenue - cogs")
    m.define("gross_margin", "gross_profit / revenue", output=True)
    m.define("ebitda", "gross_profit - opex", output=True)
    m.define("interest_expense", "debt * interest_rate", output=True)
    m.define("net_cash_position", "cash - capex", output=True)
    return m
