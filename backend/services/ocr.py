"""
OCR service for extracting financial data from receipt images.

Uses pytesseract to perform OCR on uploaded images and then applies
regex-based extraction for amount, date, and vendor information.
"""

import re
from datetime import date
from io import BytesIO
from typing import Dict, Optional

from PIL import Image

# pytesseract is optional — if not installed, we fall back to mock extraction
try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False

from services.parser import parse_amount, parse_date_from_text


def extract_text_from_image(image_bytes: bytes) -> str:
    """
    Run OCR on raw image bytes and return the extracted text.
    Falls back to a mock result if Tesseract is not installed.
    """
    if TESSERACT_AVAILABLE:
        try:
            image = Image.open(BytesIO(image_bytes))
            text = pytesseract.image_to_string(image)
            return text.strip()
        except Exception as e:
            # If OCR fails (bad image, Tesseract not configured), return error info
            return f"[OCR_ERROR: {str(e)}]"
    else:
        # Mock OCR output for environments without Tesseract
        return "Receipt\nStore: General Store\nDate: 25/03/2026\nTotal: Rs. 1500.00\nThank you for shopping!"


def extract_vendor(ocr_text: str) -> Optional[str]:
    """
    Try to extract a vendor/store name from OCR text.
    Looks for patterns like 'Store: XYZ' or takes the first non-empty line.
    """
    # Try explicit patterns
    patterns = [
        r"(?:store|shop|vendor|merchant|from)\s*[:\-]\s*(.+)",
        r"^([A-Z][A-Za-z\s&]+)$",  # Capitalized first line (common in receipts)
    ]
    for pattern in patterns:
        match = re.search(pattern, ocr_text, re.IGNORECASE | re.MULTILINE)
        if match:
            vendor = match.group(1).strip()
            if len(vendor) > 2 and len(vendor) < 100:
                return vendor
    return None


def calculate_ocr_confidence(amount: Optional[float], entry_date: date, vendor: Optional[str]) -> float:
    """
    Calculate a confidence score (0–1) based on how many fields were
    successfully extracted from the OCR text.
    """
    score = 0.0
    fields_checked = 3  # amount, date, vendor

    if amount and amount > 0:
        score += 1.0
    if entry_date != date.today():
        # If we got a specific date (not today fallback), that's a good sign
        score += 1.0
    else:
        score += 0.5  # today might be correct, partial credit
    if vendor:
        score += 1.0

    return round(score / fields_checked, 2)


def parse_receipt(image_bytes: bytes) -> Dict:
    """
    Main OCR entry point.
    Accepts raw image bytes, performs OCR, and extracts structured data.

    Returns:
        {
            "type": "outflow",  (receipts are almost always expenses)
            "amount": float,
            "date": date,
            "description": str,
            "confidence_score": float,
            "risk_level": str,
            "flexibility": int,
            "raw_text": str,
        }
    """
    # Step 1: OCR extraction
    raw_text = extract_text_from_image(image_bytes)

    # Step 2: Parse structured fields from OCR text
    amount = parse_amount(raw_text)
    entry_date = parse_date_from_text(raw_text)
    vendor = extract_vendor(raw_text)

    # Step 3: Build description from vendor + raw text summary
    description = vendor if vendor else raw_text[:100]

    # Step 4: Calculate confidence based on extraction quality
    confidence = calculate_ocr_confidence(amount, entry_date, vendor)

    return {
        "type": "outflow",  # Receipts are expenses
        "amount": amount or 0.0,
        "date": entry_date,
        "description": f"Receipt: {description}",
        "confidence_score": confidence,
        "risk_level": "low",
        "flexibility": 5,
        "raw_text": raw_text,
    }
