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
    budget: float
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
    duration_days: Optional[int] = 1
    start_budget: Optional[float] = 1000.0
    penalty_k: Optional[float] = 0.5
    penalty_b: Optional[float] = 5.0
    pro_rata_enabled: Optional[bool] = True
    battery_max_mwh: Optional[float] = 100.0
    battery_initial_mwh: Optional[float] = 50.0
    battery_efficiency_charge: Optional[float] = 0.9
    battery_efficiency_discharge: Optional[float] = 0.9
    penalty_price: Optional[float] = 10.0
    base_demand_mw: Optional[float] = 3000.0
    max_wind_mw: Optional[float] = 1000.0
    max_solar_mw: Optional[float] = 1000.0
    max_demand_mw: Optional[float] = 3000.0
    forecast_error_margin: Optional[float] = 0.15

class SessionResponse(SessionCreate):
    id: int
    join_code: str
    status: str

    model_config = ConfigDict(from_attributes=True)

# --- Market Results ---
class MarketResultResponse(BaseModel):
    clearing_price: float
    total_volume_cleared: float
    model_config = ConfigDict(from_attributes=True)

class HourlyForecast(BaseModel):
    hour: int
    predicted_price: float
    wind_profile: float
    solar_profile: float
    demand_profile: float

class ForecastingResponse(BaseModel):
    round_id: int
    forecast: List[HourlyForecast]

class BaselineHour(BaseModel):
    hour: int
    clearing_price: float
    clearing_volume: float
    wind_profile: float
    solar_profile: float
    demand_profile: float

class BaselineResponse(BaseModel):
    round_id: int
    baseline: List[BaselineHour]

class RoundStatsEntry(BaseModel):
    round_id: int
    round_number: int
    total_profit: float
    total_penalty: float

class StandingsEntry(BaseModel):
    user_id: int
    name: str
    current_battery_mwh: float
    budget: float
    total_profit: float
    total_penalty: float
    round_stats: List[RoundStatsEntry]

class StandingsResponse(BaseModel):
    session_id: int
    standings: List[StandingsEntry]
