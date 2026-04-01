from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from enum import Enum

class BidType(str, Enum):
    BUY = "buy"
    SELL = "sell"

class MarketBid(BaseModel):
    bid_id: str
    user_id: Optional[str] = None
    volume: float
    price: float
    bid_type: BidType

class MarketResult(BaseModel):
    hour: int
    clearing_price: float
    clearing_volume: float
    fills: Dict[str, float]  # bid_id -> filled_volume

class HourlyMarketInput(BaseModel):
    hour: int
    supply_curve: List[MarketBid]
    demand_curve: List[MarketBid]
    inelastic_demand: float = 0.0

class BatteryConfig(BaseModel):
    max_mwh: float
    efficiency_charge: float
    efficiency_discharge: float
    penalty_price: float
