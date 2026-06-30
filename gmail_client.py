"""
gmail_client.py
═══════════════
Gmail API transport layer for the Water Bill Tracker.

Credentials are read exclusively from st.secrets — never from local files.
Required secrets (set in Streamlit Cloud):
    GMAIL_CLIENT_ID
    GMAIL_CLIENT_SECRET
    GMAIL_REFRESH_TOKEN

If any secret is missing, functions raise RuntimeError with a clear message
rather than falling back to mock behaviour.
"""

import base64
from datetime import datetime
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email import encoders

import streamlit as st
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

_SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly",
]
_TOKEN_URI = "https://oauth2.googleapis.com/token"
_USER = "me"


def _get_service():
    required = ("GMAIL_CLIENT_ID", "GMAIL_CLIENT_SECRET", "GMAIL_REFRESH_TOKEN")
    missing = [k for k in required if k not in st.secrets]
    if missing:
        raise RuntimeError(
            f"Gmail not configured. Missing Streamlit secrets: {', '.join(missing)}. "
            "Add them in the Streamlit Cloud dashboard under App secrets."
        )
    creds = Credentials(
        token=None,
        refresh_token=st.secrets["GMAIL_REFRESH_TOKEN"],
        token_uri=_TOKEN_URI,
        client_id=st.secrets["GMAIL_CLIENT_ID"],
        client_secret=st.secrets["GMAIL_CLIENT_SECRET"],
        scopes=_SCOPES,
    )
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


def send_email(
    to: str,
    subject: str,
    body: str,
    attachment_bytes: bytes = None,
    attachment_filename: str = None,
) -> str:
    """Send an email via Gmail. Returns the sent Gmail message ID."""
    service = _get_service()

    if attachment_bytes and attachment_filename:
        msg = MIMEMultipart()
        msg.attach(MIMEText(body, "plain"))
        part = MIMEBase("application", "octet-stream")
        part.set_payload(attachment_bytes)
        encoders.encode_base64(part)
        part["Content-Disposition"] = f'attachment; filename="{attachment_filename}"'
        msg.attach(part)
    else:
        msg = MIMEText(body, "plain")

    msg["To"] = to
    msg["Subject"] = subject

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    result = service.users().messages().send(
        userId=_USER, body={"raw": raw}
    ).execute()
    return result["id"]


def check_inbox(since_timestamp: str, from_email: str = None) -> list:
    """Search Gmail inbox for messages received since since_timestamp.

    Args:
        since_timestamp: ISO-format UTC string (e.g. from Supabase updated_at).
        from_email:      Optional sender address filter.

    Returns list of dicts: {id, from, subject, date, body, has_attachments}.
    """
    service = _get_service()

    query_parts = ["in:inbox"]
    if since_timestamp:
        try:
            dt = datetime.fromisoformat(since_timestamp.replace("Z", "+00:00"))
            query_parts.append(f"after:{dt.strftime('%Y/%m/%d')}")
        except (ValueError, AttributeError):
            pass
    if from_email:
        query_parts.append(f"from:{from_email}")

    try:
        list_result = service.users().messages().list(
            userId=_USER,
            q=" ".join(query_parts),
            maxResults=20,
        ).execute()
    except HttpError as e:
        raise RuntimeError(f"Gmail API error listing messages: {e}") from e

    results = []
    for ref in list_result.get("messages", []):
        try:
            msg = service.users().messages().get(
                userId=_USER, id=ref["id"], format="full"
            ).execute()
            headers = {
                h["name"]: h["value"]
                for h in (msg.get("payload") or {}).get("headers", [])
            }
            body_text = _extract_body(msg.get("payload") or {})
            has_attachments = any(
                p.get("filename")
                for p in _iter_parts(msg.get("payload") or {})
            )
            results.append({
                "id": msg["id"],
                "from": headers.get("From", ""),
                "subject": headers.get("Subject", ""),
                "date": headers.get("Date", ""),
                "body": body_text,
                "has_attachments": has_attachments,
            })
        except HttpError:
            continue

    return results


def _extract_body(payload: dict) -> str:
    if payload.get("mimeType") == "text/plain":
        data = (payload.get("body") or {}).get("data", "")
        if data:
            return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
    for part in _iter_parts(payload):
        if part.get("mimeType") == "text/plain":
            data = (part.get("body") or {}).get("data", "")
            if data:
                return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
    return ""


def _iter_parts(payload: dict):
    for part in payload.get("parts", []):
        yield part
        yield from _iter_parts(part)
