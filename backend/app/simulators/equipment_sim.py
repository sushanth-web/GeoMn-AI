import random
import math

class EquipmentSimulator:
    def __init__(self, equipment_ids: list[str]):
        self.equipment_ids = equipment_ids
        self.baselines = {}
        self.anomalies = {}
        self.rng = random.Random(123)
        
        for eid in equipment_ids:
            self.baselines[eid] = {
                "engine_rpm_idle": self.rng.uniform(800, 1000),
                "engine_rpm_work": self.rng.uniform(1400, 1800),
                "engine_temp_c": self.rng.uniform(82, 88),
                "hydraulic_temp_c": self.rng.uniform(65, 75),
                "coolant_temp_c": self.rng.uniform(80, 85),
                "vibration_rms": self.rng.uniform(0.8, 1.2),
                "fuel_rate_idle": self.rng.uniform(75, 85),
                "fuel_rate_work": self.rng.uniform(180, 240),
                "hydraulic_pressure_bar": self.rng.uniform(290, 310),
                "tire_pressure_psi": self.rng.uniform(108, 112)
            }

    def inject_anomaly(self, equipment_id: str, anomaly_type: str):
        max_ticks = 60 if anomaly_type == 'bearing_overheat' else (90 if anomaly_type == 'hydraulic_leak' else 120)
        self.anomalies[equipment_id] = {
            "type": anomaly_type,
            "tick_count": 0,
            "max_ticks": max_ticks,
            "equipment_id": equipment_id
        }

    def clear_anomaly(self, equipment_id: str):
        if equipment_id in self.anomalies:
            del self.anomalies[equipment_id]

    def get_health_scores(self) -> dict[str, float]:
        scores = {}
        for eid in self.equipment_ids:
            health = 100.0
            if eid in self.anomalies:
                progress = min(1.0, self.anomalies[eid]["tick_count"] / self.anomalies[eid]["max_ticks"])
                health -= progress * 40.0 # Drops to 60% health
            scores[eid] = health
        return scores

    def tick(self, fleet_state: list[dict]) -> list[dict]:
        results = []
        
        fleet_dict = {t["truck_id"]: t for t in fleet_state}
        
        for eid in self.equipment_ids:
            b = self.baselines[eid]
            status = fleet_dict.get(eid, {}).get("status", "IDLE")
            
            if status in ["LOADING", "HAULING"]:
                rpm = b["engine_rpm_work"]
                fuel = b["fuel_rate_work"]
                temp_add = 5.0
                hyd_press = b["hydraulic_pressure_bar"]
            elif status == "RETURNING":
                rpm = (b["engine_rpm_idle"] + b["engine_rpm_work"]) / 2
                fuel = (b["fuel_rate_idle"] + b["fuel_rate_work"]) / 2
                temp_add = 2.0
                hyd_press = b["hydraulic_pressure_bar"] * 0.9
            else: # QUEUING, DUMPING, IDLE
                rpm = b["engine_rpm_idle"]
                fuel = b["fuel_rate_idle"]
                temp_add = 0.0
                hyd_press = b["hydraulic_pressure_bar"] * 0.8
                
            # Base values
            readings = {
                "equipment_id": eid,
                "engine_rpm": rpm * self.rng.uniform(0.98, 1.02),
                "engine_temp_c": (b["engine_temp_c"] + temp_add) * self.rng.uniform(0.98, 1.02),
                "hydraulic_temp_c": (b["hydraulic_temp_c"] + temp_add) * self.rng.uniform(0.98, 1.02),
                "coolant_temp_c": (b["coolant_temp_c"] + temp_add * 0.5) * self.rng.uniform(0.98, 1.02),
                "vibration_rms": b["vibration_rms"] * self.rng.uniform(0.95, 1.05),
                "fuel_rate_lph": fuel * self.rng.uniform(0.95, 1.05),
                "hydraulic_pressure_bar": hyd_press * self.rng.uniform(0.98, 1.02),
                "tire_pressure_psi": b["tire_pressure_psi"] * self.rng.uniform(0.99, 1.01),
                "health_pct": 100.0
            }
            
            # Apply anomaly
            if eid in self.anomalies:
                anom = self.anomalies[eid]
                anom["tick_count"] += 1
                progress = min(1.0, anom["tick_count"] / anom["max_ticks"])
                
                readings["health_pct"] -= progress * 40.0
                
                if anom["type"] == 'bearing_overheat':
                    readings["vibration_rms"] = b["vibration_rms"] + progress * (7.8 - b["vibration_rms"])
                elif anom["type"] == 'hydraulic_leak':
                    readings["hydraulic_pressure_bar"] = b["hydraulic_pressure_bar"] - progress * (b["hydraulic_pressure_bar"] - 180)
                    readings["hydraulic_temp_c"] += progress * 20.0
                elif anom["type"] == 'engine_overheat':
                    readings["engine_temp_c"] = b["engine_temp_c"] + progress * (118 - b["engine_temp_c"])
                    
            results.append(readings)
            
        return results
