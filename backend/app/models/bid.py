from sqlalchemy import Column, Integer, Boolean, Float, ForeignKey, CheckConstraint, Index
from sqlalchemy.orm import relationship
from app.database import Base

class Bid(Base):
    __tablename__ = "bids"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    round_id = Column(Integer, ForeignKey("rounds.id"))
    hour = Column(Integer) # 0-23
    volume_mwh = Column(Float)
    filled_volume = Column(Float, default=0.0) # Actual volume cleared in the market
    price = Column(Float)
    bid_type = Column(Boolean) # True for 'buy' (charge), False for 'sell' (discharge)

    user = relationship("User", back_populates="bids")
    round = relationship("Round", back_populates="bids")
    
    # DB-level constraints for data integrity
    __table_args__ = (
        CheckConstraint("hour >= 0 AND hour <= 23", name="check_hour_range"),
        CheckConstraint("volume_mwh > 0", name="check_positive_volume"),
        CheckConstraint("price >= -100 AND price <= 500", name="check_price_range"),
        # Composite index for hourly filtering performance
        Index("idx_bid_round_hour", "round_id", "hour"),
        # Index for user bid lookups
        Index("idx_bid_user_round", "user_id", "round_id"),
    )
