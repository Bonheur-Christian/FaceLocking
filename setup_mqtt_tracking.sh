#!/bin/bash
# Setup script for MQTT camera tracking (macOS/Linux)

echo "=========================================="
echo "MQTT Camera Tracking Setup"
echo "=========================================="
echo ""

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "❌ Virtual environment not found!"
    echo "Please run setup.sh first"
    exit 1
fi

# Activate virtual environment
echo "📦 Activating virtual environment..."
source .venv/bin/activate

# Install MQTT library
echo "📥 Installing paho-mqtt..."
pip install paho-mqtt>=1.6.1

# Check if mosquitto is installed
echo ""
echo "🔍 Checking for MQTT broker (Mosquitto)..."
if command -v mosquitto &> /dev/null; then
    echo "✅ Mosquitto is installed"
    MOSQUITTO_VERSION=$(mosquitto -h 2>&1 | head -n 1)
    echo "   Version: $MOSQUITTO_VERSION"
else
    echo "⚠️  Mosquitto not found"
    echo ""
    echo "To install Mosquitto:"
    echo ""
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "  macOS (Homebrew):"
        echo "    brew install mosquitto"
        echo "    brew services start mosquitto"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        echo "  Ubuntu/Debian:"
        echo "    sudo apt-get update"
        echo "    sudo apt-get install mosquitto mosquitto-clients"
        echo "    sudo systemctl start mosquitto"
        echo ""
        echo "  Fedora/RHEL:"
        echo "    sudo dnf install mosquitto"
        echo "    sudo systemctl start mosquitto"
    fi
    echo ""
fi

# Create arduino directory if it doesn't exist
if [ ! -d "arduino" ]; then
    echo "📁 Arduino directory already created"
fi

echo ""
echo "=========================================="
echo "✅ Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo ""
echo "1. Install Arduino IDE and ESP8266 support"
echo "   See: arduino/README.md"
echo ""
echo "2. Wire up ESP8266 + Servo motor"
echo "   Servo Signal → D4 (GPIO2)"
echo "   Servo VCC → 5V"
echo "   Servo GND → GND"
echo ""
echo "3. Configure and upload Arduino sketch"
echo "   File: arduino/esp8266_camera_tracker/esp8266_camera_tracker.ino"
echo ""
echo "4. Start MQTT broker (if not running):"
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "   brew services start mosquitto"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo "   sudo systemctl start mosquitto"
fi
echo ""
echo "5. Test MQTT controller:"
echo "   python -m src.mqtt_camera_controller"
echo ""
echo "6. Run face recognition with tracking:"
echo "   python -m src.recognize_with_tracking"
echo ""
echo "📖 Full documentation: MQTT_CAMERA_TRACKING.md"
echo ""
