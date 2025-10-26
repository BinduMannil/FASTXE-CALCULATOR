# FASTXE-CALCULATOR

A command-line calculator that consolidates vendor costs, operational expenses, and revenue
assumptions to determine the break-even point for a Neobank business model. The tool can parse
pricing data from PDF agreements, combine it with manually supplied inputs, and export the results
to a multi-tab Excel workbook for further modelling.

## Features

- Parse pricing and fee ranges directly from vendor PDF agreements.
- Categorise costs across one-time, annual, per-customer, per-transaction, subscription, and
  operational categories.
- Capture manual adjustments via command-line flags or JSON.
- Compute break-even metrics for customer and transaction pricing models.
- Generate an Excel workbook with dedicated tabs for fixed costs, variable costs, overall costs,
  revenue assumptions, and a financial summary.

## Installation

The project uses a `pyproject.toml` so it can be installed in an isolated environment:

```bash
python -m venv .venv
source .venv/bin/activate
pip install .
```

## Usage

After installation the `fastxe-calculator` command becomes available. Alternatively you can run the
module directly without installing:

```bash
python -m fastxe_calculator --help
```

Example workflow:

```bash
python -m fastxe_calculator \
  --pdf vendor-core-banking.pdf vendor-kyc.pdf \
  --cost "In-house:operational:Support staff:3500" \
  --cost "In-house:subscription:Cloud infrastructure:1200" \
  --expected-customers 2500 \
  --expected-transactions 120000 \
  --customer-price 35 \
  --transaction-price 0.45 \
  --analysis-period-months 12 \
  --output fastxe-analysis.xlsx
```

The command prints a summary of key metrics to the console and creates an Excel workbook. The
workbook contains the following tabs (pass `--no-export` if you wish to skip workbook generation or
do not have `openpyxl` installed):

- **Fixed Costs** – One-time, annual, subscription, and operational expenses.
- **Variable Costs** – Per-customer and per-transaction vendor charges.
- **All Costs** – Combined view of every detected cost item.
- **Summary** – Break-even calculations, required pricing, and profitability projections.
- **Revenue Inputs** – The assumptions used when computing projections.

### Providing additional costs via JSON

You can load structured cost inputs from JSON using the `--cost-json` option. The JSON file should
contain a list of objects; each object may include the following keys:

```json
[
  {
    "vendor": "Payments Processor",
    "type": "per_transaction",
    "name": "Card interchange markup",
    "amount": 0.12,
    "notes": "USD per successful card payment"
  },
  {
    "vendor": "Compliance",
    "type": "annual",
    "name": "Regulatory reporting",
    "amount": 6000
  }
]
```

### Parsing PDFs

The parser extracts numbers and classifies them into cost categories based on keywords such as
"one-time", "annual", "per customer", or "per transaction". Review the generated Excel workbook to
validate the classifications and adjust via manual `--cost` entries or JSON as needed. If `pypdf` is
not installed the parser will raise a descriptive error so the dependency can be added.

## Development

Run the command below to execute the CLI in editable mode without installing the package:

```bash
python -m fastxe_calculator --cost "Internal:operational:Customer support:5000" --customer-price 25
```

The project intentionally keeps logic in pure Python so it can be extended or integrated with other
dashboarding tools in the future.
