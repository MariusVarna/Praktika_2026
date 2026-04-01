from app.seed_data import SEED_DATA
from typing import List, Dict
import random

# Pre-index SEED_DATA for O(1) lookup
# SEED_DATA structure is { "Grafikai": { "1": [...], "2": [...] } }
# We want { 1: [...], 2: [...] }
INDEXED_SEED_DATA = {}
for sheet_name, sheet_dict in SEED_DATA.items():
    for day_id, data in sheet_dict.items():
        # Ensure day_id is stored as int for consistent lookup
        try:
            day_key = int(day_id)
            INDEXED_SEED_DATA[day_key] = data
        except ValueError:
            continue

def get_day_seed(day: int) -> List[Dict]:
    """Returns the profile for a given day (1-365) in O(1) time."""
    return INDEXED_SEED_DATA.get(day, [])

def generate_supply_curve(hour_data: dict, session) -> List[dict]:
    """Generates a granular supply curve with realistic volatility (Steeper steps)."""
    wind = hour_data.get('wind_planned_profile', 0)
    solar = hour_data.get('solar_planned_profile', 0)
    
    max_wind = getattr(session, 'max_wind_mw', 1000.0)
    max_solar = getattr(session, 'max_solar_mw', 1000.0)
    
    curve = []
    
    # 1. Baseload (Small but cheap, 500MW)
    baseload_mw = 500.0
    for i in range(10):
        curve.append({"volume": baseload_mw/10, "price": 10.0 + i, "bid_id": f"base_{i}"})

    # 2. Renewables (The price-setters when weather is good)
    total_renew_mw = (wind * max_wind) + (solar * max_solar)
    num_renew = 100
    if total_renew_mw > 0:
        v_per_bot = total_renew_mw / num_renew
        for i in range(num_renew):
            # Prices can go negative or stay low
            price = -20.0 + (i / num_renew) * 70.0
            curve.append({"volume": v_per_bot, "price": round(price + random.uniform(-0.1, 0.1), 2), "bid_id": f"renew_{i}"})

    # 3. Peak Plants (Gas, expensive, 2000MW)
    # These set the price when renewables are low
    peak_mw = 2500.0
    num_peak = 100
    v_per_peak = peak_mw / num_peak
    for i in range(num_peak):
        # Steep curve from 60 to 400
        price = 60.0 + (i / num_peak)**2 * 350.0  # Exponential increase for peaks
        curve.append({"volume": v_per_peak, "price": round(price + random.uniform(-0.1, 0.1), 2), "bid_id": f"peak_{i}"})
    
    return curve

def calculate_clearing_price(supply_curve: List[Dict], demand_curve: List[Dict], base_demand_mw: float):
    """
    Calculates the intersection of supply and demand and returns fill volumes.
    Returns: (clearing_price, clearing_volume, fill_map)
    fill_map: {bid_id: filled_volume}
    """
    # 1. Prepare supply and demand with unique markers if not present
    # We assume player bids have 'bid_id'. Bots might not.
    prepared_supply = []
    for i, s in enumerate(supply_curve):
        prepared_supply.append({
            "volume": s["volume"],
            "price": s["price"],
            "bid_id": s.get("bid_id", f"bot_s_{i}")
        })
    
    prepared_demand = []
    # 80% is inelastic (critical demand), price at infinity
    inelastic_vol = base_demand_mw * 0.8
    prepared_demand.append({"volume": inelastic_vol, "price": 9999.0, "bid_id": "base_demand_critical"})
    
    # 20% is elastic (smart demand), split into 50 small bots with decreasing prices
    elastic_vol_total = base_demand_mw * 0.2
    num_demand_bots = 50
    v_per_d_bot = elastic_vol_total / num_demand_bots
    for i in range(num_demand_bots):
        # Price drops from 200 down to 30
        price = 200 - (i / num_demand_bots) * 170 + random.uniform(-0.1, 0.1)
        prepared_demand.append({
            "volume": v_per_d_bot,
            "price": round(price, 2),
            "bid_id": f"system_demand_{i}"
        })

    for i, d in enumerate(demand_curve):
        prepared_demand.append({
            "volume": d["volume"],
            "price": d["price"],
            "bid_id": d.get("bid_id", f"bot_d_{i}")
        })

    # Sort
    supply = sorted(prepared_supply, key=lambda x: x["price"])
    demand = sorted(prepared_demand, key=lambda x: x["price"], reverse=True)

    fill_map = {}
    clearing_price = 0.0
    total_volume = 0.0

    # We need to handle the pro-rata case for bids at the same price.
    # Group supply and demand by price
    def group_by_price(sorted_list):
        groups = []
        if not sorted_list: return groups
        current_group = [sorted_list[0]]
        for item in sorted_list[1:]:
            if item["price"] == current_group[0]["price"]:
                current_group.append(item)
            else:
                groups.append(current_group)
                current_group = [item]
        groups.append(current_group)
        return groups

    supply_groups = group_by_price(supply)
    demand_groups = group_by_price(demand)

    s_g_idx, d_g_idx = 0, 0
    s_vol_rem = sum(item["volume"] for item in supply_groups[s_g_idx]) if supply_groups else 0
    d_vol_rem = sum(item["volume"] for item in demand_groups[d_g_idx]) if demand_groups else 0

    while s_g_idx < len(supply_groups) and d_g_idx < len(demand_groups):
        s_price = supply_groups[s_g_idx][0]["price"]
        d_price = demand_groups[d_g_idx][0]["price"]

        if d_price >= s_price:
            clearing_price = s_price # Marginal pricing (pay as bid by supply or simply last accepted supply price)
            
            trade_vol = min(s_vol_rem, d_vol_rem)
            total_volume += trade_vol

            # Distribute trade_vol among current groups pro-rata
            # Supply group distribution
            s_group_total = sum(item["volume"] for item in supply_groups[s_g_idx])
            s_ratio = trade_vol / s_group_total if s_group_total > 0 else 0
            for item in supply_groups[s_g_idx]:
                item_id = item["bid_id"]
                fill_map[item_id] = fill_map.get(item_id, 0) + (item["volume"] * s_ratio)

            # Demand group distribution
            d_group_total = sum(item["volume"] for item in demand_groups[d_g_idx])
            d_ratio = trade_vol / d_group_total if d_group_total > 0 else 0
            for item in demand_groups[d_g_idx]:
                item_id = item["bid_id"]
                fill_map[item_id] = fill_map.get(item_id, 0) + (item["volume"] * d_ratio)

            s_vol_rem -= trade_vol
            d_vol_rem -= trade_vol

            if abs(s_vol_rem) < 1e-9:
                s_g_idx += 1
                if s_g_idx < len(supply_groups):
                    s_vol_rem = sum(item["volume"] for item in supply_groups[s_g_idx])
            if abs(d_vol_rem) < 1e-9:
                d_g_idx += 1
                if d_g_idx < len(demand_groups):
                    d_vol_rem = sum(item["volume"] for item in demand_groups[d_g_idx])
        else:
            break

    return clearing_price, total_volume, fill_map
