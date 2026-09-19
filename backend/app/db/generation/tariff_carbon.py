from app.models.tariff_carbon import TariffCarbon

def generate_tariff_carbon(context, renewable_records):
    records = []
    
    # Configuration for regions
    region_bases = {}
    for r in context.regions:
        region_bases[r] = {
            "off_peak": context.rng.uniform(4.0, 6.0),
            "normal": context.rng.uniform(6.5, 9.0),
            "peak": context.rng.uniform(10.0, 15.0),
            "base_carbon": context.rng.uniform(400.0, 800.0) # gCO2/kWh
        }
        
    for ren_rec in renewable_records:
        t = ren_rec.timestamp
        r = ren_rec.region
        rb = region_bases[r]
        
        hour_f = t.hour + t.minute / 60.0
        
        if 0 <= hour_f < 6:
            period = "Off-Peak"
            tariff = rb["off_peak"]
        elif 6 <= hour_f < 17:
            period = "Normal"
            tariff = rb["normal"]
        elif 17 <= hour_f < 22:
            period = "Peak"
            tariff = rb["peak"]
        else:
            period = "Normal"
            tariff = rb["normal"]
            
        # Add small variance
        tariff += context.rng.uniform(-0.2, 0.2)
        
        share = ren_rec.renewable_share_pct
        
        # Carbon intensity drops as renewable share increases
        # Carbon = Base * (1 - share/100)
        carbon = rb["base_carbon"] * (1.0 - (share / 100.0))
        carbon += context.rng.uniform(-10.0, 10.0)
        carbon = max(0.0, carbon)
        
        records.append(TariffCarbon(
            timestamp=t,
            region=r,
            tariff_period=period,
            electricity_tariff_inr_per_kwh=round(tariff, 2),
            renewable_share_pct=round(share, 2),
            grid_carbon_intensity_gco2_per_kwh=round(carbon, 2)
        ))
        
    return records
