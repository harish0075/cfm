"""
User onboarding endpoint.

POST /onboard — creates a new user with initial cash balance and assets.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends, HTTPException

from database import get_db
from models.user import User
from models.asset import Asset
from schemas.user import OnboardRequest, OnboardResponse, AssetResponse

router = APIRouter()


@router.post("/onboard", response_model=OnboardResponse, status_code=201)
async def onboard_user(request: OnboardRequest, db: AsyncSession = Depends(get_db)):
    """
    Onboard a new user with their initial financial profile.

    - Creates the user record with name, phone, and starting cash balance
    - Stores all declared assets (house, vehicles, gold, others)
    - Assets are stored as last-resort liquidity fallbacks (not actively used yet)

    Returns the created user profile with their assigned UUID.
    """
    # ── Check for duplicate phone number ──────────────────────────────────────
    existing = await db.execute(select(User).where(User.phone == request.phone))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail=f"User with phone {request.phone} already exists",
        )

    # ── Create user ───────────────────────────────────────────────────────────
    user = User(
        name=request.name,
        phone=request.phone,
        cash_balance=request.cash_balance,
    )
    db.add(user)
    await db.flush()  # Get the user.id before creating assets

    # ── Create assets ─────────────────────────────────────────────────────────
    asset_models = []
    for asset_data in request.assets:
        asset = Asset(
            user_id=user.id,
            asset_type=asset_data.asset_type,
            name=asset_data.name,
            estimated_value=asset_data.estimated_value,
            liquidity=asset_data.liquidity,
        )
        db.add(asset)
        asset_models.append(asset)

    await db.flush()  # Ensure assets get IDs

    # ── Build response ────────────────────────────────────────────────────────
    return OnboardResponse(
        user_id=user.id,
        name=user.name,
        phone=user.phone,
        cash_balance=user.cash_balance,
        assets=[
            AssetResponse(
                id=a.id,
                asset_type=a.asset_type,
                name=a.name,
                estimated_value=a.estimated_value,
                liquidity=a.liquidity,
            )
            for a in asset_models
        ],
        message="User onboarded successfully",
    )
