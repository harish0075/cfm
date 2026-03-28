"""
Layer 3: PIPELINE ORCHESTRATOR
Provides the explicit 3-step extraction validation API.
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import get_db
from models.user import User
from models.financial_entry import FinancialEntry
import datetime
from typing import List

from pydantic import BaseModel

from services.ocr import extract_raw_ocr
from services.audio import extract_raw_audio
from services.parser import run_layer2_validation
from services.ocr import (
    _extract_amount_candidates, 
    _extract_date_candidates, 
    _extract_keywords, 
    _extract_party_name
)

router = APIRouter()

@router.post("/extract_raw")
async def extract_raw(
    file: UploadFile = File(None),
    text: str = Form(None)
):
    """
    LAYER 1: RAW EXTRACTION
    Accepts text, audio, or image. Returns candidate fields.
    """
    if file:
        content = await file.read()
        filename = file.filename.lower()
        if filename.endswith((".png", ".jpg", ".jpeg", ".pdf")):
            return extract_raw_ocr(content)
        elif filename.endswith((".wav", ".mp3", ".webm", ".m4a")):
            return extract_raw_audio(content)
        else:
            raise HTTPException(400, "Unsupported format")
    elif text:
        return {
            "raw_text": text,
            "amount_candidates": _extract_amount_candidates(text),
            "date_candidates": _extract_date_candidates(text),
            "keywords": _extract_keywords(text),
            "party": _extract_party_name(text)
        }
    raise HTTPException(400, "Provide file or text")


class ValidationPayload(BaseModel):
    raw_text: str
    amount_candidates: List[float]
    date_candidates: List[str]
    keywords: List[str]
    party: str

@router.post("/validate")
async def validate_data(payload: ValidationPayload):
    """
    LAYER 2: RULE-BASED VALIDATION
    Executes strict regex and mapping rules over candidates.
    """
    data = payload.dict()
    result = run_layer2_validation(data)
    return result


class FinalizePayload(BaseModel):
    user_id: str
    type: str # inflow/outflow
    amount: float
    date: str
    description: str
    party: str
    category: str
    confidence_score: float

@router.post("/finalize")
async def finalize_data(
    payload: FinalizePayload,
    db: AsyncSession = Depends(get_db)
):
    """
    LAYER 3: FINALIZATION & COMMIT
    Saves the strictly validated data to the database and updates balance.
    """
    user_result = await db.execute(select(User).where(User.id == payload.user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User not found")

    entry_date = datetime.date.fromisoformat(payload.date)
    desc_str = payload.description.strip()
    if payload.party and payload.party not in desc_str:
        desc_str = f"{payload.party} - {desc_str}"
        
    desc_str = f"[{payload.category.upper()}] {desc_str}"

    entry = FinancialEntry(
        user_id=user.id,
        type=payload.type,
        amount=payload.amount,
        date=entry_date,
        description=desc_str,
        source="pipeline",
        confidence_score=payload.confidence_score,
        risk_level="low",
        flexibility=5
    )
    db.add(entry)

    # Deterministic Cash Balance Update
    if entry_date <= datetime.date.today():
        if payload.type == "inflow":
            user.cash_balance += payload.amount
        elif payload.type == "outflow":
            user.cash_balance -= payload.amount

    await db.commit()
    await db.refresh(user)

    return {
        "message": "Finalized successfully",
        "entry_id": entry.id,
        "new_balance": user.cash_balance
    }
