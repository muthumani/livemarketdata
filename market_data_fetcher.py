"""
Market data fetcher module to interact with Fyers API
"""

# Apply eventlet monkey patching first
import eventlet
eventlet.monkey_patch()

import os
import time
import logging
import json
import threading
from datetime import datetime, timedelta
import pandas as pd
from fyers_apiv3 import fyersModel
from fyers_apiv3.FyersWebsocket import data_ws
import random

# Import local modules - do this inside functions to avoid circular imports
# We'll import these inside functions where needed rather than at the module level

# Set up logging
logger = logging.getLogger(__name__)

class MarketDataFetcher:
    """Class to fetch and manage market data from Fyers API"""
    
    def __init__(self, fyers_client, trading_strategy, socketio, enable_history=True, shutdown_event=None):
        """
        Initialize the market data fetcher
        
        Args:
            fyers_client: Initialized Fyers API client
            trading_strategy: TradingStrategy instance
            socketio: SocketIO instance for real-time updates
            enable_history (bool): Whether to enable historical data fetching
            shutdown_event (threading.Event): Event for graceful shutdown
        """
        self.fyers = fyers_client
        self.trading_strategy = trading_strategy
        self.socketio = socketio
        self.enable_history = enable_history
        self.shutdown_event = shutdown_event
        self.running = False
        self.connected = False
        
        # Data storage
        self.market_data = {}
        self.previous_market_data = {}  # Store previous tick values for comparison
        self.historical_data = {}
        self.data_callbacks = []
        
        # Last data update time
        self.last_ws_update = None
        self.fallback_active = False
        
        # Symbol mapping - maps token/id to symbol name
        self.symbol_mapping = {}
        self.active_symbols = []
        
        # Initialize market data for all symbols
        self._initialize_data()
    
    def _initialize_data(self):
        """Initialize empty market data for all symbols"""
        # Import here to avoid circular import
        from nifty50_symbols import get_all_symbols, NIFTY_INDEX
        
        logger.info("Initializing market data with default values for all symbols")
        
        # Get all symbols and sort them
        symbols = sorted(get_all_symbols())
        
        # Initialize market data with sorted symbols
        for symbol in symbols:
            symbol_name = symbol.split(':')[1]
            self.market_data[symbol_name] = {
                'symbol': symbol_name,
                'ltp': 0,
                'open': 0,
                'high': 0,
                'low': 0,
                'close': 0,
                'volume': 0,
                'change': 0,
                'change_percent': 0,
                'trading_signal': 'HOLD',
                'timestamp': datetime.now().isoformat(),
                'is_index': symbol in NIFTY_INDEX,  # Flag to identify indices
                'market_status': 'CLOSED'  # Default to closed until market opens
            }
        
        # Store the sorted symbol list for reference
        self.sorted_symbols = [symbol.split(':')[1] for symbol in symbols]
        logger.info(f"Initialized market data with {len(self.sorted_symbols)} symbols in sorted order")
    
    def fetch_quotes_fallback(self):
        """
        Fallback method to fetch quotes via REST API if WebSocket is not working
        """
        if not self.fyers or not self.running:
            logger.warning("Cannot fetch quotes: No Fyers client or not running")
            return False
        
        now = datetime.now()
        
        # Check if it's weekend
        is_weekend = now.weekday() >= 5  # Saturday (5) or Sunday (6)
        
        current_time = now.time()
        market_open = datetime.strptime("09:15:00", "%H:%M:%S").time()
        market_close = datetime.strptime("15:30:00", "%H:%M:%S").time()
        
        is_market_hours = market_open <= current_time <= market_close and not is_weekend
        
        try:
            # Import here to avoid circular import
            from nifty50_symbols import get_all_symbols
            
            symbols = get_all_symbols()
            logger.info(f"Fetching quotes for {len(symbols)} symbols")
            
            # Get quotes for all symbols
            quotes_data = {
                "symbols": ",".join(symbols)
            }
            
            response = self.fyers.quotes(quotes_data)
            
            if response and "code" in response and response["code"] == 200:
                quotes = response.get("d", [])
                
                # Process quotes
                for data in quotes:
                    try:
                        if 'n' in data and 'v' in data:
                            symbol_parts = data['n'].split(':')
                            if len(symbol_parts) >= 2:
                                symbol_name = symbol_parts[1]
                                
                                # Extract values
                                v_data = data.get('v', {})
                                ltp = v_data.get('lp', 0)
                                open_price = v_data.get('op', v_data.get('open', 0))
                                high = v_data.get('h', v_data.get('high', 0))
                                low = v_data.get('l', v_data.get('low', 0))
                                close = v_data.get('c', v_data.get('close', 0))
                                volume = v_data.get('v', v_data.get('volume', 0))
                                
                                # Update market data
                                if symbol_name in self.market_data:
                                    # Preserve previous values
                                    prev_data = self.market_data[symbol_name].copy()
                                    
                                    # Update with new values
                                    self.market_data[symbol_name].update({
                                        'ltp': ltp if ltp > 0 else prev_data.get('ltp', 0),
                                        'open': open_price if open_price > 0 else prev_data.get('open', 0),
                                        'high': high if high > 0 else prev_data.get('high', 0),
                                        'low': low if low > 0 else prev_data.get('low', 0),
                                        'close': close if close > 0 else prev_data.get('close', 0),
                                        'volume': volume if volume > 0 else prev_data.get('volume', 0),
                                        'timestamp': datetime.now().isoformat(),
                                        'market_status': 'OPEN' if is_market_hours else 'CLOSED'
                                    })
                                    
                                    # Calculate change and change percent
                                    from trading_strategy import calculate_change
                                    current_price = self.market_data[symbol_name]['ltp']
                                    prev_close = self.market_data[symbol_name]['close']
                                    change, change_percent = calculate_change(current_price, prev_close)
                                    self.market_data[symbol_name]['change'] = change
                                    self.market_data[symbol_name]['change_percent'] = change_percent
                                    
                    except Exception as e:
                        logger.error(f"Error processing quote for {symbol_name}: {str(e)}")
                        continue
                
                # Notify of update
                self._notify_data_update()
                return True
                
        except Exception as e:
            logger.error(f"Error in fallback quotes fetching: {str(e)}")
            return False
    
    def _fallback_data_worker(self):
        """Worker thread for periodically fetching data via fallback method"""
        while self.running:
            try:
                # Only use fallback if WebSocket data isn't coming through
                now = datetime.now()
                
                # If no WS updates in the last 30 seconds, activate fallback
                if (not self.last_ws_update or 
                    (now - self.last_ws_update).total_seconds() > 30):
                    
                    if not self.fallback_active:
                        logger.warning("No recent WebSocket updates, activating fallback data fetching")
                        self.fallback_active = True
                    
                    self.fetch_quotes_fallback()
                elif self.fallback_active:
                    logger.info("WebSocket updates resumed, deactivating fallback data fetching")
                    self.fallback_active = False
            except Exception as e:
                logger.error(f"Error in fallback data worker: {str(e)}")
            
            # Sleep for 5 seconds before checking again
            time.sleep(5)
    
    def _on_ws_message(self, message):
        """
        WebSocket message handler
        
        Args:
            message (dict): Message from WebSocket
        """
        try:
            if not message or not isinstance(message, dict):
                logger.warning(f"Received invalid WebSocket message format: {type(message)}")
                return
            
            # Update last WS message time
            self.last_ws_update = datetime.now()
            
            # Handle different message formats
            if 's' in message:  # Standard Symbol update format
                # Process updates individually without batching
                for data in message.get('d', []):
                    if 'n' in data and 'v' in data:
                        symbol_parts = data['n'].split(':')
                        if len(symbol_parts) >= 2:
                            symbol_name = symbol_parts[1]
                            try:
                                # Get previous values for comparison
                                prev_values = self.previous_market_data.get(symbol_name, {})
                                
                                # Extract new values
                                v_data = data.get('v', {})
                                ltp = v_data.get('lp', 0)
                                open_price = v_data.get('op', v_data.get('open', 0))
                                high = v_data.get('h', v_data.get('high', 0))
                                low = v_data.get('l', v_data.get('low', 0))
                                close = v_data.get('c', v_data.get('close', 0))
                                volume = v_data.get('v', v_data.get('volume', 0))
                                
                                # Track which values have changed
                                changed_fields = {}
                                if ltp != prev_values.get('ltp', 0):
                                    changed_fields['ltp'] = ltp
                                    changed_fields['ltp_changed'] = True
                                    changed_fields['ltp_direction'] = 'up' if ltp > prev_values.get('ltp', 0) else 'down'
                                if volume != prev_values.get('volume', 0):
                                    changed_fields['volume'] = volume
                                    changed_fields['volume_changed'] = True
                                    changed_fields['volume_direction'] = 'up' if volume > prev_values.get('volume', 0) else 'down'
                                if open_price != prev_values.get('open', 0):
                                    changed_fields['open'] = open_price
                                if high != prev_values.get('high', 0):
                                    changed_fields['high'] = high
                                if low != prev_values.get('low', 0):
                                    changed_fields['low'] = low
                                if close != prev_values.get('close', 0):
                                    changed_fields['close'] = close
                                    changed_fields['prev_close'] = prev_values.get('close', 0)
                                
                                # Only update if there are changes
                                if changed_fields:
                                    # Update market data with only changed fields
                                    if symbol_name not in self.market_data:
                                        self.market_data[symbol_name] = {}
                                    
                                    # Preserve existing values
                                    current_data = self.market_data[symbol_name].copy()
                                    
                                    # Update only changed fields
                                    current_data.update(changed_fields)
                                    current_data['timestamp'] = datetime.now().isoformat()
                                    
                                    # Calculate change and change percent
                                    from trading_strategy import calculate_change
                                    current_price = current_data.get('ltp', 0)
                                    prev_close = current_data.get('prev_close', current_data.get('close', 0))
                                    change, change_percent = calculate_change(current_price, prev_close)
                                    current_data['change'] = change
                                    current_data['change_percent'] = change_percent
                                    
                                    # Update the data
                                    self.market_data[symbol_name] = current_data
                                    
                                    # Store current values as previous for next comparison
                                    self.previous_market_data[symbol_name] = current_data.copy()
                                    
                                    # Notify of update
                                    self._notify_data_update()
                                    
                            except Exception as e:
                                logger.error(f"Error processing update for {symbol_name}: {str(e)}")
                                continue
            
            # Handle direct data format (no 's' field, but has 'ltp')
            elif 'ltp' in message:
                try:
                    # Try to determine the symbol from message
                    symbol = None
                    
                    # Look for symbol identifiers in various fields
                    symbol_field_candidates = ['symbol', 'sym', 'symbol_name', 'n', 'name', 'tk', 'token', 'id']
                    for field in symbol_field_candidates:
                        if field in message and message[field]:
                            symbol = message[field]
                            logger.debug(f"Found symbol identifier in message field '{field}': {symbol}")
                            break
                    
                    # Check additional fields that might contain the symbol
                    if not symbol and 'instrument_name' in message:
                        symbol = message['instrument_name']
                        logger.debug(f"Found symbol identifier in 'instrument_name': {symbol}")
                    elif not symbol and 'instrument' in message:
                        symbol = message['instrument']
                        logger.debug(f"Found symbol identifier in 'instrument': {symbol}")
                    
                    # Try to extract symbol from bid or ask fields
                    if not symbol and 'bid_price' in message and message['bid_price'] > 0:
                        # Find matching symbols by comparing prices
                        potential_symbols = []
                        for sym, data in self.market_data.items():
                            if abs(data.get('ltp', 0) - message['bid_price']) < 0.1:
                                potential_symbols.append(sym)
                        
                        if len(potential_symbols) == 1:
                            # If we have exactly one match, use it
                            symbol = potential_symbols[0]
                            logger.debug(f"Determined symbol by price matching: {symbol}")
                    
                    # Check for security_id or other identifiers
                    if not symbol and 'security_id' in message:
                        # Try lookup in the symbol mapping
                        symbol = self.symbol_mapping.get(message['security_id'])
                        if symbol:
                            logger.debug(f"Found symbol from security_id mapping: {symbol}")
                    
                    # If we still don't have a symbol, use sequence tracking
                    if not symbol:
                        # Get the number of active symbols
                        num_active_symbols = len(self.active_symbols)
                        
                        if num_active_symbols > 0:
                            # Check if message has an order or sequence number
                            seq_num = message.get('seq', message.get('sequence', message.get('seq_no', None)))
                            
                            if seq_num is not None:
                                # Use sequence number to determine which symbol this is for
                                symbol_index = seq_num % num_active_symbols
                                symbol = self.active_symbols[symbol_index]
                                logger.debug(f"Determined symbol by sequence number {seq_num}: {symbol}")
                            else:
                                # Use timestamp-based heuristic
                                timestamp_ms = int(datetime.now().timestamp() * 1000)
                                symbol_index = timestamp_ms % num_active_symbols
                                symbol = self.active_symbols[symbol_index]
                                logger.debug(f"Using timestamp heuristic to map data to symbol {symbol}")
                        else:
                            logger.debug("No active symbols to map message to")
                    
                    if not symbol:
                        # If we still can't determine which symbol this is for, log and skip
                        logger.debug(f"Cannot determine symbol for message: {json.dumps(message)[:100]}...")
                        return
                    
                    # Extract symbol name in case it has exchange prefix
                    if ':' in symbol:
                        symbol_name = symbol.split(':')[1]
                    else:
                        # Try the symbol mapping
                        symbol_name = self.symbol_mapping.get(symbol, symbol)
                    
                    # Add to symbol mapping for future use
                    self.symbol_mapping[symbol] = symbol_name
                    
                    # Extract price data
                    ltp = float(message.get('ltp', 0)) 
                    
                    # Look for different field names for OHLC values
                    open_price = float(message.get('open', message.get('op', message.get('open_price', 0))))
                    high = float(message.get('high', message.get('h', message.get('high_price', 0))))
                    low = float(message.get('low', message.get('l', message.get('low_price', 0))))
                    close = float(message.get('close', message.get('c', message.get('prev_close', message.get('prev_close_price', 0)))))
                    volume = int(message.get('volume', message.get('vol', message.get('v', message.get('vol_traded_today', 0)))))
                    
                    # Default to at least using LTP value if we have no other values
                    if ltp > 0:
                        if open_price == 0:
                            open_price = ltp
                        if high == 0 or high < ltp:
                            high = ltp
                        if low == 0 or (low > ltp and ltp > 0):
                            low = ltp
                        if close == 0:
                            close = ltp
                    
                    logger.debug(f"Processing direct update for {symbol_name}: LTP={ltp:.2f}, Open={open_price:.2f}, High={high:.2f}, Low={low:.2f}, Close={close:.2f}")
                    
                    if symbol_name in self.market_data:
                        # Store previous values before updating
                        if symbol_name not in self.previous_market_data:
                            self.previous_market_data[symbol_name] = {}
                        self.previous_market_data[symbol_name] = self.market_data[symbol_name].copy()
                        
                        # Get previous data to preserve values not in this update
                        prev_data = self.market_data[symbol_name]
                        prev_close = prev_data.get('close', 0) 
                        
                        # If we still don't have a close value, use previous close
                        if close == 0 and prev_close > 0:
                            close = prev_close
                        
                        # Flag which values have changed since last update
                        changed_fields = {}
                        for field, new_value, prev_field in [
                            ('ltp_changed', ltp, 'ltp'),
                            ('open_changed', open_price, 'open'),
                            ('high_changed', high, 'high'),
                            ('low_changed', low, 'low'),
                            ('volume_changed', volume, 'volume')
                        ]:
                            prev_value = prev_data.get(prev_field, 0)
                            # Use a more sensitive detection threshold - 0.01% change is enough to trigger
                            if new_value > 0 and prev_value > 0:
                                # Calculate percent change
                                change_pct = abs(new_value - prev_value) / prev_value * 100
                                
                                # For price fields, 0.01% change is enough to trigger
                                # For volume, any change is enough
                                threshold = 0.01 if field != 'volume_changed' else 0
                                
                                if change_pct > threshold or (field == 'volume_changed' and new_value != prev_value):
                                    changed_fields[field] = True
                                    # Also track if the change is up or down
                                    if new_value > prev_value:
                                        changed_fields[f"{prev_field}_direction"] = "up"
                                    else:
                                        changed_fields[f"{prev_field}_direction"] = "down"
                                    
                                    # Log the change for debugging
                                    if random.random() > 0.9:  # Only log ~10% of changes to avoid spam
                                        logger.debug(f"Detected change in {symbol_name} {prev_field}: {prev_value} -> {new_value} ({change_pct:.4f}%)")
                        
                        # Update market data - use current values or fall back to previous values
                        self.market_data[symbol_name] = {
                            'symbol': symbol_name,
                            'ltp': ltp if ltp > 0 else prev_data.get('ltp', 0),
                            'open': open_price if open_price > 0 else prev_data.get('open', 0),
                            'high': high if high > 0 else prev_data.get('high', 0),
                            'low': low if low > 0 else prev_data.get('low', 0),
                            'close': close if close > 0 else prev_data.get('close', 0),
                            'volume': volume if volume > 0 else prev_data.get('volume', 0),
                            'timestamp': datetime.now().isoformat(),
                            # Add change indicators
                            **changed_fields,
                            # Store previous values for reference
                            'prev_ltp': prev_data.get('ltp', 0),
                            'prev_open': prev_data.get('open', 0),
                            'prev_high': prev_data.get('high', 0),
                            'prev_low': prev_data.get('low', 0),
                            'prev_volume': prev_data.get('volume', 0)
                        }
                        
                        # Calculate change and change percent
                        from trading_strategy import calculate_change
                        
                        current_price = self.market_data[symbol_name]['ltp']
                        prev_close = self.market_data[symbol_name]['close']
                        
                        change, change_percent = calculate_change(current_price, prev_close)
                        self.market_data[symbol_name]['change'] = change
                        self.market_data[symbol_name]['change_percent'] = change_percent
                        
                        # Preserve trading signal
                        if 'trading_signal' in prev_data:
                            self.market_data[symbol_name]['trading_signal'] = prev_data['trading_signal']
                        
                        # Count how many symbols have non-zero values
                        non_zero_count = sum(1 for item in self.market_data.values() 
                                           if item['ltp'] > 0 or item['open'] > 0 or 
                                              item['high'] > 0 or item['low'] > 0)
                        
                        if non_zero_count % 10 == 0:  # Log every 10 symbols to avoid excessive logging
                            logger.info(f"Updated {non_zero_count} symbols with non-zero values")
                    
                    # Notify callbacks after processing the message
                    self._notify_data_update()
                except Exception as e:
                    logger.error(f"Error processing direct symbol update: {str(e)}")
                    import traceback
                    logger.error(f"Traceback: {traceback.format_exc()}")
            
            elif 'type' in message:
                # Control message
                message_type = message.get('type', '')
                if message_type == 'cn':
                    logger.info(f"WebSocket connection message: {message.get('message', '')}")
                elif message_type == 'sub':
                    logger.info(f"WebSocket subscription message: {message.get('message', '')}")
                else:
                    logger.debug(f"WebSocket control message: {message_type} - {message.get('message', '')}")
            else:
                logger.debug(f"Unhandled WebSocket message format: {json.dumps(message)[:100]}...")
        except Exception as e:
            logger.error(f"Error in WebSocket message handler: {str(e)}")
    
    def _on_ws_error(self, error):
        """
        WebSocket error handler
        
        Args:
            error: Error from WebSocket
        """
        logger.error(f"WebSocket error: {error}")
        self.connected = False
    
    def _on_ws_close(self, message):
        """
        WebSocket close handler
        
        Args:
            message: Close message
        """
        logger.info(f"WebSocket connection closed: {message}")
        self.connected = False
        
        # Attempt to reconnect if still running
        if self.running:
            time.sleep(5)
            logger.info("Attempting to reconnect WebSocket...")
            self.connect_websocket()
    
    def _on_ws_open(self):
        """WebSocket open handler"""
        logger.info("WebSocket connection opened")
        self.connected = True
        
        # Subscribe to all symbols
        data_type = "SymbolUpdate"
        # Import here to avoid circular import
        from nifty50_symbols import get_all_symbols, NIFTY_INDEX
        
        # Get all symbols including NIFTY index
        symbols = get_all_symbols()
        logger.info(f"Subscribing to {len(symbols)} symbols")
        
        # Store active symbols list
        self.active_symbols = symbols
        
        # Create symbol mapping (maps token/id to symbol)
        for symbol in symbols:
            # Extract symbol name without exchange
            if ':' in symbol:
                symbol_name = symbol.split(':')[1]
                self.symbol_mapping[symbol] = symbol_name
                # Also store mapping by just symbol name
                self.symbol_mapping[symbol_name] = symbol_name
        
        logger.debug(f"Created symbol mapping for {len(self.symbol_mapping)} symbols")
        
        try:
            # Subscribe to all symbols at once
            self.ws_client.subscribe(symbols=symbols, data_type=data_type)
            logger.info(f"Successfully subscribed to {len(symbols)} symbols")
            
            # Force initial data fetch for all symbols
            self.fetch_quotes_fallback()
            
            # Keep the connection running
            self.ws_client.keep_running()
        except Exception as e:
            logger.error(f"Error subscribing to symbols: {str(e)}")
    
    def connect_websocket(self):
        """Connect to Fyers WebSocket"""
        try:
            # Get credentials from Fyers client
            client_id = self.fyers.client_id
            access_token = self.fyers.token
            
            if not client_id or not access_token:
                logger.error("Cannot connect WebSocket: No credentials in Fyers client")
                return False
            
            # Format access token as required by WebSocket
            ws_access_token = f"{client_id}:{access_token}"
            logger.info(f"Connecting to Fyers WebSocket with token: {ws_access_token[:10]}...")
            
            # Create WebSocket client
            self.ws_client = data_ws.FyersDataSocket(
                access_token=ws_access_token,
                log_path="",
                litemode=False,
                write_to_file=False,
                reconnect=True,
                on_connect=self._on_ws_open,
                on_close=self._on_ws_close,
                on_error=self._on_ws_error,
                on_message=self._on_ws_message
            )
            
            # Connect WebSocket
            logger.info("Initiating WebSocket connection")
            self.ws_client.connect()
            logger.info("WebSocket connection initiated")
            return True
        except Exception as e:
            logger.error(f"Error connecting to WebSocket: {str(e)}")
            return False
    
    def fetch_historical_data(self):
        """Fetch historical data for all symbols"""
        if not self.enable_history or not self.fyers:
            return
        
        # Only fetch during market hours (9:15 AM to 3:30 PM IST on weekdays)
        now = datetime.now()
        if now.weekday() >= 5:  # Saturday (5) or Sunday (6)
            return
        
        current_time = now.time()
        market_open = datetime.strptime("09:15:00", "%H:%M:%S").time()
        market_close = datetime.strptime("15:30:00", "%H:%M:%S").time()
        
        if not (market_open <= current_time <= market_close):
            return
        
        try:
            # Import here to avoid circular import
            from nifty50_symbols import get_all_symbols
            
            # Define date range for historical data (last 30 days)
            end_date = datetime.now().strftime("%Y-%m-%d")
            start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
            
            for symbol in get_all_symbols():
                try:
                    # Get historical data
                    data = {
                        "symbol": symbol,
                        "resolution": "D",  # Daily resolution
                        "date_format": "1",
                        "range_from": start_date,
                        "range_to": end_date,
                        "cont_flag": "1"
                    }
                    
                    response = self.fyers.history(data)
                    
                    if response and "code" in response and response["code"] == 200:
                        candles = response.get("candles", [])
                        
                        if candles:
                            # Process historical data
                            symbol_name = symbol.split(':')[1]
                            
                            # Convert to dict with lists
                            hist_data = {
                                'timestamp': [item[0] for item in candles],
                                'open': [item[1] for item in candles],
                                'high': [item[2] for item in candles],
                                'low': [item[3] for item in candles],
                                'close': [item[4] for item in candles],
                                'volume': [item[5] for item in candles]
                            }
                            
                            self.historical_data[symbol_name] = hist_data
                            
                            # Update trading signal using the trading strategy instance
                            if symbol_name in self.market_data:
                                self.market_data[symbol_name]['trading_signal'] = self.trading_strategy.get_trading_signal(hist_data)
                    
                    # Sleep to avoid rate limiting
                    time.sleep(0.5)
                except Exception as e:
                    logger.error(f"Error fetching historical data for {symbol}: {str(e)}")
                    time.sleep(1)  # Longer sleep on error
            
            logger.info(f"Historical data updated for {len(self.historical_data)} symbols")
            self._notify_data_update()
        except Exception as e:
            logger.error(f"Error in historical data fetching: {str(e)}")
    
    def _historical_data_worker(self):
        """Worker thread for periodically fetching historical data"""
        while self.running:
            try:
                self.fetch_historical_data()
            except Exception as e:
                logger.error(f"Error in historical data worker: {str(e)}")
            
            # Sleep for 30 minutes before refreshing historical data
            for _ in range(30 * 60):  # 30 minutes in seconds
                if not self.running:
                    break
                time.sleep(1)
    
    def register_data_callback(self, callback):
        """
        Register a callback function for data updates
        
        Args:
            callback (callable): Function to call when data is updated
        """
        if callback not in self.data_callbacks:
            self.data_callbacks.append(callback)
    
    def _notify_data_update(self):
        """Notify all registered callbacks of data updates"""
        # Make a deep copy of the market data with validated values
        data_copy = {}
        
        # Count how many fields have changed
        changed_count = 0
        
        # Process each symbol's data to ensure valid values for numeric fields
        for symbol, values in self.market_data.items():
            try:
                # Ensure numeric values
                ltp = float(values.get('ltp', 0)) if values.get('ltp') is not None else 0
                open_price = float(values.get('open', 0)) if values.get('open') is not None else 0
                high = float(values.get('high', 0)) if values.get('high') is not None else 0
                low = float(values.get('low', 0)) if values.get('low') is not None else 0
                close = float(values.get('close', 0)) if values.get('close') is not None else 0
                volume = int(values.get('volume', 0)) if values.get('volume') is not None else 0
                change = float(values.get('change', 0)) if values.get('change') is not None else 0
                change_percent = float(values.get('change_percent', 0)) if values.get('change_percent') is not None else 0
                
                # Include all symbols, even with zero values
                data_copy[symbol] = {
                    'symbol': symbol,
                    'ltp': ltp,
                    'open': open_price,
                    'high': high,
                    'low': low,
                    'close': close,
                    'volume': volume,
                    'change': change,
                    'change_percent': change_percent,
                    'trading_signal': values.get('trading_signal', 'HOLD'),
                    'timestamp': values.get('timestamp', datetime.now().isoformat()),
                    'is_index': values.get('is_index', False),  # Preserve index flag
                    'market_status': values.get('market_status', 'CLOSED')
                }
                
                # Copy only changed indicators and previous values
                for key, val in values.items():
                    if (key.endswith('_changed') and val) or key.endswith('_direction') or key.startswith('prev_'):
                        data_copy[symbol][key] = val
                
                changed_count += 1
                
            except (ValueError, TypeError) as e:
                logger.error(f"Error validating data for {symbol}: {str(e)}")
                continue
        
        # Create sorted data maintaining the original order
        sorted_data = {}
        
        # First add NIFTY INDEX if it exists
        if 'NIFTY50-INDEX' in data_copy:
            sorted_data['NIFTY50-INDEX'] = data_copy['NIFTY50-INDEX']
        
        # Then add remaining symbols in sorted order
        for symbol in sorted(data_copy.keys()):
            if symbol != 'NIFTY50-INDEX':  # Skip NIFTY as it's already added
                sorted_data[symbol] = data_copy[symbol]
        
        # Log data statistics
        non_zero_values = sum(1 for item in sorted_data.values() 
                           if item['ltp'] > 0 or item['open'] > 0 or item['high'] > 0 or item['low'] > 0)
        logger.info(f"Sending data to clients. Total symbols: {len(sorted_data)}, Non-zero values: {non_zero_values}, Changed values: {changed_count}")
        
        # Send validated and sorted data to callbacks
        for callback in self.data_callbacks:
            try:
                callback(sorted_data)
            except Exception as e:
                logger.error(f"Error in data update callback: {str(e)}")
    
    def start(self):
        """Start fetching market data"""
        if self.running:
            return
        
        if not self.fyers:
            logger.error("Cannot start market data fetcher: No Fyers client")
            return False
        
        logger.info("Starting market data fetcher")
        self.running = True
        
        # Fetch quotes immediately via fallback method to get initial data
        try:
            logger.info("Fetching initial quotes via fallback method")
            success = self.fetch_quotes_fallback()
            if not success:
                logger.warning("Initial fallback quotes fetch did not return valid data")
            else:
                logger.info("Initial quotes fetched successfully")
        except Exception as e:
            logger.error(f"Error fetching initial quotes: {str(e)}")
        
        # Connect to WebSocket after getting initial data
        if not self.connect_websocket():
            logger.error("Failed to connect to WebSocket")
            # Don't stop running - we'll rely on fallback method
            logger.info("Continuing with fallback data fetching only")
        
        # Start historical data worker thread if enabled
        if self.enable_history:
            threading.Thread(
                target=self._historical_data_worker,
                daemon=True
            ).start()
        
        # Start the fallback data worker thread
        threading.Thread(
            target=self._fallback_data_worker,
            daemon=True
        ).start()
        
        return True
    
    def stop(self):
        """Stop the market data fetcher"""
        logger.info("Stopping market data fetcher...")
        self.running = False
        
        # Set shutdown event if available
        if self.shutdown_event:
            self.shutdown_event.set()
        
        # Close WebSocket connection if it exists
        if hasattr(self, 'ws_client') and self.ws_client:
            try:
                self.ws_client.close_connection()
            except Exception as e:
                logger.error(f"Error closing WebSocket: {str(e)}")
        
        logger.info("Market data fetcher stopped")
    
    def get_market_data(self):
        """Get a copy of the current market data"""
        return self.market_data.copy()

    def _update_market_data(self, symbol, data):
        """Update market data for a symbol"""
        try:
            # Import here to avoid circular import
            from trading_strategy import get_trading_signal, calculate_change
            
            # Store previous values for change calculation
            prev_data = self.market_data.get(symbol, {})
            
            # Update market data
            self.market_data[symbol] = {
                'symbol': symbol,
                'ltp': float(data.get('lp', 0)),
                'open': float(data.get('op', 0)),
                'high': float(data.get('hi', 0)),
                'low': float(data.get('lo', 0)),
                'close': float(data.get('pc', 0)),
                'volume': int(data.get('v', 0)),
                'timestamp': datetime.now().isoformat(),
            }
            
            # Calculate changes
            change, change_percent = calculate_change(
                self.market_data[symbol]['ltp'],
                self.market_data[symbol]['close']
            )
            self.market_data[symbol]['change'] = change
            self.market_data[symbol]['change_percent'] = change_percent
            
            # Calculate trading signal using historical data
            if symbol in self.historical_data:
                signal = get_trading_signal(self.historical_data[symbol])
                self.market_data[symbol]['trading_signal'] = signal
            
            # Mark changed values
            if prev_data:
                self.market_data[symbol]['ltp_changed'] = prev_data.get('ltp', 0) != self.market_data[symbol]['ltp']
                self.market_data[symbol]['open_changed'] = prev_data.get('open', 0) != self.market_data[symbol]['open']
                self.market_data[symbol]['high_changed'] = prev_data.get('high', 0) != self.market_data[symbol]['high']
                self.market_data[symbol]['low_changed'] = prev_data.get('low', 0) != self.market_data[symbol]['low']
                self.market_data[symbol]['volume_changed'] = prev_data.get('volume', 0) != self.market_data[symbol]['volume']
                
                # Set change directions
                self.market_data[symbol]['ltp_direction'] = 'up' if self.market_data[symbol]['ltp'] > prev_data.get('ltp', 0) else 'down' if self.market_data[symbol]['ltp'] < prev_data.get('ltp', 0) else None
                self.market_data[symbol]['open_direction'] = 'up' if self.market_data[symbol]['open'] > prev_data.get('open', 0) else 'down' if self.market_data[symbol]['open'] < prev_data.get('open', 0) else None
                self.market_data[symbol]['high_direction'] = 'up' if self.market_data[symbol]['high'] > prev_data.get('high', 0) else 'down' if self.market_data[symbol]['high'] < prev_data.get('high', 0) else None
                self.market_data[symbol]['low_direction'] = 'up' if self.market_data[symbol]['low'] > prev_data.get('low', 0) else 'down' if self.market_data[symbol]['low'] < prev_data.get('low', 0) else None
                self.market_data[symbol]['volume_direction'] = 'up' if self.market_data[symbol]['volume'] > prev_data.get('volume', 0) else 'down' if self.market_data[symbol]['volume'] < prev_data.get('volume', 0) else None
            else:
                # First update, no changes
                self.market_data[symbol]['ltp_changed'] = False
                self.market_data[symbol]['open_changed'] = False
                self.market_data[symbol]['high_changed'] = False
                self.market_data[symbol]['low_changed'] = False
                self.market_data[symbol]['volume_changed'] = False
                self.market_data[symbol]['ltp_direction'] = None
                self.market_data[symbol]['open_direction'] = None
                self.market_data[symbol]['high_direction'] = None
                self.market_data[symbol]['low_direction'] = None
                self.market_data[symbol]['volume_direction'] = None
            
            return True
        except Exception as e:
            logger.error(f"Error updating market data for {symbol}: {str(e)}")
            return False

# Function to create a single instance of the market data fetcher
_MARKET_DATA_FETCHER = None

def get_market_data_fetcher(auth_dir=None, enable_history=True):
    """
    Get or create the market data fetcher instance
    
    Args:
        auth_dir (str): Directory containing authentication files
        enable_history (bool): Whether to enable historical data fetching
        
    Returns:
        MarketDataFetcher: The market data fetcher instance
    """
    global _MARKET_DATA_FETCHER
    if _MARKET_DATA_FETCHER is None:
        _MARKET_DATA_FETCHER = MarketDataFetcher(auth_dir, enable_history)
    return _MARKET_DATA_FETCHER

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s'
    )
    
    fetcher = get_market_data_fetcher()
    
    def print_data(data):
        print(f"\nMarket data updated at {datetime.now()}")
        for symbol, values in list(data.items())[:3]:  # Print first 3 symbols only
            print(f"{symbol}: LTP={values['ltp']}, Change={values['change_percent']}%, Signal={values['trading_signal']}")
    
    fetcher.register_data_callback(print_data)
    
    try:
        # Start fetcher
        if fetcher.start():
            print("Market data fetcher started. Press Ctrl+C to stop.")
            while True:
                time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        fetcher.stop()
        print("Market data fetcher stopped.") 