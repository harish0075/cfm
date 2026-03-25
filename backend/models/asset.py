"""
Asset ORM model.
Represents a user's real-world asset stored as a last-resort liquidity fallback.
"""

import uuid

from sqlalchemy import Column, Enum, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from database import Base


class Asset(Base):
    __tablename__ = "assets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Owner reference
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    # Type of asset: house, vehicle, gold, or other
    asset_type = Column(
        Enum("house", "vehicle", "gold", "other", name="asset_type_enum"),
        nullable=False,
    )

    # Human-readable name (e.g. "Main House", "Honda City")
    name = Column(String(255), nullable=True)

    # Estimated market value
    estimated_value = Column(Numeric(precision=15, scale=2), nullable=False)

    # How quickly the asset can be converted to cash
    liquidity = Column(
        Enum("low", "medium", "high", name="liquidity_enum"), nullable=False
    )

    # ── Relationship ──────────────────────────────────────────────────────────
    user = relationship("User", back_populates="assets")
