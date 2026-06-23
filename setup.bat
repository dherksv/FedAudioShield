@echo off
REM scripts\setup.bat — First time setup on Windows 11
REM Run once before start_all.bat

echo ================================================
echo   Audio Security Platform — First Time Setup
echo ================================================
echo.

REM ── Python dependencies ───────────────────────────
echo [1/4] Installing Python dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: pip install failed
    pause & exit /b 1
)

REM ── Dashboard dependencies ────────────────────────
echo [2/4] Installing dashboard dependencies...
cd dashboard
npm install
cd ..

REM ── Audio sample directories ─────────────────────
echo [3/4] Creating audio sample directories...
mkdir audio_samples\home   2>nul
mkdir audio_samples\car    2>nul
mkdir audio_samples\office 2>nul
mkdir models               2>nul
mkdir blockchain           2>nul

REM ── MQTT passwords ───────────────────────────────
echo [4/4] Generating MQTT passwords...
REM Requires mosquitto_passwd in PATH (installed with Mosquitto)
mosquitto_passwd -b mosquitto\passwords.txt sensor    sensorpass
mosquitto_passwd -b mosquitto\passwords.txt edge      edgesecret
mosquitto_passwd -b mosquitto\passwords.txt healthcheck healthcheck
if errorlevel 1 (
    echo WARNING: mosquitto_passwd not found.
    echo Download Mosquitto from https://mosquitto.org/download/
    echo After install, re-run this script.
)

echo.
echo ✓ Setup complete!
echo.
echo Next steps:
echo   1. Start Redis  : download from https://github.com/microsoftarchive/redis/releases
echo   2. Start Ganache: npm install -g ganache
echo   3. Install Mosquitto from https://mosquitto.org/download/
echo   4. Run: scripts\start_all.bat
echo.
echo Optional: drop .wav/.mp3 files into audio_samples\home\, audio_samples\car\, audio_samples\office\
pause
