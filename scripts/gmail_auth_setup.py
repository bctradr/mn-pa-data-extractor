"""
One-time Gmail OAuth setup script.
Run this locally to generate a refresh token for the Water Bill Tracker.
Outputs client_id, client_secret, and refresh_token for Streamlit Cloud secrets.

DO NOT commit gmail_credentials.json or gmail_token.json to git.
"""

import json
from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly",
]

CREDENTIALS_FILE = Path(__file__).parent.parent / "gmail_credentials.json"
TOKEN_FILE = Path(__file__).parent.parent / "gmail_token.json"


def main():
    if not CREDENTIALS_FILE.exists():
        raise FileNotFoundError(
            f"Credentials file not found at {CREDENTIALS_FILE}\n"
            "Download your OAuth Desktop client JSON from Google Cloud Console and place it there."
        )

    flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), SCOPES)
    creds = flow.run_local_server(port=0)

    token_data = {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": list(creds.scopes) if creds.scopes else SCOPES,
    }
    TOKEN_FILE.write_text(json.dumps(token_data, indent=2))

    with open(CREDENTIALS_FILE) as f:
        raw = json.load(f)
    client_info = raw.get("installed") or raw.get("web") or {}

    print("\n" + "=" * 60)
    print("OAuth complete. Copy these into Streamlit Cloud secrets:")
    print("=" * 60)
    print(f"GMAIL_CLIENT_ID     = {client_info.get('client_id', creds.client_id)!r}")
    print(f"GMAIL_CLIENT_SECRET = {client_info.get('client_secret', creds.client_secret)!r}")
    print(f"GMAIL_REFRESH_TOKEN = {creds.refresh_token!r}")
    print("=" * 60)
    print(f"\nFull token also saved to: {TOKEN_FILE}")


if __name__ == "__main__":
    main()
