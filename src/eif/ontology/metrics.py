"""The metric ontology: financial metrics that events can affect."""

from __future__ import annotations

from pydantic import Field

from ..domain.base import EIFModel
from .registry import Registry


class MetricDefinition(EIFModel):
    """Definition of an affectable financial metric."""

    key: str
    label: str
    statement: str = Field(description="Which statement: income | balance_sheet | cash_flow.")
    unit_kind: str = Field(default="currency", description="currency | percent | ratio | count.")
    description: str = ""


METRIC_REGISTRY: Registry[MetricDefinition] = Registry("metrics")


def _seed() -> None:
    defaults = [
        MetricDefinition(
            key="revenue",
            label="Revenue",
            statement="income",
            description="Top-line sales.",
        ),
        MetricDefinition(
            key="cost_of_goods_sold",
            label="Cost of Goods Sold",
            statement="income",
            description="Direct costs of goods/services sold.",
        ),
        MetricDefinition(
            key="gross_margin",
            label="Gross Margin",
            statement="income",
            unit_kind="ratio",
            description="Revenue minus COGS, as a ratio or absolute.",
        ),
        MetricDefinition(
            key="operating_expenses",
            label="Operating Expenses",
            statement="income",
            description="Overheads and operating costs.",
        ),
        MetricDefinition(
            key="operating_income",
            label="Operating Income",
            statement="income",
            description="Profit from core operations.",
        ),
        MetricDefinition(
            key="working_capital",
            label="Working Capital",
            statement="balance_sheet",
            description="Current assets minus current liabilities.",
        ),
        MetricDefinition(
            key="inventory_value",
            label="Inventory Value",
            statement="balance_sheet",
            description="Carrying value of inventory.",
        ),
        MetricDefinition(
            key="accounts_receivable",
            label="Accounts Receivable",
            statement="balance_sheet",
            description="Outstanding customer balances.",
        ),
        MetricDefinition(
            key="accounts_payable",
            label="Accounts Payable",
            statement="balance_sheet",
            description="Outstanding supplier balances.",
        ),
        MetricDefinition(
            key="cash_flow",
            label="Cash Flow",
            statement="cash_flow",
            description="Net cash movement.",
        ),
        MetricDefinition(
            key="liquidity",
            label="Liquidity",
            statement="cash_flow",
            unit_kind="ratio",
            description="Ability to meet short-term obligations.",
        ),
        MetricDefinition(
            key="capex",
            label="Capital Expenditure",
            statement="cash_flow",
            description="Spend on long-lived assets.",
        ),
    ]
    for m in defaults:
        if not METRIC_REGISTRY.has(m.key):
            METRIC_REGISTRY.register(m)


_seed()
