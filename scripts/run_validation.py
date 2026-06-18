import os
import glob
import random
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# Set custom styling for premium looks
plt.style.use('seaborn-v0_8-whitegrid')
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.size'] = 10
plt.rcParams['axes.edgecolor'] = '#e2e8f0'
plt.rcParams['axes.linewidth'] = 1.2

EVENT_TIMES = {
    'LUNA_Collapse': pd.to_datetime('2022-05-09 00:00:00', utc=True),
    'FTX_Collapse': pd.to_datetime('2022-11-11 14:00:00', utc=True),
    'SVB_Collapse': pd.to_datetime('2023-03-10 16:30:00', utc=True),
    'BTC_ETF_Approval': pd.to_datetime('2024-01-10 21:00:00', utc=True),
    'BTC_Halving': pd.to_datetime('2024-04-20 00:09:00', utc=True),
    'Carry_Trade_Shock': pd.to_datetime('2024-08-05 02:00:00', utc=True),
    'Yoon_Martial_Law_Shock': pd.to_datetime('2024-12-03 13:20:00', utc=True),
}

def get_slope(y):
    if len(y) < 2:
        return 0
    x = np.arange(len(y))
    slope, intercept = np.polyfit(x, y, 1)
    return slope

def analyze_event_data(event_name_clean, target_symbol='SOL/USDT', search_window_hours=24):
    event_dir = os.path.join('datasets/market/events', event_name_clean)
    if not os.path.exists(event_dir):
        return None, None
        
    csv_files = glob.glob(os.path.join(event_dir, '*_15m.csv'))
    volume_data = {}
    for f in csv_files:
        symbol = os.path.basename(f).replace('_15m.csv', '').replace('_', '/')
        df_temp = pd.read_csv(f)
        volume_data[symbol] = df_temp.set_index('timestamp')['volume']
        
    df_vol = pd.DataFrame(volume_data)
    df_ranks = df_vol.rank(axis=1, ascending=False)
    
    target_clean = target_symbol.replace('/', '_')
    target_path = os.path.join(event_dir, f"{target_clean}_15m.csv")
    btc_path = os.path.join(event_dir, "BTC_USDT_15m.csv")
    
    if not os.path.exists(target_path) or not os.path.exists(btc_path):
        target_symbol = 'ETH/USDT'
        target_clean = 'ETH_USDT'
        target_path = os.path.join(event_dir, f"{target_clean}_15m.csv")
        if not os.path.exists(target_path):
            return None, None
            
    df_target = pd.read_csv(target_path)
    df_btc = pd.read_csv(btc_path)
    
    df = pd.merge(df_target, df_btc, on='timestamp', suffixes=('_target', '_btc'))
    df['datetime'] = pd.to_datetime(df['datetime_target'], utc=True)
    df = df.sort_values('datetime').reset_index(drop=True)
    
    df['volume_rank'] = df['timestamp'].map(df_ranks[target_symbol])
    
    df['relative_strength_vs_btc'] = df['close_target'] / df['close_btc']
    df['price_slope'] = df['close_target'].rolling(window=6).apply(get_slope, raw=True)
    df['volume_slope'] = df['volume_target'].rolling(window=6).apply(get_slope, raw=True)
    
    df['volume_mean'] = df['volume_target'].rolling(window=20, min_periods=1).mean()
    df['volume_std'] = df['volume_target'].rolling(window=20, min_periods=1).std().replace(0, 1e-9)
    df['volume_spike'] = df['volume_target'] > (df['volume_mean'] + 3 * df['volume_std'])
    
    # Detection Point (First massive volume spike in standard window)
    spikes = df.iloc[100:572][df.iloc[100:572]['volume_spike'] == True]
    if spikes.empty:
        spikes = df.iloc[50:-50][df.iloc[50:-50]['volume_spike'] == True]
        if spikes.empty:
            return None, None
            
    detection_idx = spikes['volume_target'].idxmax()
    detection_time = df.loc[detection_idx, 'datetime']
    
    # Inception Point based on configurable search window
    candles_to_search = int(search_window_hours * 4) # 15m candles
    pre_detection_window = df.iloc[max(0, detection_idx - candles_to_search):detection_idx]
    
    inception_candidates = pre_detection_window[
        (pre_detection_window['volume_rank'] <= 15) | 
        (pre_detection_window['volume_target'] > (pre_detection_window['volume_mean'] + 1.5 * pre_detection_window['volume_std']))
    ]
    
    if not inception_candidates.empty:
        inception_idx = inception_candidates.index[0]
    else:
        inception_idx = max(0, detection_idx - int(candles_to_search / 2))
        
    inception_time = df.loc[inception_idx, 'datetime']
    lead_time_hours = (detection_time - inception_time).total_seconds() / 3600.0
    
    stats = {
        'target_symbol': target_symbol,
        'inception_idx': inception_idx,
        'inception_time': inception_time,
        'inception_price': df.loc[inception_idx, 'close_target'],
        'detection_idx': detection_idx,
        'detection_time': detection_time,
        'detection_price': df.loc[detection_idx, 'close_target'],
        'lead_time_hours': lead_time_hours,
        'volume_rank_inception': df.loc[inception_idx, 'volume_rank'],
        'volume_rank_detection': df.loc[detection_idx, 'volume_rank']
    }
    
    return df, stats

def run_phase1_visual_validation():
    print("\n--- Running Phase 1: Visual Lead Time Validation ---")
    os.makedirs('outputs/validation', exist_ok=True)
    
    for event_name, event_time in EVENT_TIMES.items():
        df, stats = analyze_event_data(event_name, 'SOL/USDT')
        if df is None:
            print(f"Skipping plot for {event_name} due to missing data.")
            continue
            
        # Filter window: Event Time ± 24 hours
        start_plot = event_time - pd.Timedelta(hours=24)
        end_plot = event_time + pd.Timedelta(hours=24)
        df_plot = df[(df['datetime'] >= start_plot) & (df['datetime'] <= end_plot)].copy()
        
        if df_plot.empty:
            print(f"No plot data in range for {event_name}")
            continue
            
        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 10), sharex=True, gridspec_kw={'height_ratios': [3, 2, 2]})
        
        # Subplot 1: Price
        ax1.plot(df_plot['datetime'], df_plot['close_target'], color='#0ea5e9', linewidth=2, label=f"{stats['target_symbol']} Close Price")
        ax1.set_title(f"Visual Validation: {event_name.replace('_', ' ')}", fontsize=14, fontweight='bold', pad=15)
        ax1.set_ylabel("Price (USDT)", fontweight='semibold')
        ax1.legend(loc='upper left', frameon=True, facecolor='white', edgecolor='none')
        
        # Subplot 2: Volume
        ax2.bar(df_plot['datetime'], df_plot['volume_target'], color='#cbd5e1', width=0.007, label="Volume")
        ax2.set_ylabel("Volume", fontweight='semibold')
        ax2.legend(loc='upper left', frameon=True, facecolor='white', edgecolor='none')
        
        # Subplot 3: Volume Rank Proxy (Lower is better)
        ax3.plot(df_plot['datetime'], df_plot['volume_rank'], color='#f59e0b', linewidth=1.5, label="Volume Rank Proxy (Top 30)")
        ax3.invert_yaxis()  # Rank 1 is at top
        ax3.set_ylabel("Volume Rank", fontweight='semibold')
        ax3.set_ylim(30.5, 0.5)
        ax3.legend(loc='upper left', frameon=True, facecolor='white', edgecolor='none')
        
        # Mark key points
        for ax in (ax1, ax2, ax3):
            ax.axvline(stats['inception_time'], color='#10b981', linestyle='--', linewidth=1.8, label="Whale Inception")
            ax.axvline(stats['detection_time'], color='#ef4444', linestyle='--', linewidth=1.8, label="Whale Detection")
            ax.axvline(event_time, color='#6366f1', linestyle='-', linewidth=2.0, label="Event Shock")
            # Clear duplicate labels in legends
            handles, labels = ax.get_legend_handles_labels()
            by_label = dict(zip(labels, handles))
            ax.legend(by_label.values(), by_label.keys(), loc='upper left', frameon=True, facecolor='white', edgecolor='none')
            
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
        plt.gca().xaxis.set_major_locator(mdates.HourLocator(interval=6))
        plt.gcf().autofmt_xdate()
        plt.tight_layout()
        
        plot_path = f"outputs/validation/phase1_{event_name}.png"
        plt.savefig(plot_path, dpi=150)
        plt.close()
        print(f"  Saved visual validation plot for {event_name} to {plot_path}")

def run_phase2_random_event_test():
    print("\n--- Running Phase 2: Random Event Test ---")
    cont_dir = 'datasets/market/continuous'
    if not os.path.exists(cont_dir):
        print("Error: Continuous dataset not found. Please run fetch_continuous_data.py first.")
        return
        
    csv_files = glob.glob(os.path.join(cont_dir, '*_15m.csv'))
    volume_data = {}
    for f in csv_files:
        symbol = os.path.basename(f).replace('_15m.csv', '').replace('_', '/')
        df_temp = pd.read_csv(f)
        volume_data[symbol] = df_temp.set_index('timestamp')['volume']
        
    df_vol = pd.DataFrame(volume_data)
    df_ranks = df_vol.rank(axis=1, ascending=False)
    
    target_path = os.path.join(cont_dir, "SOL_USDT_15m.csv")
    btc_path = os.path.join(cont_dir, "BTC_USDT_15m.csv")
    
    df_target = pd.read_csv(target_path)
    df_btc = pd.read_csv(btc_path)
    
    df_all = pd.merge(df_target, df_btc, on='timestamp', suffixes=('_target', '_btc'))
    df_all['datetime'] = pd.to_datetime(df_all['datetime_target'], utc=True)
    df_all = df_all.sort_values('datetime').reset_index(drop=True)
    df_all['volume_rank'] = df_all['timestamp'].map(df_ranks['SOL/USDT'])
    
    # Calculate features on full set
    df_all['relative_strength_vs_btc'] = df_all['close_target'] / df_all['close_btc']
    df_all['price_slope'] = df_all['close_target'].rolling(window=6).apply(get_slope, raw=True)
    df_all['volume_slope'] = df_all['volume_target'].rolling(window=6).apply(get_slope, raw=True)
    df_all['volume_mean'] = df_all['volume_target'].rolling(window=20, min_periods=1).mean()
    df_all['volume_std'] = df_all['volume_target'].rolling(window=20, min_periods=1).std().replace(0, 1e-9)
    df_all['volume_spike'] = df_all['volume_target'] > (df_all['volume_mean'] + 3 * df_all['volume_std'])
    
    # Generate 50 random timestamps in the middle range (2024-05-05 to 2024-06-25)
    # We want indices that can accommodate ±3 days (576 candles)
    valid_start_idx = 576
    valid_end_idx = len(df_all) - 576
    
    random.seed(42)  # For reproducibility
    random_indices = random.sample(range(valid_start_idx, valid_end_idx), 50)
    
    search_windows = [12, 24, 48]
    window_results = {w: [] for w in search_windows}
    
    for w in search_windows:
        for idx in random_indices:
            # Slice ±3 days window
            df_slice = df_all.iloc[idx - 288 : idx + 288].copy().reset_index(drop=True)
            
            # Find Detection Point in the slice
            spikes = df_slice.iloc[100:472][df_slice.iloc[100:472]['volume_spike'] == True]
            if spikes.empty:
                continue
                
            detection_idx = spikes['volume_target'].idxmax()
            detection_time = df_slice.loc[detection_idx, 'datetime']
            
            # Find Inception Point
            candles_to_search = int(w * 4)
            pre_detection_window = df_slice.iloc[max(0, detection_idx - candles_to_search):detection_idx]
            
            inception_candidates = pre_detection_window[
                (pre_detection_window['volume_rank'] <= 15) | 
                (pre_detection_window['volume_target'] > (pre_detection_window['volume_mean'] + 1.5 * pre_detection_window['volume_std']))
            ]
            
            if not inception_candidates.empty:
                inception_idx = inception_candidates.index[0]
            else:
                inception_idx = max(0, detection_idx - int(candles_to_search / 2))
                
            inception_time = df_slice.loc[inception_idx, 'datetime']
            lead_time_hours = (detection_time - inception_time).total_seconds() / 3600.0
            window_results[w].append(lead_time_hours)
            
    # Calculate statistics
    summary_stats = []
    plt.figure(figsize=(10, 6))
    colors = ['#38bdf8', '#0284c7', '#0369a1']
    
    for i, w in enumerate(search_windows):
        leads = window_results[w]
        mean_val = np.mean(leads)
        std_val = np.std(leads)
        min_val = np.min(leads)
        max_val = np.max(leads)
        
        summary_stats.append({
            'Search Window (Hours)': w,
            'Sample Size': len(leads),
            'Mean Lead Time (Hours)': mean_val,
            'Std Dev': std_val,
            'Min': min_val,
            'Max': max_val
        })
        
        # Plot Histogram
        plt.hist(leads, bins=15, alpha=0.6, label=f"Search Window: {w}h (Mean: {mean_val:.2f}h)", color=colors[i], edgecolor='black')
        
    df_rand_stats = pd.DataFrame(summary_stats)
    print("\nRandom Event Test Statistics:")
    print(df_rand_stats.to_string(index=False))
    
    plt.title("Lead Time Distribution vs Inception Search Window Size (Random Events)", fontsize=13, fontweight='bold', pad=15)
    plt.xlabel("Lead Time (Hours)", fontweight='semibold')
    plt.ylabel("Frequency", fontweight='semibold')
    plt.legend(frameon=True, facecolor='white', edgecolor='none')
    plt.tight_layout()
    plt.savefig('outputs/validation/phase2_random_event_distribution.png', dpi=150)
    plt.close()
    
    # Save the stats to CSV
    df_rand_stats.to_csv('outputs/validation/phase2_random_stats.csv', index=False)

def run_phase3_volume_rank_proxy_validation():
    print("\n--- Running Phase 3: Volume Rank Proxy & Rank Momentum Validation ---")
    
    rank_analysis = []
    
    for event_name, event_time in EVENT_TIMES.items():
        df, stats = analyze_event_data(event_name, 'SOL/USDT')
        if df is None:
            continue
            
        inception_idx = stats['inception_idx']
        
        # Calculate Rank Momentum = Rank(t-4) - Rank(t) (k=4 candles = 1 hour)
        df['rank_momentum_1h'] = df['volume_rank'].shift(4) - df['volume_rank']
        df['rank_momentum_2h'] = df['volume_rank'].shift(8) - df['volume_rank']
        
        # Track Rank flow around Inception: t-8, t-4, t-2, t, t+2, t+4
        idx_flow = [inception_idx - 8, inception_idx - 4, inception_idx - 2, inception_idx, inception_idx + 2, inception_idx + 4]
        rank_flow = []
        for idx in idx_flow:
            if 0 <= idx < len(df):
                rank_flow.append(f"{df.loc[idx, 'volume_rank']:.1f}")
            else:
                rank_flow.append("N/A")
                
        flow_str = " -> ".join(rank_flow)
        
        # Determine classification: Real improvement vs noise
        # A real improvement should show a positive momentum (rank going down numerically) leading into Inception
        mom_1h = df.loc[inception_idx, 'rank_momentum_1h']
        mom_2h = df.loc[inception_idx, 'rank_momentum_2h']
        
        is_real = (mom_1h > 0 or mom_2h > 0) and df.loc[inception_idx, 'volume_rank'] <= 15
        classification = "Real Signal" if is_real else "Noise / Algorithmic Artifact"
        
        rank_analysis.append({
            'Event': event_name,
            'Inception Rank': df.loc[inception_idx, 'volume_rank'],
            '1h Rank Momentum': mom_1h,
            '2h Rank Momentum': mom_2h,
            'Rank Flow (t-2h to t+1h)': flow_str,
            'Signal Validity': classification
        })
        
    df_rank_valid = pd.DataFrame(rank_analysis)
    print("\nVolume Rank & Momentum Analysis:")
    print(df_rank_valid.to_string(index=False))
    df_rank_valid.to_csv('outputs/validation/phase3_rank_validation.csv', index=False)

def run_phase4_rs_btc_validation():
    print("\n--- Running Phase 4: RS vs BTC Decoupling Validation ---")
    
    decoupling_results = []
    
    for event_name, event_time in EVENT_TIMES.items():
        df, stats = analyze_event_data(event_name, 'SOL/USDT')
        if df is None:
            continue
            
        inception_idx = stats['inception_idx']
        
        # Calculate Rolling Z-score of RS over 24 hours (96 candles)
        df['rs_mean_24h'] = df['relative_strength_vs_btc'].rolling(window=96, min_periods=12).mean()
        df['rs_std_24h'] = df['relative_strength_vs_btc'].rolling(window=96, min_periods=12).std().replace(0, 1e-9)
        df['rs_zscore'] = (df['relative_strength_vs_btc'] - df['rs_mean_24h']) / df['rs_std_24h']
        
        # Search the 24 hours preceding Inception for decoupling (Z-score > 2 or < -2)
        pre_inception_window = df.iloc[max(0, inception_idx - 96):inception_idx + 1]
        decoupled_points = pre_inception_window[pre_inception_window['rs_zscore'].abs() > 2]
        
        if not decoupled_points.empty:
            first_decouple_idx = decoupled_points.index[0]
            decouple_time = df.loc[first_decouple_idx, 'datetime']
            inception_time = df.loc[inception_idx, 'datetime']
            decouple_onset_hours = (inception_time - decouple_time).total_seconds() / 3600.0
            
            max_strength = decoupled_points['rs_zscore'].abs().max()
            duration_hours = len(decoupled_points) * 0.25
            decouple_status = "Decoupled"
        else:
            decouple_onset_hours = 0.0
            max_strength = 0.0
            duration_hours = 0.0
            decouple_status = "No Decoupling"
            
        decoupling_results.append({
            'Event': event_name,
            'Decouple Status': decouple_status,
            'Onset Time (Hours before Incep)': decouple_onset_hours,
            'Max Decoupling Strength (Z)': max_strength,
            'Decoupling Duration (Hours)': duration_hours
        })
        
    df_decouple = pd.DataFrame(decoupling_results)
    print("\nRS vs BTC Decoupling Analysis:")
    print(df_decouple.to_string(index=False))
    df_decouple.to_csv('outputs/validation/phase4_rs_btc_validation.csv', index=False)

def main():
    print("Starting WhaleLab Validation-001...")
    run_phase1_visual_validation()
    run_phase2_random_event_test()
    run_phase3_volume_rank_proxy_validation()
    run_phase4_rs_btc_validation()
    print("\nAll validation steps completed successfully.")

if __name__ == '__main__':
    main()
