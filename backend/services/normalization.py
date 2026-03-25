"""
Normalization service.

Converts raw parsed data (from any input source) into a FinancialEntry ORM
instance and persists it to the database.  Also handles cash balance updates.

This is the convergence point — all input sources (text, SMS, OCR, bank, audio)
feed through this service to produce a unified financial dataset.
"""

import uuid
from datetime import date
from decimal import Decimal
from typing import Dict

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.financial_entry import FinancialEntry
from models.user import User


def normalize_entry(
    user_id: uuid.UUID,
    parsed_data: Dict,
    source: str,
) -> FinancialEntry:
    """
    Convert a parsed data dict into a FinancialEntry ORM instance.

    Args:
        user_id:     UUID of the owning user
        parsed_data: Dict with keys: type, amount, date, description,
                     confidence_score, risk_level, flexibility
        source:      One of: text, sms, ocr, bank, audio

    Returns:
        A FinancialEntry instance (not yet committed to DB)
    """
    # Ensure date is a proper date object
    entry_date = parsed_data.get("date")
    if isinstance(entry_date, str):
        entry_date = date.fromisoformat(entry_date)
    elif not isinstance(entry_date, date):
        entry_date = date.today()

    return FinancialEntry(
        id=uuid.uuid4(),
        user_id=user_id,
        type=parsed_data.get("type", "outflow"),
        amount=Decimal(str(parsed_data.get("amount", 0))),
        date=entry_date,
        source=source,
        description=parsed_data.get("description", ""),
        confidence_score=Decimal(str(parsed_data.get("confidence_score", 0.9))),
        risk_level=parsed_data.get("risk_level", "low"),
        flexibility=parsed_data.get("flexibility", 5),
    )


async def update_cash_balance(
    db: AsyncSession,
    user_id: uuid.UUID,
    amount: Decimal,
    entry_type: str,
) -> Decimal:
    """
    Adjust the user's cash balance based on an inflow or outflow.

    Args:
        db:         Async DB session
        user_id:    UUID of the user
        amount:     Transaction amount
        entry_type: "inflow" or "outflow"

    Returns:
        The updated cash balance
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one()

    if entry_type == "inflow":
        user.cash_balance = user.cash_balance + amount
    else:
        user.cash_balance = user.cash_balance - amount

    return user.cash_balance


async def get_entry_count(db: AsyncSession, user_id: uuid.UUID) -> int:
    """Return the total number of financial entries for a user."""
    result = await db.execute(
        select(func.count(FinancialEntry.id)).where(
            FinancialEntry.user_id == user_id
        )
    )
    return result.scalar_one()


async def save_and_update(
    db: AsyncSession,
    user_id: uuid.UUID,
    parsed_data: Dict,
    source: str,
) -> Dict:
    """
    Full normalization pipeline:
        1. Create a FinancialEntry from parsed data
        2. Persist it to DB
        3. Update the user's cash balance
        4. Return entry + metadata for the API response

    Returns:
        {
            "entry": FinancialEntry,
            "total_entries": int,
            "cash_balance": Decimal,
        }
    """
    # Step 1: Normalize into ORM object
    entry = normalize_entry(user_id, parsed_data, source)

    # Step 2: Persist
    db.add(entry)
    await db.flush()  # Ensure the entry gets an ID before we count

    # Step 3: Update balance
    new_balance = await update_cash_balance(
        db, user_id, entry.amount, entry.type
    )

    # Step 4: Count total entries
    total = await get_entry_count(db, user_id)

    return {
        "entry": entry,
        "total_entries": total,
        "cash_balance": new_balance,
    }
