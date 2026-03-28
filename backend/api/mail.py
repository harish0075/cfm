"""
Microsoft 365 OAuth for negotiation email drafts and sends (Microsoft Graph).
"""

from datetime import datetime, timezone
from urllib.parse import quote

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user
from config import allowed_mail_oauth_origins, settings
from database import get_db
from models.mail_connection import MailConnection
from models.user import User
from schemas.mail import (
    MailAuthorizeResponse,
    MailStatusResponse,
    NegotiationMailRequest,
    NegotiationMailResponse,
)
from services.auth import create_oauth_state_token, decode_oauth_state_token
from services.mail_microsoft import (
    build_authorization_url,
    create_draft,
    exchange_code_for_tokens,
    graph_get_me,
    microsoft_oauth_configured,
    negotiation_email_html,
    negotiation_subject,
    refresh_access_token,
    send_mail_now,
)
from services.token_crypto import decrypt_token, encrypt_token

router = APIRouter(prefix="/mail", tags=["Mail"])


def _decisions_url(query: str, return_origin: str | None) -> str:
    base = (return_origin or settings.FRONTEND_BASE_URL).rstrip("/")
    return f"{base}/decisions{query}"


async def _get_connection(
    db: AsyncSession, user_id
) -> MailConnection | None:
    r = await db.execute(
        select(MailConnection).where(MailConnection.user_id == user_id)
    )
    return r.scalar_one_or_none()


async def _access_token_for_user(
    db: AsyncSession, conn: MailConnection
) -> str:
    refresh = decrypt_token(conn.encrypted_refresh_token)
    try:
        tok = await refresh_access_token(refresh)
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Mail session expired. Connect Microsoft 365 again.",
        ) from e
    new_refresh = tok.get("refresh_token")
    if new_refresh:
        conn.encrypted_refresh_token = encrypt_token(new_refresh)
        conn.updated_at = datetime.now(timezone.utc)
        await db.flush()
    access = tok.get("access_token")
    if not access:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not obtain access token from Microsoft.",
        )
    return access


@router.get("/microsoft/authorize", response_model=MailAuthorizeResponse)
async def microsoft_authorize(
    user: User = Depends(get_current_user),
    frontend_origin: str | None = Query(None, max_length=128),
):
    if not microsoft_oauth_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Microsoft mail is not configured (set MICROSOFT_CLIENT_ID and MICROSOFT_CLIENT_SECRET).",
        )
    return_origin = None
    if frontend_origin:
        fo = frontend_origin.strip().rstrip("/")
        if fo not in allowed_mail_oauth_origins():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="frontend_origin is not in the allowed list (must match the URL you use to open the app).",
            )
        return_origin = fo
    state = create_oauth_state_token(user.id, return_origin)
    return MailAuthorizeResponse(authorization_url=build_authorization_url(state))


@router.get("/microsoft/callback")
async def microsoft_callback(
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    error_description: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    user_id, return_origin = decode_oauth_state_token(state or "")

    if error:
        msg = quote(error_description or error)
        return RedirectResponse(
            url=_decisions_url(f"?mail_error={msg}", return_origin),
            status_code=302,
        )
    if not code or not state:
        return RedirectResponse(
            url=_decisions_url("?mail_error=missing_code_or_state", return_origin),
            status_code=302,
        )
    if user_id is None:
        return RedirectResponse(
            url=_decisions_url("?mail_error=invalid_state", return_origin),
            status_code=302,
        )

    if not microsoft_oauth_configured():
        return RedirectResponse(
            url=_decisions_url("?mail_error=not_configured", return_origin),
            status_code=302,
        )

    try:
        tokens = await exchange_code_for_tokens(code)
    except httpx.HTTPStatusError:
        return RedirectResponse(
            url=_decisions_url("?mail_error=token_exchange_failed", return_origin),
            status_code=302,
        )

    refresh = tokens.get("refresh_token")
    if not refresh:
        return RedirectResponse(
            url=_decisions_url("?mail_error=no_refresh_token", return_origin),
            status_code=302,
        )

    access = tokens.get("access_token", "")
    account_email = None
    try:
        if access:
            me = await graph_get_me(access)
            account_email = me.get("mail") or me.get("userPrincipalName")
    except httpx.HTTPError:
        pass

    result = await db.execute(select(User).where(User.id == user_id))
    owner = result.scalar_one_or_none()
    if owner is None:
        return RedirectResponse(
            url=_decisions_url("?mail_error=user_not_found", return_origin),
            status_code=302,
        )

    existing = await _get_connection(db, user_id)
    enc = encrypt_token(refresh)
    now = datetime.now(timezone.utc)
    if existing:
        existing.encrypted_refresh_token = enc
        existing.account_email = account_email
        existing.updated_at = now
    else:
        db.add(
            MailConnection(
                user_id=user_id,
                provider="microsoft",
                account_email=account_email,
                encrypted_refresh_token=enc,
                created_at=now,
                updated_at=now,
            )
        )
    await db.commit()

    return RedirectResponse(
        url=_decisions_url("?mail_connected=1", return_origin),
        status_code=302,
    )


@router.get("/status", response_model=MailStatusResponse)
async def mail_status(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    conn = await _get_connection(db, user.id)
    if not conn:
        return MailStatusResponse(connected=False)
    return MailStatusResponse(
        connected=True,
        provider=conn.provider,
        account_email=conn.account_email,
    )


@router.delete("/disconnect", status_code=status.HTTP_204_NO_CONTENT)
async def mail_disconnect(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    conn = await _get_connection(db, user.id)
    if conn:
        await db.execute(delete(MailConnection).where(MailConnection.user_id == user.id))
        await db.commit()


@router.post("/negotiation", response_model=NegotiationMailResponse)
async def send_negotiation_mail(
    body: NegotiationMailRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not microsoft_oauth_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Microsoft mail is not configured.",
        )
    conn = await _get_connection(db, user.id)
    if not conn:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Connect Microsoft 365 first (Decision page → Connect mail).",
        )
    if body.send_now:
        if not body.to_email or "@" not in body.to_email:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="A valid to_email is required to send immediately.",
            )

    access = await _access_token_for_user(db, conn)
    subject = negotiation_subject(body.obligation_description)
    html = negotiation_email_html(
        body.obligation_description,
        body.amount,
        body.days_to_due,
        body.note,
    )
    to = body.to_email.strip() if body.to_email else None

    try:
        if body.send_now:
            await send_mail_now(access, subject, html, to or "")
            return NegotiationMailResponse(mode="sent", web_link=None)
        draft = await create_draft(access, subject, html, to)
        web = draft.get("webLink")
        return NegotiationMailResponse(mode="draft", web_link=web)
    except httpx.HTTPStatusError as e:
        detail = "Microsoft Graph request failed."
        try:
            detail = e.response.json().get("error", {}).get("message", detail)
        except Exception:
            pass
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=detail,
        ) from e
