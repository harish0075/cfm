#!/bin/bash
# Test script to hit all API endpoints for CFM V1

BASE_URL="http://localhost:8000"

echo "=========================================="
echo "1. Onboarding User"
echo "=========================================="
RAW_RESPONSE=$(curl -s -X POST "$BASE_URL/onboard" -H "Content-Type: application/json" -d '{
  "name": "Harish",
  "phone": "9876543210",
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
}')
echo $RAW_RESPONSE | > response.json
# Extract UUID using basic tools (awk/sed/python)
USER_ID=$(python -c "import sys, json; print(json.load(sys.stdin)['user_id'])" < response.json)

echo -e "\nOnboarded User ID: $USER_ID\n"


echo "=========================================="
echo "2. Text Input"
echo "=========================================="
curl -s -X POST "$BASE_URL/input" -H "Content-Type: application/json" -d "{
  \"user_id\": \"$USER_ID\",
  \"message\": \"Pay 20000 rent tomorrow\"
}" | > response.json
cat response.json
echo -e "\n"


echo "=========================================="
echo "3. SMS Webhook Input"
echo "=========================================="
curl -s -X POST "$BASE_URL/sms-webhook" -H "Content-Type: application/json" -d "{
  \"sender\": \"9876543210\",
  \"message\": \"Receive 30000 from client Friday\"
}" | > response.json
cat response.json
echo -e "\n"


echo "=========================================="
echo "4. Get User State"
echo "=========================================="
curl -s "$BASE_URL/state/$USER_ID" | > response.json
cat response.json
echo -e "\n"

echo "Test script complete."
