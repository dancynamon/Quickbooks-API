"""QuickBooks Online Customer operations."""

from quickbooks_api.entities.base import BaseService


class CustomerService(BaseService):
    entity_name = "Customer"
    entity_url = "/customer"

    def create_customer(
        self,
        display_name: str,
        email: str | None = None,
        phone: str | None = None,
        company_name: str | None = None,
        billing_address: dict | None = None,
        notes: str | None = None,
    ) -> dict:
        """Create a customer with common fields."""
        data: dict = {"DisplayName": display_name}
        if email:
            data["PrimaryEmailAddr"] = {"Address": email}
        if phone:
            data["PrimaryPhone"] = {"FreeFormNumber": phone}
        if company_name:
            data["CompanyName"] = company_name
        if billing_address:
            data["BillAddr"] = billing_address
        if notes:
            data["Notes"] = notes
        return self.create(data)

    def find_by_name(self, name: str) -> list[dict]:
        """Find customers by display name."""
        escaped = name.replace("'", "\\'")
        return self.query(where=f"DisplayName LIKE '%{escaped}%'")

    def find_by_email(self, email: str) -> list[dict]:
        """Find customers by email address."""
        escaped = email.replace("'", "\\'")
        return self.query(where=f"PrimaryEmailAddr = '{escaped}'")

    def set_active(self, customer_id: str | int, sync_token: str, active: bool = True) -> dict:
        """Activate or deactivate a customer."""
        return self.update({
            "Id": str(customer_id),
            "SyncToken": sync_token,
            "Active": active,
        })
