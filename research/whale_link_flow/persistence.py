import numpy as np
from typing import Dict, List, Tuple

class FlowPersistenceEngine:
    def __init__(self, timeframe: str = '15m'):
        self.timeframe = timeframe
        # Stride=4 means each step is 1 hour. A 24-hour window requires 24 steps of history.
        self.max_history = 24
        self.history: Dict[str, List[float]] = {}
        self.consecutive_count: Dict[str, int] = {}

    def update_and_get_persistence(self, asset: str, score: float) -> float:
        """
        Updates the history for a single asset and returns its persistence_score (0-100).
        """
        if np.isnan(score):
            self.history[asset] = []
            self.consecutive_count[asset] = 0
            return np.nan
            
        # 1. Update history
        if asset not in self.history:
            self.history[asset] = []
            self.consecutive_count[asset] = 0
            
        self.history[asset].append(score)
        if len(self.history[asset]) > self.max_history:
            self.history[asset].pop(0)
            
        # 2. Update duration count (steps above 50.0)
        if score >= 50.0:
            self.consecutive_count[asset] += 1
        else:
            self.consecutive_count[asset] = 0
            
        # 3. Calculate components
        # (a) Duration score: 5 consecutive steps (5 hours) yields 100 points
        consec_steps = self.consecutive_count[asset]
        duration_score = min(100.0, consec_steps * 20.0)
        
        # (b) Acceleration score: difference between current and previous step (1h ago)
        if len(self.history[asset]) >= 2:
            score_prev = self.history[asset][-2]
            acceleration = score - score_prev
            # Scale so that +10 score increase gives +50 points (clamped between 0 and 100)
            acceleration_score = np.clip(acceleration * 5.0 + 50.0, 0.0, 100.0)
        else:
            acceleration_score = 50.0
            
        # (c) Stability score: standard deviation over history
        if len(self.history[asset]) >= 3:
            std_val = np.std(self.history[asset])
            # If std is high, stability is low. If std=20, score is 0. If std=0, score is 100.
            stability_score = np.clip(100.0 - std_val * 5.0, 0.0, 100.0)
        else:
            stability_score = 100.0
            
        # (d) Consolidated score
        persistence_score = 0.40 * duration_score + 0.30 * acceleration_score + 0.30 * stability_score
        return float(np.clip(persistence_score, 0.0, 100.0))
