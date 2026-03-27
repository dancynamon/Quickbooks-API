"""MCP server exposing QuickBooks Online API tools for Claude."""

import json
import os
import logging
from typing import Any

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from quickbooks_api.auth import QuickBooksAuth
from quickbooks_api.client import QuickBooksClient
from quickbooks_api.exceptions import QuickBooksError

load_dotenv()
logger = logging.getLogger(__name__)

mcp = FastMCP(
    "QuickBooks Online",
    instructions="QuickBooks Online API — manage customers, invoices, payments, bills, vendors, reports, and more.",
)

_client: QuickBooksClient | None = None


def _get_client() -> QuickBooksClient:
    """Lazy-initialize and return the QBO client."""
    global _client
    if _client is not None:
        return _client

    client_id = os.environ.get("QBO_CLIENT_ID", "")
    client_secret = os.environ.get("QBO_CLIENT_SECRET", "")
    redirect_uri = os.environ.get("QBO_REDIRECT_URI", "http://localhost:8080/callback")
    environment = os.environ.get("QBO_ENVIRONMENT", "sandbox")

    if not client_id or not client_secret:
        raise QuickBooksError(
            "QBO_CLIENT_ID and QBO_CLIENT_SECRET must be set in environment or .env file"
        )

    auth = QuickBooksAuth(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        environment=environment,
    )

    # If tokens are provided via env, set them directly
    access_token = os.environ.get("QBO_ACCESS_TOKEN", "")
    refresh_token = os.environ.get("QBO_REFRESH_TOKEN", "")
    realm_id = os.environ.get("QBO_REALM_ID", "")
    if access_token and refresh_token and realm_id:
        token_expiry = float(os.environ.get("QBO_TOKEN_EXPIRY", "0")) or None
        auth.set_tokens(access_token, refresh_token, realm_id, token_expiry)

    _client = QuickBooksClient(auth)
    return _client


def _safe_call(func, *args, **kwargs) -> str:
    """Call a function and return JSON result or error message."""
    try:
        result = func(*args, **kwargs)
        return json.dumps(result, indent=2, default=str)
    except QuickBooksError as e:
        return json.dumps({"error": str(e), "status_code": e.status_code, "detail": e.detail})
    except Exception as e:
        return json.dumps({"error": str(e)})


# ─── Company ─────────────────────────────────────────────────────────────────

@mcp.tool()
def get_company_info() -> str:
    """Get QuickBooks company information (name, address, fiscal year, etc.)."""
    return _safe_call(_get_client().company.get_info)


@mcp.tool()
def get_company_preferences() -> str:
    """Get QuickBooks company preferences and settings."""
    return _safe_call(_get_client().company.get_preferences)


# ─── Customers ───────────────────────────────────────────────────────────────

@mcp.tool()
def list_customers(where: str = "", max_results: int = 100) -> str:
    """List customers with optional filter.

    Args:
        where: Optional QBO query WHERE clause (e.g. "Active = true")
        max_results: Maximum number of results to return (default 100)
    """
    return _safe_call(_get_client().customers.query, where=where, max_results=max_results)


@mcp.tool()
def get_customer(customer_id: str) -> str:
    """Get a specific customer by ID.

    Args:
        customer_id: The QuickBooks customer ID
    """
    return _safe_call(_get_client().customers.get, customer_id)


@mcp.tool()
def create_customer(
    display_name: str,
    email: str = "",
    phone: str = "",
    company_name: str = "",
    notes: str = "",
) -> str:
    """Create a new customer.

    Args:
        display_name: Customer display name (required)
        email: Customer email address
        phone: Customer phone number
        company_name: Company name
        notes: Customer notes
    """
    return _safe_call(
        _get_client().customers.create_customer,
        display_name=display_name,
        email=email or None,
        phone=phone or None,
        company_name=company_name or None,
        notes=notes or None,
    )


@mcp.tool()
def update_customer(customer_data: str) -> str:
    """Update an existing customer. Must include Id and SyncToken.

    Args:
        customer_data: JSON string of customer fields to update. Must include "Id" and "SyncToken".
    """
    data = json.loads(customer_data)
    return _safe_call(_get_client().customers.update, data)


@mcp.tool()
def find_customers_by_name(name: str) -> str:
    """Search for customers by name (partial match).

    Args:
        name: Name to search for
    """
    return _safe_call(_get_client().customers.find_by_name, name)


@mcp.tool()
def find_customers_by_email(email: str) -> str:
    """Search for customers by email address.

    Args:
        email: Email address to search for
    """
    return _safe_call(_get_client().customers.find_by_email, email)


# ─── Invoices ────────────────────────────────────────────────────────────────

@mcp.tool()
def list_invoices(where: str = "", max_results: int = 100) -> str:
    """List invoices with optional filter.

    Args:
        where: Optional QBO query WHERE clause (e.g. "Balance > '0'")
        max_results: Maximum number of results
    """
    return _safe_call(_get_client().invoices.query, where=where, max_results=max_results)


@mcp.tool()
def get_invoice(invoice_id: str) -> str:
    """Get a specific invoice by ID.

    Args:
        invoice_id: The QuickBooks invoice ID
    """
    return _safe_call(_get_client().invoices.get, invoice_id)


@mcp.tool()
def create_invoice(
    customer_id: str,
    line_items: str,
    due_date: str = "",
    email: str = "",
    memo: str = "",
) -> str:
    """Create a new invoice.

    Args:
        customer_id: Customer ID to bill
        line_items: JSON array of line items. Each item needs: Amount, Description, DetailType ("SalesItemLineDetail"), and SalesItemLineDetail with ItemRef, Qty, UnitPrice.
            Example: [{"Amount": 100, "Description": "Consulting", "DetailType": "SalesItemLineDetail", "SalesItemLineDetail": {"ItemRef": {"value": "1"}, "Qty": 1, "UnitPrice": 100}}]
        due_date: Due date in YYYY-MM-DD format
        email: Email address to send invoice to
        memo: Customer memo
    """
    items = json.loads(line_items)
    return _safe_call(
        _get_client().invoices.create_invoice,
        customer_id=customer_id,
        line_items=items,
        due_date=due_date or None,
        email=email or None,
        memo=memo or None,
    )


@mcp.tool()
def send_invoice(invoice_id: str, email: str = "") -> str:
    """Send an invoice via email.

    Args:
        invoice_id: Invoice ID to send
        email: Override email address (optional, defaults to customer email)
    """
    return _safe_call(_get_client().invoices.send_invoice, invoice_id, email or None)


@mcp.tool()
def void_invoice(invoice_id: str, sync_token: str) -> str:
    """Void an invoice.

    Args:
        invoice_id: Invoice ID to void
        sync_token: Current SyncToken of the invoice
    """
    return _safe_call(_get_client().invoices.void_invoice, invoice_id, sync_token)


@mcp.tool()
def find_unpaid_invoices() -> str:
    """Find all unpaid invoices (balance > 0)."""
    return _safe_call(_get_client().invoices.find_unpaid)


@mcp.tool()
def find_overdue_invoices(as_of_date: str) -> str:
    """Find all overdue invoices as of a specific date.

    Args:
        as_of_date: Date in YYYY-MM-DD format
    """
    return _safe_call(_get_client().invoices.find_overdue, as_of_date)


@mcp.tool()
def find_invoices_by_customer(customer_id: str) -> str:
    """Find all invoices for a specific customer.

    Args:
        customer_id: Customer ID
    """
    return _safe_call(_get_client().invoices.find_by_customer, customer_id)


# ─── Payments ────────────────────────────────────────────────────────────────

@mcp.tool()
def list_payments(where: str = "", max_results: int = 100) -> str:
    """List payments with optional filter.

    Args:
        where: Optional QBO query WHERE clause
        max_results: Maximum number of results
    """
    return _safe_call(_get_client().payments.query, where=where, max_results=max_results)


@mcp.tool()
def get_payment(payment_id: str) -> str:
    """Get a specific payment by ID.

    Args:
        payment_id: The QuickBooks payment ID
    """
    return _safe_call(_get_client().payments.get, payment_id)


@mcp.tool()
def create_payment(
    customer_id: str,
    total_amount: float,
    invoice_ids: str = "",
    payment_method_ref: str = "",
) -> str:
    """Create a payment, optionally linked to invoices.

    Args:
        customer_id: Customer ID
        total_amount: Payment amount
        invoice_ids: Comma-separated invoice IDs to link (optional)
        payment_method_ref: Payment method reference ID (optional)
    """
    inv_ids = [x.strip() for x in invoice_ids.split(",") if x.strip()] if invoice_ids else None
    return _safe_call(
        _get_client().payments.create_payment,
        customer_id=customer_id,
        total_amount=total_amount,
        invoice_ids=inv_ids,
        payment_method_ref=payment_method_ref or None,
    )


@mcp.tool()
def find_payments_by_customer(customer_id: str) -> str:
    """Find all payments for a specific customer.

    Args:
        customer_id: Customer ID
    """
    return _safe_call(_get_client().payments.find_by_customer, customer_id)


# ─── Items / Products ───────────────────────────────────────────────────────

@mcp.tool()
def list_items(where: str = "", max_results: int = 100) -> str:
    """List items/products with optional filter.

    Args:
        where: Optional QBO query WHERE clause
        max_results: Maximum number of results
    """
    return _safe_call(_get_client().items.query, where=where, max_results=max_results)


@mcp.tool()
def get_item(item_id: str) -> str:
    """Get a specific item/product by ID.

    Args:
        item_id: The QuickBooks item ID
    """
    return _safe_call(_get_client().items.get, item_id)


@mcp.tool()
def create_item(
    name: str,
    item_type: str = "NonInventory",
    unit_price: float = 0,
    description: str = "",
    income_account_id: str = "",
    expense_account_id: str = "",
    taxable: bool = False,
) -> str:
    """Create a new item/product.

    Args:
        name: Item name
        item_type: Type - "Inventory", "NonInventory", or "Service"
        unit_price: Unit price
        description: Item description
        income_account_id: Income account ID
        expense_account_id: Expense account ID
        taxable: Whether the item is taxable
    """
    return _safe_call(
        _get_client().items.create_item,
        name=name,
        item_type=item_type,
        unit_price=unit_price or None,
        description=description or None,
        income_account_id=income_account_id or None,
        expense_account_id=expense_account_id or None,
        taxable=taxable,
    )


@mcp.tool()
def find_items_by_name(name: str) -> str:
    """Search for items by name (partial match).

    Args:
        name: Name to search for
    """
    return _safe_call(_get_client().items.find_by_name, name)


# ─── Accounts ────────────────────────────────────────────────────────────────

@mcp.tool()
def list_accounts(where: str = "", max_results: int = 100) -> str:
    """List accounts (chart of accounts) with optional filter.

    Args:
        where: Optional QBO query WHERE clause (e.g. "AccountType = 'Bank'")
        max_results: Maximum number of results
    """
    return _safe_call(_get_client().accounts.query, where=where, max_results=max_results)


@mcp.tool()
def get_account(account_id: str) -> str:
    """Get a specific account by ID.

    Args:
        account_id: The QuickBooks account ID
    """
    return _safe_call(_get_client().accounts.get, account_id)


@mcp.tool()
def get_chart_of_accounts() -> str:
    """Get the full chart of accounts."""
    return _safe_call(_get_client().accounts.get_chart_of_accounts)


@mcp.tool()
def find_accounts_by_type(account_type: str) -> str:
    """Find accounts by type.

    Args:
        account_type: Account type (e.g., "Bank", "Income", "Expense", "Accounts Receivable")
    """
    return _safe_call(_get_client().accounts.find_by_type, account_type)


# ─── Bills ───────────────────────────────────────────────────────────────────

@mcp.tool()
def list_bills(where: str = "", max_results: int = 100) -> str:
    """List bills with optional filter.

    Args:
        where: Optional QBO query WHERE clause
        max_results: Maximum number of results
    """
    return _safe_call(_get_client().bills.query, where=where, max_results=max_results)


@mcp.tool()
def get_bill(bill_id: str) -> str:
    """Get a specific bill by ID.

    Args:
        bill_id: The QuickBooks bill ID
    """
    return _safe_call(_get_client().bills.get, bill_id)


@mcp.tool()
def create_bill(
    vendor_id: str,
    line_items: str,
    due_date: str = "",
    memo: str = "",
) -> str:
    """Create a new bill.

    Args:
        vendor_id: Vendor ID
        line_items: JSON array of line items. Example: [{"Amount": 100, "DetailType": "AccountBasedExpenseLineDetail", "AccountBasedExpenseLineDetail": {"AccountRef": {"value": "7"}}}]
        due_date: Due date in YYYY-MM-DD format
        memo: Private note/memo
    """
    items = json.loads(line_items)
    return _safe_call(
        _get_client().bills.create_bill,
        vendor_id=vendor_id,
        line_items=items,
        due_date=due_date or None,
        memo=memo or None,
    )


@mcp.tool()
def find_bills_by_vendor(vendor_id: str) -> str:
    """Find all bills for a specific vendor.

    Args:
        vendor_id: Vendor ID
    """
    return _safe_call(_get_client().bills.find_by_vendor, vendor_id)


@mcp.tool()
def find_unpaid_bills() -> str:
    """Find all unpaid bills (balance > 0)."""
    return _safe_call(_get_client().bills.find_unpaid)


# ─── Vendors ─────────────────────────────────────────────────────────────────

@mcp.tool()
def list_vendors(where: str = "", max_results: int = 100) -> str:
    """List vendors with optional filter.

    Args:
        where: Optional QBO query WHERE clause
        max_results: Maximum number of results
    """
    return _safe_call(_get_client().vendors.query, where=where, max_results=max_results)


@mcp.tool()
def get_vendor(vendor_id: str) -> str:
    """Get a specific vendor by ID.

    Args:
        vendor_id: The QuickBooks vendor ID
    """
    return _safe_call(_get_client().vendors.get, vendor_id)


@mcp.tool()
def create_vendor(
    display_name: str,
    email: str = "",
    phone: str = "",
    company_name: str = "",
) -> str:
    """Create a new vendor.

    Args:
        display_name: Vendor display name (required)
        email: Vendor email address
        phone: Vendor phone number
        company_name: Company name
    """
    return _safe_call(
        _get_client().vendors.create_vendor,
        display_name=display_name,
        email=email or None,
        phone=phone or None,
        company_name=company_name or None,
    )


@mcp.tool()
def find_vendors_by_name(name: str) -> str:
    """Search for vendors by name (partial match).

    Args:
        name: Name to search for
    """
    return _safe_call(_get_client().vendors.find_by_name, name)


# ─── Estimates ───────────────────────────────────────────────────────────────

@mcp.tool()
def list_estimates(where: str = "", max_results: int = 100) -> str:
    """List estimates/quotes with optional filter.

    Args:
        where: Optional QBO query WHERE clause
        max_results: Maximum number of results
    """
    return _safe_call(_get_client().estimates.query, where=where, max_results=max_results)


@mcp.tool()
def get_estimate(estimate_id: str) -> str:
    """Get a specific estimate by ID.

    Args:
        estimate_id: The QuickBooks estimate ID
    """
    return _safe_call(_get_client().estimates.get, estimate_id)


@mcp.tool()
def create_estimate(
    customer_id: str,
    line_items: str,
    expiration_date: str = "",
    memo: str = "",
) -> str:
    """Create a new estimate/quote.

    Args:
        customer_id: Customer ID
        line_items: JSON array of line items (same format as invoices)
        expiration_date: Expiration date in YYYY-MM-DD format
        memo: Customer memo
    """
    items = json.loads(line_items)
    return _safe_call(
        _get_client().estimates.create_estimate,
        customer_id=customer_id,
        line_items=items,
        expiration_date=expiration_date or None,
        memo=memo or None,
    )


@mcp.tool()
def send_estimate(estimate_id: str, email: str = "") -> str:
    """Send an estimate via email.

    Args:
        estimate_id: Estimate ID to send
        email: Override email address (optional)
    """
    return _safe_call(_get_client().estimates.send_estimate, estimate_id, email or None)


# ─── Reports ─────────────────────────────────────────────────────────────────

@mcp.tool()
def report_profit_and_loss(
    start_date: str = "",
    end_date: str = "",
    accounting_method: str = "Accrual",
    summarize_by: str = "",
) -> str:
    """Get Profit and Loss (Income Statement) report.

    Args:
        start_date: Start date YYYY-MM-DD (defaults to start of fiscal year)
        end_date: End date YYYY-MM-DD (defaults to today)
        accounting_method: "Accrual" or "Cash"
        summarize_by: Summarize columns by "Month", "Quarter", "Year", etc.
    """
    return _safe_call(
        _get_client().reports.profit_and_loss,
        start_date=start_date or None,
        end_date=end_date or None,
        accounting_method=accounting_method,
        summarize_by=summarize_by or None,
    )


@mcp.tool()
def report_balance_sheet(
    start_date: str = "",
    end_date: str = "",
    accounting_method: str = "Accrual",
    summarize_by: str = "",
) -> str:
    """Get Balance Sheet report.

    Args:
        start_date: Start date YYYY-MM-DD
        end_date: End date YYYY-MM-DD
        accounting_method: "Accrual" or "Cash"
        summarize_by: Summarize columns by "Month", "Quarter", "Year", etc.
    """
    return _safe_call(
        _get_client().reports.balance_sheet,
        start_date=start_date or None,
        end_date=end_date or None,
        accounting_method=accounting_method,
        summarize_by=summarize_by or None,
    )


@mcp.tool()
def report_cash_flow(
    start_date: str = "",
    end_date: str = "",
    summarize_by: str = "",
) -> str:
    """Get Statement of Cash Flows report.

    Args:
        start_date: Start date YYYY-MM-DD
        end_date: End date YYYY-MM-DD
        summarize_by: Summarize columns by "Month", "Quarter", "Year", etc.
    """
    return _safe_call(
        _get_client().reports.cash_flow,
        start_date=start_date or None,
        end_date=end_date or None,
        summarize_by=summarize_by or None,
    )


@mcp.tool()
def report_trial_balance(
    start_date: str = "",
    end_date: str = "",
    accounting_method: str = "Accrual",
) -> str:
    """Get Trial Balance report.

    Args:
        start_date: Start date YYYY-MM-DD
        end_date: End date YYYY-MM-DD
        accounting_method: "Accrual" or "Cash"
    """
    return _safe_call(
        _get_client().reports.trial_balance,
        start_date=start_date or None,
        end_date=end_date or None,
        accounting_method=accounting_method,
    )


@mcp.tool()
def report_aged_receivables(report_date: str = "", aging_period: int = 30) -> str:
    """Get Accounts Receivable Aging Summary.

    Args:
        report_date: As-of date YYYY-MM-DD
        aging_period: Aging period in days (default 30)
    """
    return _safe_call(
        _get_client().reports.aged_receivables,
        report_date=report_date or None,
        aging_period=aging_period,
    )


@mcp.tool()
def report_aged_payables(report_date: str = "", aging_period: int = 30) -> str:
    """Get Accounts Payable Aging Summary.

    Args:
        report_date: As-of date YYYY-MM-DD
        aging_period: Aging period in days (default 30)
    """
    return _safe_call(
        _get_client().reports.aged_payables,
        report_date=report_date or None,
        aging_period=aging_period,
    )


@mcp.tool()
def report_customer_income(start_date: str = "", end_date: str = "") -> str:
    """Get Income by Customer Summary report.

    Args:
        start_date: Start date YYYY-MM-DD
        end_date: End date YYYY-MM-DD
    """
    return _safe_call(
        _get_client().reports.customer_income,
        start_date=start_date or None,
        end_date=end_date or None,
    )


@mcp.tool()
def report_vendor_expenses(start_date: str = "", end_date: str = "") -> str:
    """Get Expenses by Vendor Summary report.

    Args:
        start_date: Start date YYYY-MM-DD
        end_date: End date YYYY-MM-DD
    """
    return _safe_call(
        _get_client().reports.vendor_expenses,
        start_date=start_date or None,
        end_date=end_date or None,
    )


@mcp.tool()
def report_general_ledger(
    start_date: str = "",
    end_date: str = "",
    columns: str = "",
) -> str:
    """Get General Ledger report.

    Args:
        start_date: Start date YYYY-MM-DD
        end_date: End date YYYY-MM-DD
        columns: Comma-separated column names to include
    """
    return _safe_call(
        _get_client().reports.general_ledger,
        start_date=start_date or None,
        end_date=end_date or None,
        columns=columns or None,
    )


# ─── Generic Query ───────────────────────────────────────────────────────────

@mcp.tool()
def run_query(query: str) -> str:
    """Run a raw QBO query (SQL-like syntax).

    Args:
        query: QBO query string, e.g. "SELECT * FROM Customer WHERE Active = true MAXRESULTS 10"
    """
    return _safe_call(_get_client().query, query)


def main():
    mcp.run()


if __name__ == "__main__":
    main()
