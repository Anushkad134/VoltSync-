import random
from app.core.config import settings

class GenerationContext:
    def __init__(self, stations):
        self.seed = settings.RANDOM_SEED
        self.days = settings.SIMULATION_DAYS
        self.interval = settings.INTERVAL_MINUTES
        self.sessions_per_station = settings.SESSIONS_PER_STATION_PER_DAY
        self.rng = random.Random(self.seed)
        
        # Derive regions from stations
        self.stations = stations
        self.regions = self._derive_regions(stations)
        
    def _derive_regions(self, stations):
        regions = set()
        for s in stations:
            # Simple region identification: State + District/City
            r = f"{s.state} - {s.district_city_village}".strip()
            regions.add(r)
        return sorted(list(regions))
