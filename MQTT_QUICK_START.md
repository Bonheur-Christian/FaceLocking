# MQTT Camera Tracking - Quick Start Guide

Get your camera tracking system running in 15 minutes!

## ⚡ Prerequisites

- ✅ Face recognition system already working
- ✅ ESP8266 board (NodeMCU/Wemos D1 Mini)
- ✅ Servo motor (SG90 or similar)
- ✅ USB cable for ESP8266
- ✅ Jumper wires

## 🔌 Step 1: Wire Hardware (2 minutes)

```
ESP8266          Servo Motor
  D4    ────────  Signal (Orange/Yellow)
  5V    ────────  VCC (Red)
  GND   ────────  GND (Brown/Black)
```

Mount camera on servo motor.

## 💻 Step 2: Install Software (3 minutes)

### Install MQTT Broker

**macOS:**
```bash
brew install mosquitto
brew services start mosquitto
```

**Linux:**
```bash
sudo apt-get install mosquitto mosquitto-clients
sudo systemctl start mosquitto
```

**Windows:**
Download from https://mosquitto.org/download/ or:
```bash
choco install mosquitto
net start mosquitto
```

### Install Python Library

```bash
# Activate your virtual environment
source .venv/bin/activate  # macOS/Linux
# or
.venv\Scripts\activate.bat  # Windows

# Install MQTT library
pip install paho-mqtt

# Or run setup script
bash setup_mqtt_tracking.sh  # macOS/Linux
# or
setup_mqtt_tracking.bat  # Windows
```

## 📱 Step 3: Setup ESP8266 (5 minutes)

### Install Arduino IDE

1. Download Arduino IDE 2.0+ from https://www.arduino.cc/en/software
2. Install ESP8266 board support:
   - File → Preferences
   - Add URL: `http://arduino.esp8266.com/stable/package_esp8266com_index.json`
   - Tools → Board → Boards Manager
   - Search "esp8266" and install

3. Install PubSubClient library:
   - Tools → Manage Libraries
   - Search "PubSubClient" and install

### Configure & Upload

1. Open `arduino/esp8266_camera_tracker/esp8266_camera_tracker.ino`

2. Edit WiFi settings:
   ```cpp
   const char* ssid = "YOUR_WIFI_NAME";
   const char* password = "YOUR_WIFI_PASSWORD";
   ```

3. Edit MQTT broker IP (your computer's IP):
   ```cpp
   const char* mqtt_server = "192.168.1.100";  // Change this!
   ```
   
   **Find your IP:**
   - Windows: `ipconfig` (IPv4 Address)
   - macOS: System Preferences → Network
   - Linux: `hostname -I`

4. Upload to ESP8266:
   - Tools → Board → NodeMCU 1.0
   - Tools → Port → (select your ESP8266)
   - Click Upload (→)

5. Open Serial Monitor (115200 baud) and verify connection:
   ```
   ✓ WiFi connected!
   ✓ Connected to MQTT broker
   ```

## 🧪 Step 4: Test System (3 minutes)

```bash
# Test MQTT communication
python test_mqtt_system.py

# Or test manually
python -m src.mqtt_camera_controller
```

You should see the servo motor moving!

## 🎬 Step 5: Run Face Tracking (2 minutes)

```bash
# Make sure you have enrolled faces
python -m src.enroll  # If not done already

# Run recognition with tracking
python -m src.recognize_with_tracking
```

When prompted:
1. Enter the name/number of person to track
2. Move around - camera will follow you!

## 🎮 Controls

| Key | Action |
|-----|--------|
| q | Quit |
| c | Center camera |
| l | Stop tracking |
| f | Fullscreen |

## ❓ Troubleshooting

### ESP8266 won't connect to WiFi
- Use 2.4GHz WiFi (not 5GHz)
- Check SSID and password
- Move closer to router

### MQTT connection fails
- Check broker is running: `ps aux | grep mosquitto`
- Verify IP address is correct
- Try `localhost` if on same machine

### Servo doesn't move
- Check wiring (Signal to D4)
- Check Serial Monitor for errors
- Try external 5V power for servo

### Camera moves wrong direction
Edit `src/mqtt_camera_controller.py`, line ~120:
```python
# Swap these:
if movement_type == "move_left":
    return self.move_left()  # Change to move_right()
```

## 📊 System Architecture

```
┌──────────────────┐
│ Face Recognition │  Detects person moving
│    (Python)      │  Sends MQTT commands
└────────┬─────────┘
         │ WiFi/MQTT
         ▼
┌──────────────────┐
│  MQTT Broker     │  Routes messages
│  (Mosquitto)     │  localhost:1883
└────────┬─────────┘
         │ WiFi/MQTT
         ▼
┌──────────────────┐
│    ESP8266       │  Receives commands
│  + Servo Motor   │  Moves camera
│  + Camera        │  Tracks person
└──────────────────┘
```

## 🎯 What Happens

1. **Face Detection**: Python detects locked person's face
2. **Movement Detection**: Tracks if person moves left/right
3. **MQTT Publish**: Sends movement command via MQTT
4. **ESP8266 Receives**: Gets command over WiFi
5. **Servo Moves**: Adjusts camera angle
6. **Camera Tracks**: Keeps person centered

## 📝 MQTT Topics

| Topic | Purpose | Example |
|-------|---------|---------|
| `camera/track/horizontal` | Set angle | `90` |
| `camera/track/command` | Movement | `left`, `right`, `center` |
| `camera/status` | Current position | `{"angle":90}` |

## 🔧 Fine-Tuning

### Adjust tracking sensitivity

Edit `src/activity_logger.py`:
```python
self.movement_threshold_x = 30  # Lower = more sensitive
```

### Adjust servo speed

Edit Arduino code:
```cpp
const int MOVEMENT_DELAY = 15;  // Lower = faster
const int SERVO_STEP_SIZE = 5;  // Larger = bigger steps
```

### Adjust tracking smoothness

Edit `src/recognize_with_tracking.py`:
```python
TRACKING_SMOOTH_WINDOW = 5  # Higher = smoother but slower
```

## 📚 Full Documentation

- **Complete Guide**: `MQTT_CAMERA_TRACKING.md`
- **Arduino Details**: `arduino/README.md`
- **Activity Logging**: `ACTIVITY_LOGGING.md`

## 🆘 Need Help?

1. Check Serial Monitor on ESP8266
2. Monitor MQTT messages: `mosquitto_sub -h localhost -t "#" -v`
3. Test components separately
4. Read full documentation

## ✨ Next Steps

- Add vertical tracking (tilt servo)
- Implement auto-zoom based on distance
- Add multiple camera support
- Create standalone Raspberry Pi system

---

**You're all set! Enjoy your automated camera tracking! 🎥**
