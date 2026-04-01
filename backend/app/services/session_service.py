from sqlalchemy.orm import Session
from app import models
from app.schemas import schemas
from typing import List
from fastapi import HTTPException
import random
import string
from app.services.market import get_day_seed, generate_supply_curve, calculate_clearing_price

class SessionService:
    def __init__(self, db: Session):
        self.db = db

    def create_session(self, session_in: schemas.SessionCreate) -> models.Session:
        code = self._generate_join_code()
        while self.db.query(models.Session).filter(models.Session.join_code == code).first():
            code = self._generate_join_code()

        db_session = models.Session(
            admin_id=session_in.admin_id,
            join_code=code,
            start_day=session_in.start_day,
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
            status="pending"
        )
        self.db.add(db_session)
        self.db.commit()
        self.db.refresh(db_session)
        return db_session

    def get_forecast(self, session_id: int, round_id: int) -> schemas.ForecastingResponse:
        session = self.db.query(models.Session).filter(models.Session.id == session_id).first()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        day_to_use = session.start_day + round_id - 1
        day_data = get_day_seed(day_to_use)
        
        if not day_data:
            raise HTTPException(status_code=404, detail="Seed data for this round not found")

        forecasts = []
        for hour_info in day_data:
            base_demand = session.base_demand_mw * hour_info.get("demand_forecast_profile", 0.5)
            bot_supply = generate_supply_curve(hour_info, session)
            
            predicted_price, _, _ = calculate_clearing_price(bot_supply, [], base_demand)
            
            margin = session.forecast_error_margin
            error_margin = random.uniform(1.0 - margin, 1.0 + margin)
            predicted_price = round(predicted_price * error_margin, 2)

            forecasts.append(schemas.HourlyForecast(
                hour=hour_info["hour"],
                predicted_price=predicted_price,
                wind_profile=hour_info.get("wind_planned_profile", 0.0),
                solar_profile=hour_info.get("solar_planned_profile", 0.0),
                demand_profile=hour_info.get("demand_forecast_profile", 0.0)
            ))

        return schemas.ForecastingResponse(round_id=round_id, forecast=forecasts)

    def _generate_join_code(self, length=6):
        return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))
