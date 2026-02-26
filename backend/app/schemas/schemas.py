from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from datetime import datetime

# --- Token / Auth (Simple) ---
class AdminJoin(BaseModel):
    admin_id: str

# --- Bids ---
class BidCreate(BaseModel):
    hour: int
    volume_mwh: float
    price: float
    bid_type: str # 'buy' or 'sell'

class BidResponse(BidCreate):
    id: int
    user_id: int
    round_id: int

    model_config = ConfigDict(from_attributes=True)

# --- Team State ---
class TeamStateResponse(BaseModel):
    current_battery_mwh: float
    total_profit: float

    model_config = ConfigDict(from_attributes=True)

# --- User / Team ---
class UserCreate(BaseModel):
    name: str
    join_code: str

class UserResponse(BaseModel):
    id: int
    name: str
    session_id: int
    state: Optional[TeamStateResponse] = None

    model_config = ConfigDict(from_attributes=True)

# --- Round ---
class RoundResponse(BaseModel):
    id: int
    session_id: int
    round_number: int
    status: str

    model_config = ConfigDict(from_attributes=True)

# --- Session ---
class SessionCreate(BaseModel):
    admin_id: str
    start_day: Optional[int] = 1
    pro_rata_enabled: Optional[bool] = True
    battery_max_mwh: Optional[float] = 100.0
    battery_initial_mwh: Optional[float] = 50.0
    battery_efficiency_charge: Optional[float] = 0.9
    battery_efficiency_discharge: Optional[float] = 0.9
    penalty_price: Optional[float] = 10.0
    base_demand_mw: Optional[float] = 2.0

class SessionResponse(SessionCreate):
    id: int
    join_code: str
    status: str

    model_config = ConfigDict(from_attributes=True)

# --- Market Results ---
class MarketResultResponse(BaseModel):
    hour: int
    clearing_price: float
    total_volume_cleared: float

    model_config = ConfigDict(from_attributes=True)
