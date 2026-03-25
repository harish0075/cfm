"""
Time Simulation & Runway Detection service.

Simulates future cash balance over time based on known inflows/outflows,
detects when cash runs out (runway), and categorizes financial risk.
"""

from datetime import date, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional


def simulate_cashflow(
    current_cash: float,
    outflows: List[Dict[str, Any]],
    inflows: List[Dict[str, Any]] | None = None,
    horizon_days: int = 90,
) -> List[Dict[str, Any]]:
    """
    Simulate daily cash balance over a future horizon.

    Args:
        current_cash:  Starting cash amount
        outflows:      List of dicts with 'amount' and 'date' (ISO str or date obj)
        inflows:       List of dicts with 'amount', 'date', and optionally 'confidence'
        horizon_days:  Number of days to simulate into the future

    Returns:
        List of daily snapshots: [{"date": "YYYY-MM-DD", "balance": float, "events": [...]}]
    """
    today = date.today()
    end_date = today + timedelta(days=horizon_days)

    # Build event timeline
    events: Dict[date, List[Dict[str, Any]]] = {}

    for outflow in outflows:
        d = _parse_date(outflow.get("date", outflow.get("due_date")))
        if d and today <= d <= end_date:
            events.setdefault(d, []).append({
                "type": "outflow",
                "amount": float(outflow["amount"]),
                "description": outflow.get("description", "Payment"),
            })

    if inflows:
        for inflow in inflows:
            d = _parse_date(inflow.get("date", inflow.get("expected_date")))
            confidence = float(inflow.get("confidence", 1.0))
            if d and today <= d <= end_date:
                events.setdefault(d, []).append({
                    "type": "inflow",
                    "amount": float(inflow["amount"]) * confidence,  # weight by confidence
                    "description": inflow.get("description", "Expected inflow"),
                    "confidence": confidence,
                })

    # Simulate day-by-day
    timeline = []
    balance = float(current_cash)
    current = today

    while current <= end_date:
        day_events = events.get(current, [])
        for event in day_events:
            if event["type"] == "inflow":
                balance += event["amount"]
            else:
                balance -= event["amount"]

        timeline.append({
            "date": current.isoformat(),
            "balance": round(balance, 2),
            "events": day_events if day_events else [],
        })
        current += timedelta(days=1)

    return timeline


def detect_runway(
    current_cash: float,
    outflows: List[Dict[str, Any]],
    inflows: List[Dict[str, Any]] | None = None,
    horizon_days: int = 90,
) -> Dict[str, Any]:
    """
    Detect when cash balance becomes negative (runway) and categorize risk.

    Returns:
        {
            "runway_days": int | None (None = safe beyond horizon),
            "risk_level": "SAFE" | "WARNING" | "CRITICAL",
            "crash_date": str | None,
            "minimum_balance": float,
            "minimum_balance_date": str,
        }
    """
    timeline = simulate_cashflow(current_cash, outflows, inflows, horizon_days)

    runway_days = None
    crash_date = None
    min_balance = float("inf")
    min_balance_date = date.today().isoformat()

    for i, day in enumerate(timeline):
        if day["balance"] < min_balance:
            min_balance = day["balance"]
            min_balance_date = day["date"]

        if day["balance"] < 0 and runway_days is None:
            runway_days = i
            crash_date = day["date"]

    # Categorize risk
    if runway_days is None:
        risk_level = "SAFE"
    elif runway_days <= 7:
        risk_level = "CRITICAL"
    elif runway_days <= 30:
        risk_level = "WARNING"
    else:
        risk_level = "SAFE"

    return {
        "runway_days": runway_days,
        "risk_level": risk_level,
        "crash_date": crash_date,
        "minimum_balance": round(min_balance, 2),
        "minimum_balance_date": min_balance_date,
    }


def compute_cash_deficit(current_cash: float, obligations: List[Dict[str, Any]]) -> float:
    """Calculate total obligations minus current cash (0 if cash covers everything)."""
    total = sum(float(o.get("amount", 0)) for o in obligations)
    return max(0, total - current_cash)


def _parse_date(value) -> Optional[date]:
    """Convert a string or date object to a date, or return None."""
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError:
            return None
    return None
