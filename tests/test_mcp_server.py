"""Tests for the MCP server tool functions."""

import json
from unittest.mock import patch, MagicMock

import pytest

from quickbooks_api.exceptions import QuickBooksError


# We test the tool functions by mocking _get_client()
@pytest.fixture(autouse=True)
def mock_client(client):
    """Patch _get_client to return our test client for all MCP server tests."""
    with patch("quickbooks_api.mcp_server.server._get_client", return_value=client):
        yield client


class TestMCPCompanyTools:

    def test_get_company_info(self, client):
        from quickbooks_api.mcp_server.server import get_company_info
        with patch.object(client.company, "get_info", return_value={"CompanyName": "Test"}):
            result = json.loads(get_company_info())
        assert result["CompanyName"] == "Test"

    def test_get_company_preferences(self, client):
        from quickbooks_api.mcp_server.server import get_company_preferences
        with patch.object(client.company, "get_preferences", return_value={"key": "val"}):
            result = json.loads(get_company_preferences())
        assert result["key"] == "val"


class TestMCPCustomerTools:

    def test_list_customers(self, client):
        from quickbooks_api.mcp_server.server import list_customers
        with patch.object(client.customers, "query", return_value=[{"Id": "1"}]):
            result = json.loads(list_customers())
        assert len(result) == 1

    def test_get_customer(self, client):
        from quickbooks_api.mcp_server.server import get_customer
        with patch.object(client.customers, "get", return_value={"Id": "1", "DisplayName": "A"}):
            result = json.loads(get_customer("1"))
        assert result["Id"] == "1"

    def test_create_customer(self, client):
        from quickbooks_api.mcp_server.server import create_customer
        with patch.object(client.customers, "create_customer", return_value={"Id": "2"}):
            result = json.loads(create_customer("Alice", email="a@b.com"))
        assert result["Id"] == "2"

    def test_find_customers_by_name(self, client):
        from quickbooks_api.mcp_server.server import find_customers_by_name
        with patch.object(client.customers, "find_by_name", return_value=[]):
            result = json.loads(find_customers_by_name("Bob"))
        assert result == []


class TestMCPInvoiceTools:

    def test_create_invoice(self, client):
        from quickbooks_api.mcp_server.server import create_invoice
        lines = json.dumps([{"Amount": 100, "DetailType": "SalesItemLineDetail",
                            "SalesItemLineDetail": {"ItemRef": {"value": "1"}}}])
        with patch.object(client.invoices, "create_invoice", return_value={"Id": "10"}):
            result = json.loads(create_invoice("5", lines))
        assert result["Id"] == "10"

    def test_find_unpaid_invoices(self, client):
        from quickbooks_api.mcp_server.server import find_unpaid_invoices
        with patch.object(client.invoices, "find_unpaid", return_value=[{"Id": "1", "Balance": 500}]):
            result = json.loads(find_unpaid_invoices())
        assert result[0]["Balance"] == 500


class TestMCPReportTools:

    def test_report_profit_and_loss(self, client):
        from quickbooks_api.mcp_server.server import report_profit_and_loss
        with patch.object(client.reports, "profit_and_loss", return_value={"Header": {"ReportName": "PnL"}}):
            result = json.loads(report_profit_and_loss("2026-01-01", "2026-03-31"))
        assert result["Header"]["ReportName"] == "PnL"

    def test_report_balance_sheet(self, client):
        from quickbooks_api.mcp_server.server import report_balance_sheet
        with patch.object(client.reports, "balance_sheet", return_value={"Header": {}}):
            result = json.loads(report_balance_sheet())
        assert "Header" in result


class TestMCPErrorHandling:

    def test_tool_returns_error_json_on_qbo_error(self, client):
        from quickbooks_api.mcp_server.server import get_customer
        with patch.object(client.customers, "get", side_effect=QuickBooksError("Not found", 404)):
            result = json.loads(get_customer("999"))
        assert "error" in result
        assert result["status_code"] == 404

    def test_tool_returns_error_json_on_unexpected_error(self, client):
        from quickbooks_api.mcp_server.server import get_customer
        with patch.object(client.customers, "get", side_effect=RuntimeError("boom")):
            result = json.loads(get_customer("999"))
        assert "error" in result
        assert "boom" in result["error"]


class TestMCPPaymentTools:

    def test_create_payment_with_invoices(self, client):
        from quickbooks_api.mcp_server.server import create_payment
        with patch.object(client.payments, "create_payment", return_value={"Id": "1"}) as mock:
            result = json.loads(create_payment("5", 300.0, invoice_ids="10,11"))
        assert result["Id"] == "1"
        # Verify invoice_ids were parsed
        call_kwargs = mock.call_args[1]
        assert call_kwargs["invoice_ids"] == ["10", "11"]

    def test_create_payment_no_invoices(self, client):
        from quickbooks_api.mcp_server.server import create_payment
        with patch.object(client.payments, "create_payment", return_value={"Id": "1"}) as mock:
            create_payment("5", 100.0)
        call_kwargs = mock.call_args[1]
        assert call_kwargs["invoice_ids"] is None


class TestMCPQueryTool:

    def test_run_query(self, client):
        from quickbooks_api.mcp_server.server import run_query
        with patch.object(client, "query", return_value=[{"Id": "1"}, {"Id": "2"}]):
            result = json.loads(run_query("SELECT * FROM Customer"))
        assert len(result) == 2
