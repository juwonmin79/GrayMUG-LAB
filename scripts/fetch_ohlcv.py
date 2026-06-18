import os
import sys
import time
import datetime
import pandas as pd
import ccxt

def get_top_30_usdt_symbols(exchange):
    print("Fetching 24h tickers to find top 30 USDT pairs by volume...")
    try:
        tickers = exchange.fetch_tickers()
    except Exception as e:
        print(f"Error fetching tickers: {e}")
        # Return fallback symbols if fetching fails
        return [
            'BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'BNB/USDT', 'XRP/USDT',
            'ADA/USDT', 'DOGE/USDT', 'SHIB/USDT', 'DOT/USDT', 'LTC/USDT',
            'LINK/USDT', 'AVAX/USDT', 'NEAR/USDT', 'POL/USDT', 'UNI/USDT',
            'PEPE/USDT', 'WIF/USDT', 'APT/USDT', 'SUI/USDT', 'OP/USDT',
            'ARB/USDT', 'FIL/USDT', 'ETC/USDT', 'ORDI/USDT', 'LDO/USDT',
            'FET/USDT', 'INJ/USDT', 'RENDER/USDT', 'TAO/USDT', 'RUNE/USDT'
        ]

    usdt_tickers = []
    for symbol, data in tickers.items():
        if symbol.endswith('/USDT') and 'quoteVolume' in data and data['quoteVolume'] is not None:
            usdt_tickers.append((symbol, data['quoteVolume']))
    
    # Sort by quoteVolume descending
    usdt_tickers.sort(key=lambda x: x[1], reverse=True)
    
    # Pick top 30
    top_30 = [x[0] for x in usdt_tickers[:30]]
    
    # Ensure BTC/USDT and UNI/USDT are always included
    for must_include in ['BTC/USDT', 'UNI/USDT']:
        if must_include not in top_30:
            top_30.append(must_include)
            
    print(f"Selected {len(top_30)} symbols for data collection.")
    return top_30

def fetch_ohlcv_range(exchange, symbol, timeframe, since_ms, until_ms):
    all_candles = []
    current_since = since_ms
    
    # Timeframe duration helper to check progress
    tf_durations = {
        '1m': 60 * 1000,
        '15m': 15 * 60 * 1000,
        '1h': 60 * 60 * 1000
    }
    tf_ms = tf_durations.get(timeframe, 60 * 1000)
    
    while current_since < until_ms:
        try:
            # Add small delay to respect rate limit
            time.sleep(0.05)
            
            # Fetch up to 1000 candles
            candles = exchange.fetch_ohlcv(symbol, timeframe, since=current_since, limit=1000)
            if not candles:
                break
                
            last_timestamp = candles[-1][0]
            
            # Filter candles that are beyond until_ms
            filtered_candles = [c for c in candles if c[0] <= until_ms]
            all_candles.extend(filtered_candles)
            
            # If the last candle fetched is past our target or we got fewer than expected, or progress stopped
            if last_timestamp >= until_ms or len(candles) < 2:
                break
                
            # Move since forward
            current_since = last_timestamp + tf_ms
            
        except Exception as e:
            print(f"Error fetching {symbol} {timeframe} at {current_since}: {e}")
            time.sleep(2)  # Backoff and retry
            
    return all_candles

def main():
    exchange = ccxt.binance({
        'enableRateLimit': True,
        'options': {'defaultType': 'spot'}
    })
    
    # Target range in UTC
    start_dt = datetime.datetime(2026, 6, 14, 0, 0, 0, tzinfo=datetime.timezone.utc)
    end_dt = datetime.datetime(2026, 6, 18, 23, 59, 59, tzinfo=datetime.timezone.utc)
    
    since_ms = int(start_dt.timestamp() * 1000)
    until_ms = int(end_dt.timestamp() * 1000)
    
    print(f"Target Period: {start_dt} to {end_dt}")
    
    # Get symbols
    symbols = get_top_30_usdt_symbols(exchange)
    
    # Ensure target directories exist
    out_dir = 'datasets/market/binance'
    os.makedirs(out_dir, exist_ok=True)
    
    timeframes = ['1m', '15m', '1h']
    
    for timeframe in timeframes:
        print(f"\n--- Starting Timeframe: {timeframe} ---")
        for i, symbol in enumerate(symbols, 1):
            symbol_clean = symbol.replace('/', '_')
            out_path = os.path.join(out_dir, f"{symbol_clean}_{timeframe}.csv")
            
            # Skip if already exists and has data to save time (unless forced)
            if os.path.exists(out_path) and os.path.getsize(out_path) > 1000:
                print(f"[{i}/{len(symbols)}] {symbol_clean} {timeframe} already exists. Skipping.")
                continue
                
            print(f"[{i}/{len(symbols)}] Fetching {symbol} ({timeframe})...")
            candles = fetch_ohlcv_range(exchange, symbol, timeframe, since_ms, until_ms)
            
            if candles:
                df = pd.DataFrame(candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                # Convert timestamp (ms) to ISO datetime for readability
                df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
                # Reorder columns
                df = df[['timestamp', 'datetime', 'open', 'high', 'low', 'close', 'volume']]
                df.to_csv(out_path, index=False)
                print(f"  Saved {len(df)} rows to {out_path}")
            else:
                print(f"  WARNING: No candles retrieved for {symbol} ({timeframe})")
                
    print("\nData fetch complete!")

if __name__ == '__main__':
    main()
