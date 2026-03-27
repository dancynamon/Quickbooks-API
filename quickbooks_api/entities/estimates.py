"""QuickBooks Online Estimate operations."""

from quickbooks_api.entities.base import BaseService


class EstimateService(BaseService):
    entity_name = "Estimate"
    entity_url = "/estimate"

    def create_estimate(
        self,
        customer_id: str | int,
        line_items: list[dict],
        expiration_date: str | None = None,
        memo: str | None = None,
    ) -> dict:
        """Create an estimate/quote."""
        data: dict = {
            "CustomerRef": {"value": str(customer_id)},
            "Line": line_items,
        }
        if expiration_date:
            data["ExpirationDate"] = expiration_date
        if memo:
            data["CustomerMemo"] = {"value": memo}
        return self.create(data)

    def send_estimate(self, estimate_id: str | int, email: str | None = None) -> dict:
        """Send an estimate via email."""
        endpoint = f"{self.entity_url}/{estimate_id}/send"
        params = {}
        if email:
            params["sendTo"] = email
        return self.client.post(endpoint, json_data=params if params else None)

    def find_by_customer(self, customer_id: str | int) -> list[dict]:
        """Find all estimates for a customer."""
        return self.query(where=f"CustomerRef = '{customer_id}'")

    def get_pdf(self, estimate_id: str | int) -> bytes:
        """Download the estimate PDF."""
        url = f"{self.client.base_api_url}{self.entity_url}/{estimate_id}/pdf"
        headers = self.client.auth.get_auth_header()
        headers["Accept"] = "application/pdf"
        resp = self.client.session.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
        return resp.content
