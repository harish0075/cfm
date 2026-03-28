"""
Authentication service.

Handles password hashing (bcrypt) and JWT token creation / verification.
"""

from datetime import datetime, timedelta, timezone
from uuid import UUID

from jose import JWTError, jwt
import bcrypt

from config import settings


def hash_password(plain: str) -> str:
    """Hash a plain-text password using bcrypt."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(plain.encode('utf-8'), salt).decode('utf-8')


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plain-text password against its bcrypt hash."""
    return bcrypt.checkpw(plain.encode('utf-8'), hashed.encode('utf-8'))


# ── JWT tokens ────────────────────────────────────────────────────────────────

def create_access_token(user_id: UUID, expires_delta: timedelta | None = None) -> str:
    """
    Create a signed JWT containing the user's ID.

    Default expiry: 24 hours (configurable via settings).
    """
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(hours=24)
    )
    payload = {
        "sub": str(user_id),
        "exp": expire,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> UUID | None:
    """
    Decode and validate a JWT.  Returns the user UUID or None if invalid.
    """
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        user_id_str: str | None = payload.get("sub")
        if user_id_str is None:
            return None
        return UUID(user_id_str)
    except (JWTError, ValueError):
        return None


# ── OAuth CSRF state (Microsoft mail, etc.) ───────────────────────────────────

OAUTH_STATE_TTL = timedelta(minutes=10)


def create_oauth_state_token(
    user_id: UUID,
    return_origin: str | None = None,
) -> str:
    """
    Short-lived JWT used as OAuth `state` to bind the callback to a user.
    Optional return_origin (e.g. http://localhost:5173) so the browser returns to the same origin as the SPA.
    """
    expire = datetime.now(timezone.utc) + OAUTH_STATE_TTL
    payload: dict = {
        "sub": str(user_id),
        "exp": expire,
        "typ": "oauth_state",
    }
    if return_origin:
        payload["fro"] = return_origin[:128]
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_oauth_state_token(token: str) -> tuple[UUID | None, str | None]:
    """Returns (user_id, return_origin); return_origin may be None for older state tokens."""
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        if payload.get("typ") != "oauth_state":
            return None, None
        uid = UUID(payload["sub"])
        fro = payload.get("fro")
        origin = fro.strip().rstrip("/") if isinstance(fro, str) else None
        return uid, origin
    except (JWTError, ValueError, TypeError):
        return None, None
