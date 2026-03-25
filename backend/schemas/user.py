"""
Pydantic schemas for user onboarding and state retrieval.
"""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ── Asset Schemas ─────────────────────────────────────────────────────────────

class AssetCreate(BaseModel):
    """Schema for creating an asset during user onboarding."""

    asset_type: str = Field(
        ..., description="Type of asset: house, vehicle, gold, other"
    )
    name: Optional[str] = Field(None, description="Human-readable asset name")
    estimated_value: Decimal = Field(
        ..., gt=0, description="Estimated market value of the asset"
    )
    liquidity: str = Field(
        ..., description="How quickly asset can be liquidated: low, medium, high"
    )


class AssetResponse(BaseModel):
    """Schema for returning asset data."""

    id: UUID
    asset_type: str
    name: Optional[str]
    estimated_value: Decimal
    liquidity: str

    model_config = {"from_attributes": True}


# ── User Schemas ──────────────────────────────────────────────────────────────

class OnboardRequest(BaseModel):
    """Schema for the POST /onboard request body."""

    name: str = Field(..., min_length=1, description="User's full name")
    phone: str = Field(
        ..., min_length=10, max_length=15, description="Unique phone number"
    )
    password: str = Field(
        ..., min_length=6, description="Account password (min 6 characters)"
    )
    cash_balance: Decimal = Field(
        ..., ge=0, description="Initial cash balance"
    )
    assets: List[AssetCreate] = Field(
        default_factory=list, description="List of assets the user owns"
    )


class OnboardResponse(BaseModel):
    """Schema for the POST /onboard response."""

    user_id: UUID
    name: str
    phone: str
    cash_balance: Decimal
    assets: List[AssetResponse]
    message: str = "User onboarded successfully"

    model_config = {"from_attributes": True}


# ── Authentication Schemas ────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    """Schema for POST /login."""

    phone: str = Field(..., min_length=10, max_length=15, description="Registered phone number")
    password: str = Field(..., min_length=1, description="Account password")


class TokenResponse(BaseModel):
    """Schema for POST /login response — JWT access token."""

    access_token: str
    token_type: str = "bearer"
    user_id: UUID


from schemas.entry import EntryResponse


class UserStateResponse(BaseModel):
    """Schema for GET /state/{user_id} — full financial state of a user."""

    user_id: UUID
    name: str
    phone: str
    cash_balance: Decimal
    total_entries: int
    entries: List[EntryResponse]  # all entries (backward compat)
    inflows: List[EntryResponse]  # past/recorded inflows
    outflows: List[EntryResponse]  # past/recorded outflows
    future_payments: List[EntryResponse]  # future outflows (payables)
    assets: List[AssetResponse]

    model_config = {"from_attributes": True}
