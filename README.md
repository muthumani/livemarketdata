# Live Market Data WebSocket Application

A real-time market data application that displays live stock market data using WebSocket connections. The application provides real-time updates for NIFTY50 stocks and index data.

## Features

- Real-time market data updates via WebSocket
- Live NIFTY50 index and stock data
- Interactive data table with sorting and filtering
- Symbol search functionality
- Trading signal indicators
- Responsive design for all devices
- Dark/Light theme support
- SSL/TLS support for secure connections
- Production-ready deployment configuration

## Tech Stack

### Backend
- Python 3.8+
- Flask
- Flask-SocketIO
- Fyers API
- Python-dotenv
- Gunicorn (Production WSGI server)
- Eventlet (Async server)

### Frontend
- React
- React Data Table Component
- Socket.IO Client
- CSS3 with CSS Variables

## Prerequisites

- Python 3.8 or higher
- Node.js 14 or higher
- npm or yarn
- Fyers Trading Account with API access
- Git
- SSL certificates (for production)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/live-market-data.git
cd live-market-data
```

2. Set up the backend:
```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env
# Edit .env with your Fyers API credentials
```

3. Set up the frontend:
```bash
cd frontend
npm install
```

## Configuration

1. Create a `.env` file in the root directory with the following variables:
```
FYERS_CLIENT_ID=your_client_id
FYERS_SECRET_KEY=your_secret_key
FYERS_REDIRECT_URI=your_redirect_uri
FLASK_ENV=development  # or production
```

2. Update the frontend configuration in `frontend/src/config.js` if needed.

## Running the Application

### Development Mode

1. Start the backend server:
```bash
# From the root directory
python main.py
```

2. Start the frontend development server:
```bash
# From the frontend directory
cd frontend
npm start
```

The application will be available at `http://localhost:3000`

### Production Mode

1. Build the frontend:
```bash
cd frontend
npm run build
```

2. Set environment to production:
```bash
export FLASK_ENV=production  # On Windows: set FLASK_ENV=production
```

3. Start the production server:
```bash
# Using the provided start script
./start.sh  # On Windows: start.bat
```

## Deployment

### GitHub Deployment

1. Initialize Git repository (if not already done):
```bash
git init
git add .
git commit -m "Initial commit"
```

2. Create a new repository on GitHub

3. Push to GitHub:
```bash
git remote add origin https://github.com/yourusername/live-market-data.git
git push -u origin main
```

### Cloud Deployment

#### Option 1: Deploy to Heroku

1. Install Heroku CLI
2. Login to Heroku:
```bash
heroku login
```

3. Create Heroku app:
```bash
heroku create your-app-name
```

4. Set environment variables:
```bash
heroku config:set FYERS_CLIENT_ID=your_client_id
heroku config:set FYERS_SECRET_KEY=your_secret_key
heroku config:set FYERS_REDIRECT_URI=your_redirect_uri
heroku config:set FLASK_ENV=production
```

5. Deploy:
```bash
git push heroku main
```

#### Option 2: Deploy to AWS EC2

1. Launch an EC2 instance (Ubuntu recommended)
2. Install dependencies:
```bash
sudo apt update
sudo apt install python3-pip python3-venv nginx
```

3. Clone repository and set up:
```bash
git clone https://github.com/yourusername/live-market-data.git
cd live-market-data
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

4. Configure Nginx:
```bash
sudo nano /etc/nginx/sites-available/live-market-data
```

Add configuration:
```nginx
server {
    listen 80;
    server_name your_domain.com;

    location / {
        proxy_pass http://localhost:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}
```

5. Enable site and restart Nginx:
```bash
sudo ln -s /etc/nginx/sites-available/live-market-data /etc/nginx/sites-enabled
sudo nginx -t
sudo systemctl restart nginx
```

6. Set up SSL with Let's Encrypt:
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your_domain.com
```

7. Run the application:
```bash
./start.sh
```

## Testing

Run the test suite:
```bash
# Backend tests
python -m pytest

# Frontend tests
cd frontend
npm test
```

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Fyers API for market data
- React Data Table Component for the table implementation
- Flask and Socket.IO for real-time communication 