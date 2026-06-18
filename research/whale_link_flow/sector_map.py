# Sector mappings for the 12 assets in GrayMUG-LAB
SECTOR_MAP = {
    'BTC': 'L1',
    'ETH': 'L1',
    'SOL': 'L1',
    'AVAX': 'L1',
    'ADA': 'L1',
    'FET': 'AI',
    'TAO': 'AI',
    'DOGE': 'MEME',
    'UNI': 'DEX',
    'LINK': 'INFRA',
    'BNB': 'EXCHANGE'
}

def get_sector(symbol: str) -> str:
    """
    Returns the sector name for a given symbol (e.g. 'SOL/USDT' or 'SOL' -> 'L1').
    """
    clean_symbol = symbol.split('/')[0].upper()
    return SECTOR_MAP.get(clean_symbol, 'UNKNOWN')
