"""Test Gmail API OAuth authentication.

Run this script to verify Gmail API credentials work.
It will open a browser for OAuth consent on first run.
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Gmail send scope
SCOPES = ['https://www.googleapis.com/auth/gmail.send']

# Paths
CREDENTIALS_PATH = project_root / 'credentials' / 'google-oauth.json'
TOKEN_PATH = project_root / 'credentials' / 'gmail-token.json'


def get_gmail_credentials() -> Credentials:
    """Get or refresh Gmail API credentials."""
    creds = None

    # Load existing token
    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
        print(f"Loaded existing token from {TOKEN_PATH}")

    # Refresh or create new credentials
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Refreshing expired token...")
            creds.refresh(Request())
        else:
            print(f"Starting OAuth flow with {CREDENTIALS_PATH}...")
            flow = InstalledAppFlow.from_client_secrets_file(
                str(CREDENTIALS_PATH), SCOPES
            )
            creds = flow.run_local_server(port=0)

        # Save token for future runs
        TOKEN_PATH.write_text(creds.to_json())
        print(f"Token saved to {TOKEN_PATH}")

    return creds


def test_gmail_connection(creds: Credentials) -> bool:
    """Test Gmail API connection."""
    try:
        # Just verify we can build the service with valid credentials
        service = build('gmail', 'v1', credentials=creds)

        # Check token is valid
        if creds.valid:
            print(f"\nGmail API credentials valid!")
            print(f"Token expiry: {creds.expiry}")
            print(f"Scopes: {creds.scopes}")
            return True
        else:
            print(f"\nCredentials not valid")
            return False
    except Exception as e:
        print(f"\nGmail API connection failed: {e}")
        return False


if __name__ == '__main__':
    print("=" * 50)
    print("Gmail API Authentication Test")
    print("=" * 50)

    if not CREDENTIALS_PATH.exists():
        print(f"\nError: Credentials file not found at {CREDENTIALS_PATH}")
        sys.exit(1)

    print(f"\nCredentials: {CREDENTIALS_PATH}")
    print(f"Token: {TOKEN_PATH}")

    creds = get_gmail_credentials()

    if test_gmail_connection(creds):
        print("\n" + "=" * 50)
        print("SUCCESS: Gmail API is ready for Epic 5!")
        print("=" * 50)
    else:
        print("\n" + "=" * 50)
        print("FAILED: Check error above")
        print("=" * 50)
        sys.exit(1)
