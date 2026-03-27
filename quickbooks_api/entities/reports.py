"""QuickBooks Online Report operations."""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from quickbooks_api.client import QuickBooksClient


class ReportService:
    """Access QuickBooks Online reports."""

    def __init__(self, client: QuickBooksClient):
        self.client = client

    def _get_report(self, report_name: str, params: dict | None = None) -> dict:
        """Fetch a report by name with optional parameters."""
        return self.client.get(f"/reports/{report_name}", params=params)

    def profit_and_loss(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
        accounting_method: str = "Accrual",
        summarize_by: str | None = None,
    ) -> dict:
        """Get Profit and Loss report."""
        params: dict = {"accounting_method": accounting_method}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        if summarize_by:
            params["summarize_column_by"] = summarize_by
        return self._get_report("ProfitAndLoss", params)

    def balance_sheet(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
        accounting_method: str = "Accrual",
        summarize_by: str | None = None,
    ) -> dict:
        """Get Balance Sheet report."""
        params: dict = {"accounting_method": accounting_method}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        if summarize_by:
            params["summarize_column_by"] = summarize_by
        return self._get_report("BalanceSheet", params)

    def cash_flow(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
        summarize_by: str | None = None,
    ) -> dict:
        """Get Statement of Cash Flows report."""
        params: dict = {}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        if summarize_by:
            params["summarize_column_by"] = summarize_by
        return self._get_report("CashFlow", params)

    def general_ledger(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
        columns: str | None = None,
    ) -> dict:
        """Get General Ledger report."""
        params: dict = {}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        if columns:
            params["columns"] = columns
        return self._get_report("GeneralLedger", params)

    def trial_balance(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
        accounting_method: str = "Accrual",
    ) -> dict:
        """Get Trial Balance report."""
        params: dict = {"accounting_method": accounting_method}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        return self._get_report("TrialBalance", params)

    def aged_receivables(
        self,
        report_date: str | None = None,
        aging_period: int | None = None,
    ) -> dict:
        """Get Accounts Receivable Aging Summary."""
        params: dict = {}
        if report_date:
            params["report_date"] = report_date
        if aging_period:
            params["aging_period"] = str(aging_period)
        return self._get_report("AgedReceivables", params)

    def aged_payables(
        self,
        report_date: str | None = None,
        aging_period: int | None = None,
    ) -> dict:
        """Get Accounts Payable Aging Summary."""
        params: dict = {}
        if report_date:
            params["report_date"] = report_date
        if aging_period:
            params["aging_period"] = str(aging_period)
        return self._get_report("AgedPayables", params)

    def customer_income(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> dict:
        """Get Income by Customer Summary."""
        params: dict = {}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        return self._get_report("CustomerIncome", params)

    def vendor_expenses(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> dict:
        """Get Expenses by Vendor Summary."""
        params: dict = {}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        return self._get_report("VendorExpenses", params)
