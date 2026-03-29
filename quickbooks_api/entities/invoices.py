"""QuickBooks Online Invoice operations."""

from __future__ import annotations

from quickbooks_api.entities.base import BaseService


class InvoiceService(BaseService):
    entity_name = "Invoice"
    entity_url = "/invoice"

    def create_invoice(
        self,
        customer_id: str | int,
        line_items: list[dict],
        due_date: str | None = None,
        email: str | None = None,
        memo: str | None = None,
    ) -> dict:
        """Create an invoice.

        line_items should be a list of dicts like:
            [{"Description": "Service", "Amount": 100.00, "DetailType": "SalesItemLineDetail",
              "SalesItemLineDetail": {"ItemRef": {"value": "1"}, "Qty": 1, "UnitPrice": 100}}]
        """
        data: dict = {
            "CustomerRef": {"value": str(customer_id)},
            "Line": line_items,
        }
        if due_date:
            data["DueDate"] = due_date
        if email:
            data["BillEmail"] = {"Address": email}
        if memo:
            data["CustomerMemo"] = {"value": memo}
        return self.create(data)

    def send_invoice(self, invoice_id: str | int, email: str | None = None) -> dict:
        """Send an invoice via email."""
        endpoint = f"{self.entity_url}/{invoice_id}/send"
        params = {}
        if email:
            params["sendTo"] = email
        return self.client.post(endpoint, json_data=params if params else None)

    def void_invoice(self, invoice_id: str | int, sync_token: str) -> dict:
        """Void an invoice."""
        data = {
            "Id": str(invoice_id),
            "SyncToken": sync_token,
        }
        resp = self.client._request(
            "POST", self.entity_url, json_data=data, params={"operation": "void"}
        )
        return resp.get(self.entity_name, resp)

    def get_pdf(self, invoice_id: str | int) -> bytes:
        """Download the invoice PDF."""
        url = f"{self.client.base_api_url}{self.entity_url}/{invoice_id}/pdf"
        headers = self.client.auth.get_auth_header()
        headers["Accept"] = "application/pdf"
        resp = self.client.session.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
        return resp.content

    def find_by_customer(self, customer_id: str | int) -> list[dict]:
        """Find all invoices for a customer."""
        return self.query(where=f"CustomerRef = '{customer_id}'")

    def find_unpaid(self) -> list[dict]:
        """Find all unpaid invoices."""
        return self.query(where="Balance > '0'")

    def find_overdue(self, as_of_date: str) -> list[dict]:
        """Find overdue invoices as of a specific date (YYYY-MM-DD)."""
        return self.query(
            where=f"DueDate < '{as_of_date}' AND Balance > '0'"
        )
