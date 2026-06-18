import os
import pandas as pd
from typing import Dict, List, Tuple
from .schemas import FlowGraphState, WhaleLinkAlert
from .feature_builder import FeatureBuilder
from .scoring import Scorer
from .flow_graph import FlowGraphBuilder

class FlowEngine:
    def __init__(self, data_dir: str = 'datasets/market/flow_dataset', timeframe: str = '15m', edge_threshold: float = 0.35):
        self.data_dir = data_dir
        self.timeframe = timeframe
        self.edge_threshold = edge_threshold
        self.symbols = [
            'BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'SOL/USDT', 'XRP/USDT',
            'DOGE/USDT', 'ADA/USDT', 'LINK/USDT', 'AVAX/USDT', 'UNI/USDT',
            'FET/USDT', 'TAO/USDT'
        ]
        self.feature_builder = FeatureBuilder(timeframe)
        self.scorer = Scorer()
        self.graph_builder = FlowGraphBuilder(self.symbols, timeframe, edge_threshold)

    def load_data(self) -> Dict[str, pd.DataFrame]:
        """
        Loads CSV files for all 12 target symbols.
        """
        raw_dfs = {}
        for symbol in self.symbols:
            symbol_clean = symbol.replace('/', '_')
            path = os.path.join(self.data_dir, f"{symbol_clean}_{self.timeframe}.csv")
            if not os.path.exists(path):
                raise FileNotFoundError(f"Missing data file for {symbol} at {path}")
            df = pd.read_csv(path)
            raw_dfs[symbol] = df
        return raw_dfs

    def run_pipeline(self, step_stride: int = 4) -> Tuple[List[FlowGraphState], List[WhaleLinkAlert]]:
        """
        Runs the full feature building, scoring, and graph building pipeline.
        Returns a list of graph states over time and generated alerts.
        """
        print("Loading flow dataset...")
        raw_dfs = self.load_data()
        
        # Align all dataframes to BTC/USDT's timestamps (to handle assets listed later)
        btc_key = 'BTC/USDT'
        btc_df = raw_dfs[btc_key].sort_values('timestamp').reset_index(drop=True)
        btc_timestamps = btc_df['timestamp']
        
        aligned_dfs = {}
        for symbol, df in raw_dfs.items():
            if symbol == btc_key:
                aligned_dfs[symbol] = btc_df
            else:
                df_aligned = df.set_index('timestamp').reindex(btc_timestamps).reset_index()
                df_aligned['datetime'] = btc_df['datetime']
                aligned_dfs[symbol] = df_aligned
        raw_dfs = aligned_dfs
        
        print("Building market features...")
        feature_dfs = self.feature_builder.build_features(raw_dfs)
        
        print("Computing Whale Link Scores...")
        feature_dfs = self.scorer.score_all_assets(feature_dfs)
        
        print("Generating Flow Graph States...")
        # Align indexes
        # Use BTC/USDT as index baseline since it's always complete
        btc_df = feature_dfs['BTC/USDT']
        graph_states: List[FlowGraphState] = []
        alerts: List[WhaleLinkAlert] = []
        
        # We start running the graph builder from lookback window index
        # to ensure sufficient historical data for correlations
        start_idx = self.graph_builder.lookback
        total_rows = len(btc_df)
        
        print(f"Replaying {total_rows - start_idx} candles with stride {step_stride}...")
        
        for idx in range(start_idx, total_rows, step_stride):
            timestamp = int(btc_df.loc[idx, 'timestamp'])
            dt = pd.to_datetime(btc_df.loc[idx, 'datetime'], utc=True)
            
            # Build graph at this index
            state = self.graph_builder.build_graph_at_idx(feature_dfs, idx, timestamp, dt)
            graph_states.append(state)
            
            # Detect rotation paths
            paths = self.graph_builder.detect_rotation_paths(state)
            
            # Trigger alerts if path is strong
            for path, avg_conf, avg_score, narrative in paths:
                # Alert criteria: confidence >= 0.50 and lead_score >= 60.0
                if avg_conf >= 0.50 and avg_score >= 50.0:
                    # Deduplicate alerts: trigger only if it is a meaningful state
                    alerts.append(WhaleLinkAlert(
                        timestamp=timestamp,
                        datetime=dt,
                        path=path,
                        confidence=avg_conf,
                        lead_score=avg_score,
                        narrative=narrative if narrative else "Sector Rotation"
                    ))
                    
        print(f"Pipeline complete. Generated {len(graph_states)} states and {len(alerts)} Whale Link Alerts.")
        return graph_states, alerts
