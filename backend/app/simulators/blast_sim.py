import math
import random
from datetime import datetime, timedelta

def calculate_kuzram(burden, spacing, bench_height, powder_factor, explosive_type) -> dict:
    A = 7.0 # Medium hard rock factor
    K = powder_factor
    Qe = powder_factor * burden * spacing * bench_height
    
    rws_map = {'ANFO': 100, 'Emulsion': 110, 'Slurry': 95}
    RWS = rws_map.get(explosive_type, 100)
    
    # X50 in cm
    x50_cm = A * (K ** -0.8) * (Qe ** (1/6)) * ((115/RWS) ** (19/30))
    
    # Uniformity index (simplified)
    # n = (2.2 - 14 * burden / drill_diam) * math.sqrt(1 + spacing/burden) ...
    # Simplified estimation for n
    n = 1.2 * math.sqrt(1 + spacing/burden)
    
    # P80
    # X = Xc / (0.693 ^ (1/n)), Xc = X50
    p80_cm = x50_cm / (0.693 ** (1/n)) * (-math.log(0.2))**(1/n)
    
    return {
        "x50_cm": float(x50_cm),
        "uniformity_n": float(n),
        "p80_cm": float(p80_cm)
    }

def generate_blast_history(n_blasts=20) -> list[dict]:
    rng = random.Random(44)
    blasts = []
    
    now = datetime.now()
    start_date = now - timedelta(days=90)
    
    for i in range(n_blasts):
        # 13:00 to 14:00
        days_offset = rng.uniform(0, 90)
        blast_time = start_date + timedelta(days=days_offset)
        blast_time = blast_time.replace(hour=13, minute=rng.randint(0, 59), second=0, microsecond=0)
        
        status = 'Fired' if blast_time < now else 'Planned'
        
        burden = rng.uniform(2.5, 3.2)
        spacing = rng.uniform(3.0, 4.0)
        bench_height = rng.uniform(6.0, 8.0)
        powder_factor = rng.uniform(0.25, 0.45)
        explosive_type = rng.choice(['ANFO', 'Emulsion', 'Slurry'])
        
        kuzram = calculate_kuzram(burden, spacing, bench_height, powder_factor, explosive_type)
        
        blast = {
            "blast_id": f"BL-{blast_time.strftime('%Y%m%d')}-{i+1:02d}",
            "location_lat": rng.uniform(21.5490, 21.5510),
            "location_lng": rng.uniform(79.6825, 79.6845),
            "bench_id": f"B-{rng.randint(1, 6)}",
            "timestamp": blast_time.isoformat(),
            "status": status,
            "bench_height": float(bench_height),
            "burden": float(burden),
            "spacing": float(spacing),
            "num_holes": rng.randint(30, 80),
            "powder_factor": float(powder_factor),
            "explosive_type": explosive_type,
            "x50_cm": kuzram["x50_cm"],
            "uniformity_n": kuzram["uniformity_n"],
            "p80_cm": kuzram["p80_cm"],
            "ppv_mm_s": rng.uniform(2.0, 12.0) if status == 'Fired' else None
        }
        blasts.append(blast)
        
    blasts.sort(key=lambda x: x["timestamp"])
    return blasts
