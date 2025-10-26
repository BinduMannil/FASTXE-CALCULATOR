"""Web dashboard for the FastXE calculator."""
from __future__ import annotations

import argparse
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from flask import Flask, render_template, request

from .calculator import BreakEvenCalculator
from .models import CostItem, CostType, RevenueInputs


def _resource_path(*parts: str) -> str:
    return str(Path(__file__).resolve().parent.joinpath(*parts))


def create_app() -> Flask:
    app = Flask(
        __name__,
        template_folder=_resource_path("templates"),
        static_folder=_resource_path("static"),
    )

    cost_type_options = [
        {
            "value": cost_type.value,
            "label": cost_type.name.replace("_", " ").title(),
        }
        for cost_type in CostType
    ]

    @app.template_filter("currency")
    def format_currency(value: Optional[Decimal]) -> str:
        if value is None:
            return "—"
        return f"${value:,.2f}"

    @app.template_filter("decimal")
    def format_decimal(value: Optional[Decimal]) -> str:
        if value is None:
            return "—"
        return f"{value:,.2f}"

    def _default_cost_row() -> Dict[str, str]:
        return {
            "vendor": "",
            "name": "",
            "cost_type": CostType.OPERATIONAL.value,
            "amount": "",
            "notes": "",
        }

    def _parse_int(value: str, field: str, errors: List[str], default: int = 0) -> int:
        if not value:
            return default
        try:
            return int(value)
        except ValueError:
            errors.append(f"{field} must be an integer.")
            return default

    def _parse_decimal(
        value: str,
        field: str,
        errors: List[str],
        default: Decimal = Decimal("0"),
    ) -> Decimal:
        if not value:
            return default
        try:
            return Decimal(value)
        except (InvalidOperation, ValueError):
            errors.append(f"{field} must be a valid number.")
            return default

    @app.route("/", methods=["GET", "POST"])
    def dashboard():
        errors: List[str] = []
        results: Optional[Dict[str, object]] = None

        form_defaults = {
            "expected_customers": "2500",
            "expected_transactions": "120000",
            "customer_price": "35",
            "transaction_price": "0.45",
            "subscription_revenue": "0",
            "analysis_period_months": "12",
        }

        form_values = {key: request.form.get(key, default) for key, default in form_defaults.items()}

        cost_rows: List[Dict[str, str]] = []
        if request.method == "POST":
            vendors = request.form.getlist("cost_vendor")
            types = request.form.getlist("cost_type")
            names = request.form.getlist("cost_name")
            amounts = request.form.getlist("cost_amount")
            notes_list = request.form.getlist("cost_notes")

            cost_items: List[CostItem] = []

            for idx, vendor in enumerate(vendors):
                row = {
                    "vendor": vendor,
                    "cost_type": types[idx] if idx < len(types) else CostType.OPERATIONAL.value,
                    "name": names[idx] if idx < len(names) else "",
                    "amount": amounts[idx] if idx < len(amounts) else "",
                    "notes": notes_list[idx] if idx < len(notes_list) else "",
                }
                cost_rows.append(row)

                if not any(value.strip() for value in (row["vendor"], row["name"], row["amount"])):
                    continue

                if not row["vendor"].strip():
                    errors.append("Each cost entry must include a vendor name.")
                    continue

                if not row["name"].strip():
                    errors.append("Each cost entry must include a cost description.")
                    continue

                if not row["amount"].strip():
                    errors.append(f"An amount is required for {row['vendor']} - {row['name']}.")
                    continue

                try:
                    cost_type = CostType.from_string(row["cost_type"])
                except ValueError:
                    errors.append(f"Unknown cost type for vendor {row['vendor']}.")
                    continue

                before_errors = len(errors)
                amount_value = _parse_decimal(
                    row["amount"], f"Amount for {row['vendor']} - {row['name']}", errors
                )
                if len(errors) > before_errors:
                    continue

                cost_items.append(
                    CostItem(
                        name=row["name"].strip(),
                        cost_type=cost_type,
                        amount=amount_value,
                        notes=row["notes"].strip() or None,
                    )
                )

            expected_customers = _parse_int(form_values["expected_customers"], "Expected customers", errors)
            expected_transactions = _parse_int(form_values["expected_transactions"], "Expected transactions", errors)
            customer_price = _parse_decimal(form_values["customer_price"], "Customer price", errors)
            transaction_price = _parse_decimal(form_values["transaction_price"], "Transaction price", errors)
            subscription_revenue = _parse_decimal(form_values["subscription_revenue"], "Subscription revenue", errors)
            analysis_period = _parse_int(form_values["analysis_period_months"], "Analysis period", errors, default=12)

            revenue_inputs = RevenueInputs(
                analysis_period_months=analysis_period,
                expected_customers=expected_customers,
                expected_transactions=expected_transactions,
                customer_price=customer_price,
                transaction_price=transaction_price,
                subscription_revenue=subscription_revenue,
            )

            if not errors:
                calculator = BreakEvenCalculator(cost_items, revenue_inputs)
                summary = calculator.summary()
                profitability = calculator.profitability_projection()
                results = {
                    "summary": summary,
                    "break_even_customers": calculator.break_even_customers(),
                    "break_even_transactions": calculator.break_even_transactions(),
                    "required_customer_price": calculator.required_customer_price(),
                    "required_transaction_price": calculator.required_transaction_price(),
                    "profitability": profitability,
                    "revenue_inputs": revenue_inputs,
                    "cost_count": len(cost_items),
                }

        if not cost_rows:
            cost_rows.append(_default_cost_row())

        return render_template(
            "dashboard.html",
            cost_rows=cost_rows,
            form_values=form_values,
            cost_type_options=cost_type_options,
            errors=errors,
            results=results,
        )

    @app.route("/healthz")
    def healthcheck():
        return {"status": "ok"}

    return app


def main(argv: Optional[Iterable[str]] = None) -> None:
    parser = argparse.ArgumentParser(description="Run the FastXE web dashboard")
    parser.add_argument("--host", default="127.0.0.1", help="Hostname to bind the development server to")
    parser.add_argument("--port", type=int, default=8000, help="Port to run the development server on")
    parser.add_argument("--debug", action="store_true", help="Enable Flask debug mode")
    args = parser.parse_args(list(argv) if argv is not None else None)

    app = create_app()
    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":  # pragma: no cover
    main()
