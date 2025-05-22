"""
Module to provide NIFTY50 symbols list for the dashboard
"""

# List of NIFTY50 symbols
NIFTY50_SYMBOLS = [
    "NSE:ADANIENT-EQ", "NSE:ADANIPORTS-EQ", "NSE:APOLLOHOSP-EQ", "NSE:ASIANPAINT-EQ", 
    "NSE:AXISBANK-EQ", "NSE:BAJAJ-AUTO-EQ", "NSE:BAJFINANCE-EQ", "NSE:BAJAJFINSV-EQ", 
    "NSE:BEL-EQ", "NSE:BHARTIARTL-EQ", "NSE:BRITANNIA-EQ", "NSE:CIPLA-EQ", 
    "NSE:COALINDIA-EQ", "NSE:DRREDDY-EQ", "NSE:EICHERMOT-EQ", "NSE:GRASIM-EQ",
    "NSE:HCLTECH-EQ", "NSE:HDFCBANK-EQ", "NSE:HDFCLIFE-EQ", "NSE:HEROMOTOCO-EQ", 
    "NSE:HINDALCO-EQ", "NSE:HINDUNILVR-EQ", "NSE:ICICIBANK-EQ", "NSE:INFY-EQ", 
    "NSE:INDUSINDBK-EQ", "NSE:ITC-EQ", "NSE:JIOFIN-EQ", "NSE:JSWSTEEL-EQ", 
    "NSE:KOTAKBANK-EQ", "NSE:LT-EQ", "NSE:M&M-EQ", "NSE:MARUTI-EQ",
    "NSE:NTPC-EQ", "NSE:NESTLEIND-EQ", "NSE:ONGC-EQ", "NSE:POWERGRID-EQ", 
    "NSE:RELIANCE-EQ", "NSE:SBILIFE-EQ", "NSE:SBIN-EQ", "NSE:SHRIRAMFIN-EQ",
    "NSE:SUNPHARMA-EQ", "NSE:TCS-EQ", "NSE:TATACONSUM-EQ", "NSE:TATAMOTORS-EQ", 
    "NSE:TATASTEEL-EQ", "NSE:TECHM-EQ", "NSE:TITAN-EQ", "NSE:TRENT-EQ", 
    "NSE:ULTRACEMCO-EQ", "NSE:WIPRO-EQ"
]

# Main index
NIFTY_INDEX = ["NSE:NIFTY50-INDEX"]

# Function to get all symbols including index
def get_all_symbols():
    """Return all symbols including NIFTY50 index"""
    return NIFTY_INDEX + NIFTY50_SYMBOLS

# Function to get only stock symbols
def get_stock_symbols():
    """Return only NIFTY50 stock symbols"""
    return NIFTY50_SYMBOLS

if __name__ == "__main__":
    print("NIFTY50 Symbols:", len(NIFTY50_SYMBOLS))
    print("All Symbols (including index):", len(get_all_symbols())) 