from sqlalchemy import Column, Integer, Float, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class TeamState(Base):
    __tablename__ = "team_states"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    current_battery_mwh = Column(Float, default=0.0)
    total_profit = Column(Float, default=0.0)

    user = relationship("User", back_populates="state")
