"""Core pricing and break-even calculations."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, Iterable, List, Optional

from .models import CostItem, CostType, RevenueInputs


@dataclass
class CostSummary:
    """Aggregated totals used in reports and exports."""

    fixed_costs: Decimal
    variable_cost_per_customer: Decimal
    variable_cost_per_transaction: Decimal
    total_costs: Decimal


class BreakEvenCalculator:
    """Compute break-even metrics from vendor and internal costs."""

    def __init__(
        self,
        cost_items: Iterable[CostItem],
        revenue_inputs: Optional[RevenueInputs] = None,
    ) -> None:
        self.cost_items: List[CostItem] = list(cost_items)
        self.revenue_inputs = revenue_inputs or RevenueInputs()

    def _sum_costs(self, *types: CostType) -> Decimal:
        total = Decimal("0")
        for item in self.cost_items:
            if item.cost_type in types:
                amount = item.average_amount
                if amount is not None:
                    total += amount
        return total

    def total_fixed_costs(self) -> Decimal:
        return self._sum_costs(
            CostType.ONE_TIME,
            CostType.ANNUAL,
            CostType.SUBSCRIPTION,
            CostType.OPERATIONAL,
        )

    def variable_cost_per_customer(self) -> Decimal:
        return self._sum_costs(CostType.PER_CUSTOMER)

    def variable_cost_per_transaction(self) -> Decimal:
        return self._sum_costs(CostType.PER_TRANSACTION)

    def total_costs(self) -> Decimal:
        return self.total_fixed_costs() + self.variable_cost_per_customer() + self.variable_cost_per_transaction()

    def summary(self) -> CostSummary:
        return CostSummary(
            fixed_costs=self.total_fixed_costs(),
            variable_cost_per_customer=self.variable_cost_per_customer(),
            variable_cost_per_transaction=self.variable_cost_per_transaction(),
            total_costs=self.total_costs(),
        )

    # --- Break-even computations -------------------------------------------------

    def break_even_customers(self) -> Optional[Decimal]:
        """Return how many customers are needed to cover fixed costs."""

        revenue_per_customer = self.revenue_inputs.customer_price
        variable = self.variable_cost_per_customer()
        contribution_margin = revenue_per_customer - variable
        if contribution_margin <= 0:
            return None
        return self.total_fixed_costs() / contribution_margin

    def break_even_transactions(self) -> Optional[Decimal]:
        revenue_per_transaction = self.revenue_inputs.transaction_price
        variable = self.variable_cost_per_transaction()
        contribution_margin = revenue_per_transaction - variable
        if contribution_margin <= 0:
            return None
        return self.total_fixed_costs() / contribution_margin

    def required_customer_price(self) -> Optional[Decimal]:
        expected_customers = self.revenue_inputs.expected_customers
        if expected_customers <= 0:
            return None
        variable = self.variable_cost_per_customer()
        fixed = self.total_fixed_costs()
        return variable + (fixed / Decimal(expected_customers))

    def required_transaction_price(self) -> Optional[Decimal]:
        expected_transactions = self.revenue_inputs.expected_transactions
        if expected_transactions <= 0:
            return None
        variable = self.variable_cost_per_transaction()
        fixed = self.total_fixed_costs()
        return variable + (fixed / Decimal(expected_transactions))

    def profitability_projection(self) -> Dict[str, Decimal]:
        revenue = (
            self.revenue_inputs.subscription_revenue
            + self.revenue_inputs.customer_price * Decimal(self.revenue_inputs.expected_customers)
            + self.revenue_inputs.transaction_price * Decimal(self.revenue_inputs.expected_transactions)
        )

        variable_costs = (
            self.variable_cost_per_customer() * Decimal(self.revenue_inputs.expected_customers)
            + self.variable_cost_per_transaction() * Decimal(self.revenue_inputs.expected_transactions)
        )

        fixed_costs = self.total_fixed_costs()
        profit = revenue - variable_costs - fixed_costs
        return {
            "revenue": revenue,
            "variable_costs": variable_costs,
            "fixed_costs": fixed_costs,
            "profit": profit,
        }
