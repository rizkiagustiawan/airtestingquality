@echo off
TITLE AirQ WebGIS - Startup
echo ===================================================
echo     Starting AirQ WebGIS System (Localhost)
echo ===================================================
echo.

set "ROOT_DIR=%~dp0"
set "BACKEND_DIR=%ROOT_DIR%backend"
set "PYTHON_EXE=%BACKEND_DIR%\.venv\Scripts\python.exe"

if not exist "%PYTHON_EXE%" (
    echo [ERROR] Virtual environment Python not found:
    echo         %PYTHON_EXE%
    echo.
    echo Create it first with:
    echo     cd "%BACKEND_DIR%"
    echo     python -m venv .venv
    echo     .\.venv\Scripts\python.exe -m pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)

echo [1/2] Booting up Python Backend (Uvicorn)...
echo (Synchronous Mode - No Redis Required)
start "AirQ Backend Server" cmd /k "cd /d \"%BACKEND_DIR%\" && \"%PYTHON_EXE%\" -m uvicorn main:app --host 127.0.0.1 --port 8000"

echo [2/2] Waiting for systems to initialize...
timeout /t 5 /nobreak >nul

echo.
echo Launching Dashboard in default web browser...
start http://127.0.0.1:8000/app/

echo.
echo System Running! 
echo Keep the Backend window open in the background.
echo.
timeout /t 5 >nul
exit
