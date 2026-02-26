from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app import models
from app.schemas import schemas
from app.websockets import manager
from app.services.market import get_day_seed, generate_supply_curve, calculate_clearing_price

router = APIRouter()

@router.post("/{session_id}/start", response_model=schemas.RoundResponse)
async def start_session(session_id: int, admin_id: str, db: Session = Depends(get_db)):
    """Admin starts the session, creating round 1."""
    session = db.query(models.Session).filter(models.Session.id == session_id).first()
    if not session or session.admin_id != admin_id:
        raise HTTPException(status_code=404, detail="Session not found or unauthorized")
        
    if session.status != "pending":
        raise HTTPException(status_code=400, detail="Session already started")
        
    session.status = "active"
    
    # Create first round
    new_round = models.Round(session_id=session.id, round_number=1, status="bidding")
    db.add(new_round)
    db.commit()
    db.refresh(new_round)
    
    await manager.broadcast_to_session(session.id, {"event": "SESSION_STARTED", "round_id": new_round.id, "round_number": 1})
    return new_round

@router.post("/{session_id}/round/{round_id}/calculate")
async def calculate_round(session_id: int, round_id: int, admin_id: str, db: Session = Depends(get_db)):
    """Admin ends bidding for the round and calculates results."""
    session = db.query(models.Session).filter(models.Session.id == session_id).first()
    if not session or session.admin_id != admin_id:
        raise HTTPException(status_code=404, detail="Unauthorized")
        
    current_round = db.query(models.Round).filter(models.Round.id == round_id).first()
    if not current_round or current_round.status != "bidding":
        raise HTTPException(status_code=400, detail="Round is not in bidding state")
        
    # 1. Get seed data for the day
    day_profile = get_day_seed(session.start_day + current_round.round_number - 1)
    
    if not day_profile:
        # Fallback if we run out of days
        day_profile = [{"hour": h, "wind_planned_profile": 0, "solar_planned_profile": 0, "demand_forecast_profile": 1} for h in range(24)]

    # Map profiles by hour
    hour_data_map = {d["hour"]: d for d in day_profile}
    
    # Process each hour 0-23
    for hour in range(24):
        hour_data = hour_data_map.get(hour, {"wind_planned_profile": 0, "solar_planned_profile": 0, "demand_forecast_profile": 1})
        
        # Generator bots
        supply_curve = generate_supply_curve(hour_data, session)
        
        # Get player bids for this round & hour
        bids = db.query(models.Bid).filter(models.Bid.round_id == round_id, models.Bid.hour == hour).all()
        
        # Construct elastic demand
        demand_curve = []
        for b in bids:
            if b.bid_type == 'buy':
                demand_curve.append({"volume": b.volume_mwh, "price": b.price, "bid_id": b.id})
            elif b.bid_type == 'sell':
                supply_curve.append({"volume": b.volume_mwh, "price": b.price, "bid_id": b.id})
                
        # Calculate clearing
        c_price, c_vol, fill_map = calculate_clearing_price(supply_curve, demand_curve, session.base_demand_mw * hour_data.get("demand_forecast_profile", 1))
        
        # Save market result
        m_result = models.MarketResult(
            round_id=round_id,
            hour=hour,
            clearing_price=c_price,
            total_volume_cleared=c_vol
        )
        db.add(m_result)
        
        # Evaluate player bids & update battery states
        for b in bids:
            team_state = db.query(models.TeamState).filter(models.TeamState.user_id == b.user_id).first()
            if not team_state: continue
            
            fill_volume = 0.0
            if session.pro_rata_enabled:
                fill_volume = fill_map.get(b.id, 0.0)
            else:
                # Simple mode: if price meets clearing, you get everything
                if b.bid_type == 'buy' and b.price >= c_price:
                    fill_volume = b.volume_mwh
                elif b.bid_type == 'sell' and b.price <= c_price:
                    fill_volume = b.volume_mwh

            if fill_volume <= 1e-9:
                continue

            penalty = 0.0
            profit = 0.0
            
            if b.bid_type == 'buy':
                # Execution
                charge_needed = fill_volume * session.battery_efficiency_charge
                if team_state.current_battery_mwh + charge_needed <= session.battery_max_mwh:
                    team_state.current_battery_mwh += charge_needed
                    profit -= fill_volume * c_price
                else:
                    # Penalty for promising to buy but battery is full
                    penalty = fill_volume * session.penalty_price
            
            elif b.bid_type == 'sell':
                discharge_needed = fill_volume / session.battery_efficiency_discharge
                if team_state.current_battery_mwh >= discharge_needed:
                    team_state.current_battery_mwh -= discharge_needed
                    profit += fill_volume * c_price
                else:
                    penalty = fill_volume * session.penalty_price
                    
            team_state.total_profit += profit - penalty
            db.add(team_state)

    current_round.status = "calculated"
    db.commit()
    
    await manager.broadcast_to_session(session_id, {"event": "ROUND_CALCULATED", "round_id": round_id})
    return {"status": "ok", "message": "Round calculated"}

@router.post("/{session_id}/next")
async def next_round(session_id: int, admin_id: str, db: Session = Depends(get_db)):
    """Admin creates the next round."""
    session = db.query(models.Session).filter(models.Session.id == session_id).first()
    if not session or session.admin_id != admin_id:
        raise HTTPException(status_code=404)
        
    last_round = db.query(models.Round).filter(models.Round.session_id == session.id).order_by(models.Round.round_number.desc()).first()
    
    if last_round and last_round.status != "calculated":
        raise HTTPException(status_code=400, detail="Previous round not calculated")
        
    next_num = last_round.round_number + 1 if last_round else 1
    
    new_round = models.Round(session_id=session.id, round_number=next_num, status="bidding")
    db.add(new_round)
    db.commit()
    db.refresh(new_round)
    
    await manager.broadcast_to_session(session.id, {"event": "NEW_ROUND", "round_id": new_round.id, "round_number": next_num})
    return new_round
