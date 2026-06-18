import numpy as np
import pandas as pd
from typing import Dict, List
from .flow_graph import FlowGraphState

class LiveFlowAnalyzer:
    def __init__(self, timeframe: str = '15m'):
        self.timeframe = timeframe
        if timeframe == '15m':
            self.h24_candles = 96
        else:
            self.h24_candles = 24

    def prepare_vectorized_features(self, feature_dfs: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
        """
        Pre-computes rs_vs_eth, rs_eth_zscore, and decoupling_score in a vectorized manner
        for all dataframes to maximize performance.
        """
        # Ensure we have ETH and BTC data
        eth_key = 'ETH/USDT'
        btc_key = 'BTC/USDT'
        if eth_key not in feature_dfs or btc_key not in feature_dfs:
            raise KeyError("ETH/USDT and BTC/USDT must be present in feature_dfs for Live Flow calculations.")
            
        eth_close = feature_dfs[eth_key]['close']
        btc_returns = feature_dfs[btc_key]['close'].pct_change().fillna(0)
        
        updated_dfs = {}
        for symbol, df in feature_dfs.items():
            df = df.copy()
            
            # 1. RS vs ETH
            df['rs_vs_eth'] = df['close'] / eth_close
            rs_eth_mean = df['rs_vs_eth'].rolling(window=self.h24_candles, min_periods=min(12, self.h24_candles)).mean()
            rs_eth_std = df['rs_vs_eth'].rolling(window=self.h24_candles, min_periods=min(12, self.h24_candles)).std().replace(0, 1e-9)
            df['rs_eth_zscore'] = (df['rs_vs_eth'] - rs_eth_mean) / rs_eth_std
            
            # 2. Decoupling Score (1.0 - Pearson correlation of returns)
            asset_returns = df['close'].pct_change().fillna(0)
            rolling_corr = asset_returns.rolling(window=self.h24_candles, min_periods=min(12, self.h24_candles)).corr(btc_returns)
            rolling_corr = rolling_corr.fillna(1.0) # Assume full decoupling if no correlation can be computed
            
            # Upside decoupling factor: returns over 4 hours (16 candles) are positive
            ret_4h = df['close'].pct_change(16).fillna(0)
            upside_factor = np.where(ret_4h > 0, 1.0, 0.2)
            
            # Decoupling score ranges from 0 to 100 ((1.0 - corr) * 50)
            df['decoupling_score'] = np.clip((1.0 - rolling_corr) * 50.0 * upside_factor, 0.0, 100.0)
            
            # Fill pre-listing NaNs back to NaN
            pre_listing_mask = df['close'].isna()
            df.loc[pre_listing_mask, ['rs_vs_eth', 'rs_eth_zscore', 'decoupling_score']] = np.nan
            
            updated_dfs[symbol] = df
            
        return updated_dfs

    def compute_live_flow_scores(self, feature_dfs: Dict[str, pd.DataFrame], graph_state: FlowGraphState, current_idx: int) -> Dict[str, float]:
        """
        Computes the final live_flow_score (0-100) for all assets at a specific index.
        Requires the current active graph_state to compute sector_rotation_score.
        """
        # Sum incoming edge weights for each asset
        incoming_weights = {s.split('/')[0]: 0.0 for s in feature_dfs.keys()}
        for edge in graph_state.edges:
            if edge.target in incoming_weights:
                incoming_weights[edge.target] += edge.weight
                
        live_flow_scores = {}
        for symbol, df in feature_dfs.items():
            symbol_short = symbol.split('/')[0]
            
            if current_idx >= len(df):
                live_flow_scores[symbol_short] = np.nan
                continue
                
            row = df.iloc[current_idx]
            
            # If asset is not listed or has missing data, score is NaN
            if pd.isna(row['close']) or pd.isna(row['volume_rank']):
                live_flow_scores[symbol_short] = np.nan
                continue
                
            # Compute raw components
            whale_link_score = float(row.get('whale_link_score', 0.0))
            
            rs_eth_z = float(row.get('rs_eth_zscore', 0.0))
            rs_eth_score = float(np.clip(rs_eth_z * 20.0, 0.0, 100.0))
            
            decoupling_score = float(row.get('decoupling_score', 0.0))
            
            # Sector rotation score based on incoming edge sum
            incoming_sum = incoming_weights.get(symbol_short, 0.0)
            sector_rotation_score = float(np.clip(incoming_sum * 100.0, 0.0, 100.0))
            
            # Weighted live flow score composition
            # 40% Core Whale Link Score
            # 20% RS vs ETH Score
            # 20% Decoupling Score
            # 20% Sector Rotation Score
            score = (
                0.40 * whale_link_score +
                0.20 * rs_eth_score +
                0.20 * decoupling_score +
                0.20 * sector_rotation_score
            )
            
            live_flow_scores[symbol_short] = float(np.clip(score, 0.0, 100.0))
            
        return live_flow_scores
