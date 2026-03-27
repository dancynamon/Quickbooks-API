"""QuickBooks Online Company Info operations."""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from quickbooks_api.client import QuickBooksClient


class CompanyService:
    """Read company information."""

    def __init__(self, client: QuickBooksClient):
        self.client = client

    def get_info(self) -> dict:
        """Get company information."""
        resp = self.client.get("/companyinfo/" + self.client.auth.realm_id)
        return resp.get("CompanyInfo", resp)

    def get_preferences(self) -> dict:
        """Get company preferences."""
        resp = self.client.get("/preferences")
        return resp.get("Preferences", resp)
