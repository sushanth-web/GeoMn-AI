from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import numpy as np
from typing import Dict, Any, List

class HealthModel:
    def __init__(self):
        self.model = IsolationForest(contamination=0.1, random_state=42)
        self.scaler = StandardScaler()
        self.is_trained = False
        self.features = ['engine_temp_c', 'hydraulic_temp_c', 'coolant_temp_c', 
                         'vibration_rms', 'fuel_rate_lph', 'hydraulic_pressure_bar']
                         
    def train(self, telemetry_history: List[Dict[str, Any]]):
        if not telemetry_history:
            X = np.random.randn(200, len(self.features))
            X = self.scaler.fit_transform(X)
            self.model.fit(X)
        else:
            import pandas as pd
            df = pd.DataFrame(telemetry_history)
            if all(f in df.columns for f in self.features):
                X = df[self.features].values
                X = self.scaler.fit_transform(X)
                self.model.fit(X)
        self.is_trained = True
        
    def predict(self, current_telemetry: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        results = []
        if not current_telemetry or not self.is_trained:
            return results
            
        for tele in current_telemetry:
            feats = []
            for f in self.features:
                feats.append(tele.get(f, 0.0))
            
            X = np.array([feats])
            X_scaled = self.scaler.transform(X)
            
            score = self.model.decision_function(X_scaled)[0]
            is_anomaly = self.model.predict(X_scaled)[0] == -1
            
            health_pct = 100 if not is_anomaly else max(0, int(100 + score * 50))
            
            msg = ""
            action = ""
            if is_anomaly:
                msg = "Abnormal sensor readings detected."
                action = "Schedule immediate inspection."
                if tele.get('engine_temp_c', 0) > 105:
                    msg = "Engine overheating."
                    action = "Reduce load and inspect cooling system."
                elif tele.get('vibration_rms', 0) > 5.0:
                    msg = "High vibration detected."
                    action = "Inspect bearings and structural integrity."
            
            results.append({
                "equipment_id": tele.get("equipment_id", "Unknown"),
                "health_pct": health_pct,
                "anomaly_score": float(score),
                "is_anomaly": bool(is_anomaly),
                "alert_message": msg,
                "recommended_action": action
            })
            
        return results
