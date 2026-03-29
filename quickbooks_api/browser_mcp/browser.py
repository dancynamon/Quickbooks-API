"""Headless browser automation for QuickBooks Online using Playwright."""

from __future__ import annotations

import asyncio
import base64
import json
import os
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class BrowserConfig:
    """Configuration for the QBO browser automation."""

    email: str = ""
    password: str = ""
    headless: bool = True
    slow_mo: int = 0
    timeout: int = 30_000
    viewport_width: int = 1280
    viewport_height: int = 900
    downloads_dir: str = "/tmp/qbo-downloads"
    user_data_dir: str = ""
    base_url: str = "https://app.qbo.intuit.com"
    sandbox_base_url: str = "https://app.sandbox.qbo.intuit.com"
    environment: str = "sandbox"

    @property
    def app_url(self) -> str:
        if self.environment == "production":
            return self.base_url
        return self.sandbox_base_url

    @classmethod
    def from_env(cls) -> BrowserConfig:
        return cls(
            email=os.environ.get("QBO_EMAIL", ""),
            password=os.environ.get("QBO_PASSWORD", ""),
            headless=os.environ.get("QBO_HEADLESS", "true").lower() == "true",
            slow_mo=int(os.environ.get("QBO_SLOW_MO", "0")),
            timeout=int(os.environ.get("QBO_TIMEOUT", "30000")),
            downloads_dir=os.environ.get("QBO_DOWNLOADS_DIR", "/tmp/qbo-downloads"),
            user_data_dir=os.environ.get("QBO_USER_DATA_DIR", ""),
            environment=os.environ.get("QBO_ENVIRONMENT", "sandbox"),
        )


@dataclass
class PageInfo:
    """Snapshot of the current browser page state."""

    url: str
    title: str
    content_text: str = ""


@dataclass
class ElementInfo:
    """Information about a DOM element."""

    tag: str
    text: str
    attributes: dict[str, str] = field(default_factory=dict)
    bounding_box: Optional[dict[str, float]] = None
    visible: bool = True


class QBOBrowser:
    """Headless browser wrapper for QuickBooks Online automation.

    Manages a Playwright browser instance and provides high-level methods
    for navigating and interacting with QuickBooks Online.
    """

    def __init__(self, config: Optional[BrowserConfig] = None):
        self.config = config or BrowserConfig.from_env()
        self._playwright = None
        self._browser = None
        self._context = None
        self._page = None
        self._started = False

    async def start(self) -> None:
        """Launch the browser and create a page."""
        if self._started:
            return

        from playwright.async_api import async_playwright

        self._playwright = await async_playwright().start()

        os.makedirs(self.config.downloads_dir, exist_ok=True)

        launch_args = {
            "headless": self.config.headless,
            "slow_mo": self.config.slow_mo,
        }

        if self.config.user_data_dir:
            self._browser = await self._playwright.chromium.launch_persistent_context(
                self.config.user_data_dir,
                **launch_args,
                viewport={
                    "width": self.config.viewport_width,
                    "height": self.config.viewport_height,
                },
                accept_downloads=True,
            )
            self._context = self._browser
            self._page = self._context.pages[0] if self._context.pages else await self._context.new_page()
        else:
            self._browser = await self._playwright.chromium.launch(**launch_args)
            self._context = await self._browser.new_context(
                viewport={
                    "width": self.config.viewport_width,
                    "height": self.config.viewport_height,
                },
                accept_downloads=True,
            )
            self._page = await self._context.new_page()

        self._page.set_default_timeout(self.config.timeout)
        self._started = True

    async def stop(self) -> None:
        """Close the browser and clean up."""
        if not self._started:
            return
        try:
            if self._page:
                await self._page.close()
            if self._context and not self.config.user_data_dir:
                await self._context.close()
            if self._browser:
                await self._browser.close()
            if self._playwright:
                await self._playwright.stop()
        finally:
            self._playwright = None
            self._browser = None
            self._context = None
            self._page = None
            self._started = False

    @property
    def page(self):
        if not self._page:
            raise RuntimeError("Browser not started. Call start() first.")
        return self._page

    # ── Authentication ──────────────────────────────────────────────

    async def login(self, email: str = "", password: str = "") -> dict[str, Any]:
        """Log in to QuickBooks Online via the Intuit sign-in page."""
        email = email or self.config.email
        password = password or self.config.password

        if not email or not password:
            return {"success": False, "error": "Email and password are required"}

        page = self.page
        await page.goto("https://accounts.intuit.com/app/sign-in", wait_until="networkidle")

        # Enter email
        email_input = page.locator('input[id="ius-identifier"], input[name="Email"], input[type="email"]').first
        await email_input.wait_for(state="visible", timeout=self.config.timeout)
        await email_input.fill(email)

        # Click continue/next
        submit_btn = page.locator('button[data-testid="IdentifierFirstSubmitButton"], button[type="submit"]').first
        await submit_btn.click()

        # Wait for password field
        await page.wait_for_timeout(2000)
        password_input = page.locator('input[id="ius-password"], input[name="Password"], input[type="password"]').first
        await password_input.wait_for(state="visible", timeout=self.config.timeout)
        await password_input.fill(password)

        # Submit
        sign_in_btn = page.locator('button[data-testid="passwordVerificationContinueButton"], button[type="submit"]').first
        await sign_in_btn.click()

        # Wait for QBO to load
        try:
            await page.wait_for_url("**/app/**", timeout=self.config.timeout)
            return {"success": True, "url": page.url, "title": await page.title()}
        except Exception as e:
            return {
                "success": False,
                "error": f"Login may require MFA or failed: {e}",
                "url": page.url,
                "title": await page.title(),
            }

    async def is_logged_in(self) -> bool:
        """Check if we appear to be logged into QBO."""
        url = self.page.url
        return "/app/" in url and ("qbo.intuit.com" in url or "sandbox.qbo.intuit.com" in url)

    # ── Navigation ──────────────────────────────────────────────────

    async def navigate(self, path: str) -> PageInfo:
        """Navigate to a QBO page by path (e.g. '/app/invoices')."""
        page = self.page
        url = path if path.startswith("http") else f"{self.config.app_url}{path}"
        await page.goto(url, wait_until="networkidle")
        return PageInfo(
            url=page.url,
            title=await page.title(),
        )

    async def get_current_page(self) -> PageInfo:
        """Get info about the current page."""
        page = self.page
        return PageInfo(
            url=page.url,
            title=await page.title(),
        )

    async def wait_for_navigation(self, url_pattern: str = "**", timeout: int = 0) -> PageInfo:
        """Wait for navigation to a URL matching a pattern."""
        page = self.page
        t = timeout or self.config.timeout
        await page.wait_for_url(url_pattern, timeout=t)
        return PageInfo(url=page.url, title=await page.title())

    # ── Screenshots ─────────────────────────────────────────────────

    async def screenshot(self, full_page: bool = False, selector: str = "") -> str:
        """Take a screenshot and return it as a base64-encoded PNG."""
        page = self.page
        if selector:
            element = page.locator(selector).first
            raw = await element.screenshot()
        else:
            raw = await page.screenshot(full_page=full_page)
        return base64.b64encode(raw).decode("utf-8")

    async def screenshot_to_file(self, path: str, full_page: bool = False) -> str:
        """Take a screenshot and save it to a file."""
        page = self.page
        await page.screenshot(path=path, full_page=full_page)
        return path

    # ── DOM interaction ─────────────────────────────────────────────

    async def click(self, selector: str, timeout: int = 0) -> dict[str, Any]:
        """Click an element matching the selector."""
        page = self.page
        t = timeout or self.config.timeout
        try:
            await page.locator(selector).first.click(timeout=t)
            await page.wait_for_load_state("networkidle")
            return {"success": True, "url": page.url}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def fill(self, selector: str, value: str, timeout: int = 0) -> dict[str, Any]:
        """Fill an input field."""
        page = self.page
        t = timeout or self.config.timeout
        try:
            await page.locator(selector).first.fill(value, timeout=t)
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def select_option(self, selector: str, value: str = "", label: str = "") -> dict[str, Any]:
        """Select a dropdown option by value or label."""
        page = self.page
        try:
            if label:
                await page.locator(selector).first.select_option(label=label)
            else:
                await page.locator(selector).first.select_option(value=value)
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def type_text(self, selector: str, text: str, delay: int = 50) -> dict[str, Any]:
        """Type text character by character (useful for autocomplete fields)."""
        page = self.page
        try:
            await page.locator(selector).first.click()
            await page.keyboard.type(text, delay=delay)
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def press_key(self, key: str, selector: str = "") -> dict[str, Any]:
        """Press a keyboard key (e.g. 'Enter', 'Tab', 'Escape')."""
        page = self.page
        try:
            if selector:
                await page.locator(selector).first.press(key)
            else:
                await page.keyboard.press(key)
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ── Content extraction ──────────────────────────────────────────

    async def get_text(self, selector: str) -> str:
        """Get the text content of an element."""
        page = self.page
        return await page.locator(selector).first.text_content() or ""

    async def get_attribute(self, selector: str, attribute: str) -> str:
        """Get an attribute value from an element."""
        page = self.page
        return await page.locator(selector).first.get_attribute(attribute) or ""

    async def get_elements(self, selector: str, limit: int = 50) -> list[ElementInfo]:
        """Get info about elements matching a selector."""
        page = self.page
        locators = page.locator(selector)
        count = min(await locators.count(), limit)
        elements = []
        for i in range(count):
            loc = locators.nth(i)
            tag = await loc.evaluate("el => el.tagName.toLowerCase()")
            text = (await loc.text_content() or "").strip()[:200]
            visible = await loc.is_visible()
            bbox = await loc.bounding_box()
            elements.append(ElementInfo(
                tag=tag,
                text=text,
                visible=visible,
                bounding_box=bbox,
            ))
        return elements

    async def get_page_text(self) -> str:
        """Get the full visible text of the page."""
        page = self.page
        return await page.inner_text("body")

    async def get_page_html(self, selector: str = "body") -> str:
        """Get the inner HTML of an element."""
        page = self.page
        return await page.locator(selector).first.inner_html()

    async def evaluate_js(self, expression: str) -> Any:
        """Evaluate a JavaScript expression in the page context."""
        page = self.page
        return await page.evaluate(expression)

    # ── Table extraction ────────────────────────────────────────────

    async def extract_table(self, selector: str = "table") -> list[list[str]]:
        """Extract data from an HTML table as a list of rows."""
        page = self.page
        return await page.evaluate(f"""
            (() => {{
                const table = document.querySelector({json.dumps(selector)});
                if (!table) return [];
                const rows = [];
                for (const tr of table.querySelectorAll('tr')) {{
                    const cells = [];
                    for (const td of tr.querySelectorAll('th, td')) {{
                        cells.push(td.innerText.trim());
                    }}
                    rows.push(cells);
                }}
                return rows;
            }})()
        """)

    # ── Downloads ───────────────────────────────────────────────────

    async def download_file(self, selector: str) -> dict[str, Any]:
        """Click a download link/button and wait for the download."""
        page = self.page
        try:
            async with page.expect_download(timeout=self.config.timeout) as download_info:
                await page.locator(selector).first.click()
            download = await download_info.value
            dest = os.path.join(self.config.downloads_dir, download.suggested_filename)
            await download.save_as(dest)
            return {
                "success": True,
                "filename": download.suggested_filename,
                "path": dest,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ── Waiting ─────────────────────────────────────────────────────

    async def wait_for_selector(self, selector: str, state: str = "visible", timeout: int = 0) -> dict[str, Any]:
        """Wait for an element matching the selector."""
        page = self.page
        t = timeout or self.config.timeout
        try:
            await page.locator(selector).first.wait_for(state=state, timeout=t)
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def wait_for_load(self, state: str = "networkidle") -> None:
        """Wait for the page to reach a load state."""
        await self.page.wait_for_load_state(state)

    # ── QBO-specific navigation helpers ─────────────────────────────

    async def go_to_dashboard(self) -> PageInfo:
        return await self.navigate("/app/homepage")

    async def go_to_invoices(self) -> PageInfo:
        return await self.navigate("/app/invoices")

    async def go_to_expenses(self) -> PageInfo:
        return await self.navigate("/app/expenses")

    async def go_to_customers(self) -> PageInfo:
        return await self.navigate("/app/customers")

    async def go_to_vendors(self) -> PageInfo:
        return await self.navigate("/app/vendors")

    async def go_to_reports(self) -> PageInfo:
        return await self.navigate("/app/reports")

    async def go_to_chart_of_accounts(self) -> PageInfo:
        return await self.navigate("/app/chart-of-accounts")

    async def go_to_reconcile(self) -> PageInfo:
        return await self.navigate("/app/reconcile")

    async def go_to_bank_transactions(self) -> PageInfo:
        return await self.navigate("/app/banking")

    async def go_to_settings(self) -> PageInfo:
        return await self.navigate("/app/settings")

    async def go_to_payroll(self) -> PageInfo:
        return await self.navigate("/app/payroll")

    async def go_to_taxes(self) -> PageInfo:
        return await self.navigate("/app/salestax")
