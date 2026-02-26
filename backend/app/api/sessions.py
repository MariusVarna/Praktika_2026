from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import random
import string
from app.database import get_db
from app import models
from app.schemas import schemas

router = APIRouter()

def generate_join_code(length=6):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

@router.post("/", response_model=schemas.SessionResponse)
def create_session(session_in: schemas.SessionCreate, db: Session = Depends(get_db)):
    """Admin creates a new session."""
    code = generate_join_code()
    # Ensure uniqueness
    while db.query(models.Session).filter(models.Session.join_code == code).first():
        code = generate_join_code()
        
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
    db.add(db_session)
    db.commit()
    db.refresh(db_session)
    return db_session

@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(session_id: int, admin_id: str, db: Session = Depends(get_db)):
    """Admin deletes a session."""
    session = db.query(models.Session).filter(models.Session.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.admin_id != admin_id:
        raise HTTPException(status_code=403, detail="Not authorized")
        
    db.delete(session)
    db.commit()
    return None

from app.services.market import get_day_seed, generate_supply_curve, calculate_clearing_price

@router.get("/{session_id}/round/{round_id}/forecast", response_model=schemas.ForecastingResponse)
def get_round_forecast(session_id: int, round_id: int, db: Session = Depends(get_db)):
    """Provides a price and profile forecast for the round with ~15% error margin."""
    session = db.query(models.Session).filter(models.Session.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Calculate which day from seed data to use
    day_to_use = str(session.start_day + round_id - 1)
    day_data = get_day_seed(day_to_use)
    
    if not day_data:
        raise HTTPException(status_code=404, detail="Seed data for this round not found")

    forecasts = []
    for hour_info in day_data:
        # Calculate base predicted price (Bots only)
        base_demand = session.base_demand_mw * hour_info.get("demand_forecast_profile", 0.5)
        bot_supply = generate_supply_curve(hour_info, session)
        
        # Calculate clearing price
        predicted_price, _, _ = calculate_clearing_price(bot_supply, [], base_demand)
        
        # Add dynamic random error based on session settings
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
