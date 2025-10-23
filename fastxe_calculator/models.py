"""Data models used across the FastXE calculator."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import List, Optional


class CostType(str, Enum):
    """Enumeration of the supported cost categories."""

    ONE_TIME = "one_time"
    ANNUAL = "annual"
    PER_TRANSACTION = "per_transaction"
    PER_CUSTOMER = "per_customer"
    SUBSCRIPTION = "subscription"
    OPERATIONAL = "operational"
    OTHER = "other"

    @classmethod
    def from_string(cls, value: str) -> "CostType":
        normalized = value.strip().lower().replace("-", "_")
        for member in cls:
            if member.value == normalized:
                return member
        raise ValueError(f"Unknown cost type: {value}")


@dataclass
class VendorCost:
    """Describes a cost line for a specific vendor."""

    vendor: str
    item: "CostItem"


@dataclass
class CostItem:
    """Represents a single cost, optionally with a range."""

    name: str
    cost_type: CostType
    amount: Optional[Decimal] = None
    min_amount: Optional[Decimal] = None
    max_amount: Optional[Decimal] = None
    unit: Optional[str] = None
    notes: Optional[str] = None
    source: Optional[str] = None

    def __post_init__(self) -> None:
        if self.amount is not None and isinstance(self.amount, (int, float)):
            self.amount = Decimal(str(self.amount))
        if self.min_amount is not None and isinstance(self.min_amount, (int, float)):
            self.min_amount = Decimal(str(self.min_amount))
        if self.max_amount is not None and isinstance(self.max_amount, (int, float)):
            self.max_amount = Decimal(str(self.max_amount))

    @property
    def average_amount(self) -> Optional[Decimal]:
        """Return the average value across min/max or the single amount."""

        if self.amount is not None:
            return self.amount
        if self.min_amount is not None and self.max_amount is not None:
            return (self.min_amount + self.max_amount) / Decimal("2")
        return self.min_amount or self.max_amount


@dataclass
class RevenueInputs:
    """Holds the revenue related assumptions for the break-even analysis."""

    analysis_period_months: int = 12
    expected_customers: int = 0
    expected_transactions: int = 0
    customer_price: Decimal = Decimal("0")
    transaction_price: Decimal = Decimal("0")
    subscription_revenue: Decimal = Decimal("0")

    def __post_init__(self) -> None:
        if not isinstance(self.customer_price, Decimal):
            self.customer_price = Decimal(str(self.customer_price))
        if not isinstance(self.transaction_price, Decimal):
            self.transaction_price = Decimal(str(self.transaction_price))
        if not isinstance(self.subscription_revenue, Decimal):
            self.subscription_revenue = Decimal(str(self.subscription_revenue))

    def clone_with(self, **updates: object) -> "RevenueInputs":
        data = {
            "analysis_period_months": self.analysis_period_months,
            "expected_customers": self.expected_customers,
            "expected_transactions": self.expected_transactions,
            "customer_price": self.customer_price,
            "transaction_price": self.transaction_price,
            "subscription_revenue": self.subscription_revenue,
        }
        data.update(updates)
        return RevenueInputs(**data)  # type: ignore[arg-type]


