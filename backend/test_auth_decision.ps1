# test_auth_decision.ps1
# End-to-end PowerShell script to test Auth + Decision Engine

$baseUrl = "http://localhost:8000"

Write-Host "`n=== 1. Register User ===" -ForegroundColor Cyan
$registerBody = @{
    name = "Test User"
    phone = "9999900000"
    password = "secure123"
    cash_balance = 50000
    assets = @()
} | ConvertTo-Json

try {
    $registerResponse = Invoke-RestMethod -Uri "$baseUrl/onboard" -Method POST -Headers @{"Content-Type"="application/json"} -Body $registerBody
    $userId = $registerResponse.user_id
    Write-Host "Success! User ID: $userId" -ForegroundColor Green
} catch {
    Write-Host "User might already exist. Attempting login anyway..." -ForegroundColor Yellow
}

Write-Host "`n=== 2. Login ===" -ForegroundColor Cyan
$loginBody = @{
    phone = "9999900000"
    password = "secure123"
} | ConvertTo-Json

$loginResponse = Invoke-RestMethod -Uri "$baseUrl/login" -Method POST -Headers @{"Content-Type"="application/json"} -Body $loginBody
$token = $loginResponse.access_token
$userId = $loginResponse.user_id
Write-Host "Success! Token: ${token:Substring(0,20)}..." -ForegroundColor Green

$authHeader = @{
    "Authorization" = "Bearer $token"
    "Content-Type" = "application/json"
}

Write-Host "`n=== 3. Get User State (Protected) ===" -ForegroundColor Cyan
$stateResponse = Invoke-RestMethod -Uri "$baseUrl/state/$userId" -Method GET -Headers $authHeader
Write-Host "Cash Balance: $($stateResponse.cash_balance)" -ForegroundColor Green

Write-Host "`n=== 4. Evaluate Decisions ===" -ForegroundColor Cyan
$decisionBody = @{
    user_id = $userId
    obligations = @(
        @{amount=20000; due_date="2026-03-28"; penalty_score=8; flexibility=2; relationship_score=7; description="Rent"},
        @{amount=35000; due_date="2026-04-10"; penalty_score=3; flexibility=8; relationship_score=4; description="Materials"}
    )
    inflows = @(
        @{amount=30000; expected_date="2026-04-01"; confidence=0.8; description="Client Payment"}
    )
} | ConvertTo-Json -Depth 10

$decisionResponse = Invoke-RestMethod -Uri "$baseUrl/decide" -Method POST -Headers $authHeader -Body $decisionBody
Write-Host "Summary: $($decisionResponse.summary)" -ForegroundColor Green
Write-Host "Decisions:" -ForegroundColor Cyan
foreach ($d in $decisionResponse.decisions) {
    Write-Host "  - $($d.description) (₹$($d.amount)): ACTION=$($d.action.ToUpper())" -ForegroundColor Yellow
    Write-Host "    Reasoning: $($d.reasoning)"
}

Write-Host "`n=== 5. Get Runway info ===" -ForegroundColor Cyan
$runwayResponse = Invoke-RestMethod -Uri "$baseUrl/runway/$userId" -Method GET -Headers $authHeader
Write-Host "Risk Level: $($runwayResponse.risk_level), Runway Days: $($runwayResponse.runway_days)" -ForegroundColor Green
