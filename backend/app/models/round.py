from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class Round(Base):
    __tablename__ = "rounds"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id"))
    round_number = Column(Integer, default=1) # E.g., translates to a specific seed day
    status = Column(String, default="bidding") # bidding, calculated

    session = relationship("Session", back_populates="rounds")
    bids = relationship("Bid", back_populates="round")
    results = relationship("MarketResult", back_populates="round")
