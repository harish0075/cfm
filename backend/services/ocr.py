"""
Advanced OCR service for extracting financial data from receipt images and PDFs.

Uses PaddleOCR for superior handwritten text recognition and scanned document processing.
Supports multiple languages, handwriting styles, and various receipt formats.
Includes advanced preprocessing and post-processing for financial data extraction.
"""

import re
import cv2
import numpy as np
from datetime import date
from io import BytesIO
from typing import Dict, Optional, List, Tuple
from PIL import Image, ImageEnhance, ImageFilter

# Advanced OCR with EasyOCR for better handwritten recognition
try:
    import easyocr
    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False

# Fallback to PaddleOCR if EasyOCR not available
try:
    from paddleocr import PaddleOCR
    PADDLE_AVAILABLE = True
except ImportError:
    PADDLE_AVAILABLE = False

# Final fallback to pytesseract
try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False

# Additional image processing
try:
    from skimage import filters, morphology
    SKIMAGE_AVAILABLE = True
except ImportError:
    SKIMAGE_AVAILABLE = False

from services.parser import parse_amount, parse_date_from_text

# Global OCR readers for better performance
_easyocr_reader = None
_paddle_model = None

def _get_easyocr_reader():
    """Initialize and return EasyOCR reader optimized for receipts."""
    global _easyocr_reader
    if _easyocr_reader is None and EASYOCR_AVAILABLE:
        try:
            # Initialize EasyOCR with English language
            # gpu=False for CPU usage, can be changed to True for GPU
            _easyocr_reader = easyocr.Reader(['en'], gpu=False)
        except Exception as e:
            print(f"Failed to initialize EasyOCR: {e}")
            _easyocr_reader = None
    return _easyocr_reader

def _get_paddle_model():
    """Initialize and return PaddleOCR model."""
    global _paddle_model
    if _paddle_model is None and PADDLE_AVAILABLE:
        try:
            _paddle_model = PaddleOCR(use_angle_cls=True, lang='en')
        except Exception as e:
            print(f"Failed to initialize PaddleOCR: {e}")
            _paddle_model = None
    return _paddle_model


def _advanced_preprocess_image(image: Image.Image) -> Image.Image:
    """
    Advanced preprocessing pipeline optimized for handwritten receipts and scanned documents.
    Includes noise reduction, contrast enhancement, and morphological operations.
    """
    # Convert to numpy array for OpenCV processing
    img_array = np.array(image)

    # Handle different image modes
    if image.mode in ("RGBA", "LA"):
        # Remove alpha channel, composite on white background
        if image.mode == "RGBA":
            background = Image.new("RGB", image.size, (255, 255, 255))
            background.paste(image, mask=image.split()[-1])
            image = background
        else:
            image = image.convert("RGB")
        img_array = np.array(image)

    # Convert to grayscale if needed
    if len(img_array.shape) == 3:
        img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    elif len(img_array.shape) == 2:
        pass  # Already grayscale
    else:
        raise ValueError("Unsupported image format")

    # Noise reduction
    img_array = cv2.medianBlur(img_array, 3)

    # Contrast enhancement using CLAHE (Contrast Limited Adaptive Histogram Equalization)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    img_array = clahe.apply(img_array)

    # Morphological operations to clean up handwriting
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 1))
    img_array = cv2.morphologyEx(img_array, cv2.MORPH_CLOSE, kernel)

    # Adaptive thresholding for better text extraction
    img_array = cv2.adaptiveThreshold(
        img_array, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
    )

    # Upscale small images for better OCR
    height, width = img_array.shape
    min_dimension = 1000
    if min(height, width) < min_dimension:
        scale_factor = max(2, min_dimension // min(height, width))
        new_width = width * scale_factor
        new_height = height * scale_factor
        img_array = cv2.resize(img_array, (new_width, new_height), interpolation=cv2.INTER_CUBIC)

    # Convert back to PIL Image
    processed_image = Image.fromarray(img_array)

    return processed_image


def _fallback_preprocess_image(image: Image.Image) -> Image.Image:
    """
    Fallback preprocessing for when advanced libraries are not available.
    """
    # Handle RGBA, palette (P), and other modes by converting to RGB first
    if image.mode in ("RGBA", "LA"):
        background = Image.new("RGB", image.size, (255, 255, 255))
        background.paste(image, mask=image.split()[-1])
        image = background
    elif image.mode != "RGB":
        image = image.convert("RGB")

    # Upscale small images
    min_width = 1000
    if image.width < min_width:
        scale = max(3, min_width // image.width)
        image = image.resize(
            (image.width * scale, image.height * scale), Image.LANCZOS
        )

    # Convert to grayscale
    image = image.convert("L")

    # Aggressive contrast enhancement
    enhancer = ImageEnhance.Contrast(image)
    image = enhancer.enhance(2.5)

    # Sharpen
    enhancer = ImageEnhance.Sharpness(image)
    image = enhancer.enhance(2.0)

    # Binarize
    image = image.point(lambda x: 0 if x < 140 else 255)

    return image

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
    Extract text from image using EasyOCR for superior accuracy on handwritten receipts.
    Falls back to PaddleOCR, then pytesseract if not available.
    """
    if isinstance(image_bytes, (bytes, bytearray)):
        stream = BytesIO(image_bytes)
    elif isinstance(image_bytes, BytesIO):
        image_bytes.seek(0)
        stream = image_bytes
    else:
        stream = BytesIO(image_bytes.read())

    stream.seek(0)
    image = Image.open(stream)
    image.load()

    # Try EasyOCR first (best for handwritten text)
    reader = _get_easyocr_reader()
    if reader is not None:
        try:
            # Convert PIL image to numpy array
            img_array = np.array(image)

            # Perform OCR
            results = reader.readtext(img_array, detail=0)  # detail=0 returns just text

            if results:
                # Filter out very short texts and join
                filtered_texts = [text.strip() for text in results if len(text.strip()) > 1]
                if filtered_texts:
                    return "\n".join(filtered_texts)

        except Exception as e:
            print(f"EasyOCR failed: {e}")

    # Fallback to PaddleOCR
    paddle_model = _get_paddle_model()
    if paddle_model is not None:
        try:
            # Preprocess image
            processed_image = _advanced_preprocess_image(image)
            img_array = np.array(processed_image)

            results = paddle_model.ocr(img_array, cls=True)
            extracted_texts = []
            if results and results[0]:
                for line in results[0]:
                    if line and len(line) >= 2:
                        text = line[1][0]
                        confidence = line[1][1]
                        if confidence > 0.5:
                            extracted_texts.append(text.strip())

            if extracted_texts:
                return "\n".join(extracted_texts)

        except Exception as e:
            print(f"PaddleOCR failed: {e}")

    # Final fallback to pytesseract
    if TESSERACT_AVAILABLE:
        try:
            processed_image = _fallback_preprocess_image(image)
            text = pytesseract.image_to_string(processed_image)
            if text.strip():
                return text.strip()
        except Exception as e:
            print(f"Tesseract fallback failed: {e}")

    return "[OCR_ERROR: No OCR engines available]"

def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """
    Extract text from PDF, with OCR fallback for scanned documents.
    """
    try:
        import pdfplumber
        from pdfplumber.page import Page

        # Try text extraction first (for text-based PDFs)
        text_content = []
        with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_content.append(page_text)

        if text_content:
            return "\n".join(text_content)

        # If no text found, treat as scanned PDF and use OCR
        print("No text found in PDF, attempting OCR on scanned pages...")
        ocr_texts = []

        with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
            for page in pdf.pages:
                # Convert page to image
                page_image = page.to_image(resolution=300).original

                # Convert PIL image to bytes
                img_buffer = BytesIO()
                page_image.save(img_buffer, format='PNG')
                img_bytes = img_buffer.getvalue()

                # OCR the page image
                page_text = extract_text_from_image(img_bytes)
                if page_text and not page_text.startswith("[OCR_ERROR"):
                    ocr_texts.append(page_text)

        if ocr_texts:
            return "\n".join(ocr_texts)

    except Exception as e:
        print(f"PDF text extraction failed: {e}")

    return "[PDF_ERROR: Could not extract text from PDF]"


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
    # US zip codes or similar 5-digit codes were previously filtered out,
    # but in real receipts totals might be 5-digit (e.g., 12,500), so we allow them.
    # For better filtering, rely on label context in extract_receipt_amount.
    # Very large round numbers are still considered unlikely for single receipt
    # line-level totals (e.g., > 500k). Keep robust but not too strict.
    if value >= 500000:
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
        r"(?:grand\s*total|net\s*amount|total\s*amount|amount\s*due|total\s*payable|total)\s*[:\-=]?\s*(?:₹|rs\.?|inr)?\s*([\d,]+(?:\.\d{1,2})?)(?:\s*/-)?",
        r"(?:grand\s*total|net\s*amount|total\s*amount|amount\s*due|total\s*payable|total)\s*[:\-=]?\s*([\d,]+(?:\.\d{1,2})?)(?:\s*/-)?\s*$",
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
    # Also capture optional '/-' suffix and comma-separated numbers.
    rupee_pattern = r"(?:₹|rs\.?|inr)\s*([\d,]+(?:\.\d{1,2})?)(?:\s*/-)?"
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



def parse_receipt_from_text(raw_text: str) -> Dict:
    """
    Parse receipt data from already extracted text.
    Used when text has been extracted from PDF or image.
    """
    # Fix ₹ misread as '7' before any further parsing
    raw_text = _fix_rupee_misread(raw_text)

    # Parse structured fields from OCR text
    amount = extract_receipt_amount(raw_text)
    entry_date = parse_date_from_text(raw_text)
    vendor = extract_vendor(raw_text)

    # Build description from vendor + raw text summary
    description = vendor if vendor else raw_text[:100]

    # Calculate confidence based on extraction quality
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


def extract_raw_ocr(content: bytes) -> Dict:
    """
    Extract raw OCR text and candidate fields from image or PDF content.
    Used by the pipeline orchestrator for multi-format processing.
    """
    # Check if it's a PDF by looking at the first few bytes
    if content.startswith(b'%PDF'):
        # It's a PDF
        raw_text = extract_text_from_pdf(content)
    else:
        # Assume it's an image
        raw_text = extract_text_from_image(content)

    # Extract candidate fields
    return {
        "raw_text": raw_text,
        "amount_candidates": _extract_amount_candidates(raw_text),
        "date_candidates": _extract_date_candidates(raw_text),
        "keywords": _extract_keywords(raw_text),
        "party_name": _extract_party_name(raw_text),
    }


def _extract_amount_candidates(text: str) -> List[Dict]:
    """Extract potential monetary amounts with context."""
    candidates = []
    # Look for amounts with currency symbols or in total contexts
    patterns = [
        r"(?:₹|rs\.?|inr|total|amount)\s*[:\-]?\s*([\d,]+(?:\.\d{1,2})?)",
        r"([\d,]+(?:\.\d{1,2})?)\s*(?:₹|rs\.?|inr)",
        r"\b([\d,]+(?:\.\d{1,2})?)\b",  # Any number that looks monetary
    ]

    for pattern in patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            try:
                amount = float(match.group(1).replace(",", ""))
                if _looks_like_monetary(amount):
                    candidates.append({
                        "value": amount,
                        "context": text[max(0, match.start()-20):match.end()+20].strip(),
                        "confidence": 0.8 if 'total' in match.group(0).lower() else 0.6
                    })
            except (ValueError, IndexError):
                continue

    return candidates


def _extract_date_candidates(text: str) -> List[Dict]:
    """Extract potential dates with context."""
    candidates = []
    # Common date patterns in receipts
    patterns = [
        r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b",  # DD/MM/YYYY or MM/DD/YYYY
        r"\b(\d{2,4}[/-]\d{1,2}[/-]\d{1,2})\b",  # YYYY/MM/DD
        r"(\d{1,2}\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\s+\d{2,4})",  # DD Mon YYYY
    ]

    for pattern in patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            candidates.append({
                "value": match.group(1),
                "context": text[max(0, match.start()-10):match.end()+10].strip(),
                "confidence": 0.7
            })

    return candidates


def _extract_keywords(text: str) -> List[str]:
    """Extract relevant financial keywords."""
    keywords = []
    financial_terms = [
        'receipt', 'invoice', 'bill', 'payment', 'purchase', 'sale',
        'total', 'amount', 'balance', 'due', 'paid', 'cash', 'card',
        'credit', 'debit', 'transaction', 'fee', 'tax', 'gst'
    ]

    text_lower = text.lower()
    for term in financial_terms:
        if term in text_lower:
            keywords.append(term)

    return keywords


def _extract_party_name(text: str) -> Optional[str]:
    """Extract vendor/store/party name."""
    return extract_vendor(text)
