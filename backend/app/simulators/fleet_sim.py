import math
import random
import time

class FleetSimulator:
    HAUL_ROAD_WAYPOINTS = [
        (21.5495, 79.6830), (21.5498, 79.6835), (21.5503, 79.6842), 
        (21.5510, 79.6850), (21.5518, 79.6858), (21.5525, 79.6863), 
        (21.5532, 79.6868), (21.5538, 79.6872), (21.5542, 79.6878), 
        (21.5548, 79.6882)
    ]
    
    RETURN_ROAD = [(lat, lng + 0.0003) for lat, lng in reversed(HAUL_ROAD_WAYPOINTS)]
    
    def __init__(self, num_trucks=12):
        self.num_trucks = num_trucks
        self.trucks = []
        self.total_tonnes = 0.0
        self.start_time = time.time()
        self.rng = random.Random(42)
        
        for i in range(num_trucks):
            truck_id = f"HT-{101 + i}"
            # Spread out initial states
            state_val = self.rng.random()
            if state_val < 0.1:
                status = "LOADING"
                progress = self.rng.uniform(0, 1)
                timer = progress * 240 # 4 mins
                payload = progress * 35.0
                wp_idx = 0
                path = self.HAUL_ROAD_WAYPOINTS
            elif state_val < 0.5:
                status = "HAULING"
                progress = self.rng.uniform(0, 1)
                timer = 0
                payload = 35.0
                wp_idx = int(progress * (len(self.HAUL_ROAD_WAYPOINTS)-1))
                path = self.HAUL_ROAD_WAYPOINTS
            elif state_val < 0.6:
                status = "DUMPING"
                progress = self.rng.uniform(0, 1)
                timer = progress * 60
                payload = 35.0 * (1 - progress)
                wp_idx = len(self.HAUL_ROAD_WAYPOINTS) - 1
                path = self.HAUL_ROAD_WAYPOINTS
            else:
                status = "RETURNING"
                progress = self.rng.uniform(0, 1)
                timer = 0
                payload = 0.0
                wp_idx = int(progress * (len(self.RETURN_ROAD)-1))
                path = self.RETURN_ROAD

            self.trucks.append({
                "truck_id": truck_id,
                "lat": path[wp_idx][0],
                "lng": path[wp_idx][1],
                "heading": 0.0,
                "speed_kmh": 0.0,
                "payload_tonnes": payload,
                "status": status,
                "cycle_count": 0,
                "timer": timer,
                "path": path,
                "wp_idx": wp_idx,
                "segment_progress": 0.0
            })

    def tick(self, dt=1.0, rain_factor=1.0) -> list[dict]:
        output = []
        loading_trucks = sum(1 for t in self.trucks if t["status"] == "LOADING")
        
        for t in self.trucks:
            if t["status"] == "QUEUING":
                if loading_trucks < 2: # Max 2 loaders
                    t["status"] = "LOADING"
                    t["timer"] = 0
                    loading_trucks += 1
                else:
                    t["speed_kmh"] = 0.0
                    
            elif t["status"] == "LOADING":
                load_time = self.rng.uniform(180, 300)
                t["timer"] += dt
                t["payload_tonnes"] = min(35.0, (t["timer"] / load_time) * 35.0)
                t["speed_kmh"] = 0.0
                if t["timer"] >= load_time:
                    t["status"] = "HAULING"
                    t["path"] = self.HAUL_ROAD_WAYPOINTS
                    t["wp_idx"] = 0
                    t["segment_progress"] = 0.0
                    t["payload_tonnes"] = 35.0
                    loading_trucks -= 1
                    
            elif t["status"] == "DUMPING":
                t["timer"] += dt
                t["payload_tonnes"] = max(0.0, 35.0 * (1 - t["timer"] / 60.0))
                t["speed_kmh"] = 0.0
                if t["timer"] >= 60.0:
                    t["status"] = "RETURNING"
                    t["path"] = self.RETURN_ROAD
                    t["wp_idx"] = 0
                    t["segment_progress"] = 0.0
                    t["payload_tonnes"] = 0.0
                    self.total_tonnes += 35.0
                    t["cycle_count"] += 1
                    
            elif t["status"] in ["HAULING", "RETURNING"]:
                speed = self.rng.uniform(12, 18) if t["status"] == "HAULING" else self.rng.uniform(25, 35)
                speed *= rain_factor
                t["speed_kmh"] = speed
                
                speed_ms = speed * (1000 / 3600)
                dist_moved = speed_ms * dt
                
                # Crude distance in meters between waypoints (1 deg lat ~ 111km, 1 deg lng ~ 103km)
                p1 = t["path"][t["wp_idx"]]
                p2 = t["path"][min(t["wp_idx"] + 1, len(t["path"]) - 1)]
                
                dx_m = (p2[1] - p1[1]) * 103000
                dy_m = (p2[0] - p1[0]) * 111000
                seg_length = math.sqrt(dx_m**2 + dy_m**2)
                
                if seg_length > 0:
                    t["heading"] = math.degrees(math.atan2(dx_m, dy_m))
                    if t["heading"] < 0: t["heading"] += 360
                    
                    t["segment_progress"] += dist_moved / seg_length
                    
                    if t["segment_progress"] >= 1.0:
                        t["wp_idx"] += 1
                        t["segment_progress"] = 0.0
                        if t["wp_idx"] >= len(t["path"]) - 1:
                            if t["status"] == "HAULING":
                                t["status"] = "DUMPING"
                                t["timer"] = 0
                            else:
                                t["status"] = "QUEUING"
                                t["path"] = self.HAUL_ROAD_WAYPOINTS
                                t["wp_idx"] = 0
                                
                # Interpolate position
                if t["wp_idx"] < len(t["path"]) - 1:
                    p1 = t["path"][t["wp_idx"]]
                    p2 = t["path"][t["wp_idx"] + 1]
                    t["lat"] = p1[0] + (p2[0] - p1[0]) * t["segment_progress"]
                    t["lng"] = p1[1] + (p2[1] - p1[1]) * t["segment_progress"]

            output.append({
                "truck_id": t["truck_id"],
                "lat": t["lat"],
                "lng": t["lng"],
                "heading": t["heading"],
                "speed_kmh": t["speed_kmh"],
                "payload_tonnes": t["payload_tonnes"],
                "status": t["status"],
                "cycle_count": t["cycle_count"]
            })
            
        return output

    def get_production_rate(self) -> float:
        elapsed_hours = max((time.time() - self.start_time) / 3600.0, 0.001)
        # Using a simulated time scale where 1 real second = maybe 1 sim minute if we wanted, 
        # but the spec asks for completed cycles. 
        # Just returning a realistic scaled value or actual rate.
        cycles = sum(t["cycle_count"] for t in self.trucks)
        if cycles == 0: return 0.0
        # Simulated rate based on cycles
        return cycles * 35.0 / elapsed_hours * 3600 # Assume dt was real time, multiply up for sensible display

    def get_queue_length(self) -> int:
        return sum(1 for t in self.trucks if t["status"] == "QUEUING")
