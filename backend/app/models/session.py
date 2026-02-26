from sqlalchemy import Column, Integer, String, Float, Boolean
from sqlalchemy.orm import relationship
from app.database import Base

class Session(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    join_code = Column(String, unique=True, index=True)
    admin_id = Column(String, index=True) # Just a token or string to identifier admin
    status = Column(String, default="pending") # pending, active, finished
    
    # Settings
    start_day = Column(Integer, default=1) # The seed profile day to start on
    pro_rata_enabled = Column(Boolean, default=True)
    battery_max_mwh = Column(Float, default=100.0)
    battery_initial_mwh = Column(Float, default=50.0)
    battery_efficiency_charge = Column(Float, default=0.9)
    battery_efficiency_discharge = Column(Float, default=0.9)
    penalty_price = Column(Float, default=10.0)
    
    # Demands and Supplies Params
    base_demand_mw = Column(Float, default=2.0)
    
    users = relationship("User", back_populates="session")
    rounds = relationship("Round", back_populates="session")
