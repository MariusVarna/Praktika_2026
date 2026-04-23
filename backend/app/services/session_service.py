from sqlalchemy.orm import Session
from app import models
from app.schemas import schemas
from app.schemas.market_models import MarketBid, HourlyMarketInput
from typing import List
from fastapi import HTTPException
import random
import string
from app.services.market import get_day_seed, generate_supply_curve
from app.services.market_engine import MarketEngine


class SessionService:
    def __init__(self, db: Session):
        self.db = db
        self.market_engine = MarketEngine()

    def create_session(self, session_in: schemas.SessionCreate) -> schemas.SessionResponse:
        # FIX: Add validation for battery_initial_mwh <= battery_max_mwh
        if session_in.battery_initial_mwh > session_in.battery_max_mwh:
            raise ValueError("Initial battery capacity cannot exceed max battery capacity")

        # FIX: Add validation for base_demand_mw and max_demand_mw consistency
        if session_in.max_demand_mw < session_in.base_demand_mw:
            raise ValueError("Max demand must be >= base demand")

        code = self._generate_join_code()
        while self.db.query(models.Session).filter(models.Session.join_code == code).first():
            code = self._generate_join_code()

        db_session = models.Session(
            admin_id=session_in.admin_id,
            game_name=session_in.game_name,
            join_code=code,
            start_day=session_in.start_day,
            duration_days=session_in.duration_days,
            bandwidth=session_in.bandwidth,
            start_budget=session_in.start_budget,
            penalty_k=session_in.penalty_k,
            penalty_b=session_in.penalty_b,
            pro_rata_enabled=session_in.pro_rata_enabled,
            battery_max_mwh=session_in.battery_max_mwh,
            battery_initial_mwh=session_in.battery_initial_mwh,
            battery_efficiency_charge=session_in.battery_efficiency_charge,
            battery_efficiency_discharge=session_in.battery_efficiency_discharge,
            penalty_price=session_in.penalty_price,
            base_demand_mw=session_in.base_demand_mw,
            max_wind_mw=session_in.max_wind_mw,
            max_solar_mw=session_in.max_solar_mw,
            max_demand_mw=session_in.max_demand_mw,
            forecast_error_margin=session_in.forecast_error_margin,
            status="waiting"
        )
        self.db.add(db_session)
        self.db.commit()
        self.db.refresh(db_session)
        return self._enrich_session(db_session)

    def list_sessions(self, admin_id: str) -> List[schemas.SessionResponse]:
        sessions = self.db.query(models.Session).filter(models.Session.admin_id == admin_id).all()
        return [self._enrich_session(s) for s in sessions]

    def get_session(self, session_id: int) -> schemas.SessionResponse:
        session = self.db.query(models.Session).filter(models.Session.id == session_id).first()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        return self._enrich_session(session)

    def get_session_by_pin(self, pin: str) -> schemas.SessionResponse:
        strict_pin = pin.strip().upper()
        session = self.db.query(models.Session).filter(models.Session.join_code == strict_pin).first()

        if not session:
            raise HTTPException(status_code=404, detail="Session with this PIN not found")
        return self._enrich_session(session)

    def _enrich_session(self, session: models.Session) -> schemas.SessionResponse:
        # Calculate current round and day
        current_round_num = 1
        current_round_id = None
        latest_calc_round = None

        if session.rounds:
            current_round_num = max(r.round_number for r in session.rounds)

            active_round = next((r for r in session.rounds if r.status == "bidding"), None)
            if active_round:
                current_round_id = active_round.id
                current_round_num = active_round.round_number
            else:
                current_round_id = max(session.rounds, key=lambda r: r.round_number).id

            calc_rounds = [r for r in session.rounds if r.status == "calculated"]
            if calc_rounds:
                latest_calc_round = max(calc_rounds, key=lambda r: r.round_number)

        current_day = session.start_day + current_round_num - 1

        # Dynamic stats from last round
        m_price = 70.0
        m_demand = 0.0

        if latest_calc_round and latest_calc_round.results:
            prices = [res.clearing_price for res in latest_calc_round.results]
            vols = [res.total_volume_cleared for res in latest_calc_round.results]

            if prices:
                m_price = round(sum(prices) / len(prices), 2)

            m_demand = round(sum(vols), 1)

        # Get last 15 transactions
        recent_txs = []
        try:
            tx_data = (
                self.db.query(models.Bid, models.User, models.Round)
                .join(models.User, models.Bid.user_id == models.User.id)
                .join(models.Round, models.Bid.round_id == models.Round.id)
                .filter(models.User.session_id == session.id, models.Bid.filled_volume > 1e-6)
                .order_by(models.Bid.id.desc())
                .limit(15)
                .all()
            )

            for b, u, r in tx_data:
                recent_txs.append({
                    "id": b.id,
                    "type": "buy" if b.bid_type else "sell",
                    "teamName": u.name,
                    "teamId": u.id,
                    "mw": round(b.filled_volume, 2),
                    "price": b.price,
                    "round": r.round_number
                })
        except Exception:
            pass

        # Build teams
        teams_data = []
        for u in session.users:
            bid_rows = {}

            for b in u.bids:
                round_num = b.round.round_number

                if round_num not in bid_rows:
                    bid_rows[round_num] = {}

                if b.hour not in bid_rows[round_num]:
                    bid_rows[round_num][b.hour] = []

                bid_rows[round_num][b.hour].append({
                    "price": b.price,
                    "mw": b.volume_mwh,
                    "type": "buy" if b.bid_type else "sell"
                })

            bid_rows_array = {}
            for round_num, hours in bid_rows.items():
                hour_array = []
                for h in range(24):
                    hour_array.append(hours.get(h, []))
                bid_rows_array[round_num] = hour_array

            teams_data.append({
                "id": u.id,
                "session_id": session.id,  # ADDED: Required field
                "name": u.name,
                "password": u.password,
                "balance": float(u.state.total_profit) if u.state else session.start_budget,
                "batteryStored": float(u.state.current_battery_mwh) if u.state else session.battery_initial_mwh,
                "batteryCapacity": session.battery_max_mwh,
                "bids": [
                    {
                        "id": b.id,  # ADDED: Required field
                        "user_id": b.user_id,  # ADDED: Required field
                        "round_id": b.round_id,  # ADDED: Required field
                        "round": b.round.round_number,
                        "hour": b.hour,
                        "price": b.price,
                        "volume_mwh": b.volume_mwh,  # CHANGED: was "mw"
                        "bid_type": True if b.bid_type else False,
                        "submitted": True,
                        "filled_volume": b.filled_volume
                    }
                    for b in u.bids
                ],
                "bidRows": bid_rows_array,
                "roundHistory": []
            })

        return schemas.SessionResponse.model_validate({
            **{c.name: getattr(session, c.name) for c in session.__table__.columns},
            "current_round": current_round_num,
            "current_round_id": current_round_id,
            "current_day": current_day,
            "market_price": m_price,
            "demand": m_demand,
            "weather": "Giedra",
            "teams": teams_data,
            "rounds": session.rounds,
            "transactions": recent_txs
        })

    def get_forecast(self, session_id: int, round_id: int) -> schemas.ForecastingResponse:
        session = self.db.query(models.Session).filter(models.Session.id == session_id).first()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        round_obj = self.db.query(models.Round).filter(models.Round.id == round_id).first()
        if not round_obj or round_obj.session_id != session_id:
            raise HTTPException(status_code=404, detail="Round not found in session")

        day_to_use = session.start_day + round_obj.round_number - 1
        day_data = get_day_seed(day_to_use)

        if not day_data:
            raise HTTPException(status_code=404, detail="Seed data for this round not found")

        # Create a deterministic seed based on session_id, round_id, and round_number
        # This ensures the same round always returns the same forecast
        deterministic_seed = hash(f"{session_id}_{round_obj.id}_{round_obj.round_number}") % 2**32
    
        forecasts = []
        for hour_info in day_data:
            base_demand = session.base_demand_mw * hour_info.get("demand_forecast_profile", 0.5)
            bot_supply = generate_supply_curve(hour_info, session)

            supply_curve = [
                MarketBid(
                    bid_id=s["bid_id"],
                    volume=s["volume"],
                    price=s["price"],
                    bid_type=False
                )
                for s in bot_supply
            ]

            market_input = HourlyMarketInput(
                hour=hour_info["hour"],
                supply_curve=supply_curve,
                demand_curve=[],
                inelastic_demand=base_demand
            )

            result = self.market_engine.calculate_clearing(market_input)
            predicted_price = result.clearing_price
        
            # Use deterministic random with seed based on hour as well
            # This ensures each hour gets a consistent error margin
            hour_seed = deterministic_seed + hour_info["hour"]
            random.seed(hour_seed)
        
            margin = session.forecast_error_margin
            error_margin = random.uniform(1.0 - margin, 1.0 + margin)
            predicted_price = round(predicted_price * error_margin, 2)
        
            # Reset random seed to avoid affecting other parts
            random.seed()

            forecasts.append(
                schemas.HourlyForecast(
                    hour=hour_info["hour"],
                    predicted_price=predicted_price,
                    wind_profile=hour_info.get("wind_planned_profile", 0.0),
                    solar_profile=hour_info.get("solar_planned_profile", 0.0),
                    demand_profile=hour_info.get("demand_forecast_profile", 0.0)
                )
            )

        return schemas.ForecastingResponse(round_id=round_id, forecast=forecasts)

    def get_standings(self, session_id: int) -> dict:
        session = self.db.query(models.Session).filter(models.Session.id == session_id).first()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        standings_data = []

        team_states = (
            self.db.query(models.TeamState, models.User)
            .join(models.User, models.TeamState.user_id == models.User.id)
            .filter(models.User.session_id == session_id)
            .order_by(models.TeamState.total_profit.desc())
            .all()
        )

        user_round_stats = {}
        rows = (
            self.db.query(models.PlayerRoundStats, models.Round)
            .join(models.Round, models.PlayerRoundStats.round_id == models.Round.id)
            .filter(models.Round.session_id == session_id)
            .all()
        )

        for prs, rnd in rows:
            if prs.user_id not in user_round_stats:
                user_round_stats[prs.user_id] = []

            user_round_stats[prs.user_id].append({
                "round_id": prs.round_id,
                "round_number": rnd.round_number,
                "total_profit": float(prs.total_profit),
                "total_penalty": float(prs.total_penalty)
            })

        for ts, user in team_states:
            rounds_for_user = user_round_stats.get(user.id, [])
            total_penalty = sum(r["total_penalty"] for r in rounds_for_user)

            standings_data.append({
                "user_id": user.id,
                "name": user.name,
                "current_battery_mwh": float(ts.current_battery_mwh),
                "total_profit": float(ts.total_profit),
                "total_penalty": total_penalty,
                "round_stats": rounds_for_user
            })

        return {"session_id": session_id, "standings": standings_data}

    def _generate_join_code(self, length=6):
        chars = "".join([c for c in string.ascii_uppercase + string.digits if c not in '0OI1'])
        return ''.join(random.choices(chars, k=length))