import numpy as np
import random
from datetime import datetime, timedelta

def generate_drill_data(n_collars=45) -> tuple[list[dict], list[dict]]:
    center_lat = 21.5500
    center_lng = 79.6833
    lat_deg_per_m = 1 / 111000
    lng_deg_per_m = 1 / 103000
    
    collars_list = []
    assays_list = []
    
    rng = np.random.default_rng(42)
    
    for i in range(1, n_collars + 1):
        hole_id = f"DH-{i:03d}"
        
        # Spread within ~800m
        r = rng.uniform(0, 800)
        theta = rng.uniform(0, 2 * np.pi)
        
        dx = r * np.cos(theta)
        dy = r * np.sin(theta)
        
        lat = center_lat + dy * lat_deg_per_m
        lng = center_lng + dx * lng_deg_per_m
        
        total_depth = rng.uniform(60, 200)
        
        collars_list.append({
            "hole_id": hole_id,
            "latitude": float(lat),
            "longitude": float(lng),
            "elevation": float(rng.uniform(300, 350)),
            "total_depth": float(total_depth),
            "dip": -90.0,
            "azimuth": 0.0,
            "drilled_date": (datetime.now() - timedelta(days=rng.uniform(10, 365))).isoformat()
        })
        
        current_depth = 0.0
        while current_depth < total_depth:
            interval_bottom = min(current_depth + 2.0, total_depth)
            
            # Grade distribution logic
            depth_factor = 1.0
            if 20 <= current_depth <= 80:
                depth_factor = 1.5 # Enrichment zone
            elif current_depth > 120:
                depth_factor = 0.5
                
            dist_center = np.sqrt(dx**2 + dy**2)
            
            if dist_center <= 200:
                # High grade
                mn_mean = 46.0 * depth_factor
                mn_std = 2.0
            elif dist_center <= 500:
                # Medium grade
                mn_mean = 39.5 * depth_factor
                mn_std = 4.5
            elif dist_center <= 800:
                # Low grade
                mn_mean = 30.0 * depth_factor
                mn_std = 5.0
            else:
                # Barren
                mn_mean = 10.0
                mn_std = 5.0
                
            mn_grade = rng.normal(mn_mean, mn_std)
            mn_grade = np.clip(mn_grade, 0.1, 52.0)
            
            if mn_grade >= 44:
                fe_grade = rng.uniform(4, 7)
                sio2 = rng.uniform(4, 9)
                lithology = rng.choice(['Mn Oxide', 'Mn Carbonate'], p=[0.8, 0.2])
            elif mn_grade >= 35:
                fe_grade = rng.uniform(7, 14)
                sio2 = rng.uniform(9, 15)
                lithology = rng.choice(['Mn Oxide', 'Mn Carbonate', 'Quartzite'], p=[0.5, 0.3, 0.2])
            elif mn_grade >= 25:
                fe_grade = rng.uniform(14, 24)
                sio2 = rng.uniform(15, 25)
                lithology = rng.choice(['Quartzite', 'Phyllite', 'Mn Carbonate'], p=[0.4, 0.4, 0.2])
            else:
                fe_grade = rng.uniform(20, 35)
                sio2 = rng.uniform(25, 45)
                lithology = rng.choice(['Quartzite', 'Phyllite', 'Laterite'], p=[0.3, 0.5, 0.2])
                
            p_grade = rng.uniform(0.05, 0.35)
            
            assays_list.append({
                "hole_id": hole_id,
                "depth_from": float(current_depth),
                "depth_to": float(interval_bottom),
                "mn_pct": float(mn_grade),
                "fe_pct": float(fe_grade),
                "sio2_pct": float(sio2),
                "p_pct": float(p_grade),
                "lithology": str(lithology)
            })
            
            current_depth = interval_bottom
            
    return collars_list, assays_list

def generate_magnetics_grid(size=512) -> np.ndarray:
    rng = np.random.default_rng(101)
    noise = rng.normal(0, 1, (size, size))
    import scipy.ndimage as ndimage
    macro = ndimage.gaussian_filter(noise, sigma=32)
    micro = ndimage.gaussian_filter(rng.normal(0, 1, (size, size)), sigma=8)
    grid = macro * 100 + micro * 20
    
    # Add structural trend
    x, y = np.meshgrid(np.arange(size), np.arange(size))
    trend = np.exp(-((x - size/2)**2 + (y - size/2 + 50)**2) / 10000) * 150
    return grid + trend

def generate_gravity_grid(size=512) -> np.ndarray:
    rng = np.random.default_rng(202)
    noise = rng.normal(0, 1, (size, size))
    import scipy.ndimage as ndimage
    base = ndimage.gaussian_filter(noise, sigma=48) * 5
    
    x, y = np.meshgrid(np.arange(size), np.arange(size))
    dist = np.sqrt((x - size/2)**2 + (y - size/2)**2)
    anomaly = np.exp(-(dist**2) / 8000) * 8.0
    return base + anomaly
