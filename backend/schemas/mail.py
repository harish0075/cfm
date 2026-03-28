from pydantic import BaseModel, Field


class MailAuthorizeResponse(BaseModel):
    authorization_url: str


class MailStatusResponse(BaseModel):
    connected: bool
    provider: str | None = None
    account_email: str | None = None


class NegotiationMailRequest(BaseModel):
    obligation_description: str = Field(..., min_length=1, max_length=500)
    amount: float = Field(..., ge=0)
    days_to_due: int = Field(..., ge=0)
    to_email: str | None = Field(None, max_length=320)
    """Counterparty address; required when send_now is true."""
    note: str | None = Field(None, max_length=2000)
    send_now: bool = True
    """If true (default), sends immediately via Graph; if false, creates a draft in the user's mailbox."""


class NegotiationMailResponse(BaseModel):
    mode: str  # "draft" | "sent"
    web_link: str | None = None
