import random
import math
from datetime import datetime, timedelta

class WeatherSimulator:
    def __init__(self, seed=42):
        self.rng = random.Random(seed)
        self.temperature_c = 30.0
        self.humidity_pct = 50.0
        self.wind_speed_kmh = 10.0
        self.rainfall_mm_hr = 0.0
        
        self.rain_event_active = False
        self.rain_intensity_target = 0.0
        self.rain_duration_ticks = 0
        self.rain_current_tick = 0
        
        self.cumulative_history = [] # store last 24h of mm falls

    def tick(self, dt=1.0) -> dict:
        # Wander temp and wind
        self.temperature_c += self.rng.uniform(-0.5, 0.5)
        self.temperature_c = max(25.0, min(42.0, self.temperature_c))
        
        self.wind_speed_kmh += self.rng.uniform(-1.0, 1.0)
        self.wind_speed_kmh = max(5.0, min(25.0, self.wind_speed_kmh))
        
        # Handle rain event
        if self.rain_event_active:
            self.rain_current_tick += 1
            progress = self.rain_current_tick / self.rain_duration_ticks
            
            # Simple parabolic shape for rain intensity
            current_intensity = self.rain_intensity_target * 4 * progress * (1 - progress)
            self.rainfall_mm_hr = max(0.0, current_intensity)
            
            if self.rain_current_tick >= self.rain_duration_ticks:
                self.rain_event_active = False
                self.rainfall_mm_hr = 0.0
        else:
            self.rainfall_mm_hr = 0.0
            
        # Update humidity based on rain
        if self.rainfall_mm_hr > 0:
            self.humidity_pct = min(95.0, self.humidity_pct + 2.0)
        else:
            self.humidity_pct = max(30.0, self.humidity_pct - 0.5)
            
        # Cumulative logic (dt is in seconds, so mm_hr * dt/3600 = mm)
        mm_fallen = self.rainfall_mm_hr * (dt / 3600.0)
        self.cumulative_history.append((datetime.now(), mm_fallen))
        
        # Prune older than 24h
        cutoff = datetime.now() - timedelta(hours=24)
        self.cumulative_history = [x for x in self.cumulative_history if x[0] > cutoff]
        
        cumulative_24h = sum(x[1] for x in self.cumulative_history)
        
        # Determine TARP level
        if self.rainfall_mm_hr > 25 or cumulative_24h > 65:
            tarp_level = "RED"
        elif self.rainfall_mm_hr >= 15 or cumulative_24h >= 40:
            tarp_level = "AMBER"
        else:
            tarp_level = "GREEN"
            
        return {
            "rainfall_mm_hr": float(self.rainfall_mm_hr),
            "cumulative_24h_mm": float(cumulative_24h),
            "temperature_c": float(self.temperature_c),
            "humidity_pct": float(self.humidity_pct),
            "wind_speed_kmh": float(self.wind_speed_kmh),
            "tarp_level": tarp_level
        }

    def get_rain_factor(self) -> float:
        if self.rainfall_mm_hr > 25:
            return 0.0 # RED - stopped
        elif self.rainfall_mm_hr >= 15:
            return 0.5 # Moderate rain slows down
        elif self.rainfall_mm_hr > 0:
            return 0.7 # Light rain
        return 1.0

    def trigger_rain_event(self, intensity='moderate'):
        self.rain_event_active = True
        self.rain_current_tick = 0
        self.rain_duration_ticks = 60 * 30 # say 30 minutes if tick=1s
        
        if intensity == 'light':
            self.rain_intensity_target = 8.0
        elif intensity == 'moderate':
            self.rain_intensity_target = 18.0
        elif intensity == 'heavy':
            self.rain_intensity_target = 35.0

def generate_weather_history(days=90) -> list[dict]:
    rng = random.Random(77)
    history = []
    
    start_time = datetime.now() - timedelta(days=days)
    
    cumulative_history = []
    
    for i in range(days * 24):
        current_time = start_time + timedelta(hours=i)
        
        # Simulate monsoon July-Aug (months 7, 8)
        is_monsoon = current_time.month in [7, 8]
        
        if is_monsoon and rng.random() < 0.15:
            rain = rng.uniform(5, 30)
        elif not is_monsoon and rng.random() < 0.02:
            rain = rng.uniform(2, 10)
        else:
            rain = 0.0
            
        cumulative_history.append(rain)
        if len(cumulative_history) > 24:
            cumulative_history.pop(0)
            
        cumulative = sum(cumulative_history)
        
        if rain > 25 or cumulative > 65:
            tarp = "RED"
        elif rain >= 15 or cumulative >= 40:
            tarp = "AMBER"
        else:
            tarp = "GREEN"
            
        temp = rng.uniform(25, 35) if is_monsoon else rng.uniform(30, 42)
        
        history.append({
            "timestamp": current_time.isoformat(),
            "temperature_c": float(temp),
            "humidity_pct": float(rng.uniform(60, 95) if is_monsoon else rng.uniform(30, 60)),
            "wind_speed_kmh": float(rng.uniform(5, 25)),
            "rainfall_mm_hr": float(rain),
            "cumulative_24h_mm": float(cumulative),
            "tarp_level": tarp
        })
        
    return history
