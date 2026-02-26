import pandas as pd
import json

def generate_seed_data(excel_path):
    print(f"Reading {excel_path}...")
    # Load all sheets
    xls = pd.ExcelFile(excel_path)
    
    seeds = {}
    
    for sheet_name in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name=sheet_name)
        
        # Columns based on user description:
        # A - Diena (Day)
        # B - Valanda (Hour)
        # C - Planuojama vėjo elektrinių gamyba
        # E - Planuojama saulės elektrinių gamyba
        # F - Faktinė saulės elektrinių gamyba
        # G - Prognozuojamas elektros energijos suvartojimas

        # Looking for actual column names in the first row or assuming standard layout based on positions
        # Let's just use indices assuming standard 0-indexed columns:
        # 0: Diena, 1: Valanda, 2: Vėjas (planuojama), 4: Saulė (planuojama), 5: Saulė (faktinė), 6: Vartojimas (prognozė)
        
        try:
            day_data = []
            # we need to make sure we parse valid rows
            for i, row in df.iterrows():
                try:
                    day = int(row.iloc[0])
                    hour = int(row.iloc[1])
                    
                    # Convert to hours 0-23 instead of 1-24 if needed
                    # Let's just store exact values for now. If they are 1-24, we will convert them.
                    if hour > 0:
                        hour -= 1 # 0-indexed hour
                    
                    wind_planned = float(row.iloc[2]) if not pd.isna(row.iloc[2]) else 0.0
                    solar_planned = float(row.iloc[4]) if not pd.isna(row.iloc[4]) else 0.0
                    solar_actual = float(row.iloc[5]) if not pd.isna(row.iloc[5]) else 0.0
                    demand_forecast = float(row.iloc[6]) if not pd.isna(row.iloc[6]) else 0.0
                    
                    day_data.append({
                        "hour": hour,
                        "wind_planned_profile": wind_planned,
                        "solar_planned_profile": solar_planned,
                        "solar_actual_profile": solar_actual,
                        "demand_forecast_profile": demand_forecast
                    })
                except (ValueError, TypeError):
                    # Skip rows that are not data (e.g. headers or text)
                    continue
            
            if day_data:
                # Group by day
                days = set(d.get("Diena", 1) for i, d in df.iterrows() if pd.notna(d.iloc[0]) and isinstance(d.iloc[0], (int, float)))
                # Actually, our day_data doesn't have day in it, let's restructure
                
                # Let's restart grouping logically
                sheet_data = {}
                for i, row in df.iterrows():
                    try:
                        day = int(row.iloc[0])
                        hour = int(row.iloc[1])
                        if hour > 0:
                            hour -= 1
                        
                        wind_planned = float(row.iloc[2]) if not pd.isna(row.iloc[2]) else 0.0
                        solar_planned = float(row.iloc[4]) if not pd.isna(row.iloc[4]) else 0.0
                        solar_actual = float(row.iloc[5]) if not pd.isna(row.iloc[5]) else 0.0
                        demand_forecast = float(row.iloc[6]) if not pd.isna(row.iloc[6]) else 0.0
                        
                        if day not in sheet_data:
                            sheet_data[day] = []
                            
                        sheet_data[day].append({
                            "hour": hour,
                            "wind_planned_profile": round(wind_planned, 6),
                            "solar_planned_profile": round(solar_planned, 6),
                            "solar_actual_profile": round(solar_actual, 6),
                            "demand_forecast_profile": round(demand_forecast, 6)
                        })
                    except (ValueError, TypeError):
                        pass
                
                seeds[sheet_name] = sheet_data
                
        except Exception as e:
            print(f"Error reading sheet {sheet_name}: {e}")
            
    # Write to seed_data.py
    with open("app/seed_data.py", "w") as f:
        f.write("# Automatically generated seed data from Excel\n\n")
        f.write("SEED_DATA = \\\n")
        f.write(json.dumps(seeds, indent=4))
        f.write("\n")
        
    print("Done! Data written to app/seed_data.py")

if __name__ == "__main__":
    generate_seed_data("Vėjo ir saulės grafikai.xlsx")
