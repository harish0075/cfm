"""
Payment Gateway Mock API.

POST /pay — Deducts cash, records the outflow entry,
            AND removes the original future-payment entry so the
            simulation doesn't count it twice.
"""
import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.user import User
from models.financial_entry import FinancialEntry
from api.deps import get_current_user
from schemas.payment import PaymentRequest, PaymentResponse

router = APIRouter()


@router.post("/pay", response_model=PaymentResponse)
async def process_payment(
    request: PaymentRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Mock payment gateway.

    Steps:
    1. Verify sufficient funds.
    2. Deduct cash_balance.
    3. Delete the original *future* FinancialEntry (type=outflow, date > today)
       that matches this payment so the simulation does not count it again.
    4. Create a new *paid* outflow entry dated today for the audit trail.
    """
    today = date.today()

    if current_user.cash_balance < request.amount:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient funds. Balance: ₹{float(current_user.cash_balance):,.2f}",
        )

    # ── 1. Deduct balance ──────────────────────────────────────────────────────
    current_user.cash_balance -= request.amount

    # ── 2. Remove the matching future payment entry (if it exists) ─────────────
    # We match on user_id + type=outflow + date > today + amount (exact or close)
    # and description contains the original description text.
    future_entry = await db.execute(
        select(FinancialEntry).where(
            FinancialEntry.user_id == current_user.id,
            FinancialEntry.type == "outflow",
            FinancialEntry.date > today,
            FinancialEntry.amount == request.amount,
        ).limit(1)
    )
    original = future_entry.scalar_one_or_none()
    if original:
        await db.delete(original)

    # ── 3. Record the actual payment as a today-dated outflow ─────────────────
    paid_entry = FinancialEntry(
        user_id=current_user.id,
        type="outflow",
        amount=request.amount,
        date=today,
        description=f"Paid: {request.description}",
        confidence_score=1.0,
        risk_level="low",
        flexibility=1,
        source="text",
    )
    db.add(paid_entry)

    await db.commit()

    return PaymentResponse(
        success=True,
        transaction_id=f"pay_{uuid.uuid4().hex[:8]}",
        new_balance=float(current_user.cash_balance),
        message=f"Payment of ₹{float(request.amount):,.2f} for '{request.description}' processed successfully.",
    )
