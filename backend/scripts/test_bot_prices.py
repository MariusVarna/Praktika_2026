#!/usr/bin/env python3
"""
Test script to run full simulation with bots only (no player bids) to see pure bot clearing prices.
Simulates frontend flow: create session → start → calculate → get results.
"""

import requests
import time

API_BASE = "http://localhost:8000"
TEST_DAYS = list(range(1, 16))  # Days 1 to 15
BASE_DEMAND = 4000  # Higher for peak prices €80-120


def create_session(start_day, base_demand=BASE_DEMAND):
    """Create a test session."""
    resp = requests.post(f"{API_BASE}/api/sessions/", json={
        "admin_id": "test_bot_script",
        "game_name": f"Bot Test Day {start_day}",
        "start_day": start_day,
        "duration_days": 1,
        "base_demand_mw": base_demand,
        "max_demand_mw": base_demand * 1.5,
        "penalty_price": 10.0,
        "penalty_k": 0.5,
        "penalty_b": 5.0,
        "bandwidth": 50.0,
        "battery_max_mwh": 100.0,
        "battery_initial_mwh": 50.0,
    })
    if resp.status_code != 200:
        print(f"ERROR creating session: {resp.status_code} {resp.text}")
        return None
    return resp.json()


def start_session(session_id):
    """Start the session and get round info."""
    resp = requests.post(f"{API_BASE}/api/admin/sessions/{session_id}/start", headers={"admin-id": "test_bot_script"})
    if resp.status_code != 200:
        print(f"ERROR starting session: {resp.status_code} {resp.text}")
        return None
    return resp.json()


def calculate_round(session_id, round_id):
    """Calculate the round."""
    resp = requests.post(
        f"{API_BASE}/api/admin/sessions/{session_id}/round/{round_id}/calculate",
        headers={"admin-id": "test_bot_script"}
    )
    if resp.status_code != 200:
        print(f"ERROR calculating round: {resp.status_code} {resp.text}")
        return None
    return resp.json()


def get_results(session_id, round_id):
    """Get round results."""
    resp = requests.get(f"{API_BASE}/api/admin/sessions/{session_id}/round/{round_id}/results")
    if resp.status_code != 200:
        print(f"ERROR getting results: {resp.status_code} {resp.text}")
        return None
    return resp.json()


def run_test_for_day(day, base_demand=BASE_DEMAND):
    """Run full simulation for one day."""
    print(f"\n{'='*60}")
    print(f"Day {day}")
    print(f"{'='*60}")
    
    # Step 1: Create session with this start day
    session = create_session(day, base_demand)
    if not session:
        return None
    
    session_id = session["id"]
    
    # Step 2: Start session (no players, bots only!)
    start_result = start_session(session_id)
    if not start_result:
        return None
    
    # Get the round ID from start response
    round_id = start_result.get("round_id") or start_result.get("id") or session.get("current_round")
    
    # Step 3: Calculate round (bots only, no player bids)
    calc_result = calculate_round(session_id, round_id)
    if not calc_result:
        return None
    
    # Step 4: Get results
    results = get_results(session_id, round_id)
    if not results or not results.get("market_clearing"):
        print("ERROR: No market results returned")
        return None
    
    # Extract prices for all 24 hours
    prices = []
    for mc in results["market_clearing"]:
        prices.append((mc["hour"], mc["clearing_price"]))
    
    # Sort by hour
    prices.sort(key=lambda x: x[0])
    
    # Print hour by hour
    for hour, price in prices:
        print(f"  Hour {hour:02d}: €{price:.2f}")
    
    # Calculate stats
    price_values = [p[1] for p in prices]
    min_price = min(price_values)
    max_price = max(price_values)
    avg_price = sum(price_values) / len(price_values)
    
    print(f"{'-'*60}")
    print(f"  Min: €{min_price:.2f} | Max: €{max_price:.2f} | Avg: €{avg_price:.2f}")
    
    return {
        "day": day,
        "min": min_price,
        "max": max_price,
        "avg": avg_price,
        "prices": dict(prices)
    }


def main():
    """Main test function."""
    print("="*60)
    print("BOT PRICE SIMULATION TEST (NO PLAYER BIDS)")
    print("Testing pure bot clearing prices across different days")
    print("="*60)
    print(f"API Base: {API_BASE}")
    print(f"Test Days: {TEST_DAYS}")
    print(f"Base Demand: {BASE_DEMAND} MW")
    
    # Check if server is running
    try:
        requests.get(f"{API_BASE}/docs", timeout=5)
    except:
        print(f"\nERROR: Server not running at {API_BASE}")
        print("Start server with: uvicorn app.main:app --host 0.0.0.0 --port 8000")
        return
    
    all_results = []
    
    for day in TEST_DAYS:
        result = run_test_for_day(day, BASE_DEMAND)
        if result:
            all_results.append(result)
        time.sleep(0.5)
    
    # Print summary
    print("\n")
    print("="*60)
    print("SUMMARY TABLE")
    print("="*60)
    print(f"{'Day':>6} | {'Min':>10} | {'Max':>10} | {'Avg':>10}")
    print("-"*60)
    
    for r in all_results:
        print(f"{r['day']:>6} | €{r['min']:>7.2f} | €{r['max']:>7.2f} | €{r['avg']:>7.2f}")
    
    print("-"*60)
    
    if all_results:
        all_mins = [r['min'] for r in all_results]
        all_maxs = [r['max'] for r in all_results]
        all_avgs = [r['avg'] for r in all_results]
        print(f"{'Overall':>6} | €{min(all_mins):>7.2f} | €{max(all_maxs):>7.2f} | €{sum(all_avgs)/len(all_avgs):>7.2f}")
    
    print("\nDone!")


if __name__ == "__main__":
    main()