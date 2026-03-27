"""Tests for the core QuickBooks API client."""

import json
import time
from unittest.mock import MagicMock, patch

import pytest

from quickbooks_api.client import QuickBooksClient
from quickbooks_api.exceptions import (
    AuthenticationError,
    NotFoundError,
    QuickBooksError,
    RateLimitError,
    ServerError,
    StaleObjectError,
    ValidationError,
)


class TestQuickBooksClient:

    def test_base_api_url(self, client):
        assert client.base_api_url == (
            "https://sandbox-quickbooks.api.intuit.com/v3/company/1234567890"
        )

    def test_get_request(self, client, mock_response):
        resp = mock_response(200, {"Customer": {"Id": "1", "DisplayName": "Test"}})
        with patch.object(client.session, "request", return_value=resp):
            result = client.get("/customer/1")
        assert result["Customer"]["Id"] == "1"

    def test_post_request(self, client, mock_response):
        customer_data = {"Customer": {"Id": "1", "DisplayName": "New Customer"}}
        resp = mock_response(200, customer_data)
        with patch.object(client.session, "request", return_value=resp):
            result = client.post("/customer", json_data={"DisplayName": "New Customer"})
        assert result["Customer"]["DisplayName"] == "New Customer"

    def test_delete_request(self, client, mock_response):
        resp = mock_response(200, {"Customer": {"Id": "1", "status": "Deleted"}})
        with patch.object(client.session, "request", return_value=resp):
            result = client.delete("/customer", json_data={"Id": "1", "SyncToken": "0"})
        assert result["Customer"]["status"] == "Deleted"

    def test_query(self, client, mock_response):
        resp = mock_response(200, {
            "QueryResponse": {
                "Customer": [
                    {"Id": "1", "DisplayName": "Alice"},
                    {"Id": "2", "DisplayName": "Bob"},
                ],
                "maxResults": 2,
            }
        })
        with patch.object(client.session, "request", return_value=resp):
            results = client.query("SELECT * FROM Customer")
        assert len(results) == 2
        assert results[0]["DisplayName"] == "Alice"

    def test_query_empty(self, client, mock_response):
        resp = mock_response(200, {"QueryResponse": {}})
        with patch.object(client.session, "request", return_value=resp):
            results = client.query("SELECT * FROM Customer WHERE Id = '999'")
        assert results == []

    def test_query_count(self, client, mock_response):
        resp = mock_response(200, {"QueryResponse": {"totalCount": 42}})
        with patch.object(client.session, "request", return_value=resp):
            count = client.query_count("Customer")
        assert count == 42


class TestErrorHandling:

    def test_400_raises_validation_error(self, client, mock_response):
        resp = mock_response(400, {
            "Fault": {"Error": [{"Message": "Bad request", "Detail": "Invalid field"}]}
        })
        with patch.object(client.session, "request", return_value=resp):
            with pytest.raises(ValidationError, match="Bad request"):
                client.get("/customer/1")

    def test_401_triggers_refresh_then_raises(self, client, mock_response):
        resp = mock_response(401, {
            "Fault": {"Error": [{"Message": "Token expired"}]}
        })
        with patch.object(client.session, "request", return_value=resp), \
             patch.object(client.auth, "refresh_access_token") as mock_refresh:
            with pytest.raises(AuthenticationError):
                client.get("/customer/1")
            # Should have attempted one refresh
            mock_refresh.assert_called_once()

    def test_404_raises_not_found(self, client, mock_response):
        resp = mock_response(404, {
            "Fault": {"Error": [{"Message": "Object Not Found"}]}
        })
        with patch.object(client.session, "request", return_value=resp):
            with pytest.raises(NotFoundError):
                client.get("/customer/999")

    def test_429_retries_then_raises(self, client, mock_response):
        resp = mock_response(429, {
            "Fault": {"Error": [{"Message": "Rate limited"}]}
        })
        with patch.object(client.session, "request", return_value=resp), \
             patch("quickbooks_api.client.time.sleep"):
            with pytest.raises(RateLimitError):
                client.get("/customer/1")

    def test_500_retries_then_raises(self, client, mock_response):
        resp = mock_response(500, {
            "Fault": {"Error": [{"Message": "Internal error"}]}
        })
        with patch.object(client.session, "request", return_value=resp), \
             patch("quickbooks_api.client.time.sleep"):
            with pytest.raises(ServerError):
                client.get("/customer/1")

    def test_stale_object_error(self, client, mock_response):
        resp = mock_response(400, {
            "Fault": {"Error": [{"Message": "Stale Object", "code": "5010"}]}
        })
        with patch.object(client.session, "request", return_value=resp):
            with pytest.raises(StaleObjectError):
                client.post("/customer", json_data={"Id": "1", "SyncToken": "0"})


class TestRetryLogic:

    def test_retry_on_server_error_then_succeed(self, client, mock_response):
        error_resp = mock_response(500, {"Fault": {"Error": [{"Message": "Oops"}]}})
        success_resp = mock_response(200, {"Customer": {"Id": "1"}})

        call_count = 0
        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return error_resp
            return success_resp

        with patch.object(client.session, "request", side_effect=side_effect), \
             patch("quickbooks_api.client.time.sleep"):
            result = client.get("/customer/1")

        assert result["Customer"]["Id"] == "1"
        assert call_count == 2

    def test_retry_on_rate_limit_then_succeed(self, client, mock_response):
        rate_resp = mock_response(429, {"Fault": {"Error": [{"Message": "Throttled"}]}})
        success_resp = mock_response(200, {"Invoice": {"Id": "5"}})

        call_count = 0
        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                return rate_resp
            return success_resp

        with patch.object(client.session, "request", side_effect=side_effect), \
             patch("quickbooks_api.client.time.sleep"):
            result = client.get("/invoice/5")

        assert result["Invoice"]["Id"] == "5"
        assert call_count == 3

    def test_401_refreshes_token_then_succeeds(self, client, mock_response):
        auth_err_resp = mock_response(401, {"Fault": {"Error": [{"Message": "Unauthorized"}]}})
        success_resp = mock_response(200, {"Customer": {"Id": "1"}})

        call_count = 0
        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return auth_err_resp
            return success_resp

        with patch.object(client.session, "request", side_effect=side_effect), \
             patch.object(client.auth, "refresh_access_token"):
            result = client.get("/customer/1")

        assert result["Customer"]["Id"] == "1"
