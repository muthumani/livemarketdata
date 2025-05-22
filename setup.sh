#!/bin/bash

echo "Setting up LiveWebsocket application..."

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/Scripts/activate

# Install Python dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt

# Install Node.js dependencies and build frontend
echo "Installing Node.js dependencies..."
cd frontend
npm install
npm run build
cd ..

# Create static directory if it doesn't exist
if [ ! -d "static" ]; then
    mkdir static
fi

# Copy frontend build files to static directory
echo "Copying frontend build files to static directory..."
cp -r frontend/build/* static/

# Create necessary directories
mkdir -p logs

echo "Setup completed successfully!"
echo
echo "To start the application:"
echo "1. Activate the virtual environment: source venv/Scripts/activate"
echo "2. Run the application: python main.py"
echo 