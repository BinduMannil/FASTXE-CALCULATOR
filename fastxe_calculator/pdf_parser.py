"""Utility helpers to extract pricing details from vendor PDF documents."""
from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Iterable, List, Optional, Sequence

try:
    from pypdf import PdfReader
except Exception:  # pragma: no cover - optional dependency at runtime
    PdfReader = None  # type: ignore[assignment]

from .models import CostItem, CostType, VendorCost

_COST_KEYWORDS = {
    CostType.ONE_TIME: ["one-time", "one time", "setup", "implementation"],
    CostType.ANNUAL: ["annual", "yearly", "per year"],
    CostType.PER_TRANSACTION: ["per transaction", "transaction fee", "per txn", "per swipe"],
    CostType.PER_CUSTOMER: ["per customer", "per account", "per user", "per business"],
    CostType.SUBSCRIPTION: ["subscription", "monthly fee", "platform fee", "saas"],
    CostType.OPERATIONAL: ["operational", "ops", "support", "maintenance"],
}

_AMOUNT_PATTERN = re.compile(
    r"(?P<prefix>^|[^\d])\$?(?P<amount>[0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]+)?)(?P<suffix>[^\d]|$)"
)
_RANGE_PATTERN = re.compile(
    r"\$?(?P<min>[0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]+)?)\s*[-–]\s*\$?(?P<max>[0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]+)?)"
)


@dataclass
class ParsedLine:
    """Intermediate representation of a parsed PDF text line."""

    text: str
    amounts: Sequence[Decimal]
    min_amount: Optional[Decimal] = None
    max_amount: Optional[Decimal] = None

    @property
    def average_amount(self) -> Optional[Decimal]:
        if self.min_amount is not None and self.max_amount is not None:
            return (self.min_amount + self.max_amount) / Decimal("2")
        if self.amounts:
            return self.amounts[0]
        return None


def _detect_cost_type(text: str) -> CostType:
    lowered = text.lower()
    for cost_type, keywords in _COST_KEYWORDS.items():
        if any(keyword in lowered for keyword in keywords):
            return cost_type
    return CostType.OTHER


def _normalize_amount(value: str) -> Decimal:
    return Decimal(value.replace(",", ""))


def _extract_amounts(text: str) -> ParsedLine:
    range_match = _RANGE_PATTERN.search(text)
    if range_match:
        return ParsedLine(
            text=text,
            amounts=[],
            min_amount=_normalize_amount(range_match.group("min")),
            max_amount=_normalize_amount(range_match.group("max")),
        )

    amounts = [_normalize_amount(match.group("amount")) for match in _AMOUNT_PATTERN.finditer(text)]
    return ParsedLine(text=text, amounts=amounts)


def parse_costs_from_pdf(path: str | Path, vendor_name: Optional[str] = None) -> List[VendorCost]:
    """Parse a PDF file and return the detected vendor cost items."""

    pdf_path = Path(path)
    if PdfReader is None:
        raise RuntimeError("pypdf is required to parse PDF files. Please install the optional dependency.")

    reader = PdfReader(str(pdf_path))
    lines: List[str] = []
    for page in reader.pages:
        try:
            text = page.extract_text() or ""
        except Exception:  # pragma: no cover - library dependent
            text = ""
        lines.extend(filter(None, (line.strip() for line in text.splitlines())))

    items: List[VendorCost] = []
    vendor_label = vendor_name or pdf_path.stem

    for line in lines:
        parsed = _extract_amounts(line)
        amount = parsed.average_amount
        if amount is None:
            continue

        cost_type = _detect_cost_type(line)
        name = line.split(":", 1)[0].strip()
        if not name:
            name = vendor_label

        item = CostItem(
            name=name,
            cost_type=cost_type,
            amount=amount if parsed.amounts else None,
            min_amount=parsed.min_amount,
            max_amount=parsed.max_amount,
            notes=line,
            source=str(pdf_path),
        )
        items.append(VendorCost(vendor=vendor_label, item=item))

    return items


def parse_multiple_pdfs(paths: Iterable[str | Path]) -> List[VendorCost]:
    """Parse several PDF files and concatenate the resulting vendor costs."""

    costs: List[VendorCost] = []
    for path in paths:
        costs.extend(parse_costs_from_pdf(path))
    return costs
