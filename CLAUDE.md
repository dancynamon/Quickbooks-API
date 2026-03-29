# QuickBooks API — Claude Workflows

## MCP Server Setup

This project provides a QuickBooks Online MCP server. Configure it in `~/.claude.json`:

```json
{
  "mcpServers": {
    "quickbooks": {
      "command": "qbo-mcp-server",
      "env": {
        "QBO_CLIENT_ID": "<your_client_id>",
        "QBO_CLIENT_SECRET": "<your_client_secret>",
        "QBO_ENVIRONMENT": "sandbox"
      }
    }
  }
}
```

## Browser Automation MCP Server Setup

This project also provides a headless browser automation MCP server for QBO tasks that require UI interaction (bank feed review, reconciliation, report exports, settings changes). Configure it in `~/.claude.json`:

```json
{
  "mcpServers": {
    "quickbooks-browser": {
      "command": "qbo-browser-mcp",
      "env": {
        "QBO_EMAIL": "<your_intuit_email>",
        "QBO_PASSWORD": "<your_intuit_password>",
        "QBO_ENVIRONMENT": "sandbox",
        "QBO_HEADLESS": "true",
        "QBO_TIMEOUT": "30000",
        "QBO_DOWNLOADS_DIR": "/tmp/qbo-downloads"
      }
    }
  }
}
```

After installing, run `playwright install chromium` to download the browser binary.

### Browser MCP Tools

**Lifecycle**: `browser_start`, `browser_stop`, `browser_status`
**Auth**: `qbo_login`
**Navigation**: `navigate`, `go_to_dashboard`, `go_to_invoices`, `go_to_expenses`, `go_to_customers`, `go_to_vendors`, `go_to_reports`, `go_to_chart_of_accounts`, `go_to_reconcile`, `go_to_bank_transactions`, `go_to_settings`, `go_to_payroll`, `go_to_taxes`
**Screenshots**: `take_screenshot`, `save_screenshot`
**DOM Interaction**: `click_element`, `fill_field`, `select_dropdown`, `type_text`, `press_key`
**Content Extraction**: `get_text`, `get_page_text`, `get_elements`, `get_element_attribute`, `extract_table`, `get_page_html`, `run_javascript`
**Downloads**: `download_file`
**Waiting**: `wait_for_element`, `wait_for_page_load`
**QBO Workflows**: `search_qbo`, `export_report`, `categorize_bank_transaction`, `get_bank_transactions_for_review`, `start_reconciliation`

## Order Processing Workflow

When asked to "process orders", "process POs", or "triage orders from email":

### Step 1 — Find new orders in Gmail
- Search Gmail for recent unread messages containing purchase orders, invoices, or order confirmations
- Read each message and extract: customer/company name, contact email, line items (description, quantity, unit price), and any PO number

### Step 2 — Match or create customer in QuickBooks
- Use `find_customers_by_name` or `find_customers_by_email` to check if the customer already exists
- If not found, use `create_customer` with the name, email, and company from the email
- Note the customer ID for invoice creation

### Step 3 — Verify items in QuickBooks
- For each line item, use `find_items_by_name` to check if the product/service exists
- If an item doesn't exist, use `create_item` to create it (default to type "Service" unless clearly a physical product)
- Note item IDs for invoice line items

### Step 4 — Create and send the invoice
- Use `create_invoice` with the customer ID, line items, and due date (default: net 30 from today)
- Include the PO number in the memo if one was provided
- Use `send_invoice` to email it to the customer

### Step 5 — Update CRM (if HubSpot is connected)
- Search HubSpot for a matching contact or deal
- Update the deal stage or add a note that the invoice was created

### Step 6 — Notify via Slack (if connected)
- Post a summary to the orders channel: customer name, invoice amount, invoice number

### Step 7 — Report back
- Summarize what was processed: how many orders, total invoice value, any issues encountered
- Flag anything that needs manual review (ambiguous items, missing info, duplicate customers)

## Manual Testing

To test the workflow manually, say:
- "Check my recent emails for any purchase orders and walk me through processing them"
- "Show me the last 5 order-related emails" (just the search step)
- "Create a test invoice for customer X" (just the QBO step)

## Error Handling
- If a customer name is ambiguous (multiple matches), ask before creating a duplicate
- If an email doesn't contain clear line items, flag it for manual review instead of guessing
- If QuickBooks returns a rate limit or auth error, report it and stop processing
