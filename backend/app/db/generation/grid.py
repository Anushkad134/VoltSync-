from app.models.grid_demand import GridDemand
import math

def generate_grid_and_update_renewable(context, timeline, renewable_records):
    grid_records = []
    
    # Base demand per region, proportional to stations in region
    region_counts = {}
    for s in context.stations:
        r = f"{s.state} - {s.district_city_village}".strip()
        region_counts[r] = region_counts.get(r, 0) + 1
        
    for r in context.regions:
        station_count = region_counts.get(r, 1)
        base_demand = station_count * context.rng.uniform(10.0, 50.0) # MW base
        peak_demand_capacity = base_demand * context.rng.uniform(1.5, 2.5)
        
        # Filter renewable records for this region for easy indexing by timestamp
        region_renewables = {rec.timestamp: rec for rec in renewable_records if rec.region == r}
        
        for t in timeline:
            hour_f = t.hour + t.minute / 60.0
            
            # Demand curve
            # low at night, rising morning, moderate midday, peak evening
            if 0 <= hour_f < 5:
                curve = 0.3
            elif 5 <= hour_f < 8:
                curve = 0.3 + (hour_f - 5) * 0.15 # rising to 0.75
            elif 8 <= hour_f < 12:
                curve = 0.75
            elif 12 <= hour_f < 16:
                curve = 0.65
            elif 16 <= hour_f < 21:
                # Peak
                curve = 0.9 + math.sin((hour_f - 16) * math.pi / 5) * 0.1 
            else:
                curve = 0.9 - (hour_f - 21) * 0.2
                
            demand = base_demand * curve + context.rng.uniform(-2.0, 2.0)
            demand = max(1.0, demand)
            
            # Available capacity is peak + reserve
            available_capacity = peak_demand_capacity + context.rng.uniform(0.0, 20.0)
            
            # Sometimes simulate grid stress (capacity drops)
            if context.rng.random() > 0.95:
                available_capacity = demand * context.rng.uniform(1.01, 1.1)
                
            demand_rounded = round(demand, 2)
            capacity_rounded = round(available_capacity, 2)
            
            reserve_margin = capacity_rounded - demand_rounded
            grid_stress = (demand_rounded / capacity_rounded) * 100.0
            
            # Update the corresponding renewable record's share
            ren_rec = region_renewables.get(t)
            if ren_rec:
                # Share is (total renewable / demand) * 100
                share = (ren_rec.total_renewable_mw / demand_rounded) * 100.0
                ren_rec.renewable_share_pct = round(min(100.0, max(0.0, share)), 2)
            
            grid_records.append(GridDemand(
                timestamp=t,
                region=r,
                demand_mw=demand_rounded,
                peak_demand_mw=round(peak_demand_capacity, 2),
                available_capacity_mw=capacity_rounded,
                reserve_margin_mw=round(reserve_margin, 2),
                grid_stress_pct=round(grid_stress, 2)
            ))
            
    return grid_records
