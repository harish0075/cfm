"""
Automated Pipeline Validator
Executes the synthetic test scenarios against the local API and documents failures.
"""
import json
import requests
from pathlib import Path
from pprint import pprint

BASE_URL = "http://127.0.0.1:8000"

def load_tests():
    p = Path(__file__).parent.parent.parent / "test_data" / "synthetic_tests.json"
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)

def test_pipeline():
    tests = load_tests()
    errors = []
    successes = 0

    print(f"Starting execution of {len(tests)} scenarios against {BASE_URL}")

    for i, t in enumerate(tests):
        raw_text = t["raw"]
        expected_amt = t["expected_amount"]
        expected_cat = t["category"]
        
        # Step 1: Extract Raw
        try:
            res1 = requests.post(f"{BASE_URL}/extract_raw", data={"text": raw_text})
            if res1.status_code != 200:
                errors.append({"test": i, "step": "extract_raw", "status": res1.status_code, "detail": res1.text, "input": raw_text})
                continue
                
            raw_data = res1.json()
        except Exception as e:
            errors.append({"test": i, "step": "extract_raw", "error": str(e), "input": raw_text})
            continue

        # Step 2: Validate
        try:
            res2 = requests.post(f"{BASE_URL}/validate", json=raw_data)
            if res2.status_code != 200:
                errors.append({"test": i, "step": "validate", "status": res2.status_code, "detail": res2.text, "input": raw_text})
                continue
                
            val_data = res2.json()
            
            # Check validation correctness
            detected_amount = val_data.get("amount")
            detected_cat = val_data.get("category")
            
            issues = []
            if detected_amount != expected_amt:
                issues.append(f"Amount mismatch: Expected {expected_amt}, got {detected_amount}")
            
            # The prompt requested specific categories. The ML didn't use expected_cat, but we can log differences based on the rules.
            # e.g., "rent" -> rent
            if detected_cat != expected_cat and expected_cat != "general":
                issues.append(f"Category mismatch: Expected {expected_cat}, got {detected_cat}")
                
            if issues:
                errors.append({"test": i, "step": "logic_check", "issues": issues, "input": raw_text, "extracted": val_data})
            else:
                successes += 1
                
        except Exception as e:
            errors.append({"test": i, "step": "validate", "error": str(e), "input": raw_text})

    print(f"\\n--- PIPELINE EXECUTION RESULTS ---")
    print(f"Total Tests: {len(tests)}")
    print(f"Successes: {successes}")
    print(f"Errors: {len(errors)}")
    
    with open("validation_errors_report.json", "w", encoding="utf-8") as f:
        json.dump(errors, f, indent=2)
        
    for e in errors:
        print(f"Test {e['test']} [{e['step']}]:")
        if 'issues' in e:
            for issue in e['issues']:
                print(f"  - {issue}")
        else:
            print(f"  - {e.get('status', 'Error')}: {e.get('detail', e.get('error'))}")
        print()

if __name__ == "__main__":
    test_pipeline()
