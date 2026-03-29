#!/usr/bin/env python3
"""Create an invoice for XYZ Company for $452.18.

Usage:
    python scripts/create_xyz_invoice.py

Requires QBO environment variables to be set (see CLAUDE.md).
"""

from __future__ import annotations

import json
import os
import sys
from datetime import date, timedelta

from dotenv import load_dotenv

load_dotenv()

from quickbooks_api.auth import QuickBooksAuth
from quickbooks_api.client import QuickBooksClient


def get_client() -> QuickBooksClient:
    auth = QuickBooksAuth(
        client_id=os.environ["QBO_CLIENT_ID"],
        client_secret=os.environ["QBO_CLIENT_SECRET"],
        redirect_uri=os.environ.get("QBO_REDIRECT_URI", "http://localhost:8080/callback"),
        environment=os.environ.get("QBO_ENVIRONMENT", "sandbox"),
    )

    access_token = os.environ.get("QBO_ACCESS_TOKEN", "")
    refresh_token = os.environ.get("QBO_REFRESH_TOKEN", "")
    realm_id = os.environ.get("QBO_REALM_ID", "")
    if access_token and refresh_token and realm_id:
        auth.set_tokens(access_token, refresh_token, realm_id)

    return QuickBooksClient(auth)


def main() -> None:
    client = get_client()

    # Step 1: Find or create XYZ Company
    customers = client.customers.find_by_name("XYZ Company")
    if customers:
        customer = customers[0]
        customer_id = customer["Id"]
        print(f"Found existing customer: {customer['DisplayName']} (ID: {customer_id})")
    else:
        print("Customer 'XYZ Company' not found — creating...")
        customer = client.customers.create_customer(
            display_name="XYZ Company",
            company_name="XYZ Company",
        )
        customer_id = customer["Id"]
        print(f"Created customer: XYZ Company (ID: {customer_id})")

    # Step 2: Create the invoice for $452.18 (net 30)
    due_date = (date.today() + timedelta(days=30)).isoformat()
    line_items = [
        {
            "Amount": 452.18,
            "Description": "Services rendered",
            "DetailType": "SalesItemLineDetail",
            "SalesItemLineDetail": {
                "ItemRef": {"value": "1", "name": "Services"},
                "Qty": 1,
                "UnitPrice": 452.18,
            },
        }
    ]

    invoice = client.invoices.create_invoice(
        customer_id=customer_id,
        line_items=line_items,
        due_date=due_date,
    )

    print(f"\nInvoice created successfully!")
    print(f"  Invoice ID : {invoice['Id']}")
    print(f"  Customer   : XYZ Company")
    print(f"  Amount     : $452.18")
    print(f"  Due Date   : {due_date}")
    print(f"\nFull response:\n{json.dumps(invoice, indent=2, default=str)}")


if __name__ == "__main__":
    main()
