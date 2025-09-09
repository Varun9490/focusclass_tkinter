@echo off
echo Starting FocusClass Production Environment...
echo.

:: Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8+ and try again
    pause
    exit /b 1
)

:: Create required directories
if not exist "logs" mkdir logs
if not exist "exports" mkdir exports
if not exist "assets" mkdir assets

:: Check for critical files
if not exist "main.py" (
    echo ERROR: main.py not found
    echo Please run this script from the FocusClass directory
    pause
    exit /b 1
)

:: Clean up any previous port issues
echo Cleaning up previous sessions...
python cleanup_ports.py --auto >nul 2>&1

:: Check dependencies
echo Checking dependencies...
python -c "import websockets, aiohttp, aiosqlite, mss, PIL, psutil, qrcode" >nul 2>&1
if errorlevel 1 (
    echo ERROR: Missing dependencies
    echo Installing required packages...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo Failed to install dependencies
        pause
        exit /b 1
    )
)

:: Set environment variables for production
set FOCUSCLASS_ENV=production
set FOCUSCLASS_LOG_LEVEL=INFO

echo.
echo ================================
echo FocusClass Production Ready
echo ================================
echo.
echo Starting application...
echo.

:: Start the application
python main.py

:: Cleanup on exit
echo.
echo Application closed. Cleaning up...
python cleanup_ports.py --auto >nul 2>&1

echo.
echo Cleanup complete. Press any key to exit.
pause >nul