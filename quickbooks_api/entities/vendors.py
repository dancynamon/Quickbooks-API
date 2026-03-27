"""QuickBooks Online Vendor operations."""

from quickbooks_api.entities.base import BaseService


class VendorService(BaseService):
    entity_name = "Vendor"
    entity_url = "/vendor"

    def create_vendor(
        self,
        display_name: str,
        email: str | None = None,
        phone: str | None = None,
        company_name: str | None = None,
        billing_address: dict | None = None,
    ) -> dict:
        """Create a vendor with common fields."""
        data: dict = {"DisplayName": display_name}
        if email:
            data["PrimaryEmailAddr"] = {"Address": email}
        if phone:
            data["PrimaryPhone"] = {"FreeFormNumber": phone}
        if company_name:
            data["CompanyName"] = company_name
        if billing_address:
            data["BillAddr"] = billing_address
        return self.create(data)

    def find_by_name(self, name: str) -> list[dict]:
        """Find vendors by name."""
        escaped = name.replace("'", "\\'")
        return self.query(where=f"DisplayName LIKE '%{escaped}%'")

    def set_active(self, vendor_id: str | int, sync_token: str, active: bool = True) -> dict:
        """Activate or deactivate a vendor."""
        return self.update({
            "Id": str(vendor_id),
            "SyncToken": sync_token,
            "Active": active,
        })
