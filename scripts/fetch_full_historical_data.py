import os
import sys
import time
import datetime
import pandas as pd
import ccxt

FLOW_SYMBOLS = [
    'BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'SOL/USDT', 'XRP/USDT',
    'DOGE/USDT', 'ADA/USDT', 'LINK/USDT', 'AVAX/USDT', 'UNI/USDT',
    'FET/USDT', 'TAO/USDT'
]

def fetch_ohlcv_range(exchange, symbol, timeframe, since_ms, until_ms):
    all_candles = []
    current_since = since_ms
    tf_ms = 15 * 60 * 1000  # 15m in ms
    
    # We use a progress log to avoid flooding stdout
    last_logged_pct = -10
    total_duration = until_ms - since_ms
    
    while current_since < until_ms:
        try:
            # Short sleep to respect rate limit (approx 12-15 calls per second max)
            time.sleep(0.06) 
            candles = exchange.fetch_ohlcv(symbol, timeframe, since=current_since, limit=1000)
            if not candles:
                # If no candles returned, move forward by 10 days to check if symbol listed later
                current_since += 1000 * tf_ms
                continue
                
            last_timestamp = candles[-1][0]
            filtered_candles = [c for c in candles if c[0] <= until_ms]
            all_candles.extend(filtered_candles)
            
            # Progress printing
            pct = int(((current_since - since_ms) / total_duration) * 100)
            if pct >= last_logged_pct + 10:
                print(f"    Fetching {symbol}: {pct}% complete...")
                last_logged_pct = pct
                
            if last_timestamp >= until_ms or len(candles) < 2:
                break
                
            current_since = last_timestamp + tf_ms
        except Exception as e:
            err_msg = str(e).lower()
            # If symbol didn't exist at this time, CCXT will throw BadSymbol/InvalidSymbol/etc
            if 'symbol' in err_msg or 'bad-symbol' in err_msg or 'not exist' in err_msg or 'invalid' in err_msg:
                # Move forward by 10 days to check for listing date
                current_since += 1000 * tf_ms
                continue
            print(f"  Error fetching {symbol} at {current_since}: {e}")
            time.sleep(2)
            
    return all_candles

def main():
    exchange = ccxt.binance({
        'enableRateLimit': True,
        'options': {'defaultType': 'spot'}
    })
    
    start_dt = datetime.datetime(2022, 1, 1, 0, 0, 0, tzinfo=datetime.timezone.utc)
    end_dt = datetime.datetime(2026, 6, 18, 0, 0, 0, tzinfo=datetime.timezone.utc)
    
    since_ms = int(start_dt.timestamp() * 1000)
    until_ms = int(end_dt.timestamp() * 1000)
    
    out_dir = 'datasets/market/full_historical'
    os.makedirs(out_dir, exist_ok=True)
    
    print(f"Starting extended historical data fetch from {start_dt} to {end_dt}")
    
    for i, symbol in enumerate(FLOW_SYMBOLS, 1):
        symbol_clean = symbol.replace('/', '_')
        out_path = os.path.join(out_dir, f"{symbol_clean}_15m.csv")
        
        # Check if file exists and has substantial size (minimum 2MB for 4.5 years of 15m data)
        # 1.5 years of 15m data is roughly 4-5MB. So 4.5 years should be at least 10MB.
        # Let's check for 2MB to ensure we don't skip half-complete downloads.
        if os.path.exists(out_path) and os.path.getsize(out_path) > 2 * 1024 * 1024:
            print(f"  [{i}/{len(FLOW_SYMBOLS)}] {symbol_clean}_15m.csv already exists with size {os.path.getsize(out_path)/1024/1024:.2f}MB. Skipping.")
            continue
            
        print(f"  [{i}/{len(FLOW_SYMBOLS)}] Fetching {symbol} (15m)...")
        start_time = time.time()
        candles = fetch_ohlcv_range(exchange, symbol, '15m', since_ms, until_ms)
        elapsed = time.time() - start_time
        
        if candles:
            df = pd.DataFrame(candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
            df = df[['timestamp', 'datetime', 'open', 'high', 'low', 'close', 'volume']]
            # Deduplicate just in case
            df = df.drop_duplicates(subset=['timestamp']).sort_values('timestamp').reset_index(drop=True)
            df.to_csv(out_path, index=False)
            print(f"    Saved {len(df)} rows to {out_path} (Took {elapsed:.1f}s)")
        else:
            print(f"    No candles retrieved for {symbol}.")
            
    print("\nExtended historical dataset download complete.")

if __name__ == '__main__':
    main()
