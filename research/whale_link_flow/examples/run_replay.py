import os
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# Add the parent directory of research to path to allow absolute imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from research.whale_link_flow.flow_engine import FlowEngine

def plot_circular_flow_graph(state, filename='outputs/whale_link_flow/flow_graph_snapshot.png'):
    """
    Plots the 12 assets in a circular layout and draws active flow edges as arrows.
    Node size/color indicates Whale Link Score, and edge color/width indicates flow probability.
    """
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    
    # 12 assets
    symbols = list(state.nodes.keys())
    short_names = [s.split('/')[0] for s in symbols]
    n_nodes = len(symbols)
    
    # Circular layout coordinates
    angles = np.linspace(0, 2*np.pi, n_nodes, endpoint=False)
    coords = {short_names[i]: (np.cos(angles[i]), np.sin(angles[i])) for i in range(n_nodes)}
    
    fig, ax = plt.subplots(figsize=(10, 10))
    ax.set_aspect('equal')
    ax.axis('off')
    
    # Draw active edges (arrows)
    for edge in state.edges:
        if edge.source in coords and edge.target in coords:
            x_src, y_src = coords[edge.source]
            x_tgt, y_tgt = coords[edge.target]
            
            # Shorten the arrow to avoid overlapping the node center
            dx = x_tgt - x_src
            dy = y_tgt - y_src
            dist = np.sqrt(dx*dx + dy*dy)
            
            # Start and end offsets
            start_scale = 0.12
            end_scale = 0.12
            x_start = x_src + dx * start_scale
            y_start = y_src + dy * start_scale
            x_end = x_tgt - dx * end_scale
            y_end = y_tgt - dy * end_scale
            
            # Edge styling based on weight/confidence
            color = '#8b5cf6' if edge.weight > 0.5 else '#cbd5e1'
            linewidth = 1.0 + edge.weight * 4.0
            
            ax.annotate(
                "",
                xy=(x_end, y_end), xytext=(x_start, y_start),
                arrowprops=dict(
                    arrowstyle="->", 
                    color=color, 
                    lw=linewidth, 
                    alpha=0.8,
                    shrinkA=5, shrinkB=5,
                    connectionstyle="arc3,rad=0.1" # slight curve to distinguish two-way flows
                )
            )
            
            # Add small label of weight/confidence in the middle of the arrow
            x_mid = (x_start + x_end) / 2.0 + 0.03 * np.sin(angles[short_names.index(edge.source)])
            y_mid = (y_start + y_end) / 2.0 - 0.03 * np.cos(angles[short_names.index(edge.source)])
            # ax.text(x_mid, y_mid, f"{edge.weight:.2f}", color='#6b7280', fontsize=8, alpha=0.6)
            
    # Draw nodes
    for name, (x, y) in coords.items():
        score = state.nodes.get(name + "/USDT", 0.0)
        
        # Color based on Whale Link Score: blue to emerald/yellow
        # Emerald for high scores, slate for low scores
        if score > 70:
            color = '#10b981' # emerald
        elif score > 40:
            color = '#0ea5e9' # sky blue
        else:
            color = '#64748b' # slate
            
        # Draw node circle
        size = 800 + score * 10
        ax.scatter(x, y, s=size, color=color, zorder=5, edgecolors='#f8fafc', linewidths=2, alpha=0.9)
        
        # Draw label inside node
        ax.text(x, y, f"{name}\n{score:.0f}", color='white', ha='center', va='center', fontweight='bold', fontsize=10, zorder=6)
        
    ax.set_title(
        f"🐋 Whale Link Flow Graph Snapshot\nDate: {state.datetime.strftime('%Y-%m-%d %H:%M:%S')} UTC",
        fontsize=14, fontweight='bold', color='#1e293b', pad=20
    )
    
    plt.tight_layout()
    plt.savefig(filename, dpi=150, facecolor='#f8fafc')
    plt.close()
    print(f"Saved flow graph snapshot plot to {filename}")

def plot_score_timeline(states, start_dt, end_dt, filename='outputs/whale_link_flow/score_timeline.png'):
    """
    Plots the timeline of Whale Link Scores for specific assets (BTC, ETH, SOL, FET)
    to visually demonstrate the rotation flow.
    """
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    
    # Filter states in range
    target_states = [s for s in states if start_dt <= s.datetime <= end_dt]
    if not target_states:
        print("No states in time range to plot timeline.")
        return
        
    dates = [s.datetime for s in target_states]
    assets_to_plot = ["BTC", "ETH", "SOL", "FET"]
    scores = {a: [] for a in assets_to_plot}
    
    for s in target_states:
        for a in assets_to_plot:
            scores[a].append(s.nodes.get(a + "/USDT", 0.0))
            
    fig, ax = plt.subplots(figsize=(12, 6))
    
    colors = {
        "BTC": "#f59e0b", # Orange
        "ETH": "#6366f1", # Indigo
        "SOL": "#0ea5e9", # Sky Blue
        "FET": "#10b981"  # Emerald
    }
    
    for a in assets_to_plot:
        ax.plot(dates, scores[a], label=f"{a} Score", color=colors[a], linewidth=2.0)
        
    ax.set_title("Whale Link Score Timeline (Capital Rotation Demo)", fontsize=14, fontweight='bold', pad=15)
    ax.set_xlabel("Date (UTC)", fontweight='semibold')
    ax.set_ylabel("Whale Link Score (0 - 100)", fontweight='semibold')
    ax.set_ylim(-5, 105)
    ax.legend(frameon=True, facecolor='white', edgecolor='none')
    
    plt.gcf().autofmt_xdate()
    plt.tight_layout()
    plt.savefig(filename, dpi=150, facecolor='#f8fafc')
    plt.close()
    print(f"Saved score timeline plot to {filename}")

def main():
    print("Initializing Whale Link Flow Replay...")
    # Initialize engine
    engine = FlowEngine(timeframe='15m', edge_threshold=0.35)
    
    # Run the full pipeline
    states, alerts = engine.run_pipeline()
    
    if not states:
        print("Error: No states generated.")
        return
        
    print("\n--- 🐋 Rotation Alerts Preview ---")
    # Show first 15 alerts to see rotation paths
    for i, alert in enumerate(alerts[:15], 1):
        path_str = " → ".join(alert.path)
        print(f"[{i}] {alert.datetime.strftime('%Y-%m-%d %H:%M')} | {path_str} | Conf: {alert.confidence*100:.0f}% | Lead Score: {alert.lead_score:.1f} | Narrative: {alert.narrative}")
        
    # Find a strong alert to visualize
    strong_alerts = [a for a in alerts if len(a.path) >= 3 and a.confidence > 0.65]
    if not strong_alerts:
        strong_alerts = alerts
        
    if strong_alerts:
        target_alert = strong_alerts[min(len(strong_alerts)-1, 10)] # Pick a representative alert
        target_time = target_alert.datetime
        
        # Find corresponding state
        target_state = None
        for s in states:
            if s.datetime == target_time:
                target_state = s
                break
                
        if target_state:
            print(f"\nVisualizing flow state for alert at {target_time}...")
            plot_circular_flow_graph(target_state)
            
            # Plot timeline around target time ± 1.5 days
            start_plot = target_time - pd.Timedelta(days=1.5)
            end_plot = target_time + pd.Timedelta(days=1.5)
            plot_score_timeline(states, start_plot, end_plot)
            
            # Print state details
            print(f"\nState Active Nodes:")
            for symbol, score in target_state.nodes.items():
                if score > 30:
                    print(f"  {symbol}: Score {score:.1f}")
                    
            print(f"\nState Active Edges:")
            for edge in target_state.edges:
                print(f"  {edge.source} → {edge.target} | Weight: {edge.weight:.2f} | Lag: {edge.lag_candles} candles | Narrative: {edge.narrative}")
        else:
            print("No matching state found for alert.")
    else:
        print("No strong alerts found to visualize.")

if __name__ == '__main__':
    main()
