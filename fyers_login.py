# Apply eventlet monkey patching first if this file is run directly
import eventlet
eventlet.monkey_patch()

from fyers_apiv3 import fyersModel
import webbrowser
import os
import logging
import time
import sys
import subprocess
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

# Set up logging
logger = logging.getLogger(__name__)

"""
In order to get started with Fyers API we would like you to do the following things first.
1. Checkout our API docs :   https://myapi.fyers.in/docs/
2. Create an APP using our API dashboard :   https://myapi.fyers.in/dashboard/
Once you have created an APP you can start using the below SDK
"""

# Default configuration from environment variables
DEFAULT_CONFIG = {
    "redirect_uri": os.getenv("FYERS_REDIRECT_URI", "https://www.google.co.in/"),
    "client_id": os.getenv("FYERS_CLIENT_ID", ""),  # Client_id here refers to APP_ID of the created app
    "secret_key": os.getenv("FYERS_SECRET_KEY", ""),  # app_secret key which you got after creating the app
    "grant_type": "authorization_code",  # The grant_type always has to be "authorization_code"
    "response_type": "code",  # The response_type always has to be "code"
    "state": "sample"  # The state field here acts as a session manager
}

def run_fyers_login(auth_dir=None):
    """
    Run the Fyers login process and save authentication tokens

    Args:
        auth_dir (str): Directory to save authentication files

    Returns:
        bool: True if authentication was successful, False otherwise
    """
    try:
        logger.info("Starting Fyers API authentication process...")

        # Validate required environment variables
        if not DEFAULT_CONFIG["client_id"] or not DEFAULT_CONFIG["secret_key"]:
            logger.error("Missing required environment variables: FYERS_CLIENT_ID and/or FYERS_SECRET_KEY")
            print("\n❌ Error: Missing required environment variables.")
            print("Please set the following environment variables:")
            print("  - FYERS_CLIENT_ID: Your Fyers API client ID")
            print("  - FYERS_SECRET_KEY: Your Fyers API secret key")
            print("  - FYERS_REDIRECT_URI: (Optional) Your redirect URI")
            return False

        # Use default auth directory if none provided
        if auth_dir is None:
            auth_dir = os.path.dirname(os.path.abspath(__file__))

        # Create auth directory if it doesn't exist
        if not os.path.exists(auth_dir):
            os.makedirs(auth_dir)

        # Define file paths
        client_id_file = os.path.join(auth_dir, "fyers_client_id.txt")
        access_token_file = os.path.join(auth_dir, "fyers_access_token.txt")

        # Get configuration
        config = DEFAULT_CONFIG

        # Connect to the sessionModel object
        appSession = fyersModel.SessionModel(
            client_id=config["client_id"],
            redirect_uri=config["redirect_uri"],
            response_type=config["response_type"],
            state=config["state"],
            secret_key=config["secret_key"],
            grant_type=config["grant_type"]
        )

        # Generate auth code URL
        generateTokenUrl = appSession.generate_authcode()

        # Open browser for user to login
        logger.info("Opening browser for Fyers login...")
        print("\n=== Fyers API Authentication ===")
        print("A browser window will open for you to log in to Fyers.")
        print("After logging in, you will be redirected to Google.")
        print("Copy the auth code from the URL and paste it here.")
        print("\nGenerating login URL...")
        
        # Open browser in private/incognito mode with login URL
        try:
            if sys.platform.startswith('win'):                # For Windows
                # Define Windows browser paths and their private mode flags
                windows_browsers = [
                    (r'C:\Program Files\Google Chrome\Application\chrome.exe', '--incognito'),
                    (r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe', '--inprivate'),
                    (r'C:\Users\%USERNAME%\AppData\Local\Programs\Opera\opera.exe', '--private'),
                    (r'C:\Program Files\Opera\opera.exe', '--private'),
                    (r'C:\Program Files (x86)\Opera\opera.exe', '--private')
                ]
                
                # Replace %USERNAME% with actual username in Opera paths
                username = os.getenv('USERNAME')
                windows_browsers = [(path.replace('%USERNAME%', username), flag) if '%USERNAME%' in path else (path, flag) 
                                 for path, flag in windows_browsers]
                
                browser_found = False
                for browser_path, private_flag in windows_browsers:
                    if os.path.exists(browser_path):
                        subprocess.Popen([browser_path, private_flag, generateTokenUrl])
                        browser_found = True
                        logger.info(f"Opening {os.path.basename(browser_path)} in private mode")
                        break
                
                if not browser_found:
                    logger.warning("No compatible browsers found. Using default browser...")
                    webbrowser.open(generateTokenUrl, new=2, autoraise=True)
            else:
                # For other platforms (Unix/Linux/Mac)
                browsers = [
                    ('/usr/bin/google-chrome', '--incognito'),
                    ('/usr/bin/firefox', '--private-window'),
                    ('/usr/bin/microsoft-edge', '--inprivate'),
                    ('/usr/bin/opera', '--private')
                ]
                browser_found = False
                for browser_path, private_flag in browsers:
                    if os.path.exists(browser_path):
                        subprocess.Popen([browser_path, private_flag, generateTokenUrl])
                        browser_found = True
                        break
                
                if not browser_found:
                    logger.warning("No compatible browsers found. Using default browser...")
                    webbrowser.open(generateTokenUrl, new=2, autoraise=True)
        except Exception as e:
            logger.warning(f"Failed to open Chrome in incognito mode: {str(e)}")
            # Fallback to default browser
            webbrowser.open(generateTokenUrl, new=2)

        # Wait for user to login and get auth code
        print("\nPlease login in the private browser window that opened.")
        time.sleep(2)  # Give browser time to open

        # Get auth code from user
        auth_code = input("\nEnter Auth Code from the redirected URL: ")
        if not auth_code:
            logger.error("No auth code provided")
            return False

        # Generate access token
        appSession.set_token(auth_code)
        response = appSession.generate_token()

        # Check if token generation was successful
        if "access_token" not in response:
            logger.error(f"Failed to generate access token: {response}")
            return False

        # Get access token
        access_token = response["access_token"]
        logger.info("Access token generated successfully")

        # Save client ID and access token to files
        with open(client_id_file, 'w') as file:
            file.write(config["client_id"])

        with open(access_token_file, 'w') as file:
            file.write(access_token)

        logger.info(f"Authentication files saved to {auth_dir}")

        # Initialize Fyers model to verify token works
        fyers = fyersModel.FyersModel(
            token=access_token,
            is_async=False,
            client_id=config["client_id"]
        )

        # Test the connection
        profile = fyers.get_profile()
        if "code" in profile and profile["code"] == 200:
            logger.info("Fyers authentication successful!")
            return True
        else:
            logger.error(f"Failed to verify Fyers connection: {profile}")
            return False

    except Exception as e:
        logger.error(f"Error during Fyers authentication: {str(e)}")
        return False

# If this script is run directly, execute the login process
if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s'
    )

    # Run the login process
    success = run_fyers_login()

    if success:
        print("\n✅ Fyers authentication completed successfully!")
    else:
        print("\n❌ Fyers authentication failed. Please try again.")

# Add performance metrics
def track_performance(self):
    self.metrics = {
        'update_count': 0,
        'error_count': 0,
        'avg_processing_time': 0,
        'last_update_time': None
    }

# Add data cleanup for old entries
def cleanup_old_data(self):
    current_time = datetime.now()
    for symbol in list(self.market_data.keys()):
        if (current_time - datetime.fromisoformat(self.market_data[symbol]['timestamp'])).days > 1:
            del self.market_data[symbol]

# Add exponential backoff for reconnection attempts
def connect_websocket(self):
    retry_count = 0
    max_retries = 5
    while retry_count < max_retries:
        try:
            # Existing connection code
            return True
        except Exception as e:
            retry_count += 1
            wait_time = min(30, 2 ** retry_count)  # Exponential backoff
            time.sleep(wait_time)
    return False

def validate_market_data(data):
    required_fields = ['ltp', 'open', 'high', 'low', 'close', 'volume']
    return all(field in data and isinstance(data[field], (int, float)) for field in required_fields)


