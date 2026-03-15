@echo off
TITLE AirQ WebGIS - Startup
echo ===================================================
echo     Starting AirQ WebGIS System (Localhost)
echo ===================================================
echo.

echo [1/2] Booting up Python Backend (Uvicorn - FastAPI)...
start "AirQ Backend Server" cmd /c "cd backend && py -m uvicorn main:app --host 127.0.0.1 --port 8000"

echo [2/2] Waiting for server auxiliary systems...
timeout /t 3 /nobreak >nul

echo.
echo Launching Dashboard in default web browser...
start http://127.0.0.1:8000/app/

echo.
echo System Running! Keep the black backend terminal open in the background.
echo You can close this specific window now.
timeout /t 5 >nul
exit
