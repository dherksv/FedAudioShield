@echo off
REM start_all.bat — Windows 11 launcher for Audio Security Platform
REM Run from project root: .\scripts\start_all.bat

echo ================================================
echo   Audio Security Platform — Starting Up
echo ================================================
echo.

REM ── Check Python ─────────────────────────────────
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Install from python.org
    pause & exit /b 1
)

REM ── 1. Redis and Mosquitto (via WSL Docker Compose) ─
echo [1/7] Starting Infrastructure via Docker...
wsl docker compose up -d
timeout /t 5 /nobreak >nul

REM ── 2. Ganache ────────────────────────────────────
echo [2/7] Starting Ganache...
start "Ganache" /min cmd /k "ganache --chain.chainId 1337 --port 8545 --wallet.deterministic true"
timeout /t 4 /nobreak >nul

REM ── 3. Deploy contracts ───────────────────────────
echo [3/7] Deploying contracts...
python blockchain\deploy.py
if errorlevel 1 (
    echo ERROR: Contract deployment failed
    pause & exit /b 1
)

REM ── 4. Mosquitto MQTT ────────────────────────────
echo [4/7] Mosquitto is already running via Docker.
timeout /t 1 /nobreak >nul

REM ── 5. Flower FL server ──────────────────────────
echo [5/7] Starting Flower FL server...
start "FL-Server" /min cmd /k "python cloud\fl_server.py"
timeout /t 3 /nobreak >nul

REM ── 6. Edge nodes ────────────────────────────────
echo [6/7] Starting edge nodes...
start "Edge-Home"   /min cmd /k "python edge\edge_node.py --node home"
start "Edge-Car"    /min cmd /k "python edge\edge_node.py --node car"
start "Edge-Office" /min cmd /k "python edge\edge_node.py --node office"
timeout /t 3 /nobreak >nul

REM ── 7. Sensor nodes ──────────────────────────────
echo [7/7] Starting sensor nodes...
start "Sensor-Home"   /min cmd /k "python sensor\sensor_node.py --node home"
start "Sensor-Car"    /min cmd /k "python sensor\sensor_node.py --node car"
start "Sensor-Office" /min cmd /k "python sensor\sensor_node.py --node office"
timeout /t 2 /nobreak >nul

REM ── API server ────────────────────────────────────
echo Starting API server...
start "API-Server" /min cmd /k "python -m uvicorn cloud.api_server:app --host 0.0.0.0 --port 8000"
timeout /t 2 /nobreak >nul

REM ── Dashboard ─────────────────────────────────────
echo Starting dashboard...
start "Dashboard" /min cmd /k "cd dashboard && npm run dev"

echo.
echo ✓ All services started!
echo   Dashboard  →  http://localhost:3000
echo   API        →  http://localhost:8000
echo   Ganache    →  http://localhost:8545
echo   MQTT       →  mqtt://localhost:1883
echo   Flower FL  →  localhost:8080
echo.
echo Close this window to keep services running.
echo To stop all: close each terminal window, or run stop_all.bat
pause
