"""Core QuickBooks Online API client with retry logic and rate limiting."""

import time
import logging

import requests

from quickbooks_api.auth import QuickBooksAuth
from quickbooks_api.exceptions import (
    AuthenticationError,
    AuthorizationError,
    NotFoundError,
    QuickBooksError,
    RateLimitError,
    ServerError,
    StaleObjectError,
    ValidationError,
)

logger = logging.getLogger(__name__)

API_VERSION = "v3"
MAX_RETRIES = 3
RETRY_BACKOFF = 2  # seconds, exponential


class QuickBooksClient:
    """Core HTTP client for QuickBooks Online API with retry and rate limiting."""

    def __init__(self, auth: QuickBooksAuth):
        self.auth = auth
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json",
            "Content-Type": "application/json",
        })
        self._last_request_time = 0.0
        self._min_request_interval = 0.1  # 100ms between requests

    @property
    def base_api_url(self) -> str:
        return f"{self.auth.base_url}/{API_VERSION}/company/{self.auth.realm_id}"

    # --- Lazy-loaded entity services ---

    @property
    def customers(self):
        from quickbooks_api.entities.customers import CustomerService
        if not hasattr(self, "_customers"):
            self._customers = CustomerService(self)
        return self._customers

    @property
    def invoices(self):
        from quickbooks_api.entities.invoices import InvoiceService
        if not hasattr(self, "_invoices"):
            self._invoices = InvoiceService(self)
        return self._invoices

    @property
    def payments(self):
        from quickbooks_api.entities.payments import PaymentService
        if not hasattr(self, "_payments"):
            self._payments = PaymentService(self)
        return self._payments

    @property
    def items(self):
        from quickbooks_api.entities.items import ItemService
        if not hasattr(self, "_items"):
            self._items = ItemService(self)
        return self._items

    @property
    def accounts(self):
        from quickbooks_api.entities.accounts import AccountService
        if not hasattr(self, "_accounts"):
            self._accounts = AccountService(self)
        return self._accounts

    @property
    def bills(self):
        from quickbooks_api.entities.bills import BillService
        if not hasattr(self, "_bills"):
            self._bills = BillService(self)
        return self._bills

    @property
    def vendors(self):
        from quickbooks_api.entities.vendors import VendorService
        if not hasattr(self, "_vendors"):
            self._vendors = VendorService(self)
        return self._vendors

    @property
    def estimates(self):
        from quickbooks_api.entities.estimates import EstimateService
        if not hasattr(self, "_estimates"):
            self._estimates = EstimateService(self)
        return self._estimates

    @property
    def company(self):
        from quickbooks_api.entities.company import CompanyService
        if not hasattr(self, "_company"):
            self._company = CompanyService(self)
        return self._company

    @property
    def reports(self):
        from quickbooks_api.entities.reports import ReportService
        if not hasattr(self, "_reports"):
            self._reports = ReportService(self)
        return self._reports

    # --- HTTP Methods ---

    def get(self, endpoint: str, params: dict | None = None) -> dict:
        return self._request("GET", endpoint, params=params)

    def post(self, endpoint: str, json_data: dict | None = None) -> dict:
        return self._request("POST", endpoint, json_data=json_data)

    def delete(self, endpoint: str, json_data: dict | None = None) -> dict:
        return self._request("POST", endpoint, json_data=json_data, params={"operation": "delete"})

    def query(self, query_string: str) -> list[dict]:
        """Execute a QBO query and return the list of results."""
        resp = self.get("/query", params={"query": query_string})
        query_response = resp.get("QueryResponse", {})
        # The results are under a key matching the entity type, or empty
        for key, value in query_response.items():
            if isinstance(value, list):
                return value
        return []

    def query_count(self, entity: str, where: str = "") -> int:
        """Return the count of entities matching an optional WHERE clause."""
        q = f"SELECT COUNT(*) FROM {entity}"
        if where:
            q += f" WHERE {where}"
        resp = self.get("/query", params={"query": q})
        return resp.get("QueryResponse", {}).get("totalCount", 0)

    # --- Internal ---

    def _request(
        self,
        method: str,
        endpoint: str,
        params: dict | None = None,
        json_data: dict | None = None,
    ) -> dict:
        url = f"{self.base_api_url}{endpoint}"

        for attempt in range(MAX_RETRIES + 1):
            self._rate_limit()
            headers = self.auth.get_auth_header()

            try:
                resp = self.session.request(
                    method,
                    url,
                    headers=headers,
                    params=params,
                    json=json_data,
                    timeout=30,
                )
                return self._handle_response(resp)

            except RateLimitError:
                if attempt < MAX_RETRIES:
                    wait = RETRY_BACKOFF ** (attempt + 1)
                    logger.warning("Rate limited. Retrying in %ss...", wait)
                    time.sleep(wait)
                else:
                    raise

            except ServerError:
                if attempt < MAX_RETRIES:
                    wait = RETRY_BACKOFF ** (attempt + 1)
                    logger.warning("Server error. Retrying in %ss...", wait)
                    time.sleep(wait)
                else:
                    raise

            except AuthenticationError:
                if attempt == 0:
                    logger.info("Token expired, refreshing...")
                    self.auth.refresh_access_token()
                else:
                    raise

        raise QuickBooksError("Max retries exceeded")

    def _handle_response(self, resp: requests.Response) -> dict:
        if resp.status_code == 200:
            return resp.json()

        # Try to extract QBO error detail
        detail = {}
        message = f"HTTP {resp.status_code}"
        try:
            body = resp.json()
            fault = body.get("Fault", {})
            errors = fault.get("Error", [])
            if errors:
                detail = errors[0]
                message = detail.get("Message", message)
                qbo_detail = detail.get("Detail", "")
                if qbo_detail:
                    message = f"{message}: {qbo_detail}"
            # Stale object check
            if any(e.get("code") == "5010" for e in errors):
                raise StaleObjectError(message, resp.status_code, detail)
        except (ValueError, KeyError):
            message = resp.text[:500]

        error_map = {
            400: ValidationError,
            401: AuthenticationError,
            403: AuthorizationError,
            404: NotFoundError,
            429: RateLimitError,
        }

        if resp.status_code in error_map:
            raise error_map[resp.status_code](message, resp.status_code, detail)
        if resp.status_code >= 500:
            raise ServerError(message, resp.status_code, detail)
        raise QuickBooksError(message, resp.status_code, detail)

    def _rate_limit(self) -> None:
        now = time.time()
        elapsed = now - self._last_request_time
        if elapsed < self._min_request_interval:
            time.sleep(self._min_request_interval - elapsed)
        self._last_request_time = time.time()
