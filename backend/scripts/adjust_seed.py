#!/usr/bin/env python3
"""
Script to adjust demand_forecast_profile in seed_data.py based on hour multipliers.
"""

import re

SEED_FILE = "/Users/mariusvarna/Desktop/Praktika/Praktika_2026/backend/app/seed_data.py"

HOUR_MULTIPLIERS = {
    (0, 1, 2, 3, 4, 5): 0.3,
    (6, 7): 0.8,
    (8, 9, 10, 11, 12, 13, 14, 15, 16): 1.15,
    (17, 18, 19, 20): 1.05,
    (21, 22, 23): 0.7,
}

def get_multiplier(hour):
    for hours, mult in HOUR_MULTIPLIERS.items():
        if hour in hours:
            return mult
    return 1.0

def process_seed_data():
    with open(SEED_FILE, "r") as f:
        lines = f.readlines()
    
    new_lines = []
    current_hour = None
    changes = 0
    
    for line in lines:
        if '"hour"' in line:
            match = re.search(r'"hour":\s*(\d+)', line)
            if match:
                current_hour = int(match.group(1))
        
        if '"demand_forecast_profile"' in line:
            match = re.search(r'"demand_forecast_profile":\s*([0-9.]+)', line)
            if match and current_hour is not None:
                old_value = float(match.group(1))
                multiplier = get_multiplier(current_hour)
                new_value = round(old_value * multiplier, 6)
                line = line.replace(match.group(1), str(new_value))
                changes += 1
        
        new_lines.append(line)
    
    with open(SEED_FILE, "w") as f:
        f.writelines(new_lines)
    
    print(f"Seed data updated! {changes} demand_forecast_profile values changed.")

if __name__ == "__main__":
    process_seed_data()