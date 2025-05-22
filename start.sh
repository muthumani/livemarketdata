#!/bin/bash

# Function to start the backend server
start_backend() {
    echo "Starting backend server..."
    source venv/Scripts/activate
    python main.py
}

# Function to start the frontend server
start_frontend() {
    echo "Starting frontend development server..."
    cd frontend
    npm start
}

# Function to handle script termination
cleanup() {
    echo "Shutting down servers..."
    
    # Kill backend process
    if [ ! -z "$BACKEND_PID" ]; then
        echo "Stopping backend server..."
        kill -TERM $BACKEND_PID 2>/dev/null
        wait $BACKEND_PID 2>/dev/null
    fi
    
    # Kill frontend process
    if [ ! -z "$FRONTEND_PID" ]; then
        echo "Stopping frontend server..."
        kill -TERM $FRONTEND_PID 2>/dev/null
        wait $FRONTEND_PID 2>/dev/null
    fi
    
    echo "Cleanup completed"
    exit 0
}

# Set up trap to catch termination signals
trap cleanup SIGINT SIGTERM

# Start backend in background
start_backend &
BACKEND_PID=$!

# Wait a moment for backend to initialize
sleep 2

# Start frontend
start_frontend &
FRONTEND_PID=$!

# Wait for both processes
wait $BACKEND_PID $FRONTEND_PID 