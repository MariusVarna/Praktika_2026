from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id"))

    session = relationship("Session", back_populates="users")
    bids = relationship("Bid", back_populates="user")
    state = relationship("TeamState", back_populates="user", uselist=False)
