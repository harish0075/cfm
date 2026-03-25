"""
User ORM model.
Represents an onboarded user with a unique phone number and cash balance.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from database import Base


class User(Base):
    __tablename__ = "users"

    # Primary key — UUID generated server-side
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    name = Column(String(255), nullable=False)

    # Phone is the unique identifier for the user
    phone = Column(String(20), unique=True, nullable=False, index=True)

    # Bcrypt-hashed password
    password_hash = Column(String(128), nullable=False)

    # Current cash balance — updated as inflows/outflows are recorded
    cash_balance = Column(Numeric(precision=15, scale=2), nullable=False, default=0)

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    assets = relationship("Asset", back_populates="user", cascade="all, delete-orphan")
    entries = relationship(
        "FinancialEntry", back_populates="user", cascade="all, delete-orphan"
    )
