"""Tests for entity service modules."""

import json
from unittest.mock import patch, MagicMock

import pytest

from quickbooks_api.entities.base import BaseService
from quickbooks_api.entities.customers import CustomerService
from quickbooks_api.entities.invoices import InvoiceService
from quickbooks_api.entities.payments import PaymentService
from quickbooks_api.entities.items import ItemService
from quickbooks_api.entities.accounts import AccountService
from quickbooks_api.entities.bills import BillService
from quickbooks_api.entities.vendors import VendorService
from quickbooks_api.entities.estimates import EstimateService
from quickbooks_api.entities.company import CompanyService
from quickbooks_api.entities.reports import ReportService


# ─── Base Service ────────────────────────────────────────────────────────────

class TestBaseService:

    def test_get(self, client):
        svc = BaseService(client)
        svc.entity_name = "Customer"
        svc.entity_url = "/customer"

        with patch.object(client, "get", return_value={"Customer": {"Id": "1", "Name": "Test"}}):
            result = svc.get("1")
        assert result["Id"] == "1"

    def test_create(self, client):
        svc = BaseService(client)
        svc.entity_name = "Customer"
        svc.entity_url = "/customer"

        with patch.object(client, "post", return_value={"Customer": {"Id": "2", "DisplayName": "New"}}):
            result = svc.create({"DisplayName": "New"})
        assert result["Id"] == "2"

    def test_update(self, client):
        svc = BaseService(client)
        svc.entity_name = "Customer"
        svc.entity_url = "/customer"

        with patch.object(client, "post", return_value={"Customer": {"Id": "1", "SyncToken": "1"}}):
            result = svc.update({"Id": "1", "SyncToken": "0", "DisplayName": "Updated"})
        assert result["SyncToken"] == "1"

    def test_delete(self, client):
        svc = BaseService(client)
        svc.entity_name = "Customer"
        svc.entity_url = "/customer"

        with patch.object(client, "delete", return_value={"status": "Deleted"}):
            result = svc.delete("1", "0")
        assert result["status"] == "Deleted"

    def test_query(self, client):
        svc = BaseService(client)
        svc.entity_name = "Customer"

        with patch.object(client, "query", return_value=[{"Id": "1"}, {"Id": "2"}]):
            results = svc.query(where="Active = true", max_results=10)
        assert len(results) == 2

    def test_count(self, client):
        svc = BaseService(client)
        svc.entity_name = "Customer"

        with patch.object(client, "query_count", return_value=5):
            assert svc.count() == 5

    def test_get_all_paginates(self, client):
        svc = BaseService(client)
        svc.entity_name = "Customer"

        # First batch: full, second batch: partial (signals end)
        batch1 = [{"Id": str(i)} for i in range(100)]
        batch2 = [{"Id": "100"}, {"Id": "101"}]

        call_count = 0
        def mock_query(where="", start_position=1, max_results=100, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return batch1
            return batch2

        with patch.object(svc, "query", side_effect=mock_query):
            results = svc.get_all()
        assert len(results) == 102


# ─── Customers ───────────────────────────────────────────────────────────────

class TestCustomerService:

    def test_create_customer_minimal(self, client):
        svc = CustomerService(client)
        with patch.object(svc, "create", return_value={"Id": "1", "DisplayName": "Alice"}) as mock:
            result = svc.create_customer("Alice")
        mock.assert_called_once_with({"DisplayName": "Alice"})
        assert result["DisplayName"] == "Alice"

    def test_create_customer_full(self, client):
        svc = CustomerService(client)
        with patch.object(svc, "create", return_value={"Id": "1"}) as mock:
            svc.create_customer(
                display_name="Bob Corp",
                email="bob@corp.com",
                phone="555-1234",
                company_name="Bob Corp LLC",
                notes="VIP customer",
            )
        data = mock.call_args[0][0]
        assert data["DisplayName"] == "Bob Corp"
        assert data["PrimaryEmailAddr"]["Address"] == "bob@corp.com"
        assert data["PrimaryPhone"]["FreeFormNumber"] == "555-1234"
        assert data["CompanyName"] == "Bob Corp LLC"
        assert data["Notes"] == "VIP customer"

    def test_find_by_name(self, client):
        svc = CustomerService(client)
        with patch.object(svc, "query", return_value=[{"Id": "1"}]) as mock:
            results = svc.find_by_name("Alice")
        assert "LIKE" in mock.call_args[1]["where"]
        assert len(results) == 1

    def test_find_by_email(self, client):
        svc = CustomerService(client)
        with patch.object(svc, "query", return_value=[]) as mock:
            results = svc.find_by_email("test@example.com")
        assert "PrimaryEmailAddr" in mock.call_args[1]["where"]

    def test_set_active(self, client):
        svc = CustomerService(client)
        with patch.object(svc, "update", return_value={"Id": "1", "Active": False}) as mock:
            svc.set_active("1", "2", active=False)
        data = mock.call_args[0][0]
        assert data["Active"] is False


# ─── Invoices ────────────────────────────────────────────────────────────────

class TestInvoiceService:

    def test_create_invoice(self, client):
        svc = InvoiceService(client)
        lines = [{"Amount": 100, "DetailType": "SalesItemLineDetail",
                  "SalesItemLineDetail": {"ItemRef": {"value": "1"}}}]

        with patch.object(svc, "create", return_value={"Id": "10"}) as mock:
            result = svc.create_invoice("5", lines, due_date="2026-04-30")

        data = mock.call_args[0][0]
        assert data["CustomerRef"]["value"] == "5"
        assert data["DueDate"] == "2026-04-30"
        assert len(data["Line"]) == 1

    def test_send_invoice(self, client):
        svc = InvoiceService(client)
        with patch.object(client, "post", return_value={"Invoice": {"Id": "10"}}) as mock:
            svc.send_invoice("10", email="test@example.com")
        assert "/10/send" in mock.call_args[0][0]

    def test_find_unpaid(self, client):
        svc = InvoiceService(client)
        with patch.object(svc, "query", return_value=[{"Id": "1", "Balance": 500}]) as mock:
            results = svc.find_unpaid()
        assert "Balance > '0'" in mock.call_args[1]["where"]

    def test_find_overdue(self, client):
        svc = InvoiceService(client)
        with patch.object(svc, "query", return_value=[]) as mock:
            svc.find_overdue("2026-03-01")
        where = mock.call_args[1]["where"]
        assert "DueDate" in where
        assert "Balance > '0'" in where

    def test_find_by_customer(self, client):
        svc = InvoiceService(client)
        with patch.object(svc, "query", return_value=[{"Id": "1"}]) as mock:
            svc.find_by_customer("42")
        assert "CustomerRef = '42'" in mock.call_args[1]["where"]


# ─── Payments ────────────────────────────────────────────────────────────────

class TestPaymentService:

    def test_create_payment_simple(self, client):
        svc = PaymentService(client)
        with patch.object(svc, "create", return_value={"Id": "1"}) as mock:
            svc.create_payment("5", 250.00)
        data = mock.call_args[0][0]
        assert data["CustomerRef"]["value"] == "5"
        assert data["TotalAmt"] == 250.00
        assert "Line" not in data

    def test_create_payment_with_invoices(self, client):
        svc = PaymentService(client)
        with patch.object(svc, "create", return_value={"Id": "1"}) as mock:
            svc.create_payment("5", 300.00, invoice_ids=["10", "11"])
        data = mock.call_args[0][0]
        assert len(data["Line"]) == 2
        assert data["Line"][0]["LinkedTxn"][0]["TxnId"] == "10"


# ─── Items ───────────────────────────────────────────────────────────────────

class TestItemService:

    def test_create_item(self, client):
        svc = ItemService(client)
        with patch.object(svc, "create", return_value={"Id": "1"}) as mock:
            svc.create_item("Widget", item_type="Service", unit_price=50.00)
        data = mock.call_args[0][0]
        assert data["Name"] == "Widget"
        assert data["Type"] == "Service"
        assert data["UnitPrice"] == 50.00

    def test_find_by_type(self, client):
        svc = ItemService(client)
        with patch.object(svc, "query", return_value=[]) as mock:
            svc.find_by_type("Inventory")
        assert "Type = 'Inventory'" in mock.call_args[1]["where"]


# ─── Bills ───────────────────────────────────────────────────────────────────

class TestBillService:

    def test_create_bill(self, client):
        svc = BillService(client)
        lines = [{"Amount": 200, "DetailType": "AccountBasedExpenseLineDetail",
                  "AccountBasedExpenseLineDetail": {"AccountRef": {"value": "7"}}}]
        with patch.object(svc, "create", return_value={"Id": "1"}) as mock:
            svc.create_bill("3", lines, due_date="2026-05-01")
        data = mock.call_args[0][0]
        assert data["VendorRef"]["value"] == "3"

    def test_find_unpaid(self, client):
        svc = BillService(client)
        with patch.object(svc, "query", return_value=[]) as mock:
            svc.find_unpaid()
        assert "Balance > '0'" in mock.call_args[1]["where"]


# ─── Vendors ─────────────────────────────────────────────────────────────────

class TestVendorService:

    def test_create_vendor(self, client):
        svc = VendorService(client)
        with patch.object(svc, "create", return_value={"Id": "1"}) as mock:
            svc.create_vendor("Acme Inc", email="acme@example.com")
        data = mock.call_args[0][0]
        assert data["DisplayName"] == "Acme Inc"
        assert data["PrimaryEmailAddr"]["Address"] == "acme@example.com"


# ─── Estimates ───────────────────────────────────────────────────────────────

class TestEstimateService:

    def test_create_estimate(self, client):
        svc = EstimateService(client)
        lines = [{"Amount": 1000, "DetailType": "SalesItemLineDetail",
                  "SalesItemLineDetail": {"ItemRef": {"value": "1"}}}]
        with patch.object(svc, "create", return_value={"Id": "1"}) as mock:
            svc.create_estimate("5", lines, expiration_date="2026-06-01")
        data = mock.call_args[0][0]
        assert data["CustomerRef"]["value"] == "5"
        assert data["ExpirationDate"] == "2026-06-01"


# ─── Company ─────────────────────────────────────────────────────────────────

class TestCompanyService:

    def test_get_info(self, client):
        svc = CompanyService(client)
        with patch.object(client, "get", return_value={"CompanyInfo": {"CompanyName": "Test Co"}}):
            result = svc.get_info()
        assert result["CompanyName"] == "Test Co"

    def test_get_preferences(self, client):
        svc = CompanyService(client)
        with patch.object(client, "get", return_value={"Preferences": {"EmailMessagePrefs": {}}}):
            result = svc.get_preferences()
        assert "EmailMessagePrefs" in result


# ─── Reports ─────────────────────────────────────────────────────────────────

class TestReportService:

    def test_profit_and_loss(self, client):
        svc = ReportService(client)
        with patch.object(client, "get", return_value={"Header": {"ReportName": "ProfitAndLoss"}}) as mock:
            result = svc.profit_and_loss(start_date="2026-01-01", end_date="2026-03-31")
        assert "/reports/ProfitAndLoss" in mock.call_args[0][0]
        params = mock.call_args[1]["params"]
        assert params["start_date"] == "2026-01-01"
        assert params["end_date"] == "2026-03-31"

    def test_balance_sheet(self, client):
        svc = ReportService(client)
        with patch.object(client, "get", return_value={"Header": {}}) as mock:
            svc.balance_sheet(accounting_method="Cash")
        params = mock.call_args[1]["params"]
        assert params["accounting_method"] == "Cash"

    def test_aged_receivables(self, client):
        svc = ReportService(client)
        with patch.object(client, "get", return_value={}) as mock:
            svc.aged_receivables(report_date="2026-03-27", aging_period=60)
        params = mock.call_args[1]["params"]
        assert params["report_date"] == "2026-03-27"
        assert params["aging_period"] == "60"

    def test_cash_flow(self, client):
        svc = ReportService(client)
        with patch.object(client, "get", return_value={}) as mock:
            svc.cash_flow(summarize_by="Month")
        params = mock.call_args[1]["params"]
        assert params["summarize_column_by"] == "Month"

    def test_general_ledger(self, client):
        svc = ReportService(client)
        with patch.object(client, "get", return_value={}) as mock:
            svc.general_ledger(start_date="2026-01-01", end_date="2026-03-31")
        assert "/reports/GeneralLedger" in mock.call_args[0][0]

    def test_vendor_expenses(self, client):
        svc = ReportService(client)
        with patch.object(client, "get", return_value={}) as mock:
            svc.vendor_expenses(start_date="2026-01-01")
        assert "/reports/VendorExpenses" in mock.call_args[0][0]
