from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, func
from sqlalchemy.orm import relationship
from app.database import Base
from enum import Enum

class SessionStatus(str, Enum):
    """Valid session states"""
    PENDING = "pending"
    ACTIVE = "active"
    FINISHED = "finished"

class Session(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    join_code = Column(String, unique=True, index=True)
    admin_id = Column(String, index=True) # Just a token or string to identifier admin
    game_name = Column(String, default="Naujas žaidimas")
    status = Column(String, default=SessionStatus.PENDING) # pending, active, finished
    created_at = Column(DateTime, server_default=func.now())
    
    # Settings
    start_day = Column(Integer, default=1) # The seed profile day to start on
    duration_days = Column(Integer, default=5)
    bandwidth = Column(Float, default=50.0) # Max charge/discharge rate in MW/hour
    start_budget = Column(Float, default=10000.0)
    penalty_k = Column(Float, default=0.5)
    penalty_b = Column(Float, default=5.0)
    pro_rata_enabled = Column(Boolean, default=True)
    forecast_error_margin = Column(Float, default=0.15)
    battery_max_mwh = Column(Float, default=100.0)
    battery_initial_mwh = Column(Float, default=50.0)
    battery_efficiency_charge = Column(Float, default=0.9)
    battery_efficiency_discharge = Column(Float, default=0.9)
    penalty_price = Column(Float, default=10.0)
    
    # Demands and Supplies Params
    base_demand_mw = Column(Float, default=3000.0)
    max_wind_mw = Column(Float, default=1000.0)
    max_solar_mw = Column(Float, default=1000.0)
    max_demand_mw = Column(Float, default=3000.0)
    
    users = relationship("User", back_populates="session", cascade="all, delete-orphan")
    rounds = relationship("Round", back_populates="session", cascade="all, delete-orphan")
