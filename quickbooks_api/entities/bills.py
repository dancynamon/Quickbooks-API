"""QuickBooks Online Bill operations."""

from quickbooks_api.entities.base import BaseService


class BillService(BaseService):
    entity_name = "Bill"
    entity_url = "/bill"

    def create_bill(
        self,
        vendor_id: str | int,
        line_items: list[dict],
        due_date: str | None = None,
        memo: str | None = None,
    ) -> dict:
        """Create a bill.

        line_items example:
            [{"Amount": 100.00, "DetailType": "AccountBasedExpenseLineDetail",
              "AccountBasedExpenseLineDetail": {"AccountRef": {"value": "7"}}}]
        """
        data: dict = {
            "VendorRef": {"value": str(vendor_id)},
            "Line": line_items,
        }
        if due_date:
            data["DueDate"] = due_date
        if memo:
            data["PrivateNote"] = memo
        return self.create(data)

    def find_by_vendor(self, vendor_id: str | int) -> list[dict]:
        """Find all bills for a vendor."""
        return self.query(where=f"VendorRef = '{vendor_id}'")

    def find_unpaid(self) -> list[dict]:
        """Find all unpaid bills."""
        return self.query(where="Balance > '0'")
