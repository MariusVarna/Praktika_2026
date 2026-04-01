from sqlalchemy.orm import Session as DBSession
from app import models
from app.services.market_engine import MarketEngine
from app.schemas.market_models import MarketBid, HourlyMarketInput, MarketResult, BidType
from app.services.market import get_day_seed, generate_supply_curve
from typing import List, Dict, Optional

class RoundService:
    def __init__(self, db: DBSession):
        self.db = db
        self.market_engine = MarketEngine()

    def calculate_round_results(self, session_id: int, round_id: int):
        """Orchestrates the full 24-hour round calculation with battery physics and state updates."""
        # 1. Load context at once to avoid N+1 queries
        game_session = self.db.query(models.Session).filter(models.Session.id == session_id).first()
        current_round = self.db.query(models.Round).filter(models.Round.id == round_id).first()
        all_bids = self.db.query(models.Bid).filter(models.Bid.round_id == round_id).all()
        # Join with User to get all states for the specific session
        team_states = {
            ts.user_id: ts for ts in self.db.query(models.TeamState)
            .join(models.User)
            .filter(models.User.session_id == session_id)
            .all()
        }

        # Get the day seed
        day_profile = get_day_seed(game_session.start_day + current_round.round_number - 1)
        if not day_profile:
            day_profile = [{"hour": h, "wind_planned_profile": 0, "solar_planned_profile": 0, "demand_forecast_profile": 1} for h in range(24)]
        hour_data_map = {d["hour"]: d for d in day_profile}

        # 2. Process each hour
        for hour in range(24):
            hour_data = hour_data_map.get(hour, {"wind_planned_profile": 0, "solar_planned_profile": 0, "demand_forecast_profile": 1})
            
            # Prepare Input Curves
            bot_supply = generate_supply_curve(hour_data, game_session)
            supply_curve = [MarketBid(bid_id=s["bid_id"], volume=s["volume"], price=s["price"], bid_type=BidType.SELL) for s in bot_supply]
            demand_curve = []
            
            # Map player bids for this hour
            hourly_player_bids = [b for b in all_bids if b.hour == hour]
            for pb in hourly_player_bids:
                bid = MarketBid(bid_id=str(pb.id), user_id=pb.user_id, volume=pb.volume_mwh, price=pb.price, bid_type=pb.bid_type)
                if pb.bid_type == 'buy':
                    demand_curve.append(bid)
                else:
                    supply_curve.append(bid)

            # System Demand Configuration
            inelastic_demand = game_session.base_demand_mw * hour_data.get("demand_forecast_profile", 1.0)
            
            # Run Market Engine
            market_input = HourlyMarketInput(
                hour=hour,
                supply_curve=supply_curve,
                demand_curve=demand_curve,
                inelastic_demand=inelastic_demand
            )
            result: MarketResult = self.market_engine.calculate_clearing(market_input)

            # 3. Store Market Result
            db_result = models.MarketResult(
                round_id=round_id,
                hour=hour,
                clearing_price=result.clearing_price,
                total_volume_cleared=result.clearing_volume
            )
            self.db.add(db_result)

            # 4. Process Consequences (Battery Physics & Profit)
            self._apply_market_outcomes(result, hourly_player_bids, team_states, game_session)

        # 5. Finalize Round
        current_round.status = "calculated"
        self.db.commit()

    def _apply_market_outcomes(self, result: MarketResult, bids: List[models.Bid], team_states: Dict[str, models.TeamState], session: models.Session):
        for bid in bids:
            ts = team_states.get(bid.user_id)
            if not ts: continue

            fill_volume = result.fills.get(str(bid.id), 0.0)
            if fill_volume <= 1e-12: continue

            penalty = 0.0
            profit = 0.0

            if bid.bid_type == 'buy':
                # Battery Charging Physics
                charge_needed = fill_volume * session.battery_efficiency_charge
                if ts.current_battery_mwh + charge_needed <= session.battery_max_mwh:
                    ts.current_battery_mwh = round(ts.current_battery_mwh + charge_needed, 4)
                    profit = round(-(fill_volume * result.clearing_price), 2)
                else:
                    # Penalty for promised to buy but can't store
                    penalty = round(fill_volume * session.penalty_price, 2)
            
            elif bid.bid_type == 'sell':
                # Battery Discharging Physics
                discharge_needed = fill_volume / session.battery_efficiency_discharge
                if ts.current_battery_mwh >= discharge_needed:
                    ts.current_battery_mwh = round(ts.current_battery_mwh - discharge_needed, 4)
                    profit = round(fill_volume * result.clearing_price, 2)
                else:
                    # Penalty: Promised to sell but battery is empty
                    penalty = round(fill_volume * session.penalty_price, 2)

            ts.total_profit = round(float(ts.total_profit) + profit - penalty, 2)
            self.db.add(ts)
