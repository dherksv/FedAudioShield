@echo off
echo ================================================
echo   Audio Security Platform — Stopping All Services
echo ================================================
echo.
echo Stopping Python processes (API, FL server, Edges, Sensors)...
taskkill /IM python.exe /F 2>nul

echo Stopping Node.js processes (Ganache, Dashboard)...
taskkill /IM node.exe /F 2>nul

echo Stopping Infrastructure (Redis & Mosquitto via Docker)...
wsl docker compose down

echo Stopping uvicorn...
taskkill /IM uvicorn.exe /F 2>nul

echo.
echo ✓ All background services stopped!
echo.
pause
