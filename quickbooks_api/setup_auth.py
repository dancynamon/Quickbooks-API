#!/usr/bin/env python3
"""Interactive setup script to authenticate with QuickBooks Online."""

import os
import sys

from dotenv import load_dotenv

from quickbooks_api.auth import QuickBooksAuth


def main():
    load_dotenv()

    client_id = os.environ.get("QBO_CLIENT_ID", "")
    client_secret = os.environ.get("QBO_CLIENT_SECRET", "")
    redirect_uri = os.environ.get("QBO_REDIRECT_URI", "http://localhost:8080/callback")
    environment = os.environ.get("QBO_ENVIRONMENT", "sandbox")

    if not client_id or not client_secret:
        print("Error: Set QBO_CLIENT_ID and QBO_CLIENT_SECRET in your .env file first.")
        print("Get credentials at: https://developer.intuit.com/app/developer/dashboard")
        sys.exit(1)

    auth = QuickBooksAuth(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        environment=environment,
    )

    print(f"Environment: {environment}")
    print(f"Redirect URI: {redirect_uri}")
    print("\nStarting OAuth flow...\n")

    try:
        token_data = auth.run_local_auth_flow()
        print(f"\nAuthentication successful!")
        print(f"Realm ID: {auth.realm_id}")
        print(f"Tokens saved to: {auth.token_file}")
        print(f"\nYou can now run the MCP server with: qbo-mcp-server")
    except Exception as e:
        print(f"\nAuthentication failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
