"""
Authentication endpoints.

POST /login — validates phone + password, returns a JWT access token.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.user import User
from schemas.user import LoginRequest, TokenResponse
from services.auth import create_access_token, verify_password

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    """
    Authenticate a user by phone number and password.

    Returns a JWT access token on success.
    """
    # Look up user by phone
    result = await db.execute(select(User).where(User.phone == request.phone))
    user = result.scalar_one_or_none()

    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid phone number or password",
        )

    # Generate JWT
    token = create_access_token(user.id)

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user_id=user.id,
    )
