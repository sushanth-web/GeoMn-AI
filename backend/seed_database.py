import random
from datetime import datetime, timedelta
from sqlmodel import Session

from backend.app.models import DrillHole, DrillAssay, BlastEvent, Equipment, ProductionShift, WeatherReading

def seed_all(engine):
    with Session(engine) as session:
        try:
            # 1. Drill Holes and Assays
            center_lat, center_lng = 21.5500, 79.6833
            
            for i in range(1, 46):
                hole = DrillHole(
                    hole_id=f"DH-{i:03d}",
                    latitude=center_lat + (random.random() - 0.5) * 0.01,
                    longitude=center_lng + (random.random() - 0.5) * 0.01,
                    elevation=random.uniform(280.0, 320.0),
                    total_depth=random.uniform(50.0, 150.0),
                )
                session.add(hole)
                
                # Assays
                current_depth = 0.0
                while current_depth < hole.total_depth:
                    to_m = min(current_depth + random.uniform(1.0, 3.0), hole.total_depth)
                    assay = DrillAssay(
                        hole_id=hole.hole_id,
                        from_m=current_depth,
                        to_m=to_m,
                        mn_pct=random.uniform(25.0, 52.0) if random.random() > 0.3 else random.uniform(5.0, 20.0),
                        fe_pct=random.uniform(5.0, 15.0),
                        sio2_pct=random.uniform(10.0, 30.0),
                        p_pct=random.uniform(0.05, 0.2),
                        lithology=random.choice(["Manganese Ore", "Gondite", "Schist", "Quartzite"])
                    )
                    session.add(assay)
                    current_depth = to_m
            
            # 2. Blast History
            for i in range(1, 21):
                blast = BlastEvent(
                    blast_id=f"BL-{i:03d}",
                    timestamp=(datetime.now() - timedelta(days=i*2)).isoformat(),
                    latitude=center_lat + (random.random() - 0.5) * 0.005,
                    longitude=center_lng + (random.random() - 0.5) * 0.005,
                    bench_id=f"B-{random.randint(1, 5)}",
                    num_holes=random.randint(50, 150),
                    bench_height=random.uniform(6.0, 8.0),
                    burden=random.uniform(2.5, 3.5),
                    spacing=random.uniform(3.0, 4.0),
                    powder_factor=random.uniform(0.4, 0.6),
                    explosive_type=random.choice(["ANFO", "Emulsion"]),
                    fragmentation_x50=random.uniform(150, 300),
                    ppv=random.uniform(2.0, 8.0)
                )
                session.add(blast)
                
            # 3. Equipment
            for i in range(1, 13):
                truck = Equipment(
                    equipment_id=f"HT-{100+i}",
                    equipment_type="Truck",
                    make="BEML",
                    model_name="BH35-2",
                    capacity="35T"
                )
                session.add(truck)
                
            for i in range(1, 4):
                excavator = Equipment(
                    equipment_id=f"EX-{i:02d}",
                    equipment_type="Excavator",
                    make="Tata Hitachi",
                    model_name="EX350",
                    capacity="2.5m3"
                )
                session.add(excavator)
                
            for i in range(1, 3):
                drill = Equipment(
                    equipment_id=f"DR-{i:02d}",
                    equipment_type="Drill",
                    make="Atlas Copco",
                    model_name="ROC D7",
                    capacity="115mm"
                )
                session.add(drill)
                
            # 4. Production Shift History
            start_date = datetime.now() - timedelta(days=90)
            for day in range(90):
                current_date = start_date + timedelta(days=day)
                
                # Simulate monsoon
                is_monsoon = current_date.month in [7, 8]
                
                for shift in range(1, 4):
                    target = random.uniform(1200, 1500)
                    actual_factor = random.uniform(0.5, 0.7) if is_monsoon else random.uniform(0.85, 1.05)
                    actual = target * actual_factor
                    
                    prod_shift = ProductionShift(
                        shift_date=current_date.strftime("%Y-%m-%d"),
                        shift_number=shift,
                        target_tonnes=target,
                        actual_tonnes=actual,
                        ore_tonnes=actual * random.uniform(0.2, 0.3),
                        ob_tonnes=actual * random.uniform(0.7, 0.8),
                        active_trucks=random.randint(8, 12),
                        active_shovels=random.randint(2, 3),
                        rainfall_mm=random.uniform(10, 50) if is_monsoon and random.random() > 0.5 else 0.0,
                        blast_downtime_hrs=random.uniform(0, 1),
                        equipment_downtime_hrs=random.uniform(0, 2)
                    )
                    session.add(prod_shift)
            
            session.commit()
            print("Database seeded successfully.")
            
        except Exception as e:
            session.rollback()
            print(f"Error seeding database: {e}")
