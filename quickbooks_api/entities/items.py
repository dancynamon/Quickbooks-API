"""QuickBooks Online Item/Product operations."""

from __future__ import annotations

from quickbooks_api.entities.base import BaseService


class ItemService(BaseService):
    entity_name = "Item"
    entity_url = "/item"

    def create_item(
        self,
        name: str,
        item_type: str = "NonInventory",
        income_account_id: str | None = None,
        expense_account_id: str | None = None,
        unit_price: float | None = None,
        description: str | None = None,
        taxable: bool = False,
    ) -> dict:
        """Create an item/product.

        item_type: "Inventory", "NonInventory", "Service"
        """
        data: dict = {
            "Name": name,
            "Type": item_type,
        }
        if income_account_id:
            data["IncomeAccountRef"] = {"value": income_account_id}
        if expense_account_id:
            data["ExpenseAccountRef"] = {"value": expense_account_id}
        if unit_price is not None:
            data["UnitPrice"] = unit_price
        if description:
            data["Description"] = description
        data["Taxable"] = taxable
        return self.create(data)

    def find_by_name(self, name: str) -> list[dict]:
        """Find items by name."""
        escaped = name.replace("'", "\\'")
        return self.query(where=f"Name LIKE '%{escaped}%'")

    def find_by_type(self, item_type: str) -> list[dict]:
        """Find items by type (Inventory, NonInventory, Service)."""
        return self.query(where=f"Type = '{item_type}'")
