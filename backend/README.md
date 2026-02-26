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
