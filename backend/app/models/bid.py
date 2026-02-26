from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class Bid(Base):
    __tablename__ = "bids"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    round_id = Column(Integer, ForeignKey("rounds.id"))
    hour = Column(Integer) # 0-23
    volume_mwh = Column(Float)
    price = Column(Float)
    bid_type = Column(String) # 'buy' (charge) or 'sell' (discharge)

    user = relationship("User", back_populates="bids")
    round = relationship("Round", back_populates="bids")
