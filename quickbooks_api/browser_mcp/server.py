"""MCP server exposing headless browser automation tools for QuickBooks Online."""

from __future__ import annotations

import asyncio
import json
import logging
import os
from dataclasses import asdict
from typing import Any

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from quickbooks_api.browser_mcp.browser import BrowserConfig, QBOBrowser

load_dotenv()
logger = logging.getLogger(__name__)

mcp = FastMCP(
    "QuickBooks Browser Automation",
    instructions=(
        "Headless browser automation for QuickBooks Online. "
        "Use these tools for UI-only workflows: reconciliation, bank feeds, "
        "settings, report exports, and anything not available via the REST API."
    ),
)

_browser: QBOBrowser | None = None


async def _get_browser() -> QBOBrowser:
    """Lazy-initialize and return the QBO browser instance."""
    global _browser
    if _browser is not None:
        return _browser
    config = BrowserConfig.from_env()
    _browser = QBOBrowser(config)
    await _browser.start()
    return _browser


def _json(obj: Any) -> str:
    """Serialize to JSON, handling dataclasses."""
    if hasattr(obj, "__dataclass_fields__"):
        obj = asdict(obj)
    return json.dumps(obj, indent=2, default=str)


async def _safe_call(coro) -> str:
    """Run an async operation and return JSON, catching errors."""
    try:
        result = await coro
        if isinstance(result, str):
            return result
        return _json(result)
    except Exception as e:
        logger.exception("Browser tool error")
        return json.dumps({"error": type(e).__name__, "detail": str(e)})


# ── Lifecycle ───────────────────────────────────────────────────────


@mcp.tool()
async def browser_start() -> str:
    """Start the headless browser. Called automatically by other tools, but can be invoked explicitly."""
    browser = await _get_browser()
    return json.dumps({"success": True, "message": "Browser started"})


@mcp.tool()
async def browser_stop() -> str:
    """Stop the headless browser and release resources."""
    global _browser
    if _browser:
        await _browser.stop()
        _browser = None
    return json.dumps({"success": True, "message": "Browser stopped"})


@mcp.tool()
async def browser_status() -> str:
    """Check if the browser is running and whether we're logged into QBO."""
    global _browser
    if not _browser or not _browser._started:
        return json.dumps({"running": False, "logged_in": False})
    logged_in = await _browser.is_logged_in()
    page = await _browser.get_current_page()
    return json.dumps({
        "running": True,
        "logged_in": logged_in,
        "url": page.url,
        "title": page.title,
    })


# ── Authentication ──────────────────────────────────────────────────


@mcp.tool()
async def qbo_login(email: str = "", password: str = "") -> str:
    """Log in to QuickBooks Online.

    Uses QBO_EMAIL / QBO_PASSWORD env vars if not provided.
    May require MFA — check the response for instructions.
    """
    browser = await _get_browser()
    return await _safe_call(browser.login(email, password))


# ── Navigation ──────────────────────────────────────────────────────


@mcp.tool()
async def navigate(path: str) -> str:
    """Navigate to a QBO page by path.

    Examples: '/app/invoices', '/app/customers', '/app/reports',
    '/app/banking', '/app/reconcile', '/app/settings'
    """
    browser = await _get_browser()
    return await _safe_call(browser.navigate(path))


@mcp.tool()
async def get_current_page() -> str:
    """Get the URL and title of the current page."""
    browser = await _get_browser()
    return await _safe_call(browser.get_current_page())


@mcp.tool()
async def go_to_dashboard() -> str:
    """Navigate to the QBO dashboard/homepage."""
    browser = await _get_browser()
    return await _safe_call(browser.go_to_dashboard())


@mcp.tool()
async def go_to_invoices() -> str:
    """Navigate to the Invoices list page."""
    browser = await _get_browser()
    return await _safe_call(browser.go_to_invoices())


@mcp.tool()
async def go_to_expenses() -> str:
    """Navigate to the Expenses page."""
    browser = await _get_browser()
    return await _safe_call(browser.go_to_expenses())


@mcp.tool()
async def go_to_customers() -> str:
    """Navigate to the Customers list page."""
    browser = await _get_browser()
    return await _safe_call(browser.go_to_customers())


@mcp.tool()
async def go_to_vendors() -> str:
    """Navigate to the Vendors list page."""
    browser = await _get_browser()
    return await _safe_call(browser.go_to_vendors())


@mcp.tool()
async def go_to_reports() -> str:
    """Navigate to the Reports center."""
    browser = await _get_browser()
    return await _safe_call(browser.go_to_reports())


@mcp.tool()
async def go_to_chart_of_accounts() -> str:
    """Navigate to the Chart of Accounts page."""
    browser = await _get_browser()
    return await _safe_call(browser.go_to_chart_of_accounts())


@mcp.tool()
async def go_to_reconcile() -> str:
    """Navigate to the bank reconciliation page."""
    browser = await _get_browser()
    return await _safe_call(browser.go_to_reconcile())


@mcp.tool()
async def go_to_bank_transactions() -> str:
    """Navigate to the Banking / Bank Transactions page for bank feed review."""
    browser = await _get_browser()
    return await _safe_call(browser.go_to_bank_transactions())


@mcp.tool()
async def go_to_settings() -> str:
    """Navigate to the QBO Company Settings page."""
    browser = await _get_browser()
    return await _safe_call(browser.go_to_settings())


@mcp.tool()
async def go_to_payroll() -> str:
    """Navigate to the Payroll section."""
    browser = await _get_browser()
    return await _safe_call(browser.go_to_payroll())


@mcp.tool()
async def go_to_taxes() -> str:
    """Navigate to the Sales Tax center."""
    browser = await _get_browser()
    return await _safe_call(browser.go_to_taxes())


# ── Screenshots ─────────────────────────────────────────────────────


@mcp.tool()
async def take_screenshot(full_page: bool = False, selector: str = "") -> str:
    """Take a screenshot of the current page or a specific element.

    Returns a base64-encoded PNG. Use selector to capture a specific element.
    Set full_page=True to capture the entire scrollable page.
    """
    browser = await _get_browser()
    return await _safe_call(browser.screenshot(full_page=full_page, selector=selector))


@mcp.tool()
async def save_screenshot(path: str, full_page: bool = False) -> str:
    """Take a screenshot and save it to a file path.

    Returns the file path on success.
    """
    browser = await _get_browser()
    return await _safe_call(browser.screenshot_to_file(path, full_page=full_page))


# ── DOM Interaction ─────────────────────────────────────────────────


@mcp.tool()
async def click_element(selector: str) -> str:
    """Click an element on the page.

    Use CSS selectors (e.g. 'button.save', '#submit-btn', '[data-testid="save"]').
    Waits for navigation to settle after clicking.
    """
    browser = await _get_browser()
    return await _safe_call(browser.click(selector))


@mcp.tool()
async def fill_field(selector: str, value: str) -> str:
    """Fill an input field with a value.

    Clears existing content first. Use CSS selectors to identify the field.
    """
    browser = await _get_browser()
    return await _safe_call(browser.fill(selector, value))


@mcp.tool()
async def select_dropdown(selector: str, value: str = "", label: str = "") -> str:
    """Select an option in a <select> dropdown by value or visible label."""
    browser = await _get_browser()
    return await _safe_call(browser.select_option(selector, value=value, label=label))


@mcp.tool()
async def type_text(selector: str, text: str, delay: int = 50) -> str:
    """Type text character by character into a field.

    Useful for autocomplete/search fields that respond to keystroke events.
    delay is milliseconds between keystrokes.
    """
    browser = await _get_browser()
    return await _safe_call(browser.type_text(selector, text, delay=delay))


@mcp.tool()
async def press_key(key: str, selector: str = "") -> str:
    """Press a keyboard key. Examples: 'Enter', 'Tab', 'Escape', 'ArrowDown'.

    Optionally target a specific element with selector.
    """
    browser = await _get_browser()
    return await _safe_call(browser.press_key(key, selector=selector))


# ── Content Extraction ──────────────────────────────────────────────


@mcp.tool()
async def get_text(selector: str) -> str:
    """Get the text content of an element matching the CSS selector."""
    browser = await _get_browser()
    return await _safe_call(browser.get_text(selector))


@mcp.tool()
async def get_page_text() -> str:
    """Get all visible text on the current page.

    Useful for understanding page state without a screenshot.
    """
    browser = await _get_browser()
    return await _safe_call(browser.get_page_text())


@mcp.tool()
async def get_elements(selector: str, limit: int = 50) -> str:
    """Get information about elements matching a CSS selector.

    Returns tag name, text content, visibility, and bounding box for each match.
    """
    browser = await _get_browser()
    result = await browser.get_elements(selector, limit=limit)
    return json.dumps([asdict(el) for el in result], indent=2, default=str)


@mcp.tool()
async def get_element_attribute(selector: str, attribute: str) -> str:
    """Get the value of an HTML attribute on an element.

    Examples: get_element_attribute('a.download', 'href')
    """
    browser = await _get_browser()
    return await _safe_call(browser.get_attribute(selector, attribute))


@mcp.tool()
async def extract_table(selector: str = "table") -> str:
    """Extract data from an HTML table as a JSON array of rows.

    Each row is an array of cell text values. Includes header rows.
    """
    browser = await _get_browser()
    return await _safe_call(browser.extract_table(selector))


@mcp.tool()
async def get_page_html(selector: str = "body") -> str:
    """Get the inner HTML of an element. Defaults to the full page body.

    Use sparingly — prefer get_text or get_elements for structured extraction.
    """
    browser = await _get_browser()
    return await _safe_call(browser.get_page_html(selector))


@mcp.tool()
async def run_javascript(expression: str) -> str:
    """Evaluate a JavaScript expression in the page context and return the result.

    Useful for extracting data from complex UI components or triggering actions.
    """
    browser = await _get_browser()
    return await _safe_call(browser.evaluate_js(expression))


# ── Downloads ───────────────────────────────────────────────────────


@mcp.tool()
async def download_file(selector: str) -> str:
    """Click a download link/button and save the resulting file.

    Returns the filename and local path of the downloaded file.
    """
    browser = await _get_browser()
    return await _safe_call(browser.download_file(selector))


# ── Waiting ─────────────────────────────────────────────────────────


@mcp.tool()
async def wait_for_element(selector: str, state: str = "visible", timeout: int = 0) -> str:
    """Wait for an element to reach a state: 'visible', 'hidden', 'attached', 'detached'.

    Default timeout uses the configured QBO_TIMEOUT (30s).
    """
    browser = await _get_browser()
    return await _safe_call(browser.wait_for_selector(selector, state=state, timeout=timeout))


@mcp.tool()
async def wait_for_page_load(state: str = "networkidle") -> str:
    """Wait for the page to finish loading.

    States: 'load', 'domcontentloaded', 'networkidle'.
    """
    browser = await _get_browser()
    await browser.wait_for_load(state)
    return json.dumps({"success": True, "state": state})


# ── QBO Workflow Helpers ────────────────────────────────────────────


@mcp.tool()
async def search_qbo(query: str) -> str:
    """Use the QBO global search bar to search for transactions, customers, etc.

    Types the query into the search bar and returns the page text after results load.
    """
    browser = await _get_browser()
    page = browser.page
    try:
        # Click the search icon/bar
        search_trigger = page.locator(
            '[data-testid="global-search"], '
            '[aria-label="Search"], '
            'button.search-icon, '
            '#globalSearch, '
            '#SearchTransaction'
        ).first
        await search_trigger.click()
        await page.wait_for_timeout(500)

        # Type the search query
        search_input = page.locator(
            'input[data-testid="global-search-input"], '
            'input[aria-label="Search Transactions"], '
            'input.search-input, '
            '#SearchTransaction input'
        ).first
        await search_input.fill(query)
        await page.keyboard.press("Enter")

        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(2000)

        text = await page.inner_text("body")
        return json.dumps({
            "success": True,
            "query": query,
            "url": page.url,
            "page_text": text[:5000],
        })
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


@mcp.tool()
async def export_report(
    report_path: str,
    export_format: str = "pdf",
) -> str:
    """Navigate to a report page and export it as PDF or Excel.

    report_path: QBO path like '/app/reports/ProfitAndLoss'
    export_format: 'pdf' or 'excel'

    Returns the path to the downloaded file.
    """
    browser = await _get_browser()
    page = browser.page
    try:
        await browser.navigate(report_path)
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(3000)

        # Click the export/print dropdown
        export_btn = page.locator(
            'button:has-text("Export"), '
            '[data-testid="export-button"], '
            'button[aria-label="Export"]'
        ).first
        await export_btn.click()
        await page.wait_for_timeout(1000)

        if export_format.lower() == "pdf":
            option = page.locator(
                'button:has-text("Export to PDF"), '
                'li:has-text("Export to PDF"), '
                '[data-testid="export-pdf"]'
            ).first
        else:
            option = page.locator(
                'button:has-text("Export to Excel"), '
                'li:has-text("Export to Excel"), '
                '[data-testid="export-excel"]'
            ).first

        async with page.expect_download(timeout=browser.config.timeout) as dl_info:
            await option.click()
        download = await dl_info.value
        dest = os.path.join(browser.config.downloads_dir, download.suggested_filename)
        await download.save_as(dest)
        return json.dumps({
            "success": True,
            "filename": download.suggested_filename,
            "path": dest,
            "format": export_format,
        })
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


@mcp.tool()
async def categorize_bank_transaction(
    transaction_text: str,
    category: str,
) -> str:
    """Categorize an uncategorized bank feed transaction in QBO.

    Navigates to Banking, finds the transaction by text match, and assigns a category.
    """
    browser = await _get_browser()
    page = browser.page
    try:
        await browser.go_to_bank_transactions()
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(3000)

        # Find the transaction row
        row = page.locator(f'tr:has-text("{transaction_text}")').first
        await row.click()
        await page.wait_for_timeout(1000)

        # Look for category field and fill it
        cat_input = page.locator(
            'input[aria-label="Category"], '
            '[data-testid="category-input"], '
            'input.category-field'
        ).first
        await cat_input.fill(category)
        await page.wait_for_timeout(1000)

        # Select the first suggestion
        suggestion = page.locator(
            '.dropdown-item:first-child, '
            'li.suggestion:first-child, '
            '[role="option"]:first-child'
        ).first
        await suggestion.click()

        # Save/confirm
        confirm_btn = page.locator(
            'button:has-text("Confirm"), '
            'button:has-text("Add"), '
            'button:has-text("Save")'
        ).first
        await confirm_btn.click()
        await page.wait_for_load_state("networkidle")

        return json.dumps({
            "success": True,
            "transaction": transaction_text,
            "category": category,
        })
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


@mcp.tool()
async def get_bank_transactions_for_review() -> str:
    """Get the list of uncategorized bank feed transactions awaiting review.

    Navigates to the Banking page and extracts the 'For Review' transactions.
    """
    browser = await _get_browser()
    page = browser.page
    try:
        await browser.go_to_bank_transactions()
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(3000)

        # Click the "For Review" tab if it exists
        review_tab = page.locator(
            'button:has-text("For Review"), '
            '[data-testid="for-review-tab"], '
            'a:has-text("For Review")'
        ).first
        try:
            await review_tab.click(timeout=5000)
            await page.wait_for_timeout(2000)
        except Exception:
            pass  # Tab might already be selected

        text = await page.inner_text("body")
        return json.dumps({
            "success": True,
            "url": page.url,
            "page_text": text[:8000],
        })
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


@mcp.tool()
async def start_reconciliation(account_name: str) -> str:
    """Navigate to the reconciliation page for a specific account.

    Starts the reconciliation workflow by navigating and selecting the account.
    """
    browser = await _get_browser()
    page = browser.page
    try:
        await browser.go_to_reconcile()
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(2000)

        # Select account from dropdown
        account_select = page.locator(
            'select[data-testid="account-select"], '
            'select#account, '
            '[aria-label="Account"] select'
        ).first
        await account_select.select_option(label=account_name)
        await page.wait_for_timeout(1000)

        text = await page.inner_text("body")
        return json.dumps({
            "success": True,
            "account": account_name,
            "url": page.url,
            "page_text": text[:5000],
        })
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


def main():
    """Entry point for the QBO Browser Automation MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
