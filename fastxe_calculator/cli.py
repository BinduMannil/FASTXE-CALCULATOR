"""Command line interface for the FastXE pricing calculator."""
from __future__ import annotations

import argparse
import json
from decimal import Decimal
from pathlib import Path
from typing import Iterable, List

from .calculator import BreakEvenCalculator
from .excel import ExportOptions, export_to_workbook
from .models import CostItem, CostType, RevenueInputs, VendorCost
from .pdf_parser import parse_multiple_pdfs


def _parse_manual_costs(entries: Iterable[str]) -> List[VendorCost]:
    costs: List[VendorCost] = []
    for entry in entries:
        parts = [part.strip() for part in entry.split(":")]
        if len(parts) < 4:
            raise ValueError(
                "Manual cost entries must follow the format 'vendor:type:name:amount[:notes]'."
            )
        vendor, cost_type_name, name, amount_str, *rest = parts
        cost_type = CostType.from_string(cost_type_name)
        amount = Decimal(amount_str)
        notes = rest[0] if rest else None
        costs.append(
            VendorCost(
                vendor=vendor,
                item=CostItem(name=name, cost_type=cost_type, amount=amount, notes=notes, source="manual"),
            )
        )
    return costs


def _load_costs_from_json(path: Path) -> List[VendorCost]:
    data = json.loads(path.read_text())
    costs: List[VendorCost] = []
    for entry in data:
        vendor = entry.get("vendor", "custom")
        cost_type = CostType.from_string(entry["type"])
        amount = Decimal(str(entry.get("amount", "0"))) if "amount" in entry else None
        min_amount = Decimal(str(entry.get("min_amount"))) if "min_amount" in entry else None
        max_amount = Decimal(str(entry.get("max_amount"))) if "max_amount" in entry else None
        costs.append(
            VendorCost(
                vendor=vendor,
                item=CostItem(
                    name=entry.get("name", cost_type.value),
                    cost_type=cost_type,
                    amount=amount,
                    min_amount=min_amount,
                    max_amount=max_amount,
                    unit=entry.get("unit"),
                    notes=entry.get("notes"),
                    source=str(path),
                ),
            )
        )
    return costs


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="FastXE pricing and break-even calculator")
    parser.add_argument("--pdf", nargs="*", help="Vendor PDF files to parse for pricing data")
    parser.add_argument(
        "--cost",
        action="append",
        default=[],
        help="Manual cost entry in the format vendor:type:name:amount[:notes]",
    )
    parser.add_argument(
        "--cost-json",
        type=Path,
        help="Optional JSON file describing additional costs (list of objects with vendor/type/amount).",
    )
    parser.add_argument("--output", type=Path, default=Path("fastxe-pricing.xlsx"))
    parser.add_argument("--expected-customers", type=int, default=0)
    parser.add_argument("--expected-transactions", type=int, default=0)
    parser.add_argument("--customer-price", type=Decimal, default=Decimal("0"))
    parser.add_argument("--transaction-price", type=Decimal, default=Decimal("0"))
    parser.add_argument(
        "--subscription-revenue",
        type=Decimal,
        default=Decimal("0"),
        help="Flat recurring revenue expected within the analysis period",
    )
    parser.add_argument(
        "--analysis-period-months",
        type=int,
        default=12,
        help="Duration of the analysis window. All costs should be expressed within this timeframe.",
    )
    parser.add_argument(
        "--period-label",
        type=str,
        default="12-month outlook",
        help="Label used in the workbook summary to describe the analysis period.",
    )
    return parser


def gather_costs_from_inputs(args: argparse.Namespace) -> List[VendorCost]:
    costs: List[VendorCost] = []
    if args.pdf:
        costs.extend(parse_multiple_pdfs(args.pdf))
    if args.cost:
        costs.extend(_parse_manual_costs(args.cost))
    if args.cost_json:
        costs.extend(_load_costs_from_json(args.cost_json))
    return costs


def main(argv: Iterable[str] | None = None) -> Path:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    costs = gather_costs_from_inputs(args)
    revenue_inputs = RevenueInputs(
        analysis_period_months=args.analysis_period_months,
        expected_customers=args.expected_customers,
        expected_transactions=args.expected_transactions,
        customer_price=Decimal(str(args.customer_price)),
        transaction_price=Decimal(str(args.transaction_price)),
        subscription_revenue=Decimal(str(args.subscription_revenue)),
    )

    calculator = BreakEvenCalculator([cost.item for cost in costs], revenue_inputs)
    summary = calculator.summary()

    print("--- Cost Summary ---")
    print(f"Fixed costs: {summary.fixed_costs:,.2f}")
    print(f"Variable cost per customer: {summary.variable_cost_per_customer:,.2f}")
    print(f"Variable cost per transaction: {summary.variable_cost_per_transaction:,.2f}")

    breakeven_customers = calculator.break_even_customers()
    breakeven_transactions = calculator.break_even_transactions()
    if breakeven_customers is not None:
        print(f"Break-even customers at configured price: {breakeven_customers:,.2f}")
    else:
        print("Break-even customers could not be determined (insufficient margin).")
    if breakeven_transactions is not None:
        print(f"Break-even transactions at configured price: {breakeven_transactions:,.2f}")
    else:
        print("Break-even transactions could not be determined (insufficient margin).")

    required_customer_price = calculator.required_customer_price()
    required_transaction_price = calculator.required_transaction_price()
    if required_customer_price is not None:
        print(f"Required price per customer: {required_customer_price:,.2f}")
    if required_transaction_price is not None:
        print(f"Required price per transaction: {required_transaction_price:,.2f}")

    profitability = calculator.profitability_projection()
    print("Projected revenue: {0:,.2f}".format(profitability["revenue"]))
    print("Projected variable costs: {0:,.2f}".format(profitability["variable_costs"]))
    print("Projected fixed costs: {0:,.2f}".format(profitability["fixed_costs"]))
    print("Projected profit: {0:,.2f}".format(profitability["profit"]))

    export_path = export_to_workbook(
        costs,
        ExportOptions(
            output_path=args.output,
            revenue_inputs=revenue_inputs,
            expected_period_label=args.period_label,
        ),
    )
    print(f"Workbook exported to {export_path}")
    return export_path


if __name__ == "__main__":  # pragma: no cover
    main()
