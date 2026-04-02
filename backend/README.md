# Electricity Market Game - Backend

This is the FastAPI backend for the Electricity Market Game.

## Project Structure
- `app/`: Main application code.
  - `api/`: REST API endpoints (Admin, Players, Bids, Sessions).
  - `models/`: SQLAlchemy database models.
  - `schemas/`: Pydantic data validation schemas.
  - `services/`: Core logic and market clearing engine.
  - `seed_data.py`: Pre-processed data from Excel.
- `extract_seeds.py`: Script to regenerate `seed_data.py` from Excel.
- `run_test.py`: Integration test scenario script.

## Setup Instructions

1. **Create Virtual Environment:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the Server:**
   ```bash
   uvicorn app.main:app --reload
   ```
   The API will be available at `http://127.0.0.1:8000`.
   Interactive Documentation: `http://127.0.0.1:8000/docs`.

4. **WebSockets:**
   WebSocket endpoint for real-time updates: `ws://127.0.0.1:8000/ws/session/{session_id}`.

## Logic Overview
- **Session Join:** Players join using a 6-digit code.
- **Round Calculation:** Admin triggers round calculation. Market clearing is performed using a marginal pricing model.
- **Pro-rata:** Configurable pro-rata sharing for bids at the same price level.
- **Batteries:** Efficiency, max capacity, and penalties are calculated during round execution.

## New Flow & Features
1. Admin creates session with: `start_day`, `duration_days`, `start_budget`, `battery_max_mwh`, `battery_initial_mwh`, `battery_efficiency_charge`, `battery_efficiency_discharge`, `penalty_k`, `penalty_b`, `penalty_price`, demand/supply caps.
2. Players join with `POST /api/players/join` and a team name (one player per team in v1).
3. Admin starts session with `POST /api/admin/sessions/{session_id}/start` → creates round 1 `bidding`.
4. Baseline graph (bot-only market) via `GET /api/sessions/{session_id}/round/{round_id}/baseline`.
5. Players submit bids via `POST /api/bids/?user_id={user_id}&round_id={round_id}`.
6. Admin closes round with `POST /api/admin/sessions/{session_id}/round/{round_id}/calculate`:
   - Per-hour clearing, player fills, penalties, battery updates.
   - Deviation penalty `= penalty_k * abs(player_price - clearing_price) + penalty_b`.
   - Physics penalty for battery overflow/unavailable state.
   - `MarketResult`, `Penalty`, `PlayerRoundStats` records are saved.
7. Admin advances with `POST /api/admin/sessions/{session_id}/next`.
8. Standings via `GET /api/sessions/{session_id}/standings` includes:
   - per-team `current_battery_mwh`, `budget`, `total_profit`, `total_penalty`
   - per-round stats (`total_profit`, `total_penalty`)

## API Endpoints
- `POST /api/sessions/` create session
- `POST /api/admin/sessions/{session_id}/start` start initial round
- `POST /api/admin/sessions/{session_id}/round/{round_id}/calculate` calculate/publish round results
- `POST /api/admin/sessions/{session_id}/next` create next round
- `GET /api/sessions/{session_id}/round/{round_id}/baseline` get 24h bot baseline
- `POST /api/players/join` join session with team name
- `POST /api/bids/?user_id={user_id}&round_id={round_id}` submit user bids
- `GET /api/sessions/{session_id}/standings` get overall standings

