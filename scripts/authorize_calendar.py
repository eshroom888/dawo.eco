"""Google Calendar API OAuth authentication setup.

Story 7-9, Task 8.1: One-time setup script for Calendar API credentials.
Follows the exact pattern from scripts/test_gmail_auth.py.

Run this script to:
1. Open browser for OAuth consent (first run)
2. Save refresh token for future runs
3. Verify token works by listing calendars

Usage:
    python scripts/authorize_calendar.py
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Calendar full read/write scope
SCOPES = ["https://www.googleapis.com/auth/calendar"]

# Paths — same OAuth client as Gmail, separate token file
CREDENTIALS_PATH = project_root / "credentials" / "google-oauth.json"
TOKEN_PATH = project_root / "credentials" / "calendar_token.json"


def get_calendar_credentials() -> Credentials:
    """Get or refresh Calendar API credentials."""
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


def verify_calendar_access(creds: Credentials) -> bool:
    """Verify Calendar API access by listing user's calendars."""
    try:
        service = build("calendar", "v3", credentials=creds)

        # List calendars to verify access
        calendar_list = service.calendarList().list().execute()
        calendars = calendar_list.get("items", [])

        print(f"\nCalendar API access verified!")
        print(f"Token expiry: {creds.expiry}")
        print(f"Found {len(calendars)} calendars:")
        for cal in calendars[:5]:
            primary = " (PRIMARY)" if cal.get("primary") else ""
            print(f"  - {cal['summary']}{primary} [{cal['id']}]")

        # Check if DAWO calendar already exists
        dawo_cals = [c for c in calendars if "DAWO" in c.get("summary", "")]
        if dawo_cals:
            print(f"\nDAWO calendar found: {dawo_cals[0]['summary']}")
            print(f"  Calendar ID: {dawo_cals[0]['id']}")
            print(f"\n  Set this in your environment:")
            print(f'  GOOGLE_CALENDAR_ID="{dawo_cals[0]["id"]}"')
        else:
            print("\nNo DAWO calendar found yet.")
            print("It will be auto-created on first sync.")

        return True
    except Exception as e:
        print(f"\nCalendar API connection failed: {e}")
        return False


if __name__ == "__main__":
    print("=" * 50)
    print("Google Calendar API Authentication Setup")
    print("=" * 50)

    if not CREDENTIALS_PATH.exists():
        print(f"\nError: Credentials file not found at {CREDENTIALS_PATH}")
        print("Download google-oauth.json from Google Cloud Console")
        print("and place it in the credentials/ directory.")
        sys.exit(1)

    print(f"\nCredentials: {CREDENTIALS_PATH}")
    print(f"Token: {TOKEN_PATH}")

    creds = get_calendar_credentials()

    if verify_calendar_access(creds):
        print("\n" + "=" * 50)
        print("SUCCESS: Google Calendar API is ready!")
        print("=" * 50)
    else:
        print("\n" + "=" * 50)
        print("FAILED: Check error above")
        print("=" * 50)
        sys.exit(1)
