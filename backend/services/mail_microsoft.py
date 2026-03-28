"""
Microsoft Graph mail: OAuth token exchange, refresh, draft creation, send.
"""

from __future__ import annotations

from typing import Any

import httpx

from config import settings

GRAPH_BASE = "https://graph.microsoft.com/v1.0"
TOKEN_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
AUTH_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/authorize"

# Mail.ReadWrite: drafts in mailbox; Mail.Send: send in one call. offline_access: refresh token.
SCOPES = "offline_access openid profile email User.Read Mail.ReadWrite Mail.Send"


def microsoft_oauth_configured() -> bool:
    return bool(
        settings.MICROSOFT_CLIENT_ID
        and settings.MICROSOFT_CLIENT_SECRET
        and settings.MICROSOFT_REDIRECT_URI
    )


def build_authorization_url(state: str) -> str:
    from urllib.parse import urlencode

    q = urlencode(
        {
            "client_id": settings.MICROSOFT_CLIENT_ID,
            "response_type": "code",
            "redirect_uri": settings.MICROSOFT_REDIRECT_URI,
            "response_mode": "query",
            "scope": SCOPES,
            "state": state,
        }
    )
    return f"{AUTH_URL}?{q}"


async def exchange_code_for_tokens(code: str) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(
            TOKEN_URL,
            data={
                "client_id": settings.MICROSOFT_CLIENT_ID,
                "client_secret": settings.MICROSOFT_CLIENT_SECRET,
                "code": code,
                "redirect_uri": settings.MICROSOFT_REDIRECT_URI,
                "grant_type": "authorization_code",
                "scope": SCOPES,
            },
        )
        r.raise_for_status()
        return r.json()


async def refresh_access_token(refresh_token: str) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(
            TOKEN_URL,
            data={
                "client_id": settings.MICROSOFT_CLIENT_ID,
                "client_secret": settings.MICROSOFT_CLIENT_SECRET,
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "scope": SCOPES,
            },
        )
        r.raise_for_status()
        return r.json()


async def graph_get_me(access_token: str) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.get(
            f"{GRAPH_BASE}/me",
            headers={"Authorization": f"Bearer {access_token}"},
            params={"$select": "mail,userPrincipalName"},
        )
        r.raise_for_status()
        return r.json()


def _message_payload(
    subject: str,
    html_body: str,
    to_address: str | None,
) -> dict[str, Any]:
    msg: dict[str, Any] = {
        "subject": subject,
        "body": {"contentType": "HTML", "content": html_body},
        "toRecipients": (
            [{"emailAddress": {"address": to_address.strip()}}]
            if to_address
            else []
        ),
    }
    return msg


async def create_draft(
    access_token: str,
    subject: str,
    html_body: str,
    to_address: str | None,
) -> dict[str, Any]:
    payload = _message_payload(subject, html_body, to_address)
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(
            f"{GRAPH_BASE}/me/messages",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        r.raise_for_status()
        return r.json()


async def send_mail_now(
    access_token: str,
    subject: str,
    html_body: str,
    to_address: str,
) -> None:
    message = _message_payload(subject, html_body, to_address)
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(
            f"{GRAPH_BASE}/me/sendMail",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            json={"message": message, "saveToSentItems": True},
        )
        r.raise_for_status()


def negotiation_email_html(
    obligation_description: str,
    amount: float,
    days_to_due: int,
    extra_note: str | None,
) -> str:
    note = extra_note or ""
    return f"""<html><body style="font-family:Segoe UI,Roboto,sans-serif;font-size:14px;color:#222;">
<p>Dear Sir/Madam,</p>
<p>Regarding <strong>{obligation_description}</strong> (amount <strong>₹{amount:,.0f}</strong>, due in <strong>{days_to_due}</strong> day(s)), we would like to discuss a possible extension or revised payment schedule that works for both parties.</p>
<p>Please let us know your availability for a brief discussion, or reply with terms that would be acceptable on your side.</p>
{f"<p>{note}</p>" if note else ""}
<p>Thank you,<br/>[Your name]</p>
</body></html>"""


def negotiation_subject(obligation_description: str) -> str:
    return f"Payment extension / negotiation — {obligation_description[:80]}"
