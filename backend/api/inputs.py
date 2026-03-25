"""
Financial input endpoints.

All five input sources converge here:
    POST /input               — natural language text
    POST /sms-webhook         — simulated SMS
    POST /upload-receipt      — OCR receipt image
    POST /upload-bank-statement — PDF bank statement
    POST /audio               — audio file (mock transcription)

Each endpoint parses the input, normalizes it into a FinancialEntry,
updates the user's cash balance, and returns the structured result.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.user import User
from api.deps import get_current_user
from schemas.entry import (
    BankStatementResponse,
    EntryResponse,
    InputResponse,
    SMSWebhookRequest,
    TextInputRequest,
)
from services.audio import parse_audio_input
from services.bank_parser import parse_bank_statement
from services.normalization import save_and_update
from services.ocr import parse_receipt
from services.parser import parse_text_input

router = APIRouter()


# ── Helper ────────────────────────────────────────────────────────────────────

async def _get_user(db: AsyncSession, user_id: UUID) -> User:
    """Fetch a user or raise 404."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


async def _get_user_by_phone(db: AsyncSession, phone: str) -> User:
    """Fetch a user by phone number or raise 404."""
    result = await db.execute(select(User).where(User.phone == phone))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=404,
            detail=f"No user found with phone {phone}",
        )
    return user


def _build_entry_response(entry) -> EntryResponse:
    """Convert a FinancialEntry ORM instance to Pydantic response."""
    return EntryResponse(
        id=entry.id,
        type=entry.type,
        amount=entry.amount,
        date=entry.date,
        source=entry.source,
        description=entry.description,
        confidence_score=entry.confidence_score,
        risk_level=entry.risk_level,
        flexibility=entry.flexibility,
        is_recurring=getattr(entry, "is_recurring", 0),
        recurrence_interval=getattr(entry, "recurrence_interval", None),
    )


# ── A. TEXT INPUT ─────────────────────────────────────────────────────────────

@router.post("/input", response_model=InputResponse)
async def text_input(
    request: TextInputRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Process a natural language financial message.

    Examples:
        "Pay 20000 rent tomorrow"
        "Receive 30000 from client Friday"
        "Bought materials for 5000 today"

    The NLP parser extracts type, amount, date, risk, and flexibility,
    then normalizes and persists the entry.
    """
    # Verify user exists
    await _get_user(db, request.user_id)

    # Parse natural language
    parsed = parse_text_input(request.message)

    # Normalize, persist, and update balance
    result = await save_and_update(db, request.user_id, parsed, source="text")

    return InputResponse(
        entry=_build_entry_response(result["entry"]),
        total_entries=result["total_entries"],
        cash_balance=result["cash_balance"],
    )


# ── B. SMS WEBHOOK ────────────────────────────────────────────────────────────

@router.post("/sms-webhook", response_model=InputResponse)
async def sms_webhook(
    request: SMSWebhookRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Simulated SMS webhook.

    Receives a message from a phone number, looks up the user by phone,
    and processes exactly like text input.
    """
    # Look up user by phone number
    user = await _get_user_by_phone(db, request.sender)

    # Parse using same NLP parser as text input
    parsed = parse_text_input(request.message)

    # Normalize, persist, and update balance
    result = await save_and_update(db, user.id, parsed, source="sms")

    return InputResponse(
        entry=_build_entry_response(result["entry"]),
        total_entries=result["total_entries"],
        cash_balance=result["cash_balance"],
    )


# ── C. OCR INPUT (RECEIPT) ───────────────────────────────────────────────────

@router.post("/upload-receipt", response_model=InputResponse)
async def upload_receipt(
    user_id: UUID = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Upload a receipt image for OCR processing.

    Accepts common image formats (JPEG, PNG).
    Uses pytesseract to extract text, then parses amount, date, and vendor.
    Confidence score reflects extraction quality.
    """
    # Verify user exists
    await _get_user(db, user_id)

    # Read image bytes
    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Empty file uploaded")

    # OCR parse
    parsed = parse_receipt(image_bytes)

    # Remove raw_text before normalization (not stored in DB)
    parsed.pop("raw_text", None)

    # Normalize, persist, and update balance
    result = await save_and_update(db, user_id, parsed, source="ocr")

    return InputResponse(
        entry=_build_entry_response(result["entry"]),
        total_entries=result["total_entries"],
        cash_balance=result["cash_balance"],
    )


# ── D. BANK STATEMENT (PDF) ──────────────────────────────────────────────────

@router.post("/upload-bank-statement", response_model=BankStatementResponse)
async def upload_bank_statement(
    user_id: UUID = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Upload a PDF bank statement.

    Extracts all transactions from the statement, converts each to
    inflow/outflow entries, and updates the user's financial dataset.
    """
    # Verify user exists
    await _get_user(db, user_id)

    # Read PDF bytes
    pdf_bytes = await file.read()
    if not pdf_bytes:
        raise HTTPException(status_code=400, detail="Empty file uploaded")

    # Parse all transactions from the PDF
    transactions = parse_bank_statement(pdf_bytes)

    # Normalize and persist each transaction
    entries = []
    final_balance = None
    total = 0

    for txn in transactions:
        result = await save_and_update(db, user_id, txn, source="bank")
        entries.append(_build_entry_response(result["entry"]))
        final_balance = result["cash_balance"]
        total = result["total_entries"]

    return BankStatementResponse(
        entries=entries,
        total_entries=total,
        cash_balance=final_balance or 0,
    )


# ── E. AUDIO INPUT ───────────────────────────────────────────────────────────

@router.post("/audio", response_model=InputResponse)
async def audio_input(
    user_id: UUID = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Upload an audio file for transcription and processing.

    Currently uses mock transcription. The transcribed text is then
    parsed using the same NLP pipeline as text input.
    """
    # Verify user exists
    await _get_user(db, user_id)

    # Read audio bytes
    audio_bytes = await file.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Empty file uploaded")

    # Transcribe and parse
    parsed = parse_audio_input(audio_bytes, filename=file.filename or "audio.wav")

    # Remove transcript key before normalization (not a DB field)
    parsed.pop("transcript", None)

    # Normalize, persist, and update balance
    result = await save_and_update(db, user_id, parsed, source="audio")

    return InputResponse(
        entry=_build_entry_response(result["entry"]),
        total_entries=result["total_entries"],
        cash_balance=result["cash_balance"],
    )
