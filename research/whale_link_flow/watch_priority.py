import numpy as np
import pandas as pd
from typing import Dict, Any
from .sector_map import get_sector

class WatchPriorityEngine:
    @staticmethod
    def compute_priority(
        asset: str,
        row: pd.Series,
        live_flow_score: float,
        persistence_score: float,
        sector_rotation_score: float,
        dominant_whale_type: str
    ) -> Dict[str, Any]:
        """
        Calculates the watch_priority_score (0-100) for a single asset.
        Formula:
        35% live_flow_score
        25% persistence_score
        20% sector_rotation_score
        10% decoupling_score
        10% whale_link_score
        """
        if np.isnan(live_flow_score) or pd.isna(row['close']):
            return {
                'priority_score': np.nan,
                'sector': get_sector(asset),
                'whale_type': 'UNKNOWN'
            }
            
        whale_link_score = float(row.get('whale_link_score', 0.0))
        decoupling_score = float(row.get('decoupling_score', 0.0))
        
        priority = (
            0.35 * live_flow_score +
            0.25 * persistence_score +
            0.20 * sector_rotation_score +
            0.10 * decoupling_score +
            0.10 * whale_link_score
        )
        
        return {
            'priority_score': float(np.clip(priority, 0.0, 100.0)),
            'sector': get_sector(asset),
            'whale_type': dominant_whale_type
        }
