#!/usr/bin/env python3
"""
Test script for the improved OCR functionality.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.ocr import _get_easyocr_reader, _get_paddle_model

def test_ocr():
    print("Testing OCR functionality...")

    # Test if EasyOCR reader can be initialized
    try:
        reader = _get_easyocr_reader()
        if reader:
            print("✓ EasyOCR reader initialized successfully")
        else:
            print("✗ EasyOCR reader initialization failed")
    except Exception as e:
        print(f"✗ EasyOCR error: {e}")

    # Test if PaddleOCR model can be initialized
    try:
        model = _get_paddle_model()
        if model:
            print("✓ PaddleOCR model initialized successfully")
        else:
            print("✗ PaddleOCR model initialization failed")
    except Exception as e:
        print(f"✗ PaddleOCR error: {e}")

if __name__ == "__main__":
    test_ocr()