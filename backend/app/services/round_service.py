from sqlalchemy.orm import Session as DBSession
from sqlalchemy.exc import SQLAlchemyError
from app import models
from app.services.market_engine import MarketEngine
from app.services.battery_service import BatteryService
from app.services.penalty_service import PenaltyService
from app.schemas.market_models import MarketBid, HourlyMarketInput, MarketResult
from app.services.market import get_day_seed, generate_supply_curve
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

class RoundService:
    def __init__(self, db: DBSession):
        self.db = db
        self.market_engine = MarketEngine()
        self.battery_service = BatteryService()
        self.penalty_service = PenaltyService()

    def get_round_baseline(self, session_id: int, round_id: int):
        """Return bot-only baseline prices and volumes for 24 hours"""
        game_session = self.db.query(models.Session).filter(models.Session.id == session_id).first()
        if not game_session:
            raise ValueError("Session not found")

        current_round = self.db.query(models.Round).filter(models.Round.id == round_id).first()
        if not current_round:
            raise ValueError("Round not found")

        day_profile = get_day_seed(game_session.start_day + current_round.round_number - 1)
        if not day_profile:
            day_profile = [{"hour": h, "wind_planned_profile": 0, "solar_planned_profile": 0, "demand_forecast_profile": 1} for h in range(24)]
        hour_data_map = {d["hour"]: d for d in day_profile}

        baseline = []
        for hour in range(24):
            hour_data = hour_data_map.get(hour, {"wind_planned_profile": 0, "solar_planned_profile": 0, "demand_forecast_profile": 1})
            bot_supply = generate_supply_curve(hour_data, game_session)
            supply_curve = [MarketBid(bid_id=s["bid_id"], volume=s["volume"], price=s["price"], bid_type=False) for s in bot_supply]
            demand_curve = []
            inelastic_demand = game_session.base_demand_mw * hour_data.get("demand_forecast_profile", 1.0)

            market_input = HourlyMarketInput(
                hour=hour,
                supply_curve=supply_curve,
                demand_curve=demand_curve,
                inelastic_demand=inelastic_demand
            )

            result: MarketResult = self.market_engine.calculate_clearing(market_input)

            baseline.append({
                "hour": hour,
                "clearing_price": result.clearing_price,
                "clearing_volume": result.clearing_volume,
                "wind_profile": hour_data.get("wind_planned_profile", 0.0),
                "solar_profile": hour_data.get("solar_planned_profile", 0.0),
                "demand_profile": hour_data.get("demand_forecast_profile", 0.0),
            })

        return baseline

    def calculate_round_results(self, session_id: int, round_id: int):
        """Orchestrates the full 24-hour round calculation with battery physics and state updates.
        
        TRANSACTION SAFETY: Wrapped in try/except to rollback all changes if any error occurs mid-calculation.
        QUERY OPTIMIZATION: Filters bids per-hour at DB level instead of Python loop (avoids N+1 pattern).
        """
        try:
            # 1. Load context at once to avoid N+1 queries
            game_session = self.db.query(models.Session).filter(models.Session.id == session_id).first()
            current_round = self.db.query(models.Round).filter(models.Round.id == round_id).first()
            
            if not game_session or not current_round:
                raise ValueError(f"Session {session_id} or Round {round_id} not found")
            
            # FIX: Add max player count validation
            player_count = self.db.query(models.User).filter(models.User.session_id == session_id).count()
            if player_count > 500:
                logger.warning(f"Session {session_id} has {player_count} players - may impact performance")
            
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
                raise ValueError(f"Seed data not available for day {game_session.start_day + current_round.round_number - 1}")
            hour_data_map = {d["hour"]: d for d in day_profile}

            round_user_profit = {}
            round_user_penalty = {}

            # 2. Process each hour
            for hour in range(24):
                hour_data = hour_data_map.get(hour, {"wind_planned_profile": 0, "solar_planned_profile": 0, "demand_forecast_profile": 1})
                
                # OPTIMIZATION: Query bids for this specific hour only (DB-level filtering)
                hourly_player_bids = self.db.query(models.Bid).filter(
                    models.Bid.round_id == round_id,
                    models.Bid.hour == hour
                ).all()
                
                # Prepare Input Curves
                bot_supply = generate_supply_curve(hour_data, game_session)
                supply_curve = [MarketBid(bid_id=s["bid_id"], volume=s["volume"], price=s["price"], bid_type=False) for s in bot_supply]
                demand_curve = []
                
                # Map player bids for this hour
                for pb in hourly_player_bids:
                    bid = MarketBid(bid_id=str(pb.id), user_id=str(pb.user_id), volume=pb.volume_mwh, price=pb.price, bid_type=pb.bid_type)
                    if pb.bid_type:
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

                # 3.1 If pro-rata disabled, override fills for player bids
                if not game_session.pro_rata_enabled:
                    for pb in hourly_player_bids:
                        if pb.bid_type and pb.price >= result.clearing_price:
                            result.fills[str(pb.id)] = pb.volume_mwh
                        elif not pb.bid_type and pb.price <= result.clearing_price:
                            result.fills[str(pb.id)] = pb.volume_mwh

                # 4. Process Consequences (Battery Physics & Profit) using extracted services
                self._apply_market_outcomes(round_id, result, hourly_player_bids, team_states, game_session, round_user_profit, round_user_penalty)

            # 5. Store per-round user results
            for user_id, profit in round_user_profit.items():
                penalty = round_user_penalty.get(user_id, 0.0)
                player_round_record = models.PlayerRoundStats(
                    user_id=user_id,
                    round_id=round_id,
                    total_profit=round(profit, 2),
                    total_penalty=round(penalty, 2)
                )
                self.db.add(player_round_record)

            # 6. Finalize Round
            current_round.status = "calculated"

            # Auto-finish the session when the calculated round reaches planned duration
            # 
            #if current_round.round_number >= game_session.duration_days:
            #    game_session.status = "finished"

            self.db.commit()
            return current_round.round_number >= game_session.duration_days
            
        except SQLAlchemyError as e:
            # Database transaction failed - rollback all changes
            logger.error(f"Database error in calculate_round_results: {str(e)}")
            self.db.rollback()
            raise ValueError(f"Round calculation failed and rolled back: {str(e)}")
        except Exception as e:
            # Any other error - rollback
            logger.error(f"Unexpected error in calculate_round_results: {str(e)}")
            self.db.rollback()
            raise

    def _apply_market_outcomes(self, round_id: int, result: MarketResult, bids: List[models.Bid], team_states: Dict[str, models.TeamState], session: models.Session, profit_acc: dict, penalty_acc: dict):
        """Apply market clearing outcomes: battery physics, penalties, and profit updates.
        
        Uses extracted services: BatteryService (physics), PenaltyService (penalties)
        This maintains Single Responsibility Principle - this method coordinates, services execute.
        
        Flow:
        1. Get fill_volume from market
        2. Apply battery physics (capacity + bandwidth)
        3. Calculate profit on actual_delivered (always, regardless of physics success)
        4. Calculate penalty on unfilled = fill_volume - actual_delivered
        5. Update total_profit = previous + profit - penalty
        """
        for bid in bids:
            ts = team_states.get(bid.user_id)
            if not ts: continue

            fill_volume = result.fills.get(str(bid.id), 0.0)
            if fill_volume <= 1e-12: continue

            profit = 0.0
            actual_delivered = 0.0

            if bid.bid_type:
                # Battery Charging Physics using BatteryService
                charge_needed = self.battery_service.calculate_charge_needed(fill_volume, session.battery_efficiency_charge)
                ts.current_battery_mwh, charge_success, actual_delivered = self.battery_service.apply_charge(
                    ts.current_battery_mwh, 
                    charge_needed, 
                    session.battery_max_mwh,
                    session.bandwidth,
                    session.battery_efficiency_charge
                )
                # Calculate profit on actual delivered (always, regardless of physics success)
                profit = round(-(actual_delivered * result.clearing_price), 2)
            
            elif not bid.bid_type:
                # Battery Discharging Physics using BatteryService
                discharge_needed = self.battery_service.calculate_discharge_available(fill_volume, session.battery_efficiency_discharge)
                ts.current_battery_mwh, discharge_success, actual_delivered = self.battery_service.apply_discharge(
                    ts.current_battery_mwh, 
                    discharge_needed,
                    session.bandwidth,
                    session.battery_efficiency_discharge
                )
                # Calculate profit on actual delivered (always, regardless of physics success)
                profit = round(actual_delivered * result.clearing_price, 2)

            # Calculate unfilled volume and penalty
            unfilled_volume = fill_volume - actual_delivered
            total_penalty = self.penalty_service.calculate_penalty(
                unfilled_volume,
                result.clearing_price,
                session.penalty_price,
                session.penalty_k,
                session.penalty_b
            )

            # Update total profit: previous + profit - penalty
            ts.total_profit = round(float(ts.total_profit) + profit - total_penalty, 2)
            self.db.add(ts)

            # Persist filled volume to the bid record for transaction history
            bid.filled_volume = fill_volume
            self.db.add(bid)

            # Initialize per-round aggregators if needed
            profit_acc[bid.user_id] = profit_acc.get(bid.user_id, 0.0) + profit
            penalty_acc[bid.user_id] = penalty_acc.get(bid.user_id, 0.0) + total_penalty

            # Save penalty record for detail/analytics
            price_diff = abs(bid.price - result.clearing_price)
            penalty_record = models.Penalty(
                user_id=bid.user_id,
                round_id=round_id,
                hour=result.hour,
                player_price=bid.price,
                clearing_price=result.clearing_price,
                price_diff=price_diff,
                penalty_amount=total_penalty
            )
            self.db.add(penalty_record)

