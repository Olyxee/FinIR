"""SaaS unit-economics template."""

from __future__ import annotations

from ..model import FinancialModel


def saas(model: FinancialModel) -> FinancialModel:
    """Given ``arpu`` (money), ``gross_margin_pct`` (ratio), ``monthly_churn`` (ratio),
    and ``cac`` (money), define lifetime value and the LTV/CAC ratio.

        lifetime_months = 1 / monthly_churn
        ltv             = arpu * gross_margin_pct * lifetime_months
        ltv_cac         = ltv / cac
    """
    model.define("lifetime_months", "1 / monthly_churn")
    model.define("ltv", "arpu * gross_margin_pct * lifetime_months")
    model.define("ltv_cac", "ltv / cac")
    return model
