@echo off
REM FocusClass Tkinter - Production Startup Script
REM Automatically checks dependencies and launches the application

title FocusClass Tkinter Launcher
echo.
echo =====================================
echo   FocusClass Tkinter - Startup
echo =====================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8+ from https://python.org
    echo.
    pause
    exit /b 1
)

REM Display Python version
echo Checking Python version...
python --version

REM Check if we're in the correct directory
if not exist "main.py" (
    echo ERROR: main.py not found
    echo Please run this script from the FocusClass tkinter directory
    echo.
    pause
    exit /b 1
)

echo.
echo Checking dependencies...

REM Run setup check first
python setup_check.py
if %errorlevel% neq 0 (
    echo.
    echo DEPENDENCY CHECK FAILED!
    echo Some required packages are missing.
    echo.
    set /p install_deps="Would you like to install missing dependencies? (y/n): "
    if /i "!install_deps!"=="y" (
        echo Installing dependencies...
        python setup_check.py --install
        if %errorlevel% neq 0 (
            echo Failed to install dependencies automatically.
            echo Please run: pip install -r requirements.txt
            echo.
            pause
            exit /b 1
        )
    ) else (
        echo Please install missing dependencies manually and try again.
        echo Run: python setup_check.py --install
        echo.
        pause
        exit /b 1
    )
)

echo.
echo =====================================
echo   Starting FocusClass Tkinter...
echo =====================================
echo.
echo Choose your mode:
echo 1. Launch main application (recommended)
echo 2. Launch teacher mode directly
echo 3. Launch student mode directly
echo 4. Run setup check only
echo 5. Exit
echo.

set /p choice="Enter your choice (1-5): "

if "%choice%"=="1" (
    echo Starting main application...
    python main.py
) else if "%choice%"=="2" (
    echo Starting teacher mode...
    cd src\teacher
    python teacher_app.py
    cd ..\..
) else if "%choice%"=="3" (
    echo Starting student mode...
    cd src\student
    python student_app.py
    cd ..\..
) else if "%choice%"=="4" (
    echo Running setup check...
    python setup_check.py --gui
) else if "%choice%"=="5" (
    echo Goodbye!
    exit /b 0
) else (
    echo Invalid choice. Launching main application...
    python main.py
)

REM Check if application exited with error
if %errorlevel% neq 0 (
    echo.
    echo Application exited with error code %errorlevel%
    echo Check logs\launcher.log for details
    echo.
)

echo.
echo Application closed.
pause