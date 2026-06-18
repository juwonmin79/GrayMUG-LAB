import os
import sys
import time
import datetime
import pandas as pd
import ccxt

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
            time.sleep(0.08)  # respect rate limit
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
            err_msg = str(e).lower()
            if 'symbol' in err_msg or 'bad-symbol' in err_msg or 'not exist' in err_msg:
                return None
            print(f"  Error fetching {symbol} at {current_since}: {e}")
            time.sleep(2)
            
    return all_candles

def main():
    exchange = ccxt.binance({
        'enableRateLimit': True,
        'options': {'defaultType': 'spot'}
    })
    
    # 2-month continuous window
    start_dt = datetime.datetime(2024, 5, 1, 0, 0, 0, tzinfo=datetime.timezone.utc)
    end_dt = datetime.datetime(2024, 7, 1, 0, 0, 0, tzinfo=datetime.timezone.utc)
    
    since_ms = int(start_dt.timestamp() * 1000)
    until_ms = int(end_dt.timestamp() * 1000)
    
    out_dir = 'datasets/market/continuous'
    os.makedirs(out_dir, exist_ok=True)
    
    print(f"Fetching continuous 15m data from {start_dt} to {end_dt}")
    
    for i, symbol in enumerate(MAJOR_SYMBOLS, 1):
        symbol_clean = symbol.replace('/', '_')
        out_path = os.path.join(out_dir, f"{symbol_clean}_15m.csv")
        
        if os.path.exists(out_path) and os.path.getsize(out_path) > 100000:
            print(f"  [{i}/{len(MAJOR_SYMBOLS)}] {symbol} already exists. Skipping.")
            continue
            
        print(f"  [{i}/{len(MAJOR_SYMBOLS)}] Fetching {symbol}...")
        candles = fetch_ohlcv_range(exchange, symbol, '15m', since_ms, until_ms)
        
        if candles:
            df = pd.DataFrame(candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
            df = df[['timestamp', 'datetime', 'open', 'high', 'low', 'close', 'volume']]
            df.to_csv(out_path, index=False)
            print(f"    Saved {len(df)} rows for {symbol}")
        elif candles is None:
            print(f"    Skipped {symbol} (not listed or error).")
        else:
            print(f"    No candles retrieved for {symbol}.")
            
    print("Continuous data fetch complete.")

if __name__ == '__main__':
    main()
