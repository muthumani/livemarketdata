@echo off
echo Setting up LiveWebsocket application...

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Python is not installed. Please install Python 3.8 or higher.
    exit /b 1
)

REM Create and activate virtual environment
if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Install Python dependencies
echo Installing Python dependencies...
pip install -r requirements.txt

REM Install Node.js dependencies and build frontend
echo Setting up frontend...
cd frontend
call npm install
call npm run build
cd ..

REM Create necessary directories
if not exist static mkdir static
if not exist logs mkdir logs

REM Copy frontend build to static directory
xcopy /E /I /Y frontend\build\* static\

echo Setup completed successfully!
echo.
echo To start the application:
echo 1. Activate the virtual environment: venv\Scripts\activate.bat
echo 2. Run the application: python main.py
echo.
pause 