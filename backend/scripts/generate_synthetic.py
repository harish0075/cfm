"""
Synthetic Data Generator
Produces 20 test scenarios (10 inflows, 10 outflows) with noise mimicking
text, OCR, and Voice transcription outputs to test the Multi-Layer Pipeline.
"""

import json
import random
from pathlib import Path

# ── 10 INFLOW SCENARIOS ───────────────────────────────────────────────────────
INFLOWS = [
    # Clean Text
    {"type": "text", "raw": "Received salary of ₹50,000 for March", "expected_amount": 50000.0, "category": "salary"},
    {"type": "text", "raw": "Client ABC credited 15000 to my account yesterday.", "expected_amount": 15000.0, "category": "general"},
    # Noisy Text
    {"type": "text", "raw": "invoice 2401 payment received Rs. 2500.50 thanks", "expected_amount": 2500.50, "category": "general"},
    
    # OCR Noise (Missing decimal, misread numbers)
    {"type": "ocr_simulation", "raw": "Reeelpt\nDate 14/05/2026\nReceived from Tenant\nRent payment\nTOTAL: 12000 INR\nThank you", "expected_amount": 12000.0, "category": "rent"},
    {"type": "ocr_simulation", "raw": "SALARY SLIP 2026\nEmployee: John\nCredited: 45,000", "expected_amount": 45000.0, "category": "salary"},
    {"type": "ocr_simulation", "raw": "REFUND APPROVED\nOrder #2024\nAmt Received: 850\nDate: 25 Mar", "expected_amount": 850.0, "category": "general"},
    {"type": "ocr_simulation", "raw": "Stripe payout credited 4300.00", "expected_amount": 4300.0, "category": "general"},
    
    # Voice Noise (Rambling, filler words)
    {"type": "voice_simulation", "raw": "Uh yes so I just received my salary it was about 32000 rupees today.", "expected_amount": 32000.0, "category": "salary"},
    {"type": "voice_simulation", "raw": "My friend returned the cash he owed me, payment received was 500 for the dinner.", "expected_amount": 500.0, "category": "food"},
    {"type": "voice_simulation", "raw": "Hey, I got credited uh 6000 rupees from the freelance gig.", "expected_amount": 6000.0, "category": "general"},
]

# ── 10 OUTFLOW SCENARIOS ──────────────────────────────────────────────────────
OUTFLOWS = [
    # Clean Text
    {"type": "text", "raw": "Paid 2000 for groceries at the supermarket", "expected_amount": 2000.0, "category": "food"},
    {"type": "text", "raw": "Rent paid ₹18000 for this month", "expected_amount": 18000.0, "category": "rent"},
    # Noisy Text
    {"type": "text", "raw": "expense: internet bill 1200", "expected_amount": 1200.0, "category": "utilities"},
    
    # OCR Noise
    {"type": "ocr_simulation", "raw": "RESTAURANT RECEIPT\nTable: 4\nFood item 1: 300\nFood item 2: 250\nTOTAL PAID: 550\nDate 2026-03-25", "expected_amount": 550.0, "category": "food"},
    {"type": "ocr_simulation", "raw": "Electricity Bill 2026\nDue Amount\n1450.00\nStatus: Paid via NetBanking", "expected_amount": 1450.0, "category": "utilities"},
    {"type": "ocr_simulation", "raw": "Amazon Purchase\nOrder ID 190045\nDebit: 899", "expected_amount": 899.0, "category": "general"},
    {"type": "ocr_simulation", "raw": "Office supplies bought\nTotal ₹4000\nGST 18%", "expected_amount": 4000.0, "category": "general"},
    
    # Voice Noise
    {"type": "voice_simulation", "raw": "Okay so I was at the restaurant and I paid 1200 for the meal tonight.", "expected_amount": 1200.0, "category": "food"},
    {"type": "voice_simulation", "raw": "Yeah I mean I just bought a new keyboard, the expense was like 3500 rupees.", "expected_amount": 3500.0, "category": "general"},
    {"type": "voice_simulation", "raw": "I paid the electricity utility bill, debited 2000 from my card.", "expected_amount": 2000.0, "category": "utilities"},
]

if __name__ == "__main__":
    all_data = INFLOWS + OUTFLOWS
    random.shuffle(all_data)
    
    out_dir = Path(__file__).parent.parent.parent / "test_data"
    out_dir.mkdir(exist_ok=True)
    out_file = out_dir / "synthetic_tests.json"
    
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(all_data, f, indent=2, ensure_ascii=False)
        
    print(f"Generated 20 synthetic test scenarios at: {out_file}")
    print("These scenarios are designed to be copy-pasted into the 'Natural Language' InputPanel to simulate OCR/Voice text extracts.")
