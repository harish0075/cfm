"""
Pydantic schemas for financial entry inputs and responses.
"""

from datetime import date
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ── Input Request Schemas ─────────────────────────────────────────────────────

class TextInputRequest(BaseModel):
    """Schema for POST /input — natural language text input."""

    user_id: UUID = Field(..., description="ID of the user")
    message: str = Field(..., min_length=1, description="Natural language financial message")


class SMSWebhookRequest(BaseModel):
    """Schema for POST /sms-webhook — simulated SMS message."""

    sender: str = Field(
        ..., min_length=10, description="Phone number of the sender (used as user lookup)"
    )
    message: str = Field(..., min_length=1, description="SMS text content")


# ── Entry Response Schemas ────────────────────────────────────────────────────

class EntryResponse(BaseModel):
    """Schema for a single normalized financial entry."""

    id: UUID
    type: str
    amount: Decimal
    date: date
    source: str
    description: Optional[str]
    confidence_score: Decimal
    risk_level: str
    flexibility: int
    is_recurring: int
    recurrence_interval: Optional[str]

    model_config = {"from_attributes": True}


class InputResponse(BaseModel):
    """Standard response returned by all input endpoints."""

    entry: EntryResponse
    total_entries: int
    cash_balance: Decimal


class BankStatementResponse(BaseModel):
    """Response for bank statement uploads (multiple entries)."""

    entries: List[EntryResponse]
    total_entries: int
    cash_balance: Decimal