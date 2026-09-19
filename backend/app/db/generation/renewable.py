from app.models.renewable_generation import RenewableGeneration

def generate_renewable(context, weather_records):
    records = []
    
    # Assume regional capacities
    region_capacities = {}
    for r in context.regions:
        region_capacities[r] = {
            "solar_cap_mw": context.rng.uniform(100.0, 500.0),
            "wind_cap_mw": context.rng.uniform(50.0, 300.0),
            "hydro_base_mw": context.rng.uniform(20.0, 100.0),
            "other_base_mw": context.rng.uniform(5.0, 20.0)
        }
        
    for w in weather_records:
        r = w.region
        rc = region_capacities[r]
        
        # Solar depends heavily on irradiance (Max 1000 W/m2 = 100% capacity)
        solar = rc["solar_cap_mw"] * (w.solar_irradiance_w_m2 / 1000.0)
        solar = max(0.0, solar)
        
        # Wind depends on wind speed (e.g. max capacity at ~20 km/h)
        wind_factor = min(1.0, w.wind_speed_kmh / 20.0)
        wind = rc["wind_cap_mw"] * wind_factor
        
        # Hydro is stable with tiny variation
        hydro = rc["hydro_base_mw"] + context.rng.uniform(-2.0, 2.0)
        
        # Other is very stable
        other = rc["other_base_mw"] + context.rng.uniform(-0.5, 0.5)
        
        total = solar + wind + hydro + other
        
        # Note: renewable_share_pct will be recalculated properly when we have grid demand.
        # For now, we set it to 0, and the grid generation step will update it, 
        # or we generate grid demand first. 
        # The PRD says "Renewable share should be calculated against regional electricity demand."
        # So we leave it as 0 here and update it later.
        
        records.append(RenewableGeneration(
            timestamp=w.timestamp,
            region=r,
            solar_generation_mw=round(solar, 2),
            wind_generation_mw=round(wind, 2),
            hydro_generation_mw=round(hydro, 2),
            other_renewable_mw=round(other, 2),
            total_renewable_mw=round(total, 2),
            renewable_share_pct=0.0
        ))
        
    return records
