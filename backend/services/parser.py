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
    Supports currency-prefixed and plain numbers, with comma separators.
    Picks the highest likely monetary value when multiple possibilities are found.
    """
    # First, find all explicit currency amounts, prioritized.
    currency_patterns = [
        r"(?:₹|rs\.?|inr)\s*([\d,]+(?:\.\d{1,2})?)(?:\s*/-)?",
        r"([\d,]+(?:\.\d{1,2})?)\s*(?:₹|rs\.?|inr|rupees?)(?:\s*/-)?",
    ]
    amounts = []

    for pattern in currency_patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            amount_str = match.group(1).replace(",", "")
            try:
                val = float(amount_str)
                amounts.append(val)
            except ValueError:
                continue

    # If we found amounts with currency context, take the max one (likely total)
    if amounts:
        return max(amounts)

    # Fallback: scan plain numbers but avoid dates, phone-like chunks
    plain_pattern = r"(\d{1,6}(?:,\d{3})*(?:\.\d{1,2})?)"
    for match in re.finditer(plain_pattern, text):
        amount_str = match.group(1).replace(",", "")
        try:
            val = float(amount_str)
            # Exclude 4-digit years and very common non-money values (for now)
            if 1900 <= val <= 2100:
                continue
            amounts.append(val)
        except ValueError:
            continue

    if amounts:
        # if there are mixed values, pick the largest of plausible amounts
        plausible = [a for a in amounts if a > 0]
        if plausible:
            return max(plausible)

    # Fallback: parse text number words
    word_amount = _text_to_number(text)
    if word_amount and word_amount > 0:
        return word_amount

    return None


def _text_to_number(text: str) -> Optional[float]:
    """Convert words to number if possible, e.g., 'twelve thousand' -> 12000."""
    units = {
        'zero': 0, 'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
        'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10,
        'eleven': 11, 'twelve': 12, 'thirteen': 13, 'fourteen': 14,
        'fifteen': 15, 'sixteen': 16, 'seventeen': 17, 'eighteen': 18,
        'nineteen': 19,
    }
    tens = {
        'twenty': 20, 'thirty': 30, 'forty': 40, 'fifty': 50,
        'sixty': 60, 'seventy': 70, 'eighty': 80, 'ninety': 90,
    }
    scales = {
        'hundred': 100,
        'thousand': 1000,
        'lakh': 100000,
        'lac': 100000,
        'million': 1000000,
    }

    text = text.lower().replace('-', ' ')
    tokens = re.findall(r"\b(?:%s|%s|%s)\b" % (
        '|'.join(units.keys()), '|'.join(tens.keys()), '|'.join(scales.keys())), text)

    if not tokens:
        return None

    current = total = 0
    for token in tokens:
        if token in units:
            current += units[token]
        elif token in tens:
            current += tens[token]
        elif token in scales:
            current = max(1, current) * scales[token]
            total += current
            current = 0
    total += current
    return float(total) if total > 0 else None


def parse_date_from_text(text: str, amount: Optional[float] = None) -> date:
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
        r"\b(?:pay|receive|got|buy|bought|from|for|to|rent|salary|client|rs\.?|inr|rupees?|\u20b9)\b",
        "",
        lower,
    )
    # Explicitly remove the extracted amount to prevent it from confusing the date parser
    if amount is not None:
        amt_float = float(amount)
        # remove float version
        cleaned = cleaned.replace(str(amt_float), "")
        # remove integer version
        if amt_float.is_integer():
            cleaned = cleaned.replace(str(int(amt_float)), "")
            
    # Remove any remaining standalone large numbers (5+ digits, or exactly 10-12 digits for phone numbers) 
    # that could confuse dateutil
    cleaned = re.sub(r"\b\d{5,}\b", "", cleaned)
    try:
        parsed = dateutil_parser.parse(cleaned, fuzzy=True, dayfirst=True)
        return parsed.date()
    except (ValueError, OverflowError):
        pass

    # Default to today
    return today


def _keyword_in_text(keyword: str, text: str) -> bool:
    """Return true if keyword appears as a whole word in text."""
    return bool(re.search(r"\b" + re.escape(keyword) + r"\b", text, re.IGNORECASE))


def _is_negated(keyword: str, text: str) -> bool:
    """Return true when keyword is negated by nearby negation words."""
    negation_terms = r"\b(?:not|no|never|dont|don't|didnt|didn't|doesnt|doesn't|cant|can't|cannot|wasnt|wasn't|wouldnt|wouldn't)\b"
    pattern_before = rf"{negation_terms}(?:\s+\w+){{0,3}}\s+{re.escape(keyword)}\b"
    pattern_after = rf"\b{re.escape(keyword)}\b(?:\s+\w+){{0,3}}\s+{negation_terms}"

    return bool(re.search(pattern_before, text, re.IGNORECASE) or re.search(pattern_after, text, re.IGNORECASE))


def _normalize_speech_metadata(text: str) -> str:
    """Clean user phrase metadata such as 'i say' / 'goes as' for direct intent parsing."""
    normalized = text.lower()
    cleanup_patterns = [
        r"\bi say\b", r"\bi said\b", r"\bi meant to say\b", r"\bwhat i said\b",
        r"\bit goes as\b", r"\bis as\b", r"\bgoes as\b", r"\bshould be\b",
    ]
    for pat in cleanup_patterns:
        normalized = re.sub(pat, "", normalized, flags=re.IGNORECASE)

    normalized = re.sub(r"\b(as outflow|as inflow|outflow|inflow)\b", "", normalized, flags=re.IGNORECASE)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def determine_type(text: str) -> str:
    """Classify message as inflow or outflow based on keyword presence."""
    normalized = _normalize_speech_metadata(text)

    inflow_keywords_found = [kw for kw in INFLOW_KEYWORDS if _keyword_in_text(kw, normalized)]
    outflow_keywords_found = [kw for kw in OUTFLOW_KEYWORDS if _keyword_in_text(kw, normalized)]

    # Explicit classification with pure inflow/outflow phrases
    if inflow_keywords_found and not outflow_keywords_found:
        return "inflow"
    if outflow_keywords_found and not inflow_keywords_found:
        return "outflow"

    # If keyword appears but is negated, ignore it for classification
    inflow_nonnegated = [kw for kw in inflow_keywords_found if not _is_negated(kw, normalized)]
    outflow_nonnegated = [kw for kw in outflow_keywords_found if not _is_negated(kw, normalized)]

    if inflow_nonnegated and not outflow_nonnegated:
        return "inflow"
    if outflow_nonnegated and not inflow_nonnegated:
        return "outflow"

    # If both remain, use earliest keyword position
    first_inflow = min((normalized.find(kw) for kw in inflow_nonnegated), default=1e9)
    first_outflow = min((normalized.find(kw) for kw in outflow_nonnegated), default=1e9)

    if first_inflow < first_outflow:
        return "inflow"
    if first_outflow < first_inflow:
        return "outflow"

    # Fallback to conservative outflow
    return "outflow"


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


def determine_recurrence(text: str):
    """Detect if a transaction is recurring and its interval."""
    lower = text.lower()
    if any(kw in lower for kw in ["every month", "monthly", "per month", "each month"]):
        return 1, "monthly"
    if any(kw in lower for kw in ["every week", "weekly", "per week", "each week"]):
        return 1, "weekly"
    if any(kw in lower for kw in ["every year", "yearly", "annually", "per year"]):
        return 1, "yearly"
    if any(kw in lower for kw in ["every day", "daily", "per day", "each day"]):
        return 1, "daily"
    return 0, None


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
            "is_recurring": int,
            "recurrence_interval": Optional[str]
        }
    """
    amount = parse_amount(message)
    entry_date = parse_date_from_text(message, amount)
    entry_type = determine_type(message)
    risk = determine_risk(message)
    flexibility = determine_flexibility(message)
    description = extract_description(message)
    is_recurring, recurrence_interval = determine_recurrence(message)

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
        "is_recurring": is_recurring,
        "recurrence_interval": recurrence_interval,
    }
