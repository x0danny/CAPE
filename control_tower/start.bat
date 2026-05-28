@echo off
REM ============================================================
REM AABS Control Tower v5.0 - Windows Startup Script
REM ============================================================

echo ============================================================
echo AABS Control Tower v5.0
echo Enterprise Decision Intelligence Platform
echo ============================================================
echo.

REM Check Python
echo [1/4] Checking Python...
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Python not found. Please install Python 3.9+
    pause
    exit /b 1
)
python --version
echo.

REM Create virtual environment if needed
echo [2/4] Setting up virtual environment...
if not exist ".venv" (
    echo Creating virtual environment...
    python -m venv .venv
)
echo Virtual environment ready
echo.

REM Activate virtual environment
call .venv\Scripts\activate.bat

REM Install dependencies
echo [3/4] Installing dependencies...
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt
echo Dependencies installed
echo.

REM Launch application
echo [4/4] Launching AABS Control Tower...
echo.
echo ============================================================
echo Starting server at http://localhost:8501
echo Press Ctrl+C to stop
echo ============================================================
echo.

streamlit run app.py --server.headless true --browser.gatherUsageStats false
