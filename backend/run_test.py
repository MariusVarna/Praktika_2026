import asyncio
import httpx
from sqlalchemy.orm import Session
from app.database import SessionLocal, engine, Base
from app import models

Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

async def run_scenario():
    # 1. Create session
    from app.main import app
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post("/api/sessions/", json={
            "admin_id": "admin_123",
            "start_day": 1,
            "base_demand_mw": 10.0
        })
        session_data = res.json()
        session_id = session_data["id"]
        join_code = session_data["join_code"]
        print("Session created:", join_code)

        # 2. Join players
        res_p1 = await ac.post("/api/players/join", json={"name": "Team A", "join_code": join_code})
        p1_id = res_p1.json()["id"]
        print("Player 1 Joined:", p1_id)

        res_p2 = await ac.post("/api/players/join", json={"name": "Team B", "join_code": join_code})
        p2_id = res_p2.json()["id"]
        print("Player 2 Joined:", p2_id)

        # 3. Start Session
        res = await ac.post(f"/api/admin/sessions/{session_id}/start?admin_id=admin_123")
        round_id = res.json()["id"]
        print("Session Started, Round:", round_id)

        # 4. Submit Bids
        # Team A wants to charge (buy) at night (hour 2) when prices might be low
        bids_a = [{"hour": 2, "volume_mwh": 10.0, "price": 50.0, "bid_type": "buy"}]
        # Team A wants to discharge (sell) at peak hour 12
        bids_a.append({"hour": 12, "volume_mwh": 8.0, "price": 100.0, "bid_type": "sell"})

        await ac.post(f"/api/bids/?user_id={p1_id}&round_id={round_id}", json=bids_a)

        # Team B wants to charge (buy) at night (hour 2) but is willing to pay more
        bids_b = [{"hour": 2, "volume_mwh": 20.0, "price": 80.0, "bid_type": "buy"}]
        await ac.post(f"/api/bids/?user_id={p2_id}&round_id={round_id}", json=bids_b)
        print("Bids submitted")

        # 5. Calculate Round
        res = await ac.post(f"/api/admin/sessions/{session_id}/round/{round_id}/calculate?admin_id=admin_123")
        print("Round Calculated:", res.json())

        # 6. Check results
        db = SessionLocal()
        state_a = db.query(models.TeamState).filter(models.TeamState.user_id == p1_id).first()
        state_b = db.query(models.TeamState).filter(models.TeamState.user_id == p2_id).first()
        
        print(f"Team A - Battery: {state_a.current_battery_mwh}, Profit: {state_a.total_profit}")
        print(f"Team B - Battery: {state_b.current_battery_mwh}, Profit: {state_b.total_profit}")
        
        # Print market clearance price for hour 2 and 12
        m_res_2 = db.query(models.MarketResult).filter(models.MarketResult.round_id == round_id, models.MarketResult.hour == 2).first()
        m_res_12 = db.query(models.MarketResult).filter(models.MarketResult.round_id == round_id, models.MarketResult.hour == 12).first()
        
        print(f"Hour 2 Clearing Price: {m_res_2.clearing_price}, Volume: {m_res_2.total_volume_cleared}")
        print(f"Hour 12 Clearing Price: {m_res_12.clearing_price}, Volume: {m_res_12.total_volume_cleared}")

if __name__ == "__main__":
    asyncio.run(run_scenario())
