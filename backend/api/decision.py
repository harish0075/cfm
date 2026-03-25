"""
Decision Engine API endpoints.

POST /decide          — evaluate obligations and get pay/delay decisions
GET  /runway/{user_id} — get runway detection and risk level
POST /simulate        — get full cash flow timeline simulation
"""

from datetime import date
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database import get_db
from models.user import User
from models.financial_entry import FinancialEntry
from api.deps import get_current_user
from schemas.decision import (
    DecisionPlan,
    DecisionRequest,
    DecisionResponse,
    ObligationDecision,
    ProbabilityBreakdown,
    RunwayInfo,
    SimulateRequest,
    SimulateResponse,
    TimelineDay,
)
from services.decision_engine import evaluate_obligations
from services.simulation import detect_runway, simulate_cashflow

router = APIRouter()


# ── Helper ────────────────────────────────────────────────────────────────────

async def _get_user_with_entries(db: AsyncSession, user_id: UUID) -> User:
    """Fetch user with eagerly-loaded financial entries."""
    result = await db.execute(
        select(User)
        .where(User.id == user_id)
        .options(selectinload(User.entries))
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


def _entries_to_outflows(entries) -> list:
    """Convert future outflow FinancialEntry records to dicts."""
    today = date.today()
    return [
        {
            "amount": float(e.amount),
            "date": e.date.isoformat(),
            "description": e.description or "",
        }
        for e in entries
        if e.type == "outflow" and e.date >= today
    ]


def _entries_to_inflows(entries) -> list:
    """Convert future inflow FinancialEntry records to dicts."""
    today = date.today()
    return [
        {
            "amount": float(e.amount),
            "date": e.date.isoformat(),
            "description": e.description or "",
            "confidence": float(e.confidence_score),
        }
        for e in entries
        if e.type == "inflow" and e.date >= today
    ]


# ── A. DECISION ENDPOINT ─────────────────────────────────────────────────────

@router.post("/decide", response_model=DecisionResponse)
async def decide(
    request: DecisionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Evaluate financial obligations using the ML decision tree.

    Accepts a list of obligations with urgency/risk/flexibility metadata,
    plus optional expected inflows. Returns prioritized pay/delay decisions
    with reasoning, runway info, and a summary.
    """
    user = await _get_user_with_entries(db, request.user_id)
    current_cash = float(user.cash_balance)

    if current_cash <= 0:
        raise HTTPException(
            status_code=400,
            detail="Cash balance is zero or negative — cannot evaluate decisions",
        )

    # Prepare obligation dicts with days_to_due computed from due_date
    today = date.today()
    obligation_dicts = []
    for ob in request.obligations:
        days_to_due = (ob.due_date - today).days
        if days_to_due < 0:
            days_to_due = 0  # overdue
        obligation_dicts.append({
            "amount": float(ob.amount),
            "days_to_due": days_to_due,
            "penalty_score": ob.penalty_score,
            "flexibility": ob.flexibility,
            "relationship_score": ob.relationship_score,
            "description": ob.description,
        })

    # Prepare inflow dicts
    inflow_dicts = []
    for inf in request.inflows:
        inflow_dicts.append({
            "amount": float(inf.amount),
            "expected_date": inf.expected_date.isoformat(),
            "confidence": inf.confidence,
            "description": inf.description,
        })

    # Combine with existing DB entries for runway calculation
    db_outflows = _entries_to_outflows(user.entries)
    db_inflows = _entries_to_inflows(user.entries)

    all_outflows = db_outflows + [
        {"amount": float(o.amount), "date": o.due_date.isoformat(), "description": o.description}
        for o in request.obligations
    ]
    all_inflows = db_inflows + [
        {"amount": float(i.amount), "date": i.expected_date.isoformat(),
         "confidence": i.confidence, "description": i.description}
        for i in request.inflows
    ]

    # Detect runway
    runway_result = detect_runway(current_cash, all_outflows, all_inflows)
    runway_days = runway_result["runway_days"] if runway_result["runway_days"] is not None else 999

    # Run decision engine
    decisions = evaluate_obligations(
        obligations=obligation_dicts,
        current_cash=current_cash,
        runway_days=runway_days,
        inflows=inflow_dicts or None,
    )

    # Run simulation for timeline
    timeline = simulate_cashflow(
        current_cash, all_outflows, all_inflows or None, horizon_days=30
    )

    # Build response format
    total_obligations = sum(float(o.amount) for o in request.obligations)
    cash_deficit = max(0, total_obligations - current_cash)

    pay_decisions = []
    delay_decisions = []
    explanations = []
    actions = []

    for d in decisions:
        obs = ObligationDecision(
            description=d["description"],
            amount=Decimal(str(d["amount"])),
            days_to_due=d["days_to_due"],
            action=d["action"],
            confidence=d["confidence"],
            reasoning=d["reasoning"],
            probabilities=ProbabilityBreakdown(**d["probabilities"]),
            action_suggestion=d.get("action_suggestion", ""),
        )
        if d["action"] == "pay":
            pay_decisions.append(obs)
        else:
            delay_decisions.append(obs)
        
        explanations.append(f"{d['description']}: {d['reasoning']}")
        if d.get("action_suggestion"):
            actions.append(d["action_suggestion"])

    pay_count = len(pay_decisions)
    delay_count = len(delay_decisions)

    # Alerts
    alerts = []
    if runway_days <= 30:
        alerts.append(f"CRITICAL: Cash will run out in {runway_days} days!")
    elif cash_deficit > 0:
        alerts.append(f"WARNING: Cash deficit of ₹{cash_deficit:,.0f} detected.")

    # Generate summary
    if cash_deficit > 0:
        summary = (
            f"Cash deficit of ₹{cash_deficit:,.0f}. "
            f"Recommending payment for {pay_count} item(s) and delay for {delay_count}. "
            f"Risk level: {runway_result['risk_level']}."
        )
    else:
        summary = (
            f"Sufficient cash to cover all obligations. "
            f"Recommending payment for {pay_count} item(s) and delay for {delay_count}. "
            f"Risk level: {runway_result['risk_level']}."
        )

    return DecisionResponse(
        balance=Decimal(str(current_cash)),
        runway_days=runway_result["runway_days"],
        risk_level=runway_result["risk_level"],
        timeline=[TimelineDay(**day) for day in timeline],
        plan=DecisionPlan(pay=pay_decisions, delay=delay_decisions),
        explanations=explanations,
        actions=actions,
        alerts=alerts,
        summary=summary,
    )


# ── B. RUNWAY ENDPOINT ───────────────────────────────────────────────────────

@router.get("/runway/{user_id}", response_model=RunwayInfo)
async def get_runway(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get the runway (days until cash runs out) for a user.

    Uses all future outflows and inflows from the user's financial entries.
    """
    user = await _get_user_with_entries(db, user_id)
    current_cash = float(user.cash_balance)
    outflows = _entries_to_outflows(user.entries)
    inflows = _entries_to_inflows(user.entries)

    runway_result = detect_runway(current_cash, outflows, inflows or None)
    return RunwayInfo(**runway_result)


# ── C. SIMULATION ENDPOINT ───────────────────────────────────────────────────

@router.post("/simulate", response_model=SimulateResponse)
async def simulate(
    request: SimulateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Simulate future cash flow timeline for a user.

    Combines existing financial entries with additional outflows/inflows
    provided in the request body.
    """
    user = await _get_user_with_entries(db, request.user_id)
    current_cash = float(user.cash_balance)

    # Combine DB entries + request entries
    db_outflows = _entries_to_outflows(user.entries)
    db_inflows = _entries_to_inflows(user.entries)

    req_outflows = [
        {"amount": float(o.amount), "date": o.due_date.isoformat(), "description": o.description}
        for o in request.outflows
    ]
    req_inflows = [
        {"amount": float(i.amount), "date": i.expected_date.isoformat(),
         "confidence": i.confidence, "description": i.description}
        for i in request.inflows
    ]

    all_outflows = db_outflows + req_outflows
    all_inflows = db_inflows + req_inflows

    # Simulate
    timeline = simulate_cashflow(
        current_cash, all_outflows, all_inflows or None, request.horizon_days
    )
    runway_result = detect_runway(
        current_cash, all_outflows, all_inflows or None, request.horizon_days
    )

    return SimulateResponse(
        timeline=[TimelineDay(**day) for day in timeline],
        runway=RunwayInfo(**runway_result),
        current_cash=Decimal(str(current_cash)),
    )
