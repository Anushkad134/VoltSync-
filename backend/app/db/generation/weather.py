from app.models.weather import Weather
import math

def generate_weather(context, timeline):
    records = []
    
    # Pre-calculate base region properties for deterministic variation
    region_bases = {}
    for r in context.regions:
        region_bases[r] = {
            "temp_base": context.rng.uniform(20.0, 35.0),
            "cloud_base": context.rng.uniform(10.0, 50.0),
            "wind_base": context.rng.uniform(5.0, 15.0),
            "lat": context.rng.uniform(8.0, 37.0),
            "lon": context.rng.uniform(68.0, 97.0)
        }
        
    for r in context.regions:
        rb = region_bases[r]
        # Carry-over state for continuity
        current_cloud = rb["cloud_base"]
        current_wind = rb["wind_base"]
        
        for t in timeline:
            # Time of day factors (0 to 1)
            hour_f = t.hour + t.minute / 60.0
            
            # Temperature follows a daily curve (coolest at 5am, hottest at 3pm)
            temp_curve = math.sin((hour_f - 9) * math.pi / 12)
            temp = rb["temp_base"] + (temp_curve * 5.0) + context.rng.uniform(-0.5, 0.5)
            
            # Solar Irradiance follows daylight (approx 6am to 6pm)
            if 6 <= hour_f <= 18:
                # Bell curve peaking at noon
                irradiance_curve = math.sin((hour_f - 6) * math.pi / 12)
                clear_sky_irradiance = irradiance_curve * 1000.0
            else:
                clear_sky_irradiance = 0.0
                
            # Continuous random walk for cloud cover and wind
            current_cloud += context.rng.uniform(-5.0, 5.0)
            current_cloud = max(0.0, min(100.0, current_cloud)) # Clamp 0-100
            
            current_wind += context.rng.uniform(-1.0, 1.0)
            current_wind = max(0.0, current_wind) # Non-negative
            
            # Rainfall correlates with high cloud cover
            rainfall = 0.0
            if current_cloud > 80.0 and context.rng.random() > 0.5:
                rainfall = context.rng.uniform(1.0, 10.0)
                
            # Effective irradiance drops with cloud cover
            effective_irradiance = clear_sky_irradiance * (1.0 - (current_cloud / 100.0) * 0.7)
            
            humidity = min(100.0, max(0.0, 50.0 + (current_cloud * 0.3) + context.rng.uniform(-5, 5)))
            
            records.append(Weather(
                timestamp=t,
                region=r,
                latitude=rb["lat"],
                longitude=rb["lon"],
                temperature_c=round(temp, 2),
                solar_irradiance_w_m2=round(max(0, effective_irradiance), 2),
                cloud_cover_pct=round(current_cloud, 2),
                wind_speed_kmh=round(current_wind, 2),
                humidity_pct=round(humidity, 2),
                rainfall_mm=round(rainfall, 2)
            ))
            
    return records
