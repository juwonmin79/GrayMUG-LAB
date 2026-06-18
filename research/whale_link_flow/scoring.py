import numpy as np
import pandas as pd
from typing import Dict

class Scorer:
    @staticmethod
    def calculate_whale_link_score(row: pd.Series) -> float:
        """
        Calculates a Whale Link Score from 0 to 100 for a single asset at a specific timestamp.
        """
        # If asset is not listed or has missing data, return NaN
        if pd.isna(row['close']) or pd.isna(row['volume_rank']):
            return np.nan
            
        score = 0.0
        
        # 1. Volume Rank Component (Max 40 points)
        rank = row['volume_rank']
        if rank <= 1:
            score += 40.0
        elif rank <= 3:
            score += 35.0
        elif rank <= 6:
            score += 25.0
        elif rank <= 9:
            score += 15.0
        else:
            score += 5.0
            
        # 2. Rank Momentum Component (Max 20 points)
        momentum = row['rank_momentum']
        if momentum > 0:
            score += min(20.0, momentum * 4.0)
            
        # 3. RS vs BTC Z-Score Component (Max 15 points)
        rs_z = row['rs_zscore']
        if rs_z > 0:
            score += min(15.0, rs_z * 5.0)
            
        # 4. Volatility Expansion Component (Max 15 points)
        vol_exp = row['volatility_expansion']
        if vol_exp > 1.1:
            score += min(15.0, (vol_exp - 1.0) * 15.0)
            
        # 5. Price Slope / Trend Component (Max 10 points)
        p_slope = row['price_slope']
        close = row['close']
        if close > 0:
            rel_slope = p_slope / close
            if rel_slope > 0:
                score += min(10.0, rel_slope * 2000.0) # Scale slope relative to price
                
        # Clip score to [0, 100]
        return float(np.clip(score, 0.0, 100.0))

    def score_all_assets(self, feature_dfs: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
        """
        Adds a 'whale_link_score' column to all asset feature dataframes.
        """
        scored_dfs = {}
        for symbol, df in feature_dfs.items():
            df = df.copy()
            df['whale_link_score'] = df.apply(self.calculate_whale_link_score, axis=1)
            scored_dfs[symbol] = df
        return scored_dfs
