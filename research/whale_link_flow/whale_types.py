import pandas as pd
import numpy as np
from typing import Dict, Any

class WhaleTypeClassifier:
    @staticmethod
    def classify_whale_types(
        symbol: str,
        row: pd.Series,
        cycle_phase: str,
        live_flow_score: float
    ) -> Dict[str, float]:
        """
        Classifies and scores the active whale profiles (0-100) for a given asset.
        """
        symbol_short = symbol.split('/')[0]
        
        # If asset is not listed or has missing data, return all scores as NaN
        if pd.isna(row['close']) or pd.isna(row['volume_rank']):
            return {
                'blue_whale': np.nan,
                'orca': np.nan,
                'humpback': np.nan,
                'shark': np.nan,
                'sperm_whale': np.nan,
                'dominant_type': 'UNKNOWN',
                'confidence': np.nan
            }
            
        # Extract features
        vol_rank = row.get('volume_rank', 12.0)
        rank_mom = row.get('rank_momentum', 0.0)
        vol_slope = row.get('volume_slope', 0.0)
        price_slope = row.get('price_slope', 0.0)
        vol_exp = row.get('volatility_expansion', 1.0)
        decoupling = row.get('decoupling_score', 50.0)
        whale_score = row.get('whale_link_score', 50.0)
        
        # 1. Blue Whale (BTC/Institution/ETF centric)
        blue_whale = 50.0
        if cycle_phase in ['pre_halving', 'post_halving_0_180']:
            blue_whale += 20.0
        if decoupling < 30.0:
            blue_whale += 20.0
        if symbol_short in ['BTC', 'ETH']:
            blue_whale += 10.0
        else:
            blue_whale -= 20.0 # Institutions rarely lead alt runs
            
        # 2. Orca (Alt season / Sector rotation)
        orca = 50.0
        if cycle_phase == 'late_cycle':
            orca += 20.0
        if rank_mom > 0:
            orca += 10.0
        if decoupling > 50.0:
            orca += 10.0
        if whale_score > 60.0 and symbol_short not in ['BTC']:
            orca += 10.0
            
        # 3. Humpback (Fear Accumulator - Buy bottom/sell top)
        humpback = 30.0
        if cycle_phase == 'bear_reset':
            humpback += 40.0
        if vol_slope > 0 and price_slope <= 0:
            humpback += 20.0
        if decoupling > 40.0:
            humpback += 10.0
            
        # 4. Shark (Short-term Pump & Dump)
        shark = 40.0
        if vol_exp > 1.3:
            shark += 20.0
        if price_slope > 0:
            shark += 20.0
        if rank_mom > 3:
            shark += 10.0
        if cycle_phase in ['late_cycle', 'post_halving_180_360']:
            shark += 10.0
            
        # 5. Sperm Whale (News/Policy Front-running)
        sperm_whale = 40.0
        if decoupling > 60.0:
            sperm_whale += 20.0
        if price_slope > 0 and vol_slope > 0:
            sperm_whale += 20.0
        if whale_score > 70.0:
            sperm_whale += 20.0
            
        scores = {
            'blue_whale': float(np.clip(blue_whale, 0.0, 100.0)),
            'orca': float(np.clip(orca, 0.0, 100.0)),
            'humpback': float(np.clip(humpback, 0.0, 100.0)),
            'shark': float(np.clip(shark, 0.0, 100.0)),
            'sperm_whale': float(np.clip(sperm_whale, 0.0, 100.0))
        }
        
        dominant_type = max(scores, key=scores.get)
        confidence = scores[dominant_type]
        
        scores['dominant_type'] = dominant_type
        scores['confidence'] = confidence
        
        return scores
