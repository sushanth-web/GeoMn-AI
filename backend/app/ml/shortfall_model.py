import xgboost as xgb
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional

FEATURES = [
    'shift_number', 'active_trucks', 'active_shovels', 'rainfall_mm',
    'blast_downtime_hrs', 'equipment_downtime_hrs', 'target_tonnes'
]


class ShortfallModel:
    """
    Predicts end-of-shift tonnage and shortfall risk.

    Two prediction modes are blended:
      - "pace-based": simple linear extrapolation of tonnes produced so far this shift.
      - "model-based": XGBoost regressor trained on historical shifts, predicting the
        likely final tonnage given operating conditions (fleet size, rainfall, downtime).

    Early in a shift we trust the condition-based model more (we have little pace data
    yet); late in the shift we trust the observed pace more (it reflects what's actually
    happening right now). The blend weight shifts smoothly with elapsed shift time.
    """

    def __init__(self):
        self.regressor = xgb.XGBRegressor(n_estimators=150, max_depth=4, random_state=42)
        self.classifier = xgb.XGBClassifier(n_estimators=150, max_depth=4, random_state=42)
        self.is_trained = False
        self.has_fitted_data = False
        self.residual_std: Optional[float] = None
        self.backtest_metrics: Optional[Dict[str, Any]] = None
        self.history_df: pd.DataFrame = pd.DataFrame()

    # ------------------------------------------------------------------ #
    # Training
    # ------------------------------------------------------------------ #
    def train(self, production_history: List[Dict[str, Any]]):
        self.history_df = pd.DataFrame(production_history) if production_history else pd.DataFrame()

        if not production_history or len(production_history) < 5:
            self.is_trained = True
            return

        df = self.history_df
        if not (all(f in df.columns for f in FEATURES) and 'actual_tonnes' in df.columns):
            self.is_trained = True
            return

        X = df[FEATURES]
        y_reg = df['actual_tonnes']
        y_clf = (df['actual_tonnes'] < 0.9 * df['target_tonnes']).astype(int)

        # Honest, out-of-sample accuracy: walk-forward backtest BEFORE we fit on
        # everything. Fitting first and scoring on the training set would just
        # tell us the model memorized the past, not that it can forecast.
        self.backtest_metrics = self._walk_forward_backtest(df)

        self.regressor.fit(X, y_reg)
        if y_clf.nunique() > 1:
            self.classifier.fit(X, y_clf)
        else:
            self.classifier = None  # not enough shortfall/no-shortfall examples to train safely

        residuals = y_reg.values - self.regressor.predict(X)
        self.residual_std = float(np.std(residuals)) if len(residuals) > 1 else max(50.0, 0.05 * y_reg.mean())
        self.has_fitted_data = True
        self.is_trained = True

    def _walk_forward_backtest(self, df: pd.DataFrame, min_train: int = 20, max_samples: int = 60) -> Dict[str, Any]:
        """Retrain on everything up to shift i, predict shift i+1, repeat.
        Capped at `max_samples` most-recent test points to keep startup fast."""
        n = len(df)
        if n <= min_train + 1:
            return {"mape_pct": None, "samples": 0, "shortfall_accuracy_pct": None}

        start = max(min_train, n - max_samples)
        errors = []
        correct_direction = 0
        total = 0

        for i in range(start, n):
            train_df = df.iloc[:i]
            test_row = df.iloc[i:i + 1]
            X_tr, y_tr = train_df[FEATURES], train_df['actual_tonnes']
            X_te = test_row[FEATURES]
            y_te = float(test_row['actual_tonnes'].values[0])
            target_te = float(test_row['target_tonnes'].values[0])

            m = xgb.XGBRegressor(n_estimators=60, max_depth=3, random_state=42)
            m.fit(X_tr, y_tr)
            pred = float(m.predict(X_te)[0])

            errors.append(abs(pred - y_te) / max(y_te, 1.0) * 100.0)

            actual_shortfall = y_te < 0.9 * target_te
            pred_shortfall = pred < 0.9 * target_te
            correct_direction += int(actual_shortfall == pred_shortfall)
            total += 1

        return {
            "mape_pct": round(float(np.mean(errors)), 1) if errors else None,
            "samples": total,
            "shortfall_accuracy_pct": round(correct_direction / total * 100.0, 1) if total else None,
        }

    def get_accuracy_report(self) -> Dict[str, Any]:
        """Backtested accuracy of the trained model, for display in the UI."""
        if self.backtest_metrics is None:
            return {"status": "insufficient_history", "mape_pct": None, "samples": 0, "shortfall_accuracy_pct": None}
        return {"status": "ok", **self.backtest_metrics}

    # ------------------------------------------------------------------ #
    # Current-shift prediction
    # ------------------------------------------------------------------ #
    def _feature_row(self, shift_number, trucks, active_shovels, rainfall, blast, health, target) -> pd.DataFrame:
        return pd.DataFrame([{
            'shift_number': shift_number,
            'active_trucks': trucks,
            'active_shovels': active_shovels,
            'rainfall_mm': rainfall,
            'blast_downtime_hrs': 1.0 if blast else 0.0,
            'equipment_downtime_hrs': max(0.0, (100 - health) / 10.0),
            'target_tonnes': target,
        }])[FEATURES]

    def predict(self, current_state: Dict[str, Any]) -> Dict[str, Any]:
        queue_len = current_state.get('queue_length', 0)
        rainfall = current_state.get('rainfall_mm_hr', 0)
        health = current_state.get('equipment_health_avg', 100)
        trucks = current_state.get('active_trucks', 15)
        active_shovels = current_state.get('active_shovels', 3)
        blast = current_state.get('blast_today', False)
        current_tonnes = current_state.get('current_tonnes', 5000)
        target = current_state.get('target_tonnes', 10000)
        elapsed = current_state.get('shift_elapsed_hrs', 4)
        shift_number = current_state.get('shift_number', 1)

        target_rate = target / 8.0 if elapsed > 0 else 0
        current_rate = current_tonnes / elapsed if elapsed > 0 else 0
        pace_based_pred = current_tonnes + current_rate * (8 - elapsed)

        model_based_pred = None
        if self.has_fitted_data:
            row = self._feature_row(shift_number, trucks, active_shovels, rainfall, blast, health, target)
            model_based_pred = float(self.regressor.predict(row)[0])

        if model_based_pred is not None:
            # Weight shifts from "trust the model" (start of shift) to
            # "trust the observed pace" (end of shift).
            w = min(1.0, max(0.0, elapsed / 8.0))
            pred_tonnes = w * pace_based_pred + (1 - w) * model_based_pred
            model_source = "xgboost_blended"
        else:
            pred_tonnes = pace_based_pred
            model_source = "heuristic_pace"

        # Confidence band: residual std from training, narrowing as the shift
        # progresses (less uncertainty left once most of the shift has happened).
        base_band = self.residual_std if self.residual_std else max(50.0, 0.08 * max(pred_tonnes, 1.0))
        band = base_band * max(0.35, 1.0 - (elapsed / 8.0) * 0.65)

        if self.classifier is not None and self.has_fitted_data:
            row_c = self._feature_row(shift_number, trucks, active_shovels, rainfall, blast, health, target)
            risk = float(self.classifier.predict_proba(row_c)[0][1]) * 100.0
        else:
            risk = 0.0
            if pred_tonnes < target:
                risk = min(100, int((target - pred_tonnes) / target * 100) * 3)

        factors = []
        actions = []

        if queue_len > 3:
            factors.append("High shovel queue times")
            actions.append("Deploy standby truck to reduce shovel queue time")
        if rainfall > 15:
            factors.append("Heavy rainfall reducing traction")
            actions.append("Prepare for potential haulage suspension; pre-position trucks on stable ground")
        if health < 60:
            factors.append("Low overall equipment health")
            actions.append("Schedule maintenance for degraded equipment; activate standby fleet")
        if trucks < 10:
            factors.append("Insufficient active trucks")
            actions.append("Redeploy trucks from lower-priority benches")
        if blast:
            factors.append("Blast downtime")
            actions.append("Coordinate blast timing to minimize shift production impact")
        if current_rate < target_rate:
            factors.append("Suboptimal production rate")
            actions.append("Redirect trucks to higher-grade bench B-2 to maximize Mn content per load")

        return {
            "predicted_tonnes": round(pred_tonnes, 2),
            "confidence_low": round(max(0.0, pred_tonnes - band), 2),
            "confidence_high": round(pred_tonnes + band, 2),
            "shortfall_risk_pct": round(risk, 1),
            "top_risk_factors": factors,
            "corrective_actions": actions,
            "model_source": model_source,
        }

    # ------------------------------------------------------------------ #
    # Multi-shift outlook
    # ------------------------------------------------------------------ #
    def forecast_shifts(self, n_ahead: int = 3) -> List[Dict[str, Any]]:
        """Project the next N shifts assuming recent typical operating conditions.
        Uncertainty widens the further out the forecast reaches."""
        df = self.history_df
        if df is None or df.empty:
            return []

        recent = df.tail(6)
        avg_trucks = float(recent['active_trucks'].mean()) if 'active_trucks' in recent else 10
        avg_shovels = float(recent['active_shovels'].mean()) if 'active_shovels' in recent else 3
        avg_rain = float(recent['rainfall_mm'].mean()) if 'rainfall_mm' in recent else 0
        avg_blast = float(recent['blast_downtime_hrs'].mean()) if 'blast_downtime_hrs' in recent else 0
        avg_eqp_down = float(recent['equipment_downtime_hrs'].mean()) if 'equipment_downtime_hrs' in recent else 0
        avg_target = float(recent['target_tonnes'].mean()) if 'target_tonnes' in recent else 1350.0
        last_shift_num = int(df['shift_number'].iloc[-1]) if 'shift_number' in df.columns and len(df) else 1

        base_band = self.residual_std if self.residual_std else max(50.0, 0.08 * avg_target)

        results = []
        for i in range(1, n_ahead + 1):
            shift_num = (last_shift_num + i - 1) % 3 + 1

            if self.has_fitted_data:
                row = pd.DataFrame([{
                    'shift_number': shift_num, 'active_trucks': avg_trucks,
                    'active_shovels': avg_shovels, 'rainfall_mm': avg_rain,
                    'blast_downtime_hrs': avg_blast, 'equipment_downtime_hrs': avg_eqp_down,
                    'target_tonnes': avg_target,
                }])[FEATURES]
                pred = float(self.regressor.predict(row)[0])
                risk = float(self.classifier.predict_proba(row)[0][1]) * 100.0 if self.classifier is not None else None
            else:
                pred = float(recent['actual_tonnes'].mean()) if 'actual_tonnes' in recent and len(recent) else avg_target * 0.9
                risk = None

            widened_band = base_band * (1 + 0.3 * i)  # further out = less certain
            results.append({
                "shift_offset": i,
                "shift_number": shift_num,
                "predicted_tonnes": round(pred, 2),
                "target_tonnes": round(avg_target, 2),
                "confidence_low": round(max(0.0, pred - widened_band), 2),
                "confidence_high": round(pred + widened_band, 2),
                "shortfall_risk_pct": round(risk, 1) if risk is not None else None,
            })

        return results
