# Sample Curl Commands for CFM V1 API

Below are sample curl commands to test the various endpoints of the Financial Input Engine.

Replace `<USER_UUID>` with the actual `user_id` returned from the `/onboard` endpoint.

---

### 1. Onboarding

```bash
curl -X POST http://localhost:8000/onboard \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Jane Doe",
    "phone": "9876543210",
    "cash_balance": 50000.00,
    "assets": [
      {
        "asset_type": "house",
        "name": "Primary Residence",
        "estimated_value": 7500000,
        "liquidity": "low"
      }
    ]
  }'
```

---

### 2. Text Input

```bash
curl -X POST http://localhost:8000/input \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "<USER_UUID>",
    "message": "Pay 15000 rent tomorrow"
  }'
```

```bash
curl -X POST http://localhost:8000/input \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "<USER_UUID>",
    "message": "Received 30000 salary from client today"
  }'
```

---

### 3. SMS Webhook

```bash
curl -X POST http://localhost:8000/sms-webhook \
  -H "Content-Type: application/json" \
  -d '{
    "sender": "9876543210",
    "message": "Bought groceries for 5000."
  }'
```

---

### 4. Upload Receipt (OCR)

_Ensure you have an image named `receipt.jpg` in the current directory._

```bash
curl -X POST http://localhost:8000/upload-receipt \
  -F "user_id=<USER_UUID>" \
  -F "file=@receipt.jpg"
```

---

### 5. Upload Bank Statement (PDF)

_Ensure you have a PDF named `statement.pdf` in the current directory._

```bash
curl -X POST http://localhost:8000/upload-bank-statement \
  -F "user_id=<USER_UUID>" \
  -F "file=@statement.pdf"
```

---

### 6. Upload Audio

_Ensure you have an audio file named `audio.wav` in the current directory._

```bash
curl -X POST http://localhost:8000/audio \
  -F "user_id=<USER_UUID>" \
  -F "file=@audio.wav"
```

---

### 7. Get User State

```bash
curl -X GET http://localhost:8000/state/<USER_UUID>
```

---

### 8. Reset User Data

```bash
curl -X POST http://localhost:8000/reset/<USER_UUID>
```
