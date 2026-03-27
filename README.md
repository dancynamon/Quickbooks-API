# QuickBooks Online API for Claude

A robust QuickBooks Online API client with an MCP server, built for use with Claude.

## Features

- **OAuth 2.0** with automatic token refresh and local auth flow
- **Full CRUD** for Customers, Invoices, Payments, Items, Bills, Vendors, Estimates
- **Reports**: P&L, Balance Sheet, Cash Flow, Trial Balance, Aged Receivables/Payables, and more
- **MCP Server** with 45+ tools so Claude can interact with your QuickBooks data directly
- **Error handling** with typed exceptions, retry logic, and rate limiting
- **Automatic pagination** for large result sets

## Quick Start

### 1. Install

```bash
pip install -e .
```

### 2. Configure

```bash
cp .env.example .env
# Edit .env with your QuickBooks OAuth credentials from
# https://developer.intuit.com/app/developer/dashboard
```

### 3. Authenticate

```bash
python -m quickbooks_api.setup_auth
```

This opens a browser-based OAuth flow and saves tokens to `tokens.json`.

### 4. Use with Claude (MCP Server)

Add to your Claude Code MCP config (`~/.claude/claude_desktop_config.json` or project settings):

```json
{
  "mcpServers": {
    "quickbooks": {
      "command": "qbo-mcp-server",
      "env": {
        "QBO_CLIENT_ID": "your_client_id",
        "QBO_CLIENT_SECRET": "your_client_secret",
        "QBO_ENVIRONMENT": "sandbox"
      }
    }
  }
}
```

Or with uvx (no install required):

```json
{
  "mcpServers": {
    "quickbooks": {
      "command": "uvx",
      "args": ["--from", "/path/to/Quickbooks-API", "qbo-mcp-server"],
      "env": {
        "QBO_CLIENT_ID": "your_client_id",
        "QBO_CLIENT_SECRET": "your_client_secret",
        "QBO_ENVIRONMENT": "sandbox"
      }
    }
  }
}
```

## MCP Tools Available

### Company
- `get_company_info` — Company name, address, fiscal year, etc.
- `get_company_preferences` — Company settings

### Customers
- `list_customers` / `get_customer` / `create_customer` / `update_customer`
- `find_customers_by_name` / `find_customers_by_email`

### Invoices
- `list_invoices` / `get_invoice` / `create_invoice`
- `send_invoice` / `void_invoice`
- `find_unpaid_invoices` / `find_overdue_invoices` / `find_invoices_by_customer`

### Payments
- `list_payments` / `get_payment` / `create_payment`
- `find_payments_by_customer`

### Items / Products
- `list_items` / `get_item` / `create_item` / `find_items_by_name`

### Accounts
- `list_accounts` / `get_account` / `get_chart_of_accounts` / `find_accounts_by_type`

### Bills
- `list_bills` / `get_bill` / `create_bill`
- `find_bills_by_vendor` / `find_unpaid_bills`

### Vendors
- `list_vendors` / `get_vendor` / `create_vendor` / `find_vendors_by_name`

### Estimates
- `list_estimates` / `get_estimate` / `create_estimate` / `send_estimate`

### Reports
- `report_profit_and_loss` / `report_balance_sheet` / `report_cash_flow`
- `report_trial_balance` / `report_general_ledger`
- `report_aged_receivables` / `report_aged_payables`
- `report_customer_income` / `report_vendor_expenses`

### Advanced
- `run_query` — Execute raw QBO queries (SQL-like syntax)

## Python API Usage

```python
from quickbooks_api import QuickBooksAuth, QuickBooksClient

auth = QuickBooksAuth(
    client_id="your_client_id",
    client_secret="your_client_secret",
    environment="sandbox",
)

# If tokens already saved:
client = QuickBooksClient(auth)

# List customers
customers = client.customers.query(where="Active = true", max_results=10)

# Create an invoice
invoice = client.invoices.create_invoice(
    customer_id="123",
    line_items=[{
        "Amount": 500.00,
        "Description": "Consulting services",
        "DetailType": "SalesItemLineDetail",
        "SalesItemLineDetail": {
            "ItemRef": {"value": "1"},
            "Qty": 5,
            "UnitPrice": 100,
        },
    }],
    due_date="2026-04-30",
)

# Get P&L report
pnl = client.reports.profit_and_loss(
    start_date="2026-01-01",
    end_date="2026-03-31",
)

# Run a raw query
results = client.query("SELECT * FROM Invoice WHERE Balance > '0' MAXRESULTS 5")
```

## Environment Variables

| Variable | Description |
|---|---|
| `QBO_CLIENT_ID` | OAuth 2.0 client ID from Intuit Developer |
| `QBO_CLIENT_SECRET` | OAuth 2.0 client secret |
| `QBO_REDIRECT_URI` | Redirect URI (default: `http://localhost:8080/callback`) |
| `QBO_ENVIRONMENT` | `sandbox` or `production` |
| `QBO_ACCESS_TOKEN` | Pre-set access token (optional) |
| `QBO_REFRESH_TOKEN` | Pre-set refresh token (optional) |
| `QBO_REALM_ID` | Company/realm ID (optional) |

## Architecture

```
quickbooks_api/
├── __init__.py            # Public API exports
├── auth.py                # OAuth 2.0 with token refresh
├── client.py              # Core HTTP client (retry, rate limit)
├── exceptions.py          # Typed error hierarchy
├── setup_auth.py          # Interactive auth setup
├── entities/
│   ├── base.py            # Base CRUD + query service
│   ├── customers.py
│   ├── invoices.py
│   ├── payments.py
│   ├── items.py
│   ├── accounts.py
│   ├── bills.py
│   ├── vendors.py
│   ├── estimates.py
│   ├── company.py
│   └── reports.py
└── mcp_server/
    └── server.py          # MCP server (45+ tools)
```
