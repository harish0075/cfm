import requests
import json
import uuid

BASE_URL = "http://localhost:8000"

def print_section(title):
    print("\n" + "=" * 50)
    print(title)
    print("=" * 50)

def main():
    print_section("1. Onboarding User for File Uploads")
    
    fake_phone = "97" + str(uuid.uuid4().int)[:8]
    payload = {
        "name": "File Upload Tester",
        "phone": fake_phone,
        "cash_balance": 50000,
        "assets": []
    }
    
    response = requests.post(f"{BASE_URL}/onboard", json=payload)
    print("Status:", response.status_code)
    try:
        user_id = response.json().get("user_id")
        print("User ID:", user_id)
    except:
        print("Failed to onboard.")
        return
        
    print_section("2. OCR Upload (test_receipt.txt)")
    with open("test_receipt.txt", "rb") as f:
        files = {"file": ("test_receipt.txt", f, "image/jpeg")}
        data = {"user_id": user_id}
        response = requests.post(f"{BASE_URL}/upload-receipt", data=data, files=files)
        print("Status:", response.status_code)
        try:
            print(json.dumps(response.json(), indent=2))
        except:
            print(response.text)

    print_section("3. Bank Statement PDF (dummy.pdf)")
    # Create an empty dummy pdf
    with open("dummy.pdf", "wb") as f:
        f.write(b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n/Resources << >>\n/Contents 4 0 R\n>>\nendobj\n4 0 obj\n<<\n/Length 12\n>>\nstream\nBT\nET\nendstream\nendobj\nxref\n0 5\n0000000000 65535 f\n0000000009 00000 n\n0000000058 00000 n\n0000000109 00000 n\n0000000213 00000 n\ntrailer\n<<\n/Size 5\n/Root 1 0 R\n>>\nstartxref\n268\n%%EOF\n")
        
    with open("dummy.pdf", "rb") as f:
        files = {"file": ("dummy.pdf", f, "application/pdf")}
        data = {"user_id": user_id}
        response = requests.post(f"{BASE_URL}/upload-bank-statement", data=data, files=files)
        print("Status:", response.status_code)
        try:
            print(json.dumps(response.json(), indent=2))
        except:
            print(response.text)

    print_section("4. Audio Upload (grocery.wav)")
    # Create an empty dummy wav
    with open("grocery.wav", "wb") as f:
        f.write(b"RIFF$\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00D\xac\x00\x00\x88X\x01\x00\x02\x00\x10\x00data\x00\x00\x00\x00")
        
    with open("grocery.wav", "rb") as f:
        files = {"file": ("grocery.wav", f, "audio/wav")}
        data = {"user_id": user_id}
        response = requests.post(f"{BASE_URL}/audio", data=data, files=files)
        print("Status:", response.status_code)
        try:
            print(json.dumps(response.json(), indent=2))
        except:
            print(response.text)

if __name__ == "__main__":
    main()
