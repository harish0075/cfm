"""
FinancialEntry ORM model.
Represents a single normalized financial event (inflow or outflow).
All input sources (text, SMS, OCR, bank, audio) converge into this structure.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, Date, DateTime, Enum, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy import ForeignKey

from database import Base


class FinancialEntry(Base):
    __tablename__ = "financial_entries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Owner reference
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    # inflow (money coming in) or outflow (money going out)
    type = Column(
        Enum("inflow", "outflow", name="entry_type_enum"), nullable=False
    )

    # Monetary amount for this entry
    amount = Column(Numeric(precision=15, scale=2), nullable=False)

    # Normalized date of the financial event (YYYY-MM-DD)
    date = Column(Date, nullable=False)

    # Where this entry originated: text, sms, ocr, bank, audio
    source = Column(
        Enum("text", "sms", "ocr", "bank", "audio", name="source_enum"),
        nullable=False,
    )

    # Human-readable description of the entry (e.g. "Rent payment")
    description = Column(String(500), nullable=True)

    # How confident the system is in the extracted data (0.0 – 1.0)
    confidence_score = Column(Numeric(precision=3, scale=2), nullable=False, default=0.9)

    # Risk classification for the entry
    risk_level = Column(
        Enum("low", "medium", "high", name="risk_level_enum"),
        nullable=False,
        default="low",
    )

    # Flexibility score indicating how adjustable this entry is (1–10)
    flexibility = Column(Integer, nullable=False, default=5)

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # ── Relationship ──────────────────────────────────────────────────────────
    user = relationship("User", back_populates="entries")
