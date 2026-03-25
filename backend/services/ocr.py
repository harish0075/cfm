"""
OCR service for extracting financial data from receipt images.

Uses pytesseract to perform OCR on uploaded images and then applies
regex-based extraction for amount, date, and vendor information.
"""

import re
from datetime import date
from io import BytesIO
from typing import Dict, Optional

from PIL import Image, ImageEnhance, ImageFilter

# pytesseract is optional — if not installed, we fall back to mock extraction
try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False

from services.parser import parse_amount, parse_date_from_text


def _preprocess_image(image: Image.Image) -> Image.Image:
    """
    Preprocess image for better OCR accuracy on receipts.
    - Composites transparency onto white background.
    - Upscales small images (Tesseract needs ~300 DPI).
    - Converts to grayscale, enhances contrast, sharpens, and binarizes.
    """
    # Handle RGBA, palette (P), and other modes by converting to RGB first
    if image.mode in ("RGBA", "LA"):
        background = Image.new("RGB", image.size, (255, 255, 255))
        background.paste(image, mask=image.split()[-1])
        image = background
    elif image.mode != "RGB":
        image = image.convert("RGB")

    # Upscale small images — Tesseract works best at ~300 DPI
    # Most receipts/photos under 1000px wide are too small for good OCR
    min_width = 1000
    if image.width < min_width:
        scale = max(3, min_width // image.width)
        image = image.resize(
            (image.width * scale, image.height * scale), Image.LANCZOS
        )

    # Convert to grayscale
    image = image.convert("L")

    # Aggressive contrast enhancement for receipt text
    enhancer = ImageEnhance.Contrast(image)
    image = enhancer.enhance(2.5)

    # Sharpen to make text crisper
    enhancer = ImageEnhance.Sharpness(image)
    image = enhancer.enhance(2.0)

    # Binarize — converts to pure black/white for cleaner OCR
    image = image.point(lambda x: 0 if x < 140 else 255)

    return image


def extract_text_from_image(image_bytes) -> str:
    """
    Run OCR on raw image bytes (or a BytesIO stream) and return the extracted text.
    Falls back to a mock result if Tesseract is not installed.
    """
    if TESSERACT_AVAILABLE:
        try:
            # Accept both raw bytes and BytesIO objects
            if isinstance(image_bytes, (bytes, bytearray)):
                stream = BytesIO(image_bytes)
            elif isinstance(image_bytes, BytesIO):
                image_bytes.seek(0)
                stream = image_bytes
            else:
                # Try reading as file-like object
                stream = BytesIO(image_bytes.read())

            stream.seek(0)  # Ensure we're at the start
            image = Image.open(stream)
            image.load()  # Force PIL to read all data before stream is closed
            image = _preprocess_image(image)

            # Run multiple OCR passes with different page segmentation modes
            # to maximize text extraction from varied receipt layouts
            all_texts = []
            for psm in [3, 4, 6]:
                try:
                    text = pytesseract.image_to_string(
                        image, config=f"--psm {psm}"
                    )
                    if text.strip():
                        all_texts.append(text.strip())
                except Exception:
                    pass

            if all_texts:
                # Merge: pick the longest result (most text extracted)
                # but also combine unique lines from all passes
                combined_lines = []
                seen = set()
                for t in all_texts:
                    for line in t.splitlines():
                        line_clean = line.strip()
                        if line_clean and line_clean not in seen:
                            seen.add(line_clean)
                            combined_lines.append(line_clean)
                return "\n".join(combined_lines)

            return ""
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


def _looks_like_monetary(value: float, context: str = "") -> bool:
    """
    Filter out numbers that are clearly not monetary amounts.
    Rejects years (1900-2099), zip codes (5+ digits no decimal),
    and other non-monetary patterns.
    """
    # Years: 1900-2099
    if 1900 <= value <= 2099 and value == int(value):
        return False
    # US zip codes or similar 5-digit codes
    if 10000 <= value <= 99999 and value == int(value):
        return False
    # Very large round numbers unlikely to be receipt amounts
    if value >= 100000:
        return False
    # Zero or negative
    if value <= 0:
        return False
    return True


def _fix_rupee_misread(text: str) -> str:
    """
    Correct Tesseract OCR's common misreading of the ₹ symbol as the digit '7'.

    The ₹ glyph is rendered as '7' by older/unconfigured Tesseract builds, so:
        ₹3150.00  →  OCR produces  73150.00
        ₹104.29   →  OCR produces  7104.29

    Strategy: detect '7' NOT preceded by another digit, followed immediately by
    2–4 digits then a decimal point.  Requiring a decimal makes the rule safe —
    it avoids turning a real integer like 7500 into 500.
    """
    # 7 + 2-4 digits + decimal  (covers 7104.29, 73150.00, 7XX.XX)
    text = re.sub(r'(?<!\d)7(\d{2,4}\.\d{1,2})\b', r'₹\1', text)
    # After price-context keywords, also catch bare integers like 73150
    text = re.sub(
        r'(?i)(total|amount|price|payable|due)\b([^\n]{0,20}?\s)7(\d{3,}(?:\.\d{1,2})?)\b',
        lambda m: m.group(1) + m.group(2) + '₹' + m.group(3),
        text,
    )
    return text


def extract_receipt_amount(ocr_text: str) -> Optional[float]:
    """
    Extract total amount from OCR receipt text.

    Strategy (in order):
    1. Amount on the same line as 'total' / 'grand total' / 'amount' keyword.
    2. The LAST rupee/Rs-prefixed amount in the text
       (receipt totals are usually printed last with the currency symbol).
    3. The number that appears on the same line or immediately after a
       total-like label — even without a currency prefix.
    4. Median of all valid monetary amounts as a safe fallback
       (avoids phone numbers and large codes that inflate max()).
    """
    if not ocr_text:
        return None

    lines = ocr_text.splitlines()

    # ── 1. Look for explicit total labels on the same line ────────────────────
    total_line_patterns = [
        r"(?:grand\s*total|net\s*amount|total\s*amount|amount\s*due|total\s*payable|total)\s*[:\-=]?\s*(?:₹|rs\.?|inr)?\s*([\d,]+(?:\.\d{1,2})?)",
        r"(?:grand\s*total|net\s*amount|total\s*amount|amount\s*due|total\s*payable|total)\s*[:\-=]?\s*([\d,]+(?:\.\d{1,2})?)\s*$",
    ]
    for line in reversed(lines):  # search from bottom of receipt upward
        for pattern in total_line_patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                try:
                    val = float(match.group(1).replace(",", ""))
                    if _looks_like_monetary(val):
                        return val
                except ValueError:
                    continue

    # ── 2. Last rupee / Rs-prefixed amount (most likely the total) ───────────
    rupee_pattern = r"(?:₹|rs\.?|inr)\s*([\d,]+(?:\.\d{1,2})?)"
    rupee_matches = list(re.finditer(rupee_pattern, ocr_text, re.IGNORECASE))
    if rupee_matches:
        for m in reversed(rupee_matches):
            try:
                val = float(m.group(1).replace(",", ""))
                if _looks_like_monetary(val):
                    return val
            except ValueError:
                continue

    # ── 3. Collect ALL valid monetary-looking numbers ─────────────────────────
    all_amounts: list[float] = []
    decimal_amounts: list[float] = []  # prefer numbers with decimal points
    amount_patterns = [
        r"\b(\d{1,6}\.\d{2})\b",           # 3150.00 or 13.73 (with decimals)
        r"\b(\d{1,3}(?:,\d{3})+)\b",        # 3,150 (comma thousands)
        r"\b(\d{3,6})\b",                   # bare integers 100–999999
    ]
    for i, pattern in enumerate(amount_patterns):
        for match in re.finditer(pattern, ocr_text):
            try:
                val = float(match.group(1).replace(",", ""))
                if _looks_like_monetary(val):
                    all_amounts.append(val)
                    if i == 0:  # decimal amounts are more trustworthy
                        decimal_amounts.append(val)
            except ValueError:
                continue

    # Prefer decimal amounts; if multiple exist, take the largest of those
    # (avoids picking up line-item quantities while still avoiding phone numbers)
    if decimal_amounts:
        return max(decimal_amounts)

    if all_amounts:
        # Use median to resist outlier phone numbers / pump IDs
        sorted_amounts = sorted(all_amounts)
        mid = len(sorted_amounts) // 2
        return sorted_amounts[mid]

    # ── 4. Last resort: generic parser ───────────────────────────────────────
    generic = parse_amount(ocr_text)
    if generic and _looks_like_monetary(generic):
        return generic

    return None



def parse_receipt(image_bytes) -> Dict:
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

    # Step 1b: Fix ₹ misread as '7' before any further parsing
    raw_text = _fix_rupee_misread(raw_text)

    # Step 2: Parse structured fields from OCR text
    amount = extract_receipt_amount(raw_text)
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
