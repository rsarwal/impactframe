@echo off
REM ImpactFrame Setup Script for Windows
REM Run this once to set up the project

echo ========================================
echo   ImpactFrame Setup
echo ========================================
echo.

REM Check Python
python --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo ERROR: Python not found. Please install Python 3.10+ from python.org
    pause
    exit /b 1
)

echo [1/3] Installing dependencies...
pip install -r requirements.txt

echo.
echo [2/3] Creating .env file...
IF NOT EXIST .env (
    copy .env.example .env
    echo .env file created. Please add your GOOGLE_API_KEY to it.
) ELSE (
    echo .env already exists, skipping.
)

echo.
echo [3/3] Setup complete!
echo.
echo ========================================
echo   NEXT STEPS:
echo   1. Open .env and add your GOOGLE_API_KEY
echo   2. Run: start.bat
echo ========================================
pause
