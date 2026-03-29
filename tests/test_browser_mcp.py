"""Tests for the browser automation MCP server tool functions."""

import json
from dataclasses import asdict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from quickbooks_api.browser_mcp.browser import BrowserConfig, PageInfo, QBOBrowser


@pytest.fixture
def browser_config():
    return BrowserConfig(
        email="test@example.com",
        password="secret",
        headless=True,
        environment="sandbox",
    )


@pytest.fixture
def mock_browser(browser_config):
    """Create a QBOBrowser with mocked internals (no real Playwright)."""
    browser = QBOBrowser(browser_config)
    browser._started = True
    browser._page = MagicMock()
    browser._context = MagicMock()
    browser._browser = MagicMock()
    browser._playwright = MagicMock()
    return browser


@pytest.fixture(autouse=True)
def patch_get_browser(mock_browser):
    """Patch _get_browser so all server tools use the mock."""
    async def fake_get_browser():
        return mock_browser

    with patch("quickbooks_api.browser_mcp.server._get_browser", side_effect=fake_get_browser):
        yield mock_browser


class TestBrowserConfig:

    def test_defaults(self):
        cfg = BrowserConfig()
        assert cfg.headless is True
        assert cfg.environment == "sandbox"
        assert cfg.timeout == 30_000

    def test_app_url_sandbox(self):
        cfg = BrowserConfig(environment="sandbox")
        assert "sandbox" in cfg.app_url

    def test_app_url_production(self):
        cfg = BrowserConfig(environment="production")
        assert cfg.app_url == "https://app.qbo.intuit.com"

    def test_from_env(self):
        with patch.dict("os.environ", {
            "QBO_EMAIL": "a@b.com",
            "QBO_PASSWORD": "pw",
            "QBO_HEADLESS": "false",
            "QBO_ENVIRONMENT": "production",
        }):
            cfg = BrowserConfig.from_env()
        assert cfg.email == "a@b.com"
        assert cfg.headless is False
        assert cfg.environment == "production"


class TestBrowserLifecycle:

    @pytest.mark.asyncio
    async def test_browser_start(self, mock_browser):
        from quickbooks_api.browser_mcp.server import browser_start
        result = json.loads(await browser_start())
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_browser_stop(self):
        from quickbooks_api.browser_mcp.server import browser_stop
        result = json.loads(await browser_stop())
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_browser_status(self, mock_browser):
        import quickbooks_api.browser_mcp.server as server_mod
        from quickbooks_api.browser_mcp.server import browser_status

        mock_browser.is_logged_in = AsyncMock(return_value=True)
        mock_browser.get_current_page = AsyncMock(return_value=PageInfo(
            url="https://app.sandbox.qbo.intuit.com/app/homepage",
            title="Dashboard",
        ))

        # browser_status checks the global _browser directly
        old = server_mod._browser
        server_mod._browser = mock_browser
        try:
            result = json.loads(await browser_status())
            assert result["running"] is True
            assert result["logged_in"] is True
            assert "homepage" in result["url"]
        finally:
            server_mod._browser = old


class TestNavigation:

    @pytest.mark.asyncio
    async def test_navigate(self, mock_browser):
        from quickbooks_api.browser_mcp.server import navigate

        mock_browser.navigate = AsyncMock(return_value=PageInfo(
            url="https://app.sandbox.qbo.intuit.com/app/invoices",
            title="Invoices",
        ))

        result = json.loads(await navigate("/app/invoices"))
        assert result["title"] == "Invoices"
        mock_browser.navigate.assert_awaited_once_with("/app/invoices")

    @pytest.mark.asyncio
    async def test_go_to_dashboard(self, mock_browser):
        from quickbooks_api.browser_mcp.server import go_to_dashboard

        mock_browser.go_to_dashboard = AsyncMock(return_value=PageInfo(
            url="https://app.sandbox.qbo.intuit.com/app/homepage",
            title="Dashboard",
        ))

        result = json.loads(await go_to_dashboard())
        assert result["title"] == "Dashboard"

    @pytest.mark.asyncio
    async def test_go_to_reconcile(self, mock_browser):
        from quickbooks_api.browser_mcp.server import go_to_reconcile

        mock_browser.go_to_reconcile = AsyncMock(return_value=PageInfo(
            url="https://app.sandbox.qbo.intuit.com/app/reconcile",
            title="Reconcile",
        ))

        result = json.loads(await go_to_reconcile())
        assert "reconcile" in result["url"]

    @pytest.mark.asyncio
    async def test_get_current_page(self, mock_browser):
        from quickbooks_api.browser_mcp.server import get_current_page

        mock_browser.get_current_page = AsyncMock(return_value=PageInfo(
            url="https://app.sandbox.qbo.intuit.com/app/reports",
            title="Reports",
        ))

        result = json.loads(await get_current_page())
        assert result["title"] == "Reports"


class TestScreenshots:

    @pytest.mark.asyncio
    async def test_take_screenshot(self, mock_browser):
        from quickbooks_api.browser_mcp.server import take_screenshot

        mock_browser.screenshot = AsyncMock(return_value="iVBORw0KGgo=")
        result = await take_screenshot()
        assert "iVBORw0KGgo=" in result

    @pytest.mark.asyncio
    async def test_save_screenshot(self, mock_browser):
        from quickbooks_api.browser_mcp.server import save_screenshot

        mock_browser.screenshot_to_file = AsyncMock(return_value="/tmp/shot.png")
        result = await save_screenshot("/tmp/shot.png")
        assert "/tmp/shot.png" in result


class TestDOMInteraction:

    @pytest.mark.asyncio
    async def test_click_element(self, mock_browser):
        from quickbooks_api.browser_mcp.server import click_element

        mock_browser.click = AsyncMock(return_value={"success": True, "url": "https://example.com"})
        result = json.loads(await click_element("button.save"))
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_fill_field(self, mock_browser):
        from quickbooks_api.browser_mcp.server import fill_field

        mock_browser.fill = AsyncMock(return_value={"success": True})
        result = json.loads(await fill_field("#name", "Test Customer"))
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_type_text(self, mock_browser):
        from quickbooks_api.browser_mcp.server import type_text

        mock_browser.type_text = AsyncMock(return_value={"success": True})
        result = json.loads(await type_text("#search", "invoice"))
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_press_key(self, mock_browser):
        from quickbooks_api.browser_mcp.server import press_key

        mock_browser.press_key = AsyncMock(return_value={"success": True})
        result = json.loads(await press_key("Enter"))
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_select_dropdown(self, mock_browser):
        from quickbooks_api.browser_mcp.server import select_dropdown

        mock_browser.select_option = AsyncMock(return_value={"success": True})
        result = json.loads(await select_dropdown("#account", label="Checking"))
        assert result["success"] is True


class TestContentExtraction:

    @pytest.mark.asyncio
    async def test_get_text(self, mock_browser):
        from quickbooks_api.browser_mcp.server import get_text

        mock_browser.get_text = AsyncMock(return_value="Invoice #1001")
        result = await get_text(".invoice-number")
        assert "1001" in result

    @pytest.mark.asyncio
    async def test_get_page_text(self, mock_browser):
        from quickbooks_api.browser_mcp.server import get_page_text

        mock_browser.get_page_text = AsyncMock(return_value="Dashboard\nRevenue: $5,000")
        result = await get_page_text()
        assert "Revenue" in result

    @pytest.mark.asyncio
    async def test_extract_table(self, mock_browser):
        from quickbooks_api.browser_mcp.server import extract_table

        mock_browser.extract_table = AsyncMock(return_value=[
            ["Date", "Description", "Amount"],
            ["03/29", "Payment", "$100"],
        ])
        result = json.loads(await extract_table("table.transactions"))
        assert len(result) == 2
        assert result[0][0] == "Date"

    @pytest.mark.asyncio
    async def test_get_elements(self, mock_browser):
        from quickbooks_api.browser_mcp.server import get_elements
        from quickbooks_api.browser_mcp.browser import ElementInfo

        mock_browser.get_elements = AsyncMock(return_value=[
            ElementInfo(tag="button", text="Save", visible=True),
            ElementInfo(tag="button", text="Cancel", visible=True),
        ])
        result = json.loads(await get_elements("button"))
        assert len(result) == 2
        assert result[0]["tag"] == "button"

    @pytest.mark.asyncio
    async def test_run_javascript(self, mock_browser):
        from quickbooks_api.browser_mcp.server import run_javascript

        mock_browser.evaluate_js = AsyncMock(return_value={"count": 42})
        result = json.loads(await run_javascript("document.querySelectorAll('tr').length"))
        assert result["count"] == 42


class TestDownloads:

    @pytest.mark.asyncio
    async def test_download_file(self, mock_browser):
        from quickbooks_api.browser_mcp.server import download_file

        mock_browser.download_file = AsyncMock(return_value={
            "success": True,
            "filename": "report.pdf",
            "path": "/tmp/qbo-downloads/report.pdf",
        })
        result = json.loads(await download_file("a.download-link"))
        assert result["success"] is True
        assert result["filename"] == "report.pdf"


class TestWaiting:

    @pytest.mark.asyncio
    async def test_wait_for_element(self, mock_browser):
        from quickbooks_api.browser_mcp.server import wait_for_element

        mock_browser.wait_for_selector = AsyncMock(return_value={"success": True})
        result = json.loads(await wait_for_element("#loading", state="hidden"))
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_wait_for_page_load(self, mock_browser):
        from quickbooks_api.browser_mcp.server import wait_for_page_load

        mock_browser.wait_for_load = AsyncMock()
        result = json.loads(await wait_for_page_load("networkidle"))
        assert result["success"] is True


class TestQBOWorkflows:

    @pytest.mark.asyncio
    async def test_search_qbo(self, mock_browser):
        from quickbooks_api.browser_mcp.server import search_qbo

        page = mock_browser.page
        # Mock the locator chain
        locator_mock = MagicMock()
        locator_mock.first = MagicMock()
        locator_mock.first.click = AsyncMock()
        locator_mock.first.fill = AsyncMock()
        page.locator = MagicMock(return_value=locator_mock)
        page.keyboard = MagicMock()
        page.keyboard.press = AsyncMock()
        page.wait_for_load_state = AsyncMock()
        page.wait_for_timeout = AsyncMock()
        page.inner_text = AsyncMock(return_value="Search results: Invoice #1001")
        page.url = "https://app.sandbox.qbo.intuit.com/app/search"

        result = json.loads(await search_qbo("Invoice 1001"))
        assert result["success"] is True
        assert "1001" in result["page_text"]

    @pytest.mark.asyncio
    async def test_get_bank_transactions_for_review(self, mock_browser):
        from quickbooks_api.browser_mcp.server import get_bank_transactions_for_review

        mock_browser.go_to_bank_transactions = AsyncMock(return_value=PageInfo(
            url="https://app.sandbox.qbo.intuit.com/app/banking",
            title="Banking",
        ))
        page = mock_browser.page
        page.wait_for_load_state = AsyncMock()
        page.wait_for_timeout = AsyncMock()
        page.url = "https://app.sandbox.qbo.intuit.com/app/banking"

        locator_mock = MagicMock()
        locator_mock.first = MagicMock()
        locator_mock.first.click = AsyncMock(side_effect=Exception("not found"))
        page.locator = MagicMock(return_value=locator_mock)
        page.inner_text = AsyncMock(return_value="For Review (3)\nTransaction 1\nTransaction 2")

        result = json.loads(await get_bank_transactions_for_review())
        assert result["success"] is True
        assert "Transaction 1" in result["page_text"]


class TestErrorHandling:

    @pytest.mark.asyncio
    async def test_tool_returns_error_on_exception(self, mock_browser):
        from quickbooks_api.browser_mcp.server import navigate

        mock_browser.navigate = AsyncMock(side_effect=RuntimeError("page crashed"))
        result = json.loads(await navigate("/app/invoices"))
        assert "error" in result
        assert "page crashed" in result["detail"]

    @pytest.mark.asyncio
    async def test_login_without_credentials(self, mock_browser):
        from quickbooks_api.browser_mcp.server import qbo_login

        mock_browser.config.email = ""
        mock_browser.config.password = ""
        mock_browser.login = AsyncMock(return_value={"success": False, "error": "Email and password are required"})

        result = json.loads(await qbo_login())
        assert result["success"] is False
