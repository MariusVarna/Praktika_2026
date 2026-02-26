from sqlalchemy import Column, Integer, Float, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class MarketResult(Base):
    __tablename__ = "market_results"

    id = Column(Integer, primary_key=True, index=True)
    round_id = Column(Integer, ForeignKey("rounds.id"))
    hour = Column(Integer) # 0-23
    clearing_price = Column(Float)
    total_volume_cleared = Column(Float)

    round = relationship("Round", back_populates="results")
