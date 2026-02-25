# Gmail API OAuth 2.0 Setup Guide

**Date:** 2026-02-09
**Purpose:** Epic 5 - B2B Outreach Email Integration
**Owner:** eshroom

---

## Overview

Gmail API allows sending emails programmatically using OAuth 2.0 authentication. This is required for Story 5-4 (Gmail API Integration) to send personalized B2B outreach emails.

## Prerequisites

- Google account (recommend using a dedicated business Gmail)
- Access to [Google Cloud Console](https://console.cloud.google.com/)
- Python 3.11+ installed

## Step-by-Step Setup

### 1. Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click project dropdown → "New Project"
3. Name: `DAWO-Email-Integration`
4. Click "Create"

### 2. Enable Gmail API

1. Go to **APIs & Services** → **Library**
2. Search for "Gmail API"
3. Click **Enable**

### 3. Configure OAuth Consent Screen

1. Go to **APIs & Services** → **OAuth consent screen**
2. Select **External** (or Internal if using Google Workspace)
3. Fill in required fields:
   - App name: `DAWO Email Integration`
   - User support email: your email
   - Developer contact: your email
4. Click **Save and Continue**
5. Add scopes:
   - `https://www.googleapis.com/auth/gmail.send` (required)
   - `https://www.googleapis.com/auth/gmail.readonly` (optional, for tracking)
6. Add test users (your email) while in testing mode
7. Click **Save and Continue**

### 4. Create OAuth 2.0 Credentials

1. Go to **APIs & Services** → **Credentials**
2. Click **Create Credentials** → **OAuth client ID**
3. Application type: **Desktop App** (for initial testing)
4. Name: `DAWO CLI`
5. Click **Create**
6. Click **Download JSON**
7. Save as `credentials/gmail_credentials.json` in project

### 5. Install Python Dependencies

```bash
pip install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib
```

Or add to `requirements.txt`:
```
google-api-python-client>=2.0.0
google-auth-httplib2>=0.1.0
google-auth-oauthlib>=1.0.0
```

### 6. First-Time Authentication

Run this script to generate `token.json`:

```python
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from pathlib import Path

SCOPES = ['https://www.googleapis.com/auth/gmail.send']

def get_gmail_credentials():
    """Get or refresh Gmail API credentials."""
    creds = None
    token_path = Path('credentials/gmail_token.json')
    creds_path = Path('credentials/gmail_credentials.json')

    # Load existing token
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    # Refresh or create new credentials
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(creds_path), SCOPES
            )
            creds = flow.run_local_server(port=0)

        # Save token for future runs
        token_path.write_text(creds.to_json())

    return creds

if __name__ == '__main__':
    creds = get_gmail_credentials()
    print("Gmail credentials obtained successfully!")
```

Run this once to complete OAuth flow in browser.

## File Structure

```
credentials/
├── gmail_credentials.json  # Downloaded from Google Cloud (DO NOT COMMIT)
├── gmail_token.json        # Generated after first auth (DO NOT COMMIT)
└── .gitignore              # Ensure these files are ignored
```

Add to `.gitignore`:
```
credentials/gmail_credentials.json
credentials/gmail_token.json
```

## Required Scopes

| Scope | Purpose |
|-------|---------|
| `gmail.send` | Send emails on behalf of user |
| `gmail.readonly` | Read emails (for tracking replies) |
| `gmail.modify` | Mark as read, archive (optional) |
| `gmail.labels` | Manage labels (optional) |

**Minimum for Epic 5:** `gmail.send` only

## Rate Limits

| Limit | Value |
|-------|-------|
| Daily sending limit | 500 emails/day (free Gmail) |
| Daily sending limit | 2,000 emails/day (Workspace) |
| Bandwidth limit | 128 MB/request |
| Concurrent requests | 10 per user |

## Verification for Production

For production use (>100 users or sensitive scopes):

1. Submit app for Google verification
2. Provide privacy policy URL
3. Demonstrate OAuth usage
4. Wait for review (can take weeks)

**For DAWO.ECO:** Internal use only, verification not required if staying under 100 users.

## Testing the Setup

```python
from googleapiclient.discovery import build
import base64
from email.mime.text import MIMEText

def send_test_email(creds):
    """Send a test email."""
    service = build('gmail', 'v1', credentials=creds)

    message = MIMEText("Test email from DAWO.ECO Gmail integration")
    message['to'] = 'your-email@example.com'
    message['subject'] = 'DAWO Gmail API Test'

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    body = {'raw': raw}

    result = service.users().messages().send(userId='me', body=body).execute()
    print(f"Message sent! ID: {result['id']}")

# Run after getting credentials
creds = get_gmail_credentials()
send_test_email(creds)
```

## Security Checklist

- [ ] `credentials.json` NOT in version control
- [ ] `token.json` NOT in version control
- [ ] Using minimum required scopes
- [ ] Credentials stored securely (not in code)
- [ ] HTTPS for any web callbacks
- [ ] Token refresh implemented

## Next Steps for eshroom

1. [ ] Create Google Cloud project
2. [ ] Enable Gmail API
3. [ ] Configure OAuth consent screen
4. [ ] Download credentials.json to `credentials/`
5. [ ] Run first-time auth script
6. [ ] Test sending email
7. [ ] Mark Gmail API credentials task as Done

---

## Sources

- [Gmail API Python Quickstart - Google Developers](https://developers.google.com/workspace/gmail/api/quickstart/python)
- [OAuth 2.0 for Google APIs](https://developers.google.com/identity/protocols/oauth2)
- [Gmail API Authorization](https://developers.google.com/workspace/gmail/api/auth/web-server)
- [Gmail API Python Guide - PyTutorial](https://pytutorial.com/gmail-api-python-guide-for-automation/)
