from sqlalchemy import Column, Integer, Float, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class Penalty(Base):
    __tablename__ = "penalties"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    round_id = Column(Integer, ForeignKey("rounds.id"), index=True)
    hour = Column(Integer)
    player_price = Column(Float)
    clearing_price = Column(Float)
    price_diff = Column(Float)
    penalty_amount = Column(Float)

    user = relationship("User")
    round = relationship("Round")
