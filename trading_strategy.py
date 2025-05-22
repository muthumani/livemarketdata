"""
Simple trading strategy module for NIFTY50 stocks
"""

import pandas as pd
import numpy as np

def calculate_rsi(data, period=14):
    """
    Calculate Relative Strength Index (RSI)
    
    Args:
        data (pd.Series): Series of price data
        period (int): RSI period, default 14
        
    Returns:
        float: RSI value
    """
    # Calculate price changes
    delta = data.diff()
    
    # Calculate gains and losses
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    
    # Calculate average gain and loss
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    
    # Calculate relative strength
    rs = avg_gain / avg_loss
    
    # Calculate RSI
    rsi = 100 - (100 / (1 + rs))
    
    return rsi.iloc[-1] if not pd.isna(rsi.iloc[-1]) else 50

def calculate_macd(data, fast_period=12, slow_period=26, signal_period=9):
    """
    Calculate Moving Average Convergence Divergence (MACD)
    
    Args:
        data (pd.Series): Series of price data
        fast_period (int): Fast EMA period
        slow_period (int): Slow EMA period
        signal_period (int): Signal line period
        
    Returns:
        tuple: (MACD line, Signal line, Histogram)
    """
    # Calculate fast and slow EMAs
    ema_fast = data.ewm(span=fast_period, adjust=False).mean()
    ema_slow = data.ewm(span=slow_period, adjust=False).mean()
    
    # Calculate MACD line
    macd_line = ema_fast - ema_slow
    
    # Calculate signal line
    signal_line = macd_line.ewm(span=signal_period, adjust=False).mean()
    
    # Calculate histogram
    histogram = macd_line - signal_line
    
    return (
        macd_line.iloc[-1] if not pd.isna(macd_line.iloc[-1]) else 0,
        signal_line.iloc[-1] if not pd.isna(signal_line.iloc[-1]) else 0,
        histogram.iloc[-1] if not pd.isna(histogram.iloc[-1]) else 0
    )

def calculate_change(current_price, previous_close):
    """
    Calculate price change and percentage change
    
    Args:
        current_price (float): Current price
        previous_close (float): Previous closing price
        
    Returns:
        tuple: (price_change, price_change_percent)
    """
    price_change = current_price - previous_close
    price_change_percent = (price_change / previous_close) * 100 if previous_close > 0 else 0
    return price_change, price_change_percent

class TradingStrategy:
    def __init__(self):
        """Initialize the trading strategy"""
        self.historical_data = {}

    def get_trading_signal(self, historical_data):
        """
        Generate trading signal based on RSI, MACD, and price action analysis
        
        Args:
            historical_data (dict): Dictionary containing historical OHLC data
            
        Returns:
            str: Trading signal - 'BUY', 'SELL', or 'HOLD'
        """
        if not historical_data or 'close' not in historical_data:
            return 'HOLD'
        
        # Convert to pandas series
        close_prices = pd.Series(historical_data['close'])
        high_prices = pd.Series(historical_data['high'])
        low_prices = pd.Series(historical_data['low'])
        volume = pd.Series(historical_data.get('volume', []))
        
        if len(close_prices) < 30:  # Need at least 30 periods for reliable signals
            return 'HOLD'
        
        # Calculate technical indicators
        rsi = calculate_rsi(close_prices)
        macd, signal, histogram = calculate_macd(close_prices)
        
        # Calculate price action metrics
        recent_changes = close_prices.diff().tail(5)  # Last 5 price changes
        price_trend = recent_changes.mean()  # Average price change
        
        # Calculate volatility
        volatility = close_prices.pct_change().std() * 100
        
        # Calculate volume trend
        volume_trend = volume.pct_change().tail(5).mean() if len(volume) > 0 else 0
        
        # Calculate price momentum
        momentum = (close_prices.iloc[-1] / close_prices.iloc[-5] - 1) * 100 if len(close_prices) >= 5 else 0
        
        # Calculate support and resistance levels
        recent_high = high_prices.tail(20).max()
        recent_low = low_prices.tail(20).min()
        current_price = close_prices.iloc[-1]
        
        # Calculate price position relative to recent range
        price_position = (current_price - recent_low) / (recent_high - recent_low) if (recent_high - recent_low) > 0 else 0.5
        
        # Enhanced trading logic with multiple conditions
        
        # Strong Buy Conditions
        if (rsi < 30 and  # Oversold
            histogram > 0 and  # MACD histogram positive
            macd > signal and  # MACD above signal line
            price_trend > 0 and  # Upward price trend
            volume_trend > 0 and  # Increasing volume
            price_position < 0.3):  # Price near support
            return 'BUY'
        
        # Moderate Buy Conditions
        elif (rsi < 40 and  # Approaching oversold
            histogram > 0 and  # MACD histogram positive
            momentum > 0 and  # Positive momentum
            price_trend > 0):  # Upward price trend
            return 'BUY'
        
        # Strong Sell Conditions
        elif (rsi > 70 and  # Overbought
            histogram < 0 and  # MACD histogram negative
            macd < signal and  # MACD below signal line
            price_trend < 0 and  # Downward price trend
            volume_trend < 0 and  # Decreasing volume
            price_position > 0.7):  # Price near resistance
            return 'SELL'
        
        # Moderate Sell Conditions
        elif (rsi > 60 and  # Approaching overbought
            histogram < 0 and  # MACD histogram negative
            momentum < 0 and  # Negative momentum
            price_trend < 0):  # Downward price trend
            return 'SELL'
        
        # Hold Conditions
        else:
            return 'HOLD'

    def get_current_signal(self, current_data):
        """
        Generate trading signal based on current market data
        
        Args:
            current_data (dict): Dictionary containing current market data
            
        Returns:
            str: Trading signal - 'BUY', 'SELL', or 'HOLD'
        """
        if not current_data:
            return 'HOLD'
        
        # Extract required values
        ltp = current_data.get('ltp', 0)
        open_price = current_data.get('open', 0)
        high = current_data.get('high', 0)
        low = current_data.get('low', 0)
        close = current_data.get('close', 0)
        
        if not all([ltp, open_price, high, low, close]):
            return 'HOLD'
        
        # Calculate price change
        price_change = ltp - close
        price_change_percent = (price_change / close) * 100 if close > 0 else 0
        
        # Simple trading logic based on current price movement
        if price_change_percent > 1.0:  # Price up by more than 1%
            return 'BUY'
        elif price_change_percent < -1.0:  # Price down by more than 1%
            return 'SELL'
        else:
            return 'HOLD'

    def calculate_change(self, current_price, previous_close):
        """
        Calculate price change and percentage change
        
        Args:
            current_price (float): Current price
            previous_close (float): Previous closing price
            
        Returns:
            tuple: (Change, Change percentage)
        """
        if previous_close == 0 or previous_close is None:
            return 0, 0
        
        change = current_price - previous_close
        change_percent = (change / previous_close) * 100
        
        return round(change, 2), round(change_percent, 2) 