# app/services/market.py
from app.seed_data import SEED_DATA
from typing import List, Dict

def get_day_seed(day: int) -> List[Dict]:
    """Returns the profile for a given day (1-365)."""
    # Keys in SEED_DATA are usually sheet names, but we mapped them to days.
    # We generated SEED_DATA based on sheet_name keys: { "Sheet1": { 1: [...], 2: [...] } }
    # So we need to find the day across all sheets or specify the sheet.
    
    for sheet_name, data in SEED_DATA.items():
        if day in data:
            return data[day]
            
    # Default fallback if day not found
    return []

def generate_supply_curve(hour_data: dict, session) -> List[dict]:
    """Generates the supply curve bots/tiers based on config."""
    # Based on Plan: 50% avg price, 25% cheap, 25% expensive
    wind = hour_data.get('wind_planned_profile', 0)
    solar = hour_data.get('solar_planned_profile', 0)
    
    total_supply_mw = (wind + solar) # Base MW calculation based on profile (assuming profile is absolute MW or we apply a multiplier, user said "max poreikis 3000 megawwatt dauginam is valandinio poreikio")
    # Actually user said Qmax * profile. So if profile is already percentage, we multiply by max.
    # For now, let's treat the profile value as the actual MWh or MW.
    
    # We will split it into 3 bot tiers for simplicity
    v_cheap = total_supply_mw * 0.25
    v_avg = total_supply_mw * 0.50
    v_exp = total_supply_mw * 0.25
    
    # Arbitrary prices for now, these could be admin configurable too
    curve = [
        {"volume": v_cheap, "price": -5.0}, # Subsidized
        {"volume": v_avg, "price": 40.0},   # Average
        {"volume": v_exp, "price": 120.0},  # Expensive
    ]
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
    
    prepared_demand = [{"volume": base_demand_mw, "price": 9999.0, "bid_id": "base_demand"}]
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
