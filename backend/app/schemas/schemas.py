from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import List, Optional
from datetime import datetime
from app.utils.sanitization import (
    sanitize_string, 
    sanitize_alphanumeric, 
    sanitize_join_code,
    validate_input
)

# --- Token / Auth (Simple) ---
class AdminJoin(BaseModel):
    admin_id: str

class AdminCreate(BaseModel):
    username: str = Field(..., min_length=1, max_length=50)
    password: str = Field(..., min_length=1, max_length=100)

class AdminLogin(BaseModel):
    username: str
    password: str

class AdminResponse(BaseModel):
    id: int
    username: str
    admin_token: str

    model_config = ConfigDict(from_attributes=True)

# --- Bids ---
class BidCreate(BaseModel):
    hour: int = Field(..., ge=0, le=23)
    volume_mwh: float = Field(..., gt=0.0)
    price: float = Field(..., ge=-100.0, le=500.0)
    bid_type: bool # True for 'buy' (charge), False for 'sell' (discharge)

class BidResponse(BidCreate):
    id: int
    user_id: int
    round_id: int
    filled_volume: float = 0.0

    model_config = ConfigDict(from_attributes=True)

# --- Team State ---
class TeamStateResponse(BaseModel):
    current_battery_mwh: float
    total_profit: float

    model_config = ConfigDict(from_attributes=True)

# --- User / Team ---
class UserCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    password: Optional[str] = Field(None, max_length=100)
    join_code: str = Field(..., min_length=1, max_length=10)
    
    @field_validator('name')
    @classmethod
    def sanitize_name(cls, v):
        """FIX: Comprehensive input sanitization - XSS/injection prevention."""
        return validate_input(v, field_name="name", max_length=255)
    
    @field_validator('join_code')
    @classmethod
    def sanitize_join_code_validator(cls, v):
        """FIX: Sanitize join code - alphanumeric only."""
        return sanitize_join_code(v)

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
    admin_id: str = Field(..., min_length=1, max_length=255)
    game_name: str = Field("Naujas žaidimas", min_length=1, max_length=255)
    start_day: int = Field(1, ge=1)
    duration_days: int = Field(5, ge=1, le=365)
    bandwidth: float = Field(50.0, gt=0.0)
    start_budget: float = Field(10000.0, ge=0.0)
    penalty_k: float = Field(0.5, ge=0.0)
    penalty_b: float = Field(5.0, ge=0.0)
    pro_rata_enabled: bool = True
    battery_max_mwh: float = Field(100.0, gt=0.0)
    battery_initial_mwh: float = Field(50.0, ge=0.0)
    battery_efficiency_charge: float = Field(0.9, ge=0.0, le=1.0)
    battery_efficiency_discharge: float = Field(0.9, ge=0.0, le=1.0)
    penalty_price: float = Field(10.0, ge=0.0)
    base_demand_mw: float = Field(3000.0, gt=0.0)
    max_wind_mw: float = Field(1000.0, gt=0.0)
    max_solar_mw: float = Field(1000.0, gt=0.0)
    max_demand_mw: float = Field(3000.0, gt=0.0)
    forecast_error_margin: float = Field(0.15, ge=0.0, le=1.0)
    
    @field_validator('admin_id')
    @classmethod
    def validate_admin_id(cls, v):
        """FIX: Comprehensive admin_id validation and sanitization."""
        if not v or len(v.strip()) == 0:
            raise ValueError('admin_id cannot be empty or whitespace')
        # Use comprehensive alphanumeric sanitization
        return sanitize_alphanumeric(v, max_length=255, allow_underscore=True, allow_hyphen=True)

class UserResponse(BaseModel):
    id: int
    name: str
    session_id: int
    password: Optional[str] = None
    state: Optional[TeamStateResponse] = None
    bids: List[BidResponse] = []

    model_config = ConfigDict(from_attributes=True)

class TransactionResponse(BaseModel):
    id: int
    type: str # 'buy' or 'sell'
    teamName: str
    mw: float
    price: float
    round: int

class SessionResponse(SessionCreate):
    id: int
    join_code: str
    status: str
    created_at: datetime
    current_round: int = 1
    current_day: int = 1
    market_price: float = 0.0
    demand: float = 0.0
    weather: str = "Giedra"
    teams: List[UserResponse] = []
    rounds: List[RoundResponse] = []
    transactions: List[TransactionResponse] = []

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
    total_profit: float
    total_penalty: float
    round_stats: List[RoundStatsEntry]

class StandingsResponse(BaseModel):
    session_id: int
    standings: List[StandingsEntry]

# --- Round Results (Detailed Market Analysis) ---
class HourlyMarketClearing(BaseModel):
    hour: int
    clearing_price: float
    clearing_volume: float

class PlayerHourBid(BaseModel):
    hour: int
    volume_mwh: float
    price: float
    bid_type: bool  # True = buy (charge), False = sell (discharge)

class PlayerRoundFill(BaseModel):
    player_name: str
    player_id: int
    total_volume_bought: float  # Total filled on buy bids
    total_volume_sold: float    # Total filled on sell bids
    round_profit: float
    round_penalty: float
    bids: List[PlayerHourBid]  # All bids for this round

class RoundResultsResponse(BaseModel):
    round_id: int
    round_number: int
    session_id: int
    status: str
    market_clearing: List[HourlyMarketClearing]  # 24 hours of market data
    player_results: List[PlayerRoundFill]  # Details per player
    
    model_config = ConfigDict(from_attributes=True)
