import matplotlib.pyplot as plt
import numpy as np
import random
from app.services.market import get_day_seed, generate_supply_curve, calculate_clearing_price

# Mock session object
class MockSession:
    def __init__(self):
        self.max_wind_mw = 1000.0
        self.max_solar_mw = 1000.0
        self.base_demand_mw = 3000.0

def run_daily_simulation(day_num=1):
    session = MockSession()
    day_data = get_day_seed(day_num)
    
    if not day_data:
        print(f"No data for day {day_num}")
        return

    # Map data by hour
    hour_map = {d["hour"]: d for d in day_data}
    hours = []

    # --- 1. First Pass: Calculate all baseline prices for the day ---
    prices_baseline = []
    for h in range(24):
        hour_info = hour_map.get(h, {"wind_planned_profile": 0, "solar_planned_profile": 0, "demand_forecast_profile": 0.5})
        base_demand = session.base_demand_mw * hour_info.get("demand_forecast_profile", 0.5)
        bot_supply = generate_supply_curve(hour_info, session)
        price_base, _, _ = calculate_clearing_price(bot_supply, [], base_demand)
        prices_baseline.append(price_base)

    # Calculate thresholds based on the full day's results
    p_min = np.percentile(prices_baseline, 25)
    p_max = np.percentile(prices_baseline, 75)

    # --- 2. Second Pass: Simulate players with full knowledge of the day ---
    prices_with_players = []
    num_players = 10
    player_batteries = [50.0] * num_players

    for h in range(24):
        hour_info = hour_map.get(h, {"wind_planned_profile": 0, "solar_planned_profile": 0, "demand_forecast_profile": 0.5})
        base_demand = session.base_demand_mw * hour_info.get("demand_forecast_profile", 0.5)
        bot_supply = generate_supply_curve(hour_info, session)
        price_base = prices_baseline[h]
        
        player_bids_supply = []
        player_bids_demand = []

        for i in range(num_players):
            battery = player_batteries[i]
            
            # 1. PIRKIMAS (Valleys): Kai kaina tarp žemiausių dienos kainų
            if price_base <= p_min:
                if battery < 90:
                    # Agresyvus pirkimas
                    bid_price = price_base + 30.0 
                    vol = random.uniform(30, 60)
                    player_bids_demand.append({"volume": vol, "price": bid_price, "bid_id": f"buy_{h}_{i}"})
                    player_batteries[i] = min(100, battery + vol * 0.9)
            
            # 2. PARDAVIMAS (Peaks): Kai kaina tarp aukščiausių dienos kainų
            elif price_base >= p_max:
                if battery > 10:
                    # Agresyvus pardavimas
                    bid_price = price_base - 30.0
                    vol = random.uniform(30, 60)
                    player_bids_supply.append({"volume": vol, "price": bid_price, "bid_id": f"sell_{h}_{i}"})
                    player_batteries[i] = max(0, battery - vol)

        price_active, _, _ = calculate_clearing_price(bot_supply + player_bids_supply, player_bids_demand, base_demand)
        prices_with_players.append(price_active)
        hours.append(h)

    # Plotting
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 12), gridspec_kw={'height_ratios': [2, 1]})

    # --- Price Plot ---
    ax1.plot(hours, prices_baseline, label='Baseline Price (No Players)', color='gray', linestyle='--', marker='o', alpha=0.6)
    ax1.plot(hours, prices_with_players, label=f'Market Price ({num_players} Players Trading)', color='blue', linewidth=3, marker='s')
    
    ax1.fill_between(hours, prices_baseline, prices_with_players, 
                     where=(np.array(prices_with_players) < np.array(prices_baseline)),
                     color='green', alpha=0.2, label='Price Lowered (Selling)')
    ax1.fill_between(hours, prices_baseline, prices_with_players, 
                     where=(np.array(prices_with_players) > np.array(prices_baseline)),
                     color='red', alpha=0.2, label='Price Raised (Buying)')

    ax1.set_title(f"Market Simulation: {num_players} Players Impact (Day {day_num})", fontsize=16)
    ax1.set_ylabel("Clearing Price (€/MWh)", fontsize=12)
    ax1.grid(True, alpha=0.3)
    ax1.legend(loc='upper left')

    # --- Profile Plot ---
    wind_p = [h.get("wind_planned_profile", 0)*100 for h in day_data]
    solar_p = [h.get("solar_planned_profile", 0)*100 for h in day_data]
    demand_p = [h.get("demand_forecast_profile", 0)*100 for h in day_data]

    ax2.plot(hours, wind_p, label='Wind %', color='cyan', linewidth=2)
    ax2.plot(hours, solar_p, label='Solar %', color='orange', linewidth=2)
    ax2.plot(hours, demand_p, label='Demand %', color='black', linestyle=':', linewidth=2)
    ax2.set_ylabel("Profile Percentage (%)", fontsize=12)
    ax2.set_xlabel("Hour of Day (0-23)", fontsize=12)
    ax2.set_ylim(0, 110)
    ax2.grid(True, alpha=0.3)
    ax2.legend(loc='upper left', ncol=3)

    plt.xticks(range(24))
    plt.tight_layout()
    
    filename = "daily_price_profile.png"
    plt.savefig(filename)
    print(f"Saved: {filename}")
    plt.close()

if __name__ == "__main__":
    run_daily_simulation(day_num=1)
