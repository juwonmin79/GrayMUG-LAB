import pandas as pd
from typing import Dict, List, Any
from .flow_graph import FlowGraphState

class LinkGraphSummarizer:
    @staticmethod
    def summarize_edges(
        graph_state: FlowGraphState,
        feature_dfs: Dict[str, pd.DataFrame],
        current_idx: int
    ) -> List[Dict[str, Any]]:
        """
        Summarizes the active edges in graph_state with enhanced indicators:
        - B's RS rising faster than A
        - B's volume_rank improving
        - A's momentum slowing
        - B's momentum strengthening
        """
        summarized = []
        
        for edge in graph_state.edges:
            src = edge.source
            tgt = edge.target
            
            src_key = src + "/USDT"
            tgt_key = tgt + "/USDT"
            
            if src_key not in feature_dfs or tgt_key not in feature_dfs:
                continue
                
            df_src = feature_dfs[src_key]
            df_tgt = feature_dfs[tgt_key]
            
            if current_idx >= len(df_src) or current_idx >= len(df_tgt):
                continue
                
            # Current values
            src_row = df_src.iloc[current_idx]
            tgt_row = df_tgt.iloc[current_idx]
            
            # Values from 4 candles ago (1 hour ago) for trend
            prev_idx = max(0, current_idx - 4)
            src_row_prev = df_src.iloc[prev_idx]
            tgt_row_prev = df_tgt.iloc[prev_idx]
            
            # 1. B's RS rising faster than A
            src_rs_change = src_row['rs_zscore'] - src_row_prev['rs_zscore']
            tgt_rs_change = tgt_row['rs_zscore'] - tgt_row_prev['rs_zscore']
            rs_rising_faster = float(tgt_rs_change) > float(src_rs_change)
            
            # 2. B's volume rank improving (rank decreases = improvement)
            rank_improving = float(tgt_row['volume_rank']) < float(tgt_row_prev['volume_rank'])
            
            # 3. A's momentum slowing
            src_mom_slowing = float(src_row['rank_momentum']) <= float(src_row_prev['rank_momentum'])
            
            # 4. B's momentum strengthening
            tgt_mom_strengthening = float(tgt_row['rank_momentum']) > 0
            
            summarized.append({
                'datetime': graph_state.datetime.strftime('%Y-%m-%d %H:%M'),
                'timestamp': graph_state.timestamp,
                'source': src,
                'target': tgt,
                'weight': edge.weight,
                'confidence': edge.confidence,
                'lag_candles': edge.lag_candles,
                'narrative': edge.narrative,
                'rs_rising_faster': int(rs_rising_faster),
                'target_rank_improving': int(rank_improving),
                'source_momentum_slowing': int(src_mom_slowing),
                'target_momentum_strengthening': int(tgt_mom_strengthening)
            })
            
        return summarized
