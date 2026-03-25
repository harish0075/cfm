import requests
import json
import uuid

BASE_URL = "http://localhost:8000"

def print_section(title):
    print("\n" + "=" * 50)
    print(title)
    print("=" * 50)

def main():
    print_section("1. Onboarding User")
    
    # Generate unique phone number to avoid duplicate errors on re-runs
    fake_phone = "98" + str(uuid.uuid4().int)[:8]
    
    payload = {
        "name": "Harish Test",
        "phone": fake_phone,
        "cash_balance": 100000,
        "assets": [
            {
                "asset_type": "house",
                "name": "Main House",
                "estimated_value": 5000000,
                "liquidity": "low"
            },
            {
                "asset_type": "vehicle",
                "name": "Car",
                "estimated_value": 800000,
                "liquidity": "medium"
            }
        ]
    }
    
    response = requests.post(f"{BASE_URL}/onboard", json=payload)
    print("Status:", response.status_code)
    try:
        data = response.json()
        print(json.dumps(data, indent=2))
        user_id = data.get("user_id")
    except Exception as e:
        print("Error parsing JSON:", e)
        print("Raw text:", response.text)
        return

    if not user_id:
        print("Failed to get user_id, stopping tests.")
        return

    print_section("2. Text Input (Inflow)")
    text_payload = {
        "user_id": user_id,
        "message": "Received 30000 salary from client today"
    }
    response = requests.post(f"{BASE_URL}/input", json=text_payload)
    print("Status:", response.status_code)
    try:
        print(json.dumps(response.json(), indent=2))
    except:
        print(response.text)

    print_section("3. Text Input (Outflow)")
    text_payload = {
        "user_id": user_id,
        "message": "Pay 15000 rent tomorrow"
    }
    response = requests.post(f"{BASE_URL}/input", json=text_payload)
    print("Status:", response.status_code)
    try:
        print(json.dumps(response.json(), indent=2))
    except:
        print(response.text)

    print_section("4. SMS Webhook Input")
    sms_payload = {
        "sender": fake_phone,
        "message": "Bought groceries for 5000"
    }
    response = requests.post(f"{BASE_URL}/sms-webhook", json=sms_payload)
    print("Status:", response.status_code)
    try:
        print(json.dumps(response.json(), indent=2))
    except:
        print(response.text)

    print_section("5. Get User State")
    response = requests.get(f"{BASE_URL}/state/{user_id}")
    print("Status:", response.status_code)
    try:
        print(json.dumps(response.json(), indent=2))
    except:
        print(response.text)
        
    print_section("6. Reset User Data")
    response = requests.post(f"{BASE_URL}/reset/{user_id}")
    print("Status:", response.status_code)
    try:
        print(json.dumps(response.json(), indent=2))
    except:
        print(response.text)
        
    # Verify reset worked
    print_section("7. Get User State (Post-Reset)")
    response = requests.get(f"{BASE_URL}/state/{user_id}")
    print("Status:", response.status_code)
    try:
        print(json.dumps(response.json(), indent=2))
    except:
        print(response.text)

if __name__ == "__main__":
    main()
