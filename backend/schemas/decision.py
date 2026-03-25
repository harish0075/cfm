"""
Pydantic schemas for the Decision Engine API.
"""

from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ── Input Schemas ─────────────────────────────────────────────────────────────

class ObligationInput(BaseModel):
    """A single financial obligation to evaluate."""

    amount: Decimal = Field(..., gt=0, description="Obligation amount")
    due_date: date = Field(..., description="When this obligation is due")
    penalty_score: int = Field(
        ..., ge=0, le=10, description="Impact of missing payment (0–10)"
    )
    flexibility: int = Field(
        ..., ge=1, le=10, description="How adjustable this obligation is (1–10)"
    )
    relationship_score: int = Field(
        ..., ge=0, le=10, description="Importance of relationship (0–10)"
    )
    description: str = Field("", description="Human-readable description")
    is_recurring: int = Field(0, description="0=False, 1=True")
    recurrence_interval: Optional[str] = Field(None, description="'monthly', 'weekly', etc.")


class InflowInput(BaseModel):
    """An expected inflow of money."""

    amount: Decimal = Field(..., gt=0, description="Expected inflow amount")
    expected_date: date = Field(..., description="When the inflow is expected")
    confidence: float = Field(
        ..., ge=0, le=1, description="Confidence in the inflow (0–1)"
    )
    description: str = Field("", description="Source of inflow")


class DecisionRequest(BaseModel):
    """Request body for POST /decide."""

    user_id: UUID = Field(..., description="ID of the user")
    obligations: List[ObligationInput] = Field(
        ..., min_length=1, description="List of obligations to evaluate"
    )
    inflows: List[InflowInput] = Field(
        default_factory=list, description="Expected inflows (optional)"
    )


class SimulateRequest(BaseModel):
    """Request body for POST /simulate."""

    user_id: UUID = Field(..., description="ID of the user")
    outflows: List[ObligationInput] = Field(
        default_factory=list, description="Upcoming outflows / obligations"
    )
    inflows: List[InflowInput] = Field(
        default_factory=list, description="Expected inflows"
    )
    horizon_days: int = Field(
        90, ge=7, le=365, description="Number of days to simulate"
    )


# ── Response Schemas ──────────────────────────────────────────────────────────

class ProbabilityBreakdown(BaseModel):
    """Probability of each action."""
    pay: float
    delay: float


class ObligationDecision(BaseModel):
    """Decision result for a single obligation."""

    description: str
    amount: Decimal
    days_to_due: int
    action: str = Field(..., description="pay or delay")
    confidence: float
    reasoning: str
    probabilities: ProbabilityBreakdown
    action_suggestion: str


class DecisionPlan(BaseModel):
    """Shows the categorized plan of what to pay vs delay."""
    pay: List[ObligationDecision]
    delay: List[ObligationDecision]


class RunwayInfo(BaseModel):
    """Runway detection result."""

    runway_days: Optional[int] = Field(
        None, description="Days until cash runs out (None = safe)"
    )
    risk_level: str = Field(..., description="SAFE, WARNING, or CRITICAL")
    crash_date: Optional[str] = None
    minimum_balance: float
    minimum_balance_date: str


class TimelineDay(BaseModel):
    """A single day in the cash flow timeline."""
    date: str
    balance: float
    events: List[Dict[str, Any]] = Field(default_factory=list)

class DecisionResponse(BaseModel):
    """Full response from POST /decide."""

    balance: Decimal
    runway_days: Optional[int]
    risk_level: str
    timeline: List[TimelineDay]
    plan: DecisionPlan
    explanations: List[str]
    actions: List[str]
    alerts: List[str]
    summary: str



class SimulateResponse(BaseModel):
    """Response from POST /simulate."""

    timeline: List[TimelineDay]
    runway: RunwayInfo
    current_cash: Decimal
