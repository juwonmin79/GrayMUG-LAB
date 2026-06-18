import os
import sys
import time
import datetime
import pandas as pd
import ccxt

# Curated list of 30 major liquid coins that existed historically or are key market assets
MAJOR_SYMBOLS = [
    'BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'BNB/USDT', 'XRP/USDT',
    'ADA/USDT', 'DOGE/USDT', 'DOT/USDT', 'LTC/USDT', 'LINK/USDT',
    'AVAX/USDT', 'NEAR/USDT', 'UNI/USDT', 'TRX/USDT', 'ETC/USDT',
    'FIL/USDT', 'ATOM/USDT', 'FTM/USDT', 'ICP/USDT', 'SHIB/USDT',
    'APE/USDT', 'SAND/USDT', 'MANA/USDT', 'GALA/USDT', 'DYDX/USDT',
    'OP/USDT', 'ARB/USDT', 'LDO/USDT', 'APT/USDT', 'SUI/USDT'
]

def fetch_ohlcv_range(exchange, symbol, timeframe, since_ms, until_ms):
    all_candles = []
    current_since = since_ms
    tf_ms = 15 * 60 * 1000  # 15m in ms
    
    while current_since < until_ms:
        try:
            time.sleep(0.05)  # rate limit support
            candles = exchange.fetch_ohlcv(symbol, timeframe, since=current_since, limit=1000)
            if not candles:
                break
                
            last_timestamp = candles[-1][0]
            filtered_candles = [c for c in candles if c[0] <= until_ms]
            all_candles.extend(filtered_candles)
            
            if last_timestamp >= until_ms or len(candles) < 2:
                break
                
            current_since = last_timestamp + tf_ms
        except Exception as e:
            # If symbol not listed yet, ccxt will throw BadSymbol or similar
            err_msg = str(e).lower()
            if 'symbol' in err_msg or 'bad-symbol' in err_msg or 'not exist' in err_msg:
                # Symbol probably didn't exist at this time
                return None
            print(f"  Error fetching {symbol} at {current_since}: {e}")
            time.sleep(2)
            
    return all_candles

def main():
    exchange = ccxt.binance({
        'enableRateLimit': True,
        'options': {'defaultType': 'spot'}
    })
    
    # Load events
    events_path = 'datasets/events/events.csv'
    if not os.path.exists(events_path):
        print(f"Error: {events_path} not found.")
        sys.exit(1)
        
    df_events = pd.read_csv(events_path)
    
    timeframe = '15m'
    
    for idx, row in df_events.iterrows():
        event_name = row['event_name']
        event_date_str = row['event_date']
        category = row['category']
        
        event_name_clean = event_name.replace(' ', '_').replace('/', '_')
        print(f"\n==================================================")
        print(f"Processing Event: {event_name} ({category}) | Date: {event_date_str}")
        print(f"==================================================")
        
        # Parse date and build ±3 days window
        event_dt = datetime.datetime.strptime(event_date_str, '%Y-%m-%d').replace(tzinfo=datetime.timezone.utc)
        start_dt = event_dt - datetime.timedelta(days=3)
        end_dt = event_dt + datetime.timedelta(days=3, hours=23, minutes=59, seconds=59)
        
        since_ms = int(start_dt.timestamp() * 1000)
        until_ms = int(end_dt.timestamp() * 1000)
        
        # Setup output directory
        out_dir = os.path.join('datasets/market/events', event_name_clean)
        os.makedirs(out_dir, exist_ok=True)
        
        print(f"Time Range: {start_dt} to {end_dt}")
        
        for i, symbol in enumerate(MAJOR_SYMBOLS, 1):
            symbol_clean = symbol.replace('/', '_')
            out_path = os.path.join(out_dir, f"{symbol_clean}_{timeframe}.csv")
            
            if os.path.exists(out_path) and os.path.getsize(out_path) > 1000:
                print(f"  [{i}/{len(MAJOR_SYMBOLS)}] {symbol} already exists. Skipping.")
                continue
                
            # Fetch data
            candles = fetch_ohlcv_range(exchange, symbol, timeframe, since_ms, until_ms)
            if candles is not None and len(candles) > 0:
                df = pd.DataFrame(candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
                df = df[['timestamp', 'datetime', 'open', 'high', 'low', 'close', 'volume']]
                df.to_csv(out_path, index=False)
                print(f"  [{i}/{len(MAJOR_SYMBOLS)}] Fetched {len(df)} rows for {symbol}")
            elif candles is None:
                print(f"  [{i}/{len(MAJOR_SYMBOLS)}] {symbol} skipped (possibly not listed yet during this event).")
            else:
                print(f"  [{i}/{len(MAJOR_SYMBOLS)}] No data returned for {symbol}.")
                
    print("\nAll event data fetched successfully!")

if __name__ == '__main__':
    main()
