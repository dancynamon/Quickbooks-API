"""QuickBooks Online Account operations."""

from quickbooks_api.entities.base import BaseService


class AccountService(BaseService):
    entity_name = "Account"
    entity_url = "/account"

    def find_by_type(self, account_type: str) -> list[dict]:
        """Find accounts by type (e.g., 'Bank', 'Income', 'Expense')."""
        return self.query(where=f"AccountType = '{account_type}'")

    def find_by_name(self, name: str) -> list[dict]:
        """Find accounts by name."""
        escaped = name.replace("'", "\\'")
        return self.query(where=f"Name LIKE '%{escaped}%'")

    def get_chart_of_accounts(self) -> list[dict]:
        """Get the full chart of accounts."""
        return self.get_all()
