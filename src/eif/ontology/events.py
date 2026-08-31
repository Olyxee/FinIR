"""The economic-event-type ontology.

This registry ships with a rich default catalogue of event types but is fully
extensible: downstream users call ``EVENT_REGISTRY.register(...)`` to add their
own without touching the framework. Each definition declares the metrics an event
of that type typically affects and the usual direction of impact, which the
deterministic impact estimator uses as a starting point.
"""

from __future__ import annotations

from pydantic import Field

from ..domain.base import EIFModel
from ..domain.enums import Direction
from .registry import Registry


class EventTypeDefinition(EIFModel):
    """Definition of an economic event type."""

    key: str
    label: str
    category: str = Field(description="cost | revenue | supply | liquidity | operations | risk.")
    description: str = ""
    default_metrics: list[str] = Field(default_factory=list)
    typical_direction: Direction = Direction.UNKNOWN
    # Impact-estimation strategy name (see eif.pipeline.impact). Optional; the
    # estimator falls back to a generic strategy when unset.
    impact_strategy: str | None = None


EVENT_REGISTRY: Registry[EventTypeDefinition] = Registry("event_types")


_DEFAULTS: tuple[EventTypeDefinition, ...] = (
    EventTypeDefinition(
        key="price_change",
        label="Price Change",
        category="cost",
        description="Generic price change from a counterparty.",
        default_metrics=["cost_of_goods_sold", "gross_margin"],
        typical_direction=Direction.INCREASE,
        impact_strategy="spend_pct",
    ),
    EventTypeDefinition(
        key="supplier_price_change",
        label="Supplier Price Change",
        category="cost",
        description="A supplier announces a change to prices on goods/services purchased.",
        default_metrics=["cost_of_goods_sold", "gross_margin"],
        typical_direction=Direction.INCREASE,
        impact_strategy="spend_pct",
    ),
    EventTypeDefinition(
        key="demand_change",
        label="Demand Change",
        category="revenue",
        description="A change in customer demand for products/services.",
        default_metrics=["revenue"],
        typical_direction=Direction.UNKNOWN,
        impact_strategy="revenue_run_rate",
    ),
    EventTypeDefinition(
        key="supply_change",
        label="Supply Change",
        category="supply",
        description="A change in available supply of an input.",
        default_metrics=["cost_of_goods_sold"],
        impact_strategy="spend_pct",
    ),
    EventTypeDefinition(
        key="supply_disruption",
        label="Supply Disruption",
        category="supply",
        description="An interruption to the supply of a critical input.",
        default_metrics=["cost_of_goods_sold", "revenue"],
        typical_direction=Direction.INCREASE,
        impact_strategy="generic",
    ),
    EventTypeDefinition(
        key="customer_expansion",
        label="Customer Expansion",
        category="revenue",
        description="A customer increases usage/orders.",
        default_metrics=["revenue"],
        typical_direction=Direction.INCREASE,
        impact_strategy="revenue_run_rate",
    ),
    EventTypeDefinition(
        key="customer_contraction",
        label="Customer Contraction",
        category="revenue",
        description="A customer reduces usage/orders or signals churn.",
        default_metrics=["revenue"],
        typical_direction=Direction.DECREASE,
        impact_strategy="revenue_run_rate",
    ),
    EventTypeDefinition(
        key="contract_obligation",
        label="Contract Obligation",
        category="liquidity",
        description="An upcoming financial obligation embedded in a contract.",
        default_metrics=["operating_expenses", "cash_flow"],
        typical_direction=Direction.INCREASE,
        impact_strategy="fixed_amount",
    ),
    EventTypeDefinition(
        key="contract_expiration",
        label="Contract Expiration",
        category="revenue",
        description="A contract is approaching expiry, creating renewal/loss risk.",
        default_metrics=["revenue"],
        typical_direction=Direction.DECREASE,
        impact_strategy="fixed_amount",
    ),
    EventTypeDefinition(
        key="payment_delay",
        label="Payment Delay",
        category="liquidity",
        description="A customer is likely to pay late.",
        default_metrics=["accounts_receivable", "cash_flow"],
        typical_direction=Direction.INCREASE,
        impact_strategy="fixed_amount",
    ),
    EventTypeDefinition(
        key="collection_risk",
        label="Collection Risk",
        category="risk",
        description="Risk that a receivable will not be collected in full.",
        default_metrics=["accounts_receivable", "cash_flow"],
        typical_direction=Direction.DECREASE,
        impact_strategy="fixed_amount",
    ),
    EventTypeDefinition(
        key="project_delay",
        label="Project Delay",
        category="operations",
        description="A project is expected to slip its schedule.",
        default_metrics=["operating_expenses", "revenue"],
        typical_direction=Direction.INCREASE,
        impact_strategy="delay_cost",
    ),
    EventTypeDefinition(
        key="cost_overrun",
        label="Cost Overrun",
        category="cost",
        description="A project/initiative is expected to exceed budget.",
        default_metrics=["operating_expenses"],
        typical_direction=Direction.INCREASE,
        impact_strategy="fixed_amount",
    ),
    EventTypeDefinition(
        key="capacity_change",
        label="Capacity Change",
        category="operations",
        description="A change in operational capacity.",
        default_metrics=["revenue", "operating_expenses"],
        impact_strategy="generic",
    ),
    EventTypeDefinition(
        key="inventory_accumulation",
        label="Inventory Accumulation",
        category="operations",
        description="Inventory is building up beyond expected levels.",
        default_metrics=["inventory_value", "working_capital"],
        typical_direction=Direction.INCREASE,
        impact_strategy="inventory_delta",
    ),
    EventTypeDefinition(
        key="inventory_shortage",
        label="Inventory Shortage",
        category="operations",
        description="Inventory is depleting below safe levels.",
        default_metrics=["revenue", "inventory_value"],
        typical_direction=Direction.DECREASE,
        impact_strategy="inventory_delta",
    ),
    EventTypeDefinition(
        key="asset_failure_risk",
        label="Asset Failure Risk",
        category="risk",
        description="An asset shows signs of imminent failure.",
        default_metrics=["operating_expenses", "capex"],
        typical_direction=Direction.INCREASE,
        impact_strategy="generic",
    ),
    EventTypeDefinition(
        key="regulatory_change",
        label="Regulatory Change",
        category="risk",
        description="A regulatory change creates new obligations or costs.",
        default_metrics=["operating_expenses"],
        typical_direction=Direction.INCREASE,
        impact_strategy="generic",
    ),
    EventTypeDefinition(
        key="workforce_change",
        label="Workforce Change",
        category="operations",
        description="A material change in workforce (attrition, hiring, strike).",
        default_metrics=["operating_expenses"],
        impact_strategy="generic",
    ),
    EventTypeDefinition(
        key="revenue_opportunity",
        label="Revenue Opportunity",
        category="revenue",
        description="An emerging opportunity to grow revenue.",
        default_metrics=["revenue"],
        typical_direction=Direction.INCREASE,
        impact_strategy="revenue_run_rate",
    ),
    EventTypeDefinition(
        key="revenue_risk",
        label="Revenue Risk",
        category="risk",
        description="An emerging risk to expected revenue.",
        default_metrics=["revenue"],
        typical_direction=Direction.DECREASE,
        impact_strategy="revenue_run_rate",
    ),
    EventTypeDefinition(
        key="liquidity_pressure",
        label="Liquidity Pressure",
        category="liquidity",
        description="Pressure on the organization's short-term liquidity.",
        default_metrics=["cash_flow", "liquidity"],
        typical_direction=Direction.DECREASE,
        impact_strategy="generic",
    ),
    EventTypeDefinition(
        key="margin_pressure",
        label="Margin Pressure",
        category="cost",
        description="Downward pressure on gross/operating margin.",
        default_metrics=["gross_margin"],
        typical_direction=Direction.DECREASE,
        impact_strategy="generic",
    ),
)


def _seed() -> None:
    for defn in _DEFAULTS:
        if not EVENT_REGISTRY.has(defn.key):
            EVENT_REGISTRY.register(defn)


_seed()


def is_known_event_type(key: str) -> bool:
    return EVENT_REGISTRY.has(key)
