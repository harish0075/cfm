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


def extract_receipt_amount(ocr_text: str) -> Optional[float]:
    """
    Extract total amount from OCR receipt text.
    
    Strategy:
    1. Look for explicit 'Total' / 'Subtotal' / 'Grand Total' labels.
    2. Fall back to finding amounts with decimal points (e.g., 13.73).
    3. Fall back to the generic parser as last resort.
    """
    if not ocr_text:
        return None

    # 1. Look for labeled totals (e.g., "Total: 13.73", "Total 13 73", "Total $13.73")
    total_patterns = [
        r"(?:grand\s*)?total\s*[:\-]?\s*\$?\s*(\d+[\.,]\d{2})",
        r"(?:grand\s*)?total\s*[:\-]?\s*\$?\s*(\d+)\s+(\d{2})\b",  # "Total 13 73"
        r"(?:grand\s*)?total\s*[:\-]?\s*(?:₹|rs\.?|inr)?\s*([\d,]+(?:\.\d{1,2})?)",
        r"(?:sub\s*)?total\s*[:\-]?\s*\$?\s*(\d+[\.,]\d{2})",
    ]
    for pattern in total_patterns:
        match = re.search(pattern, ocr_text, re.IGNORECASE)
        if match:
            groups = match.groups()
            try:
                if len(groups) == 2 and groups[1] is not None:
                    val = float(f"{groups[0]}.{groups[1]}")
                else:
                    val = float(groups[0].replace(",", "."))
                if val > 0:
                    return val
            except (ValueError, IndexError):
                continue

    # 2. Find ALL numbers that look like monetary amounts in the text
    all_amounts = []
    amount_patterns = [
        r"\$\s*(\d+[\.,]\d{2})",                        # $13.73
        r"(?:₹|rs\.?|inr)\s*([\d,]+(?:\.\d{1,2})?)",   # Rs.1500, ₹200
        r"(\d+\.\d{2})\b",                               # 13.73 (decimal amounts)
        r"(\d+),(\d{2})\b",                               # 13,73 (European)
    ]
    for pattern in amount_patterns:
        for match in re.finditer(pattern, ocr_text, re.IGNORECASE):
            try:
                groups = match.groups()
                if len(groups) == 2 and groups[1] is not None:
                    val = float(f"{groups[0]}.{groups[1]}")
                else:
                    val = float(groups[0].replace(",", ""))
                if _looks_like_monetary(val):
                    all_amounts.append(val)
            except ValueError:
                continue

    if all_amounts:
        # Return the largest amount (most likely the total on a receipt)
        return max(all_amounts)

    # 3. Fall back to the generic parser (but filter results)
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
