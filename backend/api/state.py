"""
User state and management endpoints.

GET  /state/{user_id}  — full financial state (balance, entries, assets)
POST /reset/{user_id}  — clear all financial entries and reset cash balance
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database import get_db
from models.asset import Asset
from models.financial_entry import FinancialEntry
from models.user import User
from api.deps import get_current_user
from schemas.entry import EntryResponse
from schemas.user import AssetResponse, UserStateResponse

router = APIRouter()


@router.get("/state/{user_id}", response_model=UserStateResponse)
async def get_user_state(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieve the complete financial state for a user.

    Returns:
        - Current cash balance
        - All normalized financial entries
        - All declared assets
    """
    # Eagerly load relationships to avoid lazy-loading issues in async
    result = await db.execute(
        select(User)
        .where(User.id == user_id)
        .options(selectinload(User.entries), selectinload(User.assets))
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Build entry list sorted by date (newest first)
    entries = sorted(user.entries, key=lambda e: e.date, reverse=True)

    return UserStateResponse(
        user_id=user.id,
        name=user.name,
        phone=user.phone,
        cash_balance=user.cash_balance,
        total_entries=len(entries),
        entries=[
            EntryResponse(
                id=e.id,
                type=e.type,
                amount=e.amount,
                date=e.date,
                source=e.source,
                description=e.description,
                confidence_score=e.confidence_score,
                risk_level=e.risk_level,
                flexibility=e.flexibility,
            )
            for e in entries
        ],
        assets=[
            AssetResponse(
                id=a.id,
                asset_type=a.asset_type,
                name=a.name,
                estimated_value=a.estimated_value,
                liquidity=a.liquidity,
            )
            for a in user.assets
        ],
    )


@router.post("/reset/{user_id}")
async def reset_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Reset a user's financial data.

    - Deletes all financial entries
    - Resets cash balance to 0
    - Keeps assets intact (they are baseline data from onboarding)
    """
    # Verify user exists
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Delete all financial entries for this user
    await db.execute(
        delete(FinancialEntry).where(FinancialEntry.user_id == user_id)
    )

    # Reset cash balance
    user.cash_balance = 0

    return {
        "message": f"User {user.name} data reset successfully",
        "user_id": str(user_id),
        "cash_balance": 0,
        "entries_deleted": True,
    }
