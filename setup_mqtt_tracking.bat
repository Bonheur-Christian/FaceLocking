@echo off
REM Setup script for MQTT camera tracking (Windows)

echo ==========================================
echo MQTT Camera Tracking Setup
echo ==========================================
echo.

REM Check if virtual environment exists
if not exist ".venv" (
    echo ERROR: Virtual environment not found!
    echo Please run setup.bat first
    pause
    exit /b 1
)

REM Activate virtual environment
echo Activating virtual environment...
call .venv\Scripts\activate.bat

REM Install MQTT library
echo Installing paho-mqtt...
pip install paho-mqtt>=1.6.1

REM Check if mosquitto is installed
echo.
echo Checking for MQTT broker (Mosquitto)...
where mosquitto >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    echo Mosquitto is installed
) else (
    echo WARNING: Mosquitto not found
    echo.
    echo To install Mosquitto on Windows:
    echo   1. Download from: https://mosquitto.org/download/
    echo   2. Or use Chocolatey: choco install mosquitto
    echo   3. Start service: net start mosquitto
    echo.
)

REM Create arduino directory if it doesn't exist
if not exist "arduino" (
    echo Arduino directory already created
)

echo.
echo ==========================================
echo Setup Complete!
echo ==========================================
echo.
echo Next steps:
echo.
echo 1. Install Arduino IDE and ESP8266 support
echo    See: arduino\README.md
echo.
echo 2. Wire up ESP8266 + Servo motor
echo    Servo Signal -^> D4 (GPIO2)
echo    Servo VCC -^> 5V
echo    Servo GND -^> GND
echo.
echo 3. Configure and upload Arduino sketch
echo    File: arduino\esp8266_camera_tracker\esp8266_camera_tracker.ino
echo.
echo 4. Start MQTT broker (if not running):
echo    net start mosquitto
echo.
echo 5. Test MQTT controller:
echo    python -m src.mqtt_camera_controller
echo.
echo 6. Run face recognition with tracking:
echo    python -m src.recognize_with_tracking
echo.
echo Full documentation: MQTT_CAMERA_TRACKING.md
echo.
pause
