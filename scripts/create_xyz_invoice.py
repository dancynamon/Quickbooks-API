#!/usr/bin/env python3
"""Create an invoice to XYZ Corp for $450.82.

Usage:
    python scripts/create_xyz_invoice.py

Requires a .env file with QBO credentials and completed OAuth setup.
"""

from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

# Ensure project root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

from quickbooks_api.auth import QuickBooksAuth
from quickbooks_api.client import QuickBooksClient

load_dotenv()

CUSTOMER_NAME = "XYZ Corp"
INVOICE_AMOUNT = 450.82
DUE_DATE = (date.today() + timedelta(days=30)).isoformat()


def main() -> None:
    auth = QuickBooksAuth.from_env()
    client = QuickBooksClient(auth)

    # Step 1: Find or create the customer
    matches = client.customers.find_by_name(CUSTOMER_NAME)
    if matches:
        customer = matches[0]
        print(f"Found existing customer: {customer['DisplayName']} (ID {customer['Id']})")
    else:
        customer = client.customers.create_customer(
            display_name=CUSTOMER_NAME,
            company_name=CUSTOMER_NAME,
        )
        print(f"Created customer: {customer['DisplayName']} (ID {customer['Id']})")

    # Step 2: Create the invoice
    invoice = client.invoices.create_invoice(
        customer_id=customer["Id"],
        line_items=[
            {
                "Amount": INVOICE_AMOUNT,
                "Description": "Services rendered",
                "DetailType": "SalesItemLineDetail",
                "SalesItemLineDetail": {
                    "ItemRef": {"value": "1"},
                    "Qty": 1,
                    "UnitPrice": INVOICE_AMOUNT,
                },
            }
        ],
        due_date=DUE_DATE,
    )

    print(f"Invoice #{invoice.get('DocNumber', invoice['Id'])} created for ${INVOICE_AMOUNT}")
    print(f"Due date: {DUE_DATE}")


if __name__ == "__main__":
    main()
