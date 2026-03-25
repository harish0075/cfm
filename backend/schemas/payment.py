"""
Schemas for the Payment API.
"""
from pydantic import BaseModel, Field

class PaymentRequest(BaseModel):
    amount: float = Field(..., gt=0, description="Amount to pay")
    description: str = Field(..., description="Description of the payment")

class PaymentResponse(BaseModel):
    success: bool
    transaction_id: str
    new_balance: float
    message: str
