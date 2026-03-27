"""QuickBooks Online OAuth 2.0 authentication handler."""

import base64
import json
import time
import threading
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

import requests


INTUIT_AUTH_URL = "https://appcenter.intuit.com/connect/oauth2"
INTUIT_TOKEN_URL = "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer"
INTUIT_REVOKE_URL = "https://developer.api.intuit.com/v2/oauth2/tokens/revoke"


class QuickBooksAuth:
    """Handles OAuth 2.0 authentication for QuickBooks Online API."""

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str = "http://localhost:8080/callback",
        environment: str = "sandbox",
        token_file: str | None = None,
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.environment = environment
        self.token_file = Path(token_file) if token_file else Path("tokens.json")

        self.access_token: str | None = None
        self.refresh_token: str | None = None
        self.realm_id: str | None = None
        self.token_expiry: float = 0
        self._lock = threading.Lock()

        self._load_tokens()

    @property
    def base_url(self) -> str:
        if self.environment == "production":
            return "https://quickbooks.api.intuit.com"
        return "https://sandbox-quickbooks.api.intuit.com"

    @property
    def is_authenticated(self) -> bool:
        return self.access_token is not None and self.realm_id is not None

    @property
    def is_token_expired(self) -> bool:
        return time.time() >= self.token_expiry - 60  # 60s buffer

    def get_authorization_url(self, scopes: list[str] | None = None) -> str:
        """Generate the OAuth 2.0 authorization URL."""
        if scopes is None:
            scopes = ["com.intuit.quickbooks.accounting"]

        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": " ".join(scopes),
            "state": "quickbooks_auth",
        }
        return f"{INTUIT_AUTH_URL}?{urllib.parse.urlencode(params)}"

    def exchange_code(self, auth_code: str, realm_id: str) -> dict:
        """Exchange authorization code for access and refresh tokens."""
        headers = {
            "Authorization": f"Basic {self._get_basic_auth()}",
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        }
        data = {
            "grant_type": "authorization_code",
            "code": auth_code,
            "redirect_uri": self.redirect_uri,
        }

        resp = requests.post(INTUIT_TOKEN_URL, headers=headers, data=data, timeout=30)
        resp.raise_for_status()
        token_data = resp.json()

        self.access_token = token_data["access_token"]
        self.refresh_token = token_data["refresh_token"]
        self.realm_id = realm_id
        self.token_expiry = time.time() + token_data.get("expires_in", 3600)

        self._save_tokens()
        return token_data

    def refresh_access_token(self) -> dict:
        """Refresh the access token using the refresh token."""
        if not self.refresh_token:
            raise AuthenticationError("No refresh token available. Please re-authorize.")

        headers = {
            "Authorization": f"Basic {self._get_basic_auth()}",
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        }
        data = {
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token,
        }

        resp = requests.post(INTUIT_TOKEN_URL, headers=headers, data=data, timeout=30)
        resp.raise_for_status()
        token_data = resp.json()

        with self._lock:
            self.access_token = token_data["access_token"]
            self.refresh_token = token_data["refresh_token"]
            self.token_expiry = time.time() + token_data.get("expires_in", 3600)

        self._save_tokens()
        return token_data

    def ensure_valid_token(self) -> str:
        """Return a valid access token, refreshing if needed."""
        with self._lock:
            if not self.access_token:
                raise AuthenticationError("Not authenticated. Run OAuth flow first.")
            if self.is_token_expired:
                pass  # Release lock before refresh
            else:
                return self.access_token

        self.refresh_access_token()
        return self.access_token

    def get_auth_header(self) -> dict[str, str]:
        """Return the authorization header with a valid token."""
        token = self.ensure_valid_token()
        return {"Authorization": f"Bearer {token}"}

    def revoke_token(self) -> None:
        """Revoke the current refresh token."""
        if not self.refresh_token:
            return

        headers = {
            "Authorization": f"Basic {self._get_basic_auth()}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        data = {"token": self.refresh_token}

        requests.post(INTUIT_REVOKE_URL, headers=headers, json=data, timeout=30)

        self.access_token = None
        self.refresh_token = None
        self.realm_id = None
        self.token_expiry = 0
        self._save_tokens()

    def run_local_auth_flow(self, scopes: list[str] | None = None, port: int = 8080) -> dict:
        """Run a local OAuth flow with a temporary HTTP server to capture the callback."""
        auth_url = self.get_authorization_url(scopes)
        print(f"\nOpen this URL in your browser to authorize:\n\n{auth_url}\n")

        result = {}

        class CallbackHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                query = urllib.parse.urlparse(self.path).query
                params = urllib.parse.parse_qs(query)
                if "code" in params and "realmId" in params:
                    result["code"] = params["code"][0]
                    result["realm_id"] = params["realmId"][0]
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html")
                    self.end_headers()
                    self.wfile.write(
                        b"<html><body><h2>Authorization successful!</h2>"
                        b"<p>You can close this window.</p></body></html>"
                    )
                else:
                    self.send_response(400)
                    self.send_header("Content-Type", "text/html")
                    self.end_headers()
                    self.wfile.write(b"<html><body><h2>Authorization failed.</h2></body></html>")

            def log_message(self, format, *args):
                pass  # Suppress logs

        server = HTTPServer(("localhost", port), CallbackHandler)
        server.timeout = 120
        server.handle_request()
        server.server_close()

        if "code" not in result:
            raise AuthenticationError("OAuth callback did not receive authorization code.")

        return self.exchange_code(result["code"], result["realm_id"])

    def set_tokens(
        self,
        access_token: str,
        refresh_token: str,
        realm_id: str,
        token_expiry: float | None = None,
    ) -> None:
        """Manually set tokens (useful when loading from environment variables)."""
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.realm_id = realm_id
        self.token_expiry = token_expiry or (time.time() + 3600)
        self._save_tokens()

    def _get_basic_auth(self) -> str:
        credentials = f"{self.client_id}:{self.client_secret}"
        return base64.b64encode(credentials.encode()).decode()

    def _save_tokens(self) -> None:
        data = {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "realm_id": self.realm_id,
            "token_expiry": self.token_expiry,
        }
        self.token_file.write_text(json.dumps(data, indent=2))

    def _load_tokens(self) -> None:
        if not self.token_file.exists():
            return
        try:
            data = json.loads(self.token_file.read_text())
            self.access_token = data.get("access_token")
            self.refresh_token = data.get("refresh_token")
            self.realm_id = data.get("realm_id")
            self.token_expiry = data.get("token_expiry", 0)
        except (json.JSONDecodeError, KeyError):
            pass


class AuthenticationError(Exception):
    """Raised when authentication fails."""
