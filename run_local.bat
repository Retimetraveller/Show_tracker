@echo off
title VFX Tracker - Local Test
echo ============================================
echo  VFX Tracker - Local Test
echo ============================================
echo.

echo [1] Checking app.py syntax...
python -c "import app" 2>nul
if errorlevel 1 (
    echo ❌ Syntax error in app.py - fix it first!
    pause
    exit /b
)
echo ✅ Syntax OK.
echo.

echo [2] Starting local server...
echo.
echo ✅ Server running at: http://127.0.0.1:5000
echo.
echo Press Ctrl+C to stop the server when done.
echo.
echo ============================================
echo.

python app.py