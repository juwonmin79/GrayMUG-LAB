import pandas as pd
import numpy as np
from typing import Dict, List
from .schemas import AssetFeatures

def get_slope(y):
    if len(y) < 2:
        return 0.0
    x = np.arange(len(y))
    slope, intercept = np.polyfit(x, y, 1)
    return slope

class FeatureBuilder:
    def __init__(self, timeframe: str = '15m'):
        self.timeframe = timeframe
        # Define rolling windows based on timeframe
        if timeframe == '15m':
            self.h1_candles = 4
            self.h1_5_candles = 6
            self.h24_candles = 96
        else:  # '1h'
            self.h1_candles = 1
            self.h1_5_candles = 2
            self.h24_candles = 24

    def build_features(self, symbol_dfs: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
        """
        Receives raw dataframes for the 12 assets, aligns timestamps,
        and computes the 6 capital flow features for each asset.
        """
        # Ensure all dataframes are sorted and indexed by timestamp
        processed_dfs = {}
        
        # We need BTC/USDT to calculate RS vs BTC
        btc_key = None
        for k in symbol_dfs.keys():
            if 'BTC' in k:
                btc_key = k
                break
                
        if btc_key is None:
            raise ValueError("BTC/USDT data is required for RS vs BTC calculations.")
            
        btc_df = symbol_dfs[btc_key].copy().sort_values('timestamp').reset_index(drop=True)
        btc_close_series = btc_df.set_index('timestamp')['close']
        
        # 1. Compute Volume Rank among the 12 assets using Quote Volume (volume * close)
        quote_volume_data = {}
        for symbol, df in symbol_dfs.items():
            df_sorted = df.copy().sort_values('timestamp')
            quote_volume_data[symbol] = df_sorted.set_index('timestamp')['volume'] * df_sorted.set_index('timestamp')['close']
            
        df_quote_volumes = pd.DataFrame(quote_volume_data)
        df_ranks = df_quote_volumes.rank(axis=1, ascending=False) # Rank 1 is highest quote volume
        
        # 2. Process each symbol
        for symbol, df in symbol_dfs.items():
            df = df.copy().sort_values('timestamp').reset_index(drop=True)
            
            # Align volume rank
            df['volume_rank'] = df['timestamp'].map(df_ranks[symbol])
            
            # Map BTC close for RS
            df['btc_close'] = df['timestamp'].map(btc_close_series)
            df['rs_vs_btc'] = df['close'] / df['btc_close']
            
            # RS Z-Score over 24h
            rs_mean = df['rs_vs_btc'].rolling(window=self.h24_candles, min_periods=min(12, self.h24_candles)).mean()
            rs_std = df['rs_vs_btc'].rolling(window=self.h24_candles, min_periods=min(12, self.h24_candles)).std().replace(0, 1e-9)
            df['rs_zscore'] = (df['rs_vs_btc'] - rs_mean) / rs_std
            
            # Rank Momentum: Rank(t - 1h) - Rank(t)
            df['rank_momentum'] = df['volume_rank'].shift(self.h1_candles) - df['volume_rank']
            
            # Volume Slope: 1.5h linear regression
            df['volume_slope'] = df['volume'].rolling(window=self.h1_5_candles).apply(get_slope, raw=True)
            
            # Price Slope: 1.5h linear regression
            df['price_slope'] = df['close'].rolling(window=self.h1_5_candles).apply(get_slope, raw=True)
            
            # Volatility Expansion
            df['return'] = df['close'].pct_change().fillna(0)
            short_vol = df['return'].rolling(window=self.h1_candles).std()
            long_vol = df['return'].rolling(window=self.h24_candles, min_periods=min(12, self.h24_candles)).std().replace(0, 1e-9)
            df['volatility_expansion'] = (short_vol / long_vol).fillna(1.0)
            
            # Preserve NaNs for pre-listing rows and fill warm-up NaNs only for post-listing
            pre_listing_mask = df['close'].isna()
            fill_cols = ['volume_rank', 'rs_vs_btc', 'rs_zscore', 'rank_momentum', 'volume_slope', 'price_slope', 'volatility_expansion']
            for col in fill_cols:
                df.loc[~pre_listing_mask, col] = df.loc[~pre_listing_mask, col].fillna(0.0)
            df.loc[pre_listing_mask, fill_cols] = np.nan
            
            processed_dfs[symbol] = df
            
        return processed_dfs
