"""Tests for OAuth 2.0 authentication module."""

import json
import time
from unittest.mock import MagicMock, patch, mock_open

import pytest
import requests

from quickbooks_api.auth import QuickBooksAuth, AuthenticationError


class TestQuickBooksAuth:

    @patch.object(QuickBooksAuth, "_load_tokens")
    @patch.object(QuickBooksAuth, "_save_tokens")
    def _make_auth(self, mock_save, mock_load, **kwargs):
        defaults = {
            "client_id": "test_id",
            "client_secret": "test_secret",
            "redirect_uri": "http://localhost:8080/callback",
            "environment": "sandbox",
        }
        defaults.update(kwargs)
        return QuickBooksAuth(**defaults)

    def test_base_url_sandbox(self):
        auth = self._make_auth(environment="sandbox")
        assert "sandbox" in auth.base_url

    def test_base_url_production(self):
        auth = self._make_auth(environment="production")
        assert auth.base_url == "https://quickbooks.api.intuit.com"

    def test_is_authenticated_false_initially(self):
        auth = self._make_auth()
        assert not auth.is_authenticated

    def test_is_authenticated_true_with_tokens(self):
        auth = self._make_auth()
        auth.access_token = "tok"
        auth.realm_id = "123"
        assert auth.is_authenticated

    def test_is_token_expired(self):
        auth = self._make_auth()
        auth.token_expiry = time.time() - 100
        assert auth.is_token_expired

    def test_is_token_not_expired(self):
        auth = self._make_auth()
        auth.token_expiry = time.time() + 3600
        assert not auth.is_token_expired

    def test_get_authorization_url(self):
        auth = self._make_auth()
        url = auth.get_authorization_url()
        assert "appcenter.intuit.com" in url
        assert "client_id=test_id" in url
        assert "response_type=code" in url
        assert "com.intuit.quickbooks.accounting" in url

    def test_get_authorization_url_custom_scopes(self):
        auth = self._make_auth()
        url = auth.get_authorization_url(scopes=["com.intuit.quickbooks.payment"])
        assert "com.intuit.quickbooks.payment" in url

    @patch("quickbooks_api.auth.requests.post")
    def test_exchange_code(self, mock_post):
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                "access_token": "new_access",
                "refresh_token": "new_refresh",
                "expires_in": 3600,
            },
        )
        mock_post.return_value.raise_for_status = MagicMock()

        auth = self._make_auth()
        result = auth.exchange_code("auth_code_123", "realm_456")

        assert auth.access_token == "new_access"
        assert auth.refresh_token == "new_refresh"
        assert auth.realm_id == "realm_456"
        assert result["access_token"] == "new_access"

    @patch("quickbooks_api.auth.requests.post")
    def test_refresh_access_token(self, mock_post):
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                "access_token": "refreshed_access",
                "refresh_token": "refreshed_refresh",
                "expires_in": 3600,
            },
        )
        mock_post.return_value.raise_for_status = MagicMock()

        auth = self._make_auth()
        auth.refresh_token = "old_refresh"
        result = auth.refresh_access_token()

        assert auth.access_token == "refreshed_access"
        assert auth.refresh_token == "refreshed_refresh"

    def test_refresh_access_token_no_refresh_token(self):
        auth = self._make_auth()
        auth.refresh_token = None
        with pytest.raises(AuthenticationError, match="No refresh token"):
            auth.refresh_access_token()

    def test_ensure_valid_token_not_authenticated(self):
        auth = self._make_auth()
        auth.access_token = None
        with pytest.raises(AuthenticationError, match="Not authenticated"):
            auth.ensure_valid_token()

    def test_ensure_valid_token_returns_current(self):
        auth = self._make_auth()
        auth.access_token = "valid_token"
        auth.token_expiry = time.time() + 3600
        assert auth.ensure_valid_token() == "valid_token"

    @patch("quickbooks_api.auth.requests.post")
    def test_ensure_valid_token_refreshes_expired(self, mock_post):
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                "access_token": "fresh_token",
                "refresh_token": "fresh_refresh",
                "expires_in": 3600,
            },
        )
        mock_post.return_value.raise_for_status = MagicMock()

        auth = self._make_auth()
        auth.access_token = "expired_token"
        auth.refresh_token = "old_refresh"
        auth.token_expiry = time.time() - 100  # expired

        token = auth.ensure_valid_token()
        assert token == "fresh_token"

    def test_get_auth_header(self):
        auth = self._make_auth()
        auth.access_token = "my_token"
        auth.token_expiry = time.time() + 3600
        headers = auth.get_auth_header()
        assert headers == {"Authorization": "Bearer my_token"}

    def test_set_tokens(self):
        auth = self._make_auth()
        auth.set_tokens("at", "rt", "realm", 99999999999.0)
        assert auth.access_token == "at"
        assert auth.refresh_token == "rt"
        assert auth.realm_id == "realm"
        assert auth.token_expiry == 99999999999.0
