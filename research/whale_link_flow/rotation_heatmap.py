import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import networkx as nx
from typing import List

def generate_plots(df_link_edges: pd.DataFrame, df_live_flow: pd.DataFrame, output_dir: str):
    """
    Generates premium dark-mode visualizations:
    1. rotation_heatmap.png (transition matrix between assets)
    2. flow_network.png (active flow graph network)
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # 12 Target symbols list
    symbols = ['BTC', 'ETH', 'BNB', 'SOL', 'XRP', 'DOGE', 'ADA', 'LINK', 'AVAX', 'UNI', 'FET', 'TAO']
    
    # ----------------------------------------------------
    # Plot 1: Rotation Heatmap
    # ----------------------------------------------------
    plt.style.use('dark_background')
    fig, ax = plt.subplots(figsize=(10, 8), facecolor='#0d0e15')
    ax.set_facecolor('#0d0e15')
    
    # Calculate average edge weight for pivot table
    if not df_link_edges.empty:
        df_mean_edges = df_link_edges.groupby(['source', 'target'])['weight'].mean().reset_index()
        pivot_matrix = df_mean_edges.pivot(index='source', columns='target', values='weight')
        # Reindex to ensure all 12 assets are represented in order
        pivot_matrix = pivot_matrix.reindex(index=symbols, columns=symbols).fillna(0.0)
    else:
        pivot_matrix = pd.DataFrame(0.0, index=symbols, columns=symbols)
        
    # Draw heatmap
    sns.heatmap(
        pivot_matrix, 
        annot=True, 
        fmt=".2f", 
        cmap='magma', 
        ax=ax, 
        cbar_kws={'label': 'Flow Probability / Weight'},
        annot_kws={'size': 9, 'color': 'white'}
    )
    
    ax.set_title("Capital Flow Transition Heatmap (Average Weight)", fontsize=14, pad=15, color='cyan')
    ax.set_xlabel("Target Asset (Destination)", fontsize=11, labelpad=10, color='white')
    ax.set_ylabel("Source Asset (Origin)", fontsize=11, labelpad=10, color='white')
    
    plt.tight_layout()
    heatmap_path = os.path.join(output_dir, 'rotation_heatmap.png')
    plt.savefig(heatmap_path, dpi=200, facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close()
    print(f"Saved rotation heatmap to {heatmap_path}")
    
    # ----------------------------------------------------
    # Plot 2: Flow Network Graph
    # ----------------------------------------------------
    fig, ax = plt.subplots(figsize=(10, 8), facecolor='#0d0e15')
    ax.set_facecolor('#0d0e15')
    
    G = nx.DiGraph()
    G.add_nodes_from(symbols)
    
    # Node weights: average live_flow_score
    node_sizes = []
    if not df_live_flow.empty:
        mean_scores = df_live_flow.groupby('asset')['live_flow_score'].mean().to_dict()
    else:
        mean_scores = {}
        
    for node in symbols:
        score = mean_scores.get(node, 50.0)
        # Scale score to a reasonable size
        node_sizes.append(max(200.0, score * 15.0))
        
    # Edge weights: filter and take the top 15 edges by weight
    if not df_link_edges.empty:
        top_edges = df_link_edges.groupby(['source', 'target'])['weight'].mean().reset_index().sort_values('weight', ascending=False).head(15)
        for _, row in top_edges.iterrows():
            G.add_edge(row['source'], row['target'], weight=row['weight'])
            
    # Draw directed graph layout
    pos = nx.circular_layout(G)
    
    # Draw nodes with neon cyan
    nx.draw_networkx_nodes(
        G, pos, 
        node_size=node_sizes, 
        node_color='#00f0ff', 
        alpha=0.8,
        ax=ax
    )
    
    # Draw labels
    nx.draw_networkx_labels(
        G, pos, 
        font_size=10, 
        font_color='white', 
        font_weight='bold',
        ax=ax
    )
    
    # Draw edges with bright magenta
    edges = G.edges(data=True)
    if edges:
        weights = [e[2]['weight'] * 4.0 for e in edges]
        nx.draw_networkx_edges(
            G, pos, 
            width=weights, 
            edge_color='#ff00ff', 
            alpha=0.6,
            arrowsize=15,
            ax=ax
        )
        
    ax.set_title("Capital Flow Directed Network Map (Top 15 Edges)", fontsize=14, pad=15, color='cyan')
    plt.axis('off')
    plt.tight_layout()
    
    network_path = os.path.join(output_dir, 'flow_network.png')
    plt.savefig(network_path, dpi=200, facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close()
    print(f"Saved flow network map to {network_path}")
