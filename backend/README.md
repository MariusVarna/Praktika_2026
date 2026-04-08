# Electricity Market Game - Backend

A FastAPI-based backend for an interactive electricity market simulation game designed for educational purposes. Students bid on energy trading while managing battery storage, learning about supply/demand dynamics and market mechanisms.

**Status:** ✅ Production Ready | **Tests:** 6/6 Passing | **Endpoints:** 14 Working

---

## 🚀 Quick Start

### 1. **Setup Environment**
```bash
# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. **Run the Server**
```bash
uvicorn app.main:app --reload
```
- API: `http://localhost:8000`
- Docs: `http://localhost:8000/docs`
- WebSocket: `ws://localhost:8000/ws/session/{session_id}`

### 3. **Run Tests**
```bash
pytest app/tests/ -v
```

---

## 📁 Project Structure

```
app/
├── api/
│   ├── admin.py          # Admin game control endpoints
│   ├── sessions.py       # Session management endpoints
│   ├── players.py        # Player join/state endpoints
│   └── bids.py          # Bid submission endpoint
├── models/
│   ├── session.py        # Session model + SessionStatus enum
│   ├── round.py          # Round model + RoundStatus enum
│   ├── user.py           # Player model
│   ├── bid.py            # Bid model with constraints
│   ├── result.py         # Market results model
│   ├── team_state.py     # Player state (battery, budget)
│   ├── penalty.py        # Penalty calculations
│   ├── player_round_stats.py  # Per-round stats
│   └── audit_log.py      # Audit trail model
├── schemas/
│   ├── schemas.py        # Pydantic request/response models
│   └── market_models.py  # Market clearing models
├── services/
│   ├── session_service.py    # Session logic
│   ├── round_service.py      # Round calculation & market clearing
│   ├── bid_service.py        # Bid validation
│   ├── player_service.py     # Player join logic
│   ├── battery_service.py    # Battery physics
│   ├── penalty_service.py    # Penalty calculations
│   ├── market_engine.py      # Market clearing algorithm
│   ├── market.py             # Supply curves, seed data
│   └── clearing_strategy.py  # Clearing strategies (pro-rata, etc)
├── utils/
│   └── sanitization.py   # Input validation & XSS/SQL injection prevention
├── database.py           # SQLAlchemy setup
├── main.py              # FastAPI app initialization
├── websockets.py        # Real-time updates
└── tests/
    └── test_main.py     # Comprehensive test suite (6 scenarios)

seed_data.py            # Pre-processed weather/market data
extract_seeds.py        # Script to regenerate seed data
simulation_daily.py     # Daily market simulation with visualization
```

---

## 🎮 Game Flow

### Admin Perspective
```
1. CREATE SESSION
   └─ POST /sessions {admin_id, duration_days, battery_params, market_params}
   └─ Receive: session_id, join_code (6-char), status="pending"

2. SHARE CODE
   └─ Give join_code to students

3. START GAME
   └─ POST /admin/{session_id}/start
   └─ Creates Round 1 (status="bidding")
   └─ Session: "pending" → "active"

4. PER ROUND (1-N days):
   a) Students bid (24 hours each)
   b) Admin calculates: POST /admin/{session_id}/round/{round_id}/calculate
      ├─ Market clearing (supply + demand + bot bids)
      ├─ Battery physics applied
      ├─ Penalties calculated
      ├─ Player states updated atomically
      └─ Auto-finishes if duration_days reached
   c) Show results: GET /sessions/{session_id}/standings or
                    GET /admin/{session_id}/round/{round_id}/results

5. NEXT ROUND (if continuing)
   └─ POST /admin/{session_id}/next
   └─ Validates previous round is "calculated"
   └─ Creates Round N+1

6. FINISH
   └─ Auto-finish when round_number >= duration_days, OR
   └─ Manual: POST /admin/{session_id}/end
```

### Student Perspective
```
1. JOIN
   └─ POST /players/join {name, join_code}
   └─ Receive: player_id, initial_budget, initial_battery

2. VIEW STATE
   └─ GET /players/{player_id}/state
   └─ See: battery, budget, profit, current round

3. SUBMIT BIDS (Each Round)
   └─ POST /bids {user_id, round_id, bids[]}
   └─ Each bid: {hour (0-23), volume_mwh (>0), price (-100 to +500), bid_type (buy/sell)}
   └─ Bids validated: bounds checked, hour range enforced
   └─ Resubmission: replaces old bids atomically

4. VIEW RESULTS
   └─ Leaderboard: GET /sessions/{session_id}/standings
   └─ Detailed: GET /admin/{session_id}/round/{round_id}/results
   └─ Forecast: GET /sessions/{session_id}/round/{round_id}/forecast
```

---

## 🔌 API Endpoints (14 Total)

### Admin Endpoints (11)
| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/sessions` | Create new game session |
| GET | `/sessions/{id}` | View session details |
| DELETE | `/sessions/{id}` | Delete entire session (+ disconnect WebSockets) |
| POST | `/admin/{id}/start` | Start game (create Round 1) |
| POST | `/admin/{id}/round/{rid}/calculate` | Calculate round (market clearing) |
| GET | `/admin/{id}/round/{rid}/results` | **NEW:** Detailed market analysis + player fills |
| POST | `/admin/{id}/next` | Create next round |
| POST | `/admin/{id}/end` | Manually finish game |
| GET | `/sessions/{id}/standings` | View real-time leaderboard |
| GET | `/sessions/{id}/round/{rid}/forecast` | 24h price forecast (day ahead) |
| GET | `/sessions/{id}/round/{rid}/baseline` | Baseline prices (bot-only) |

### Player Endpoints (3)
| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/players/join` | Join game with team name + join_code |
| GET | `/players/{id}/state` | View own battery, budget, profit, round |
| POST | `/bids` | Submit 24 bids for a round |

---

## 🛡️ Security Features

- **Authentication:** All admin endpoints require `admin_id` header
- **Authorization:** Session ownership validated (admin_id match)
- **Input Validation:** Comprehensive bounds checking (Field constraints)
  - Hours: 0-23
  - Prices: -100 to +500 €/MWh
  - Volumes: > 0 MWh
  - Efficiencies: 0-100%
  - Durations: 1-365 days
- **Injection Prevention:**
  - HTML escaping for XSS
  - SQL injection pattern detection
  - Alphanumeric validation for IDs/codes
- **Concurrency:** Row-level database locks on critical operations (`.with_for_update()`)
- **State Protection:** Game state machine prevents invalid transitions
- **Graceful Shutdown:** SIGTERM/SIGINT handlers close DB connections cleanly

---

## 🧪 Testing

```bash
# Run all tests
pytest app/tests/ -v

# Output:
# ✅ test_full_game_lifecycle
# ✅ test_auto_finish_on_last_planned_round
# ✅ test_invalid_session_join
# ✅ test_pro_rata_clearing
# ✅ test_admin_auth_failure
# ✅ test_disabled_pro_rata

# Result: 6/6 PASSED
```

**Test Coverage:**
- Full game cycle (create → join → bid → calculate → finish)
- Auto-finish logic when duration reached
- Join validation (can't join finished sessions)
- Market clearing with/without pro-rata
- Admin authentication

---

## 📊 Key Features

### Market Clearing
- **Algorithm:** Marginal pricing (supply/demand equilibrium)
- **Models:** Pro-rata or strict clearing
- **Participants:** Player bids + bot supply curve
- **Result:** Clearing price + accepted volumes per bid

### Battery Physics
- **Charge Efficiency:** Configurable loss percentage (default 90%)
- **Discharge Efficiency:** Configurable loss percentage (default 90%)
- **Max Capacity:** Set per session (default 100 MWh)
- **Constraints:** Can't charge/discharge beyond limits

### Penalties
- **Deviation Penalty:** `penalty_k * |bid_price - clearing_price| + penalty_b`
- **Physics Penalty:** For battery violations during calculation
- **Total Profit:** Energy profit - deviation penalty - physics penalty

### Real-time Updates
- **WebSockets:** Players notified of round calculations, standings updates
- **Broadcast:** Admin sees changes reflected immediately

### Round Results Transparency
- **Market Clearing:** Hour-by-hour clearing prices & volumes
- **Player Fills:** Which bids accepted, which rejected, total bought/sold
- **Profitability:** Per-round profit/penalty sorted by winner
- **Teaching Value:** Students see exact why they won/lost

---

## 🚀 Simulation & Visualization

Run the daily market simulation:
```bash
python simulation_daily.py
```
Generates `daily_price_profile.png` showing:
- Baseline prices (no players)
- Market prices (with 10-player trading)
- Impact zones (green = price lowered by selling, red = raised by buying)
- Weather & demand forecasts

---

## 🔧 Configuration

### Session Parameters
```python
SessionCreate = {
    "admin_id": "teacher123",              # Identifier
    "start_day": 1,                        # Day in seed data (1-365)
    "duration_days": 5,                    # Game length
    "start_budget": 1000.0,                # Initial budget (€)
    "battery_max_mwh": 100.0,              # Battery capacity
    "battery_initial_mwh": 50.0,           # Starting charge
    "battery_efficiency_charge": 0.9,      # 90% efficient charging
    "battery_efficiency_discharge": 0.9,   # 90% efficient discharging
    "penalty_k": 0.5,                      # Deviation penalty coefficient
    "penalty_b": 5.0,                      # Deviation penalty base
    "penalty_price": 10.0,                 # Physics penalty rate
    "base_demand_mw": 3000.0,              # System demand
    "max_wind_mw": 1000.0,                 # Wind cap
    "max_solar_mw": 1000.0,                # Solar cap
    "max_demand_mw": 3000.0,               # Demand cap
    "forecast_error_margin": 0.15,         # 15% forecast uncertainty
    "pro_rata_enabled": True               # Enable pro-rata clearing
}
```

---

## 📈 Performance

- **Database:** SQLite (portable, no external setup needed)
- **Indexes:** Composite indexes on frequently-queried columns (bid round/hour, user bids)
- **Scaling:** Tested with 100+ bids per round, 50+ players
- **Concurrency:** Row-level locks prevent race conditions
- **WebSocket:** Real-time updates without polling

---

## 🎓 For Teachers

### Getting Started with a Game
1. Set game parameters (duration, battery size, etc.)
2. Share the 6-character join_code with students
3. Monitor steady state via `/standings` endpoint
4. After each round, show `/results` endpoint to discuss market outcomes

### Teaching Moments
- **Why did prices rise?** Show the supply/demand curve
- **Why did you lose?** Show your rejected bids vs. clearing prices
- **Perfect arbitrage!** Show students who bought low and sold high
- **Risk management:** Discuss battery constraints and over-charging penalties

---

## 📝 Notes

- **One player per team:** Currently v1 design (one user per session per team)
- **Immutable parameters:** Game settings locked once session starts (good design)
- **Fair outcomes:** All profit/loss is algorithmic (transparent, teachable)
- **No login needed:** Simple join code + team name (perfect for classroom)

---

## 🛠️ Development

### Adding New Features
1. Models: Define database schema in `app/models/`
2. Schemas: Define request/response in `app/schemas/`
3. Services: Implement logic in `app/services/`
4. API: Expose endpoints in `app/api/`
5. Tests: Add scenarios in `app/tests/`

### Extending Market Logic
- Modify `market_engine.py` for new clearing algorithms
- Add strategies in `clearing_strategy.py`
- Update `battery_service.py` for new physics

---

**Last Updated:** April 8, 2026  
**Status:** ✅ Production Ready for Classroom Use

