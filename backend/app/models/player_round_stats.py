from sqlalchemy import Column, Integer, Float, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class PlayerRoundStats(Base):
    __tablename__ = "player_round_stats"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    round_id = Column(Integer, ForeignKey("rounds.id"), index=True)
    total_profit = Column(Float, default=0.0)
    total_penalty = Column(Float, default=0.0)

    user = relationship("User")
    round = relationship("Round")
