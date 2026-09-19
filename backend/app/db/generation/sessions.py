from app.models.charging_session import ChargingSession
import uuid
from datetime import timedelta

def generate_sessions(context, timeline):
    records = []
    
    # We will generate sessions per station
    for station in context.stations:
        # Number of sessions for this station based on configuration and weight
        base_sessions = context.sessions_per_station * context.days
        # Weight by connectors
        weight = min(5.0, max(0.5, station.no_of_connectors / 2.0))
        num_sessions = int(base_sessions * weight)
        
        # Randomize arrival times (skewed towards day/evening)
        for _ in range(num_sessions):
            # Pick a random day
            day_offset = context.rng.randint(0, context.days - 1)
            
            # Pick hour using distribution
            hour_roll = context.rng.random()
            if hour_roll < 0.05:
                hour = context.rng.randint(0, 4) # Very low
            elif hour_roll < 0.15:
                hour = context.rng.randint(5, 6) # Low
            elif hour_roll < 0.35:
                hour = context.rng.randint(7, 9) # High
            elif hour_roll < 0.65:
                hour = context.rng.randint(10, 15) # Moderate
            elif hour_roll < 0.90:
                hour = context.rng.randint(16, 20) # Very high
            else:
                hour = context.rng.randint(21, 23) # Moderate
                
            minute = context.rng.choice([0, 15, 30, 45])
            
            arrival_time = timeline[0] + timedelta(days=day_offset, hours=hour, minutes=minute)
            
            # Ensure it fits in timeline
            if arrival_time >= timeline[-1]:
                continue
                
            # Battery & SOC
            battery_kwh = context.rng.choice([30.0, 40.0, 50.0, 60.0, 75.0, 90.0])
            initial_soc = context.rng.uniform(10.0, 70.0)
            target_soc = context.rng.uniform(initial_soc + 10.0, 100.0)
            
            energy_req = battery_kwh * (target_soc - initial_soc) / 100.0
            
            # Power (bounded by station capacity)
            max_charger = min(150.0, station.charger_rating)
            power = min(max_charger, context.rng.choice([7.4, 11.0, 22.0, 50.0, 100.0]))
            
            duration_hrs = energy_req / power
            duration_min = duration_hrs * 60.0
            
            # Flexibility
            flex_roll = context.rng.random()
            if flex_roll < 0.3:
                flexibility = "Low"
                buffer_hrs = context.rng.uniform(0.1, 1.0)
            elif flex_roll < 0.75:
                flexibility = "Medium"
                buffer_hrs = context.rng.uniform(1.0, 4.0)
            else:
                flexibility = "High"
                buffer_hrs = context.rng.uniform(4.0, 12.0)
                
            ready_by = arrival_time + timedelta(minutes=duration_min) + timedelta(hours=buffer_hrs)
            
            # Preference
            pref_roll = context.rng.random()
            if pref_roll < 0.4:
                pref = "Fastest"
            elif pref_roll < 0.7:
                pref = "Cheapest"
            else:
                pref = "Greenest"
                
            records.append(ChargingSession(
                session_id=f"SESS-{uuid.uuid4().hex[:8].upper()}",
                station_id=station.station_id,
                clerk_user_id="synthetic_user", # Required by model, but we might want to allow null or seed a synthetic user. Let's seed a synthetic user in seed.py.
                arrival_time=arrival_time,
                ready_by=ready_by,
                initial_soc_pct=round(initial_soc, 2),
                target_soc_pct=round(target_soc, 2),
                battery_capacity_kwh=round(battery_kwh, 2),
                energy_required_kwh=round(energy_req, 2),
                max_charging_power_kw=round(power, 2),
                estimated_duration_min=round(duration_min, 2),
                flexibility=flexibility,
                preference=pref,
                status="Queued"
            ))
            
    return records
