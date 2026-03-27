"""Shared test fixtures for QuickBooks API tests."""

import json
import time
from unittest.mock import MagicMock, patch

import pytest

from quickbooks_api.auth import QuickBooksAuth
from quickbooks_api.client import QuickBooksClient


@pytest.fixture
def auth():
    """Create an auth instance with mock tokens (no file I/O)."""
    with patch.object(QuickBooksAuth, "_load_tokens"), \
         patch.object(QuickBooksAuth, "_save_tokens"):
        a = QuickBooksAuth(
            client_id="test_client_id",
            client_secret="test_client_secret",
            redirect_uri="http://localhost:8080/callback",
            environment="sandbox",
        )
        a.access_token = "test_access_token"
        a.refresh_token = "test_refresh_token"
        a.realm_id = "1234567890"
        a.token_expiry = time.time() + 3600
        return a


@pytest.fixture
def client(auth):
    """Create a QuickBooksClient with mocked auth."""
    return QuickBooksClient(auth)


@pytest.fixture
def mock_response():
    """Factory for creating mock HTTP responses."""
    def _make(status_code=200, json_data=None, text=""):
        resp = MagicMock()
        resp.status_code = status_code
        resp.json.return_value = json_data or {}
        resp.text = text or json.dumps(json_data or {})
        return resp
    return _make
