from sqlalchemy import Column, Integer, String, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from app.database import Base
from enum import Enum

class RoundStatus(str, Enum):
    """Valid round states"""
    BIDDING = "bidding"
    CALCULATED = "calculated"

class Round(Base):
    __tablename__ = "rounds"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id"))
    round_number = Column(Integer, default=1) # E.g., translates to a specific seed day
    status = Column(String, default=RoundStatus.BIDDING) # bidding, calculated

    session = relationship("Session", back_populates="rounds")
    bids = relationship("Bid", back_populates="round", cascade="all, delete-orphan")
    results = relationship("MarketResult", back_populates="round", cascade="all, delete-orphan")
    
    # Ensure no duplicate rounds in a session
    __table_args__ = (
        UniqueConstraint("session_id", "round_number", name="uq_session_round_number"),
        # Index for efficient round lookups by session
        Index("idx_round_session_number", "session_id", "round_number"),
    )
