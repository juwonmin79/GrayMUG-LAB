import numpy as np
import pandas as pd
from typing import Dict, List, Tuple
from .schemas import FlowEdge, FlowGraphState

def fast_corr(x, y):
    n = len(x)
    if n < 2:
        return 0.0
    x_mean = np.mean(x)
    y_mean = np.mean(y)
    x_dev = x - x_mean
    y_dev = y - y_mean
    num = np.sum(x_dev * y_dev)
    den = np.sqrt(np.sum(x_dev**2) * np.sum(y_dev**2))
    if den == 0.0:
        return 0.0
    return num / den

class FlowGraphBuilder:
    def __init__(self, symbols: List[str], timeframe: str = '15m', edge_threshold: float = 0.35):
        self.symbols = symbols
        self.timeframe = timeframe
        self.edge_threshold = edge_threshold
        if timeframe == '15m':
            self.lookback = 96  # 24 hours
            self.lags = [1, 2, 3, 4] # 15m to 1h lag
        else:
            self.lookback = 24  # 24 hours
            self.lags = [1, 2] # 1h to 2h lag

    def build_graph_at_idx(self, feature_dfs: Dict[str, pd.DataFrame], current_idx: int, timestamp: int, dt) -> FlowGraphState:
        """
        Builds the Flow Graph at a specific dataframe index by computing lead-lag correlations
        and rotation factors over the lookback window.
        """
        nodes = {}
        edges: List[FlowEdge] = []
        
        # 1. Fetch current scores for nodes and filter active symbols
        active_symbols = []
        for symbol in self.symbols:
            df = feature_dfs[symbol]
            if current_idx < len(df):
                score = df.loc[current_idx, 'whale_link_score']
                if not np.isnan(score):
                    nodes[symbol] = float(score)
                    active_symbols.append(symbol)
                else:
                    nodes[symbol] = np.nan
            else:
                nodes[symbol] = np.nan
                
        # If we don't have enough history to compute correlations, return empty graph
        if current_idx < self.lookback:
            return FlowGraphState(timestamp=timestamp, datetime=dt, nodes=nodes, edges=[])
            
        # 2. Extract series and pre-normalize them for each lag (only for active symbols)
        x_shifted_norms = {}
        y_target_norms = {}
        rs_z_series = {}
        
        for symbol in active_symbols:
            df = feature_dfs[symbol]
            window = df.iloc[current_idx - self.lookback : current_idx + 1]
            x_mom = window['rank_momentum'].values
            rs_z_series[symbol] = window['rs_zscore'].values
            
            x_shifted_norms[symbol] = {}
            y_target_norms[symbol] = {}
            
            for lag in self.lags:
                x_shifted = x_mom[:-lag]
                y_target = x_mom[lag:]
                
                # Pre-normalize x_shifted
                x_dev = x_shifted - np.mean(x_shifted)
                x_std_sum = np.sqrt(np.sum(x_dev**2))
                if x_std_sum > 0:
                    x_shifted_norms[symbol][lag] = x_dev / x_std_sum
                else:
                    x_shifted_norms[symbol][lag] = None
                    
                # Pre-normalize y_target
                y_dev = y_target - np.mean(y_target)
                y_std_sum = np.sqrt(np.sum(y_dev**2))
                if y_std_sum > 0:
                    y_target_norms[symbol][lag] = y_dev / y_std_sum
                else:
                    y_target_norms[symbol][lag] = None
                    
        # 3. Compute pairwise edge weights using dot product
        for x in active_symbols:
            for y in active_symbols:
                if x == y:
                    continue
                    
                max_corr = 0.0
                best_lag = 0
                
                for lag in self.lags:
                    x_norm = x_shifted_norms[x][lag]
                    y_norm = y_target_norms[y][lag]
                    
                    if x_norm is not None and y_norm is not None:
                        corr = np.dot(x_norm, y_norm)
                        if corr > max_corr:
                            max_corr = corr
                            best_lag = lag
                            
                # Relative Strength Divergence (Rotation Factor)
                x_rs = rs_z_series[x]
                y_rs = rs_z_series[y]
                x_rs_curr = x_rs[-1]
                y_rs_curr = y_rs[-1]
                x_rs_prev = x_rs[-2] if len(x_rs) > 1 else 0.0
                y_rs_prev = y_rs[-2] if len(y_rs) > 1 else 0.0
                
                x_rs_decay = x_rs_curr < x_rs_prev
                y_rs_rise = y_rs_curr > y_rs_prev
                
                rot_factor = 0.0
                if y_rs_curr > 1.0 and x_rs_curr < 0.5 and y_rs_rise and x_rs_decay:
                    rot_factor = 0.5
                    
                # Combine correlation and rotation factor
                weight = 0.7 * max_corr + 0.3 * rot_factor
                weight = float(np.clip(weight, 0.0, 1.0))
                
                # We filter edges by threshold
                if weight >= self.edge_threshold:
                    # Determine confidence based on current Whale Link Scores
                    score_diff = nodes[y] - nodes[x]
                    # If target has a higher score, confidence increases
                    conf_scale = 1.2 if score_diff > 0 else 0.8
                    confidence = float(np.clip(weight * conf_scale, 0.0, 1.0))
                    
                    # Define classification narrative
                    narrative = "Capital Rotation"
                    if "BTC" in x and ("ETH" in y or "SOL" in y):
                        narrative = "Majors to L1 Rotation"
                    elif ("BTC" in x or "ETH" in x) and ("FET" in y or "TAO" in y):
                        narrative = "Majors to AI Rotation"
                    elif "SOL" in x and ("FET" in y or "TAO" in y):
                        narrative = "L1 to AI Rotation"
                    elif "ETH" in x and "UNI" in y:
                        narrative = "L1 to DeFi Rotation"
                        
                    edges.append(FlowEdge(
                        source=x.split('/')[0],
                        target=y.split('/')[0],
                        weight=weight,
                        lag_candles=best_lag,
                        confidence=confidence,
                        timestamp=timestamp,
                        narrative=narrative
                    ))
                    
        return FlowGraphState(timestamp=timestamp, datetime=dt, nodes=nodes, edges=edges)

    def detect_rotation_paths(self, graph_state: FlowGraphState) -> List[Tuple[List[str], float, float, str]]:
        """
        Finds directed paths (chains of capital rotation) in the active edges.
        Returns a list of Tuple: (path, avg_confidence, avg_lead_score, narrative)
        """
        # Create adjacency list representation
        adj = {}
        edge_data = {}
        for edge in graph_state.edges:
            src = edge.source
            tgt = edge.target
            if src not in adj:
                adj[src] = []
            adj[src].append((tgt, edge.confidence, edge.narrative))
            
        paths = []
        
        # Define sources (usually majors BTC/ETH, L1s SOL)
        sources = ["BTC", "ETH", "SOL"]
        
        def dfs(node: str, current_path: List[str], total_conf: float, path_narrative: str):
            # Limit path length to 4 nodes to avoid long loop artifacts
            if len(current_path) >= 4:
                # Calculate avg metrics and store
                avg_conf = total_conf / (len(current_path) - 1)
                scores = [graph_state.nodes.get(n + "/USDT", 0.0) for n in current_path]
                # Filter scores
                avg_score = np.mean(scores)
                paths.append((list(current_path), avg_conf, avg_score, path_narrative))
                return
                
            if node not in adj or not adj[node]:
                # If we can't go further, but have a path of at least length 2
                if len(current_path) >= 2:
                    avg_conf = total_conf / (len(current_path) - 1)
                    scores = [graph_state.nodes.get(n + "/USDT", 0.0) for n in current_path]
                    avg_score = np.mean(scores)
                    paths.append((list(current_path), avg_conf, avg_score, path_narrative))
                return
                
            for neighbor, conf, narr in adj[node]:
                if neighbor not in current_path:  # Avoid cycles
                    new_narr = narr if not path_narrative else path_narrative
                    dfs(neighbor, current_path + [neighbor], total_conf + conf, new_narr)
                    
        for src in sources:
            if src in adj:
                dfs(src, [src], 0.0, "")
                
        # Sort paths by avg_confidence * avg_lead_score descending
        paths.sort(key=lambda x: x[1] * x[2], reverse=True)
        return paths[:5] # Return top 5 rotation paths
