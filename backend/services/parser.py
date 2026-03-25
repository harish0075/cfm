"""
Natural-language financial message parser.

Uses regex and keyword matching to extract structured financial data from
free-form text messages like:
    "Pay 20000 rent tomorrow"
    "Receive 30000 from client Friday"
    "Bought materials for 5000 today"

Returns a dict with: type, amount, date, description, confidence, risk, flexibility.
"""

import re
from datetime import date, timedelta
from typing import Dict, Optional

from dateutil import parser as dateutil_parser

# ── Keyword banks ─────────────────────────────────────────────────────────────

# Words that indicate money coming IN
INFLOW_KEYWORDS = [
    "receive", "received", "got", "salary", "credit", "credited",
    "income", "earn", "earned", "refund", "reimbursement", "bonus",
    "deposit", "deposited", "collected", "collection", "inflow",
]

# Words that indicate money going OUT
OUTFLOW_KEYWORDS = [
    "pay", "paid", "buy", "bought", "purchase", "purchased", "spend",
    "spent", "rent", "bill", "expense", "debit", "debited", "transfer",
    "sent", "emi", "loan", "outflow", "cost",
]

# Risk heuristic based on category keywords
HIGH_RISK_KEYWORDS = ["loan", "emi", "debt", "penalty", "fine", "overdue"]
MEDIUM_RISK_KEYWORDS = ["rent", "bill", "insurance", "tax", "medical"]

# Flexibility heuristic: essential expenses are less flexible
LOW_FLEXIBILITY_KEYWORDS = ["rent", "emi", "loan", "tax", "insurance", "bill"]
HIGH_FLEXIBILITY_KEYWORDS = ["gift", "shopping", "entertainment", "dining", "travel"]


def parse_amount(text: str) -> Optional[float]:
    """
    Extract monetary amount from text.
    Supports formats: 20000, 20,000, ₹20000, Rs.20000, Rs 20,000
    """
    # Match currency-prefixed or plain numbers
    patterns = [
        r"(?:₹|rs\.?|inr)\s*([\d,]+(?:\.\d{1,2})?)",  # ₹20000, Rs.20000
        r"([\d,]+(?:\.\d{1,2})?)\s*(?:₹|rs\.?|inr|rupees?)",
        r"Rs\.?\s?(\d+(?:\.\d{1,2})?)",  # 20000 Rs
        r"\b([\d,]+(?:\.\d{1,2})?)\b",  # plain number: 20000
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            amount_str = match.group(1).replace(",", "")
            try:
                return float(amount_str)
            except ValueError:
                continue
    return None


def parse_date_from_text(text: str) -> date:
    """
    Extract date from text. Supports:
    - Relative words: today, tomorrow, yesterday
    - Named weekdays: Monday, Friday, etc.
    - Explicit dates: 25/03/2026, March 25, 2026-03-25
    Falls back to today if nothing found.
    """
    today = date.today()
    lower = text.lower()

    # Relative dates
    if "today" in lower:
        return today
    if "tomorrow" in lower:
        return today + timedelta(days=1)
    if "yesterday" in lower:
        return today - timedelta(days=1)

    # Named weekdays — find the next occurrence
    weekdays = [
        "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"
    ]
    for i, day in enumerate(weekdays):
        if day in lower:
            # Calculate days until the next occurrence of this weekday
            current_weekday = today.weekday()  # Monday=0 … Sunday=6
            days_ahead = i - current_weekday
            if days_ahead <= 0:
                days_ahead += 7
            return today + timedelta(days=days_ahead)

    # Try dateutil parser for explicit date strings
    # Remove common words that confuse the parser
    cleaned = re.sub(
        r"\b(?:pay|receive|got|buy|bought|from|for|to|rent|salary|client)\b",
        "",
        lower,
    )
    try:
        parsed = dateutil_parser.parse(cleaned, fuzzy=True, dayfirst=True)
        return parsed.date()
    except (ValueError, OverflowError):
        pass

    # Default to today
    return today


def determine_type(text: str) -> str:
    """Classify message as inflow or outflow based on keyword presence."""
    lower = text.lower()
    inflow_score = sum(1 for kw in INFLOW_KEYWORDS if kw in lower)
    outflow_score = sum(1 for kw in OUTFLOW_KEYWORDS if kw in lower)

    if inflow_score > outflow_score:
        return "inflow"
    return "outflow"  # default to outflow if ambiguous


def determine_risk(text: str) -> str:
    """Assign risk level based on financial keywords."""
    lower = text.lower()
    if any(kw in lower for kw in HIGH_RISK_KEYWORDS):
        return "high"
    if any(kw in lower for kw in MEDIUM_RISK_KEYWORDS):
        return "medium"
    return "low"


def determine_flexibility(text: str) -> int:
    """Assign flexibility score (1-10) based on expense category."""
    lower = text.lower()
    if any(kw in lower for kw in LOW_FLEXIBILITY_KEYWORDS):
        return 2  # Essential, not flexible
    if any(kw in lower for kw in HIGH_FLEXIBILITY_KEYWORDS):
        return 8  # Discretionary, flexible
    return 5  # Default mid-range


def extract_description(text: str) -> str:
    """
    Extract a clean description from the message.
    Removes amounts and dates, keeps the meaningful words.
    """
    # Remove currency and numbers
    cleaned = re.sub(r"(?:₹|rs\.?|inr)\s*[\d,]+(?:\.\d{1,2})?", "", text, flags=re.IGNORECASE)
    cleaned = re.sub(r"\b\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?\b", "", cleaned)
    # Collapse whitespace
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned if cleaned else text


def parse_text_input(message: str) -> Dict:
    """
    Main parser entry point.
    Takes a natural-language financial message and returns structured data.

    Returns:
        {
            "type": "inflow" | "outflow",
            "amount": float,
            "date": date,
            "description": str,
            "confidence_score": float,
            "risk_level": str,
            "flexibility": int,
        }
    """
    amount = parse_amount(message)
    entry_date = parse_date_from_text(message)
    entry_type = determine_type(message)
    risk = determine_risk(message)
    flexibility = determine_flexibility(message)
    description = extract_description(message)

    # Confidence is high for text (user directly typed it)
    # but reduced if we couldn't extract an amount
    confidence = 0.9 if amount else 0.5

    return {
        "type": entry_type,
        "amount": amount or 0.0,
        "date": entry_date,
        "description": description,
        "confidence_score": confidence,
        "risk_level": risk,
        "flexibility": flexibility,
    }
