import eventlet
eventlet.monkey_patch()

import os
import logging
import signal
import sys
import threading
import ssl
import time
from flask import Flask, send_from_directory
from flask_socketio import SocketIO
from flask_cors import CORS
from fyers_apiv3 import fyersModel
from market_data_fetcher import MarketDataFetcher
from trading_strategy import TradingStrategy
from fyers_login import run_fyers_login

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Initialize Flask app with static folder pointing to React build directory
app = Flask(__name__, static_folder='frontend/build', static_url_path='')
CORS(app, resources={r"/*": {"origins": "*"}})
socketio = SocketIO(app, 
    cors_allowed_origins="*",
    async_mode='eventlet',
    logger=True,
    engineio_logger=True,
    ping_timeout=60,
    ping_interval=25,
    allow_upgrades=True,
    transports=['websocket', 'polling'],
    max_http_buffer_size=1e8,  # Increase buffer size for large payloads
    async_handlers=True,  # Enable async handlers
    message_queue=None,  # Disable message queue for direct processing
    compression_threshold=1024  # Enable compression for messages larger than 1KB
)

# Global variables
market_data_fetcher = None
trading_strategy = None
shutdown_event = threading.Event()
last_emit_time = 0
EMIT_INTERVAL = 0.1  # Minimum time between emits (100ms)

def graceful_shutdown(signum, frame):
    """Handle graceful shutdown of the application"""
    logger.info("Received shutdown signal. Starting graceful shutdown...")
    shutdown_event.set()
    
    try:
        # Stop market data fetcher
        if market_data_fetcher:
            logger.info("Stopping market data fetcher...")
            market_data_fetcher.stop()
        
        # Close Fyers connection
        if market_data_fetcher and hasattr(market_data_fetcher, 'fyers'):
            logger.info("Closing Fyers connection...")
            try:
                # Fyers client doesn't have a close method, so we just log it
                logger.info("Fyers connection closed")
            except Exception as e:
                logger.error(f"Error closing Fyers connection: {str(e)}")
        
        # Stop SocketIO server
        logger.info("Stopping SocketIO server...")
        socketio.stop()
        
        logger.info("Graceful shutdown completed")
    except Exception as e:
        logger.error(f"Error during shutdown: {str(e)}")
    finally:
        sys.exit(0)

# Register signal handlers
signal.signal(signal.SIGINT, graceful_shutdown)
signal.signal(signal.SIGTERM, graceful_shutdown)

def initialize_fyers():
    """Initialize Fyers API connection and return the client"""
    try:
        # Check if we have valid credentials
        auth_dir = os.path.dirname(os.path.abspath(__file__))
        client_id_file = os.path.join(auth_dir, "fyers_client_id.txt")
        access_token_file = os.path.join(auth_dir, "fyers_access_token.txt")

        # If credentials don't exist or are invalid, run login
        if not (os.path.exists(client_id_file) and os.path.exists(access_token_file)):
            logger.info("No valid credentials found. Starting Fyers login...")
            if not run_fyers_login(auth_dir):
                raise Exception("Fyers login failed")

        # Read credentials
        with open(client_id_file, 'r') as f:
            client_id = f.read().strip()
        with open(access_token_file, 'r') as f:
            access_token = f.read().strip()

        # Initialize Fyers client
        fyers = fyersModel.FyersModel(
            token=access_token,
            is_async=False,
            client_id=client_id
        )

        # Verify connection
        profile = fyers.get_profile()
        if "code" not in profile or profile["code"] != 200:
            logger.warning("Stored credentials invalid. Starting new login...")
            if not run_fyers_login(auth_dir):
                raise Exception("Fyers login failed")
            
            # Read new credentials
            with open(client_id_file, 'r') as f:
                client_id = f.read().strip()
            with open(access_token_file, 'r') as f:
                access_token = f.read().strip()
            
            # Initialize Fyers client with new credentials
            fyers = fyersModel.FyersModel(
                token=access_token,
                is_async=False,
                client_id=client_id
            )

        logger.info("Fyers API initialized successfully")
        return fyers

    except Exception as e:
        logger.error(f"Failed to initialize Fyers API: {str(e)}")
        raise

def emit_market_data(data):
    """Emit market data with rate limiting"""
    global last_emit_time
    current_time = time.time()
    
    # Rate limit emissions
    if current_time - last_emit_time < EMIT_INTERVAL:
        return
        
    try:
        socketio.emit('market_data', {'data': data})
        last_emit_time = current_time
        logger.info(f"Emitted market data update with {len(data)} symbols")
    except Exception as e:
        logger.error(f"Error emitting market data: {str(e)}")

def start_market_data_fetcher(fyers_client):
    """Initialize and start the market data fetcher"""
    global market_data_fetcher, trading_strategy
    
    try:
        # Initialize trading strategy
        trading_strategy = TradingStrategy()
        
        # Initialize market data fetcher
        market_data_fetcher = MarketDataFetcher(
            fyers_client=fyers_client,
            trading_strategy=trading_strategy,
            socketio=socketio,
            shutdown_event=shutdown_event  # Pass shutdown event
        )
        
        # Register callback for market data updates
        market_data_fetcher.register_data_callback(emit_market_data)
        
        # Start market data fetcher
        if not market_data_fetcher.start():
            logger.error("Failed to start market data fetcher")
            return False
            
        logger.info("Market data fetcher started successfully")
        
        # Force initial data fetch
        try:
            logger.info("Forcing initial data fetch")
            market_data_fetcher.fetch_quotes_fallback()
        except Exception as e:
            logger.error(f"Error in initial data fetch: {str(e)}")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to start market data fetcher: {str(e)}")
        raise

def create_ssl_context():
    """Create SSL context for HTTPS"""
    try:
        cert_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'certificates')
        cert_file = os.path.join(cert_path, 'cert.pem')
        key_file = os.path.join(cert_path, 'key.pem')
        
        if not os.path.exists(cert_path):
            os.makedirs(cert_path)
            
        if not (os.path.exists(cert_file) and os.path.exists(key_file)):
            logger.info("Generating self-signed SSL certificates using Python...")
            
            # Generate certificate using Python's cryptography library
            from cryptography import x509
            from cryptography.x509.oid import NameOID
            from cryptography.hazmat.primitives import hashes
            from cryptography.hazmat.primitives import serialization
            from cryptography.hazmat.primitives.asymmetric import rsa
            from datetime import datetime, timedelta
            
            # Generate private key
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048
            )
            
            # Generate public key
            public_key = private_key.public_key()
            
            # Generate certificate
            subject = issuer = x509.Name([
                x509.NameAttribute(NameOID.COMMON_NAME, u"localhost"),
            ])
            
            cert = x509.CertificateBuilder().subject_name(
                subject
            ).issuer_name(
                issuer
            ).public_key(
                public_key
            ).serial_number(
                x509.random_serial_number()
            ).not_valid_before(
                datetime.utcnow()
            ).not_valid_after(
                datetime.utcnow() + timedelta(days=365)
            ).add_extension(
                x509.SubjectAlternativeName([x509.DNSName(u"localhost")]),
                critical=False,
            ).sign(private_key, hashes.SHA256())
            
            # Write certificate
            with open(cert_file, "wb") as f:
                f.write(cert.public_bytes(serialization.Encoding.PEM))
            
            # Write private key
            with open(key_file, "wb") as f:
                f.write(private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption()
                ))
            
            logger.info("Successfully generated self-signed certificate")
        
        # Create SSL context
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(cert_file, key_file)
        return context
    except Exception as e:
        logger.error(f"Failed to create SSL context: {str(e)}")
        return None

@app.route('/')
def index():
    """Serve the React frontend application"""
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/api/market-data')
def get_market_data():
    """API endpoint to get current market data"""
    try:
        if market_data_fetcher:
            data = market_data_fetcher.get_market_data()
            if data:
                return {
                    'status': 'success',
                    'data': data
                }
        return {
            'status': 'error',
            'message': 'Market data not available'
        }, 503
    except Exception as e:
        logger.error(f"Error fetching market data: {str(e)}")
        return {
            'status': 'error',
            'message': str(e)
        }, 500

@app.route('/<path:path>')
def serve_static(path):
    """Serve static files from the React build directory"""
    if os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, 'index.html')

def main():
    """Main entry point for the application"""
    try:
        # Initialize Fyers API
        fyers_client = initialize_fyers()
        
        # Start market data fetcher
        start_market_data_fetcher(fyers_client)
        
        # Start the Flask server
        logger.info("Starting Flask server...")
        if os.environ.get('FLASK_ENV') == 'production':
            # Production mode with SSL
            ssl_context = create_ssl_context()
            if not ssl_context:
                logger.error("Failed to create SSL context. Exiting...")
                return
            socketio.run(
                app, 
                host='0.0.0.0', 
                port=5000, 
                debug=False,
                use_reloader=False,
                ssl_context=ssl_context
            )
        else:
            # Development mode without SSL
            socketio.run(
                app, 
                host='0.0.0.0', 
                port=5000, 
                debug=False,
                use_reloader=False
            )
        
    except Exception as e:
        logger.error(f"Application failed to start: {str(e)}")
        raise
    finally:
        if not shutdown_event.is_set():
            graceful_shutdown(None, None)

if __name__ == "__main__":
    main() 