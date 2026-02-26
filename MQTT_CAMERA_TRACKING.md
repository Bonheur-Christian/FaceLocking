# MQTT Camera Tracking Setup Guide

This guide explains how to set up ESP8266 with a servo motor to track a person's face using MQTT communication.

## 📋 Overview

The system consists of three main components:

1. **ESP8266 + Servo Motor** - Physical camera tracking hardware
2. **MQTT Broker** - Message broker for communication (Mosquitto)
3. **Python Face Recognition** - Detects face movement and sends tracking commands

```
┌─────────────────────┐
│  Face Recognition   │
│  (Python)           │
│  - Detects face     │
│  - Tracks movement  │
└──────────┬──────────┘
           │ MQTT
           │ (WiFi)
           ▼
┌─────────────────────┐
│   MQTT Broker       │
│   (Mosquitto)       │
│   - localhost:1883  │
└──────────┬──────────┘
           │ MQTT
           │ (WiFi)
           ▼
┌─────────────────────┐
│   ESP8266           │
│   + Servo Motor     │
│   + Camera          │
│   - Moves camera    │
└─────────────────────┘
```

---

## 🛠️ Hardware Requirements

### Components Needed

1. **ESP8266 Board** (any of these):
   - NodeMCU v1.0 (recommended)
   - Wemos D1 Mini
   - ESP-12E/F module

2. **Servo Motor**:
   - SG90 (9g micro servo) - recommended
   - MG90S (metal gear version)
   - Any 180° servo motor (5V)

3. **Camera**:
   - USB webcam
   - Laptop built-in camera

4. **Power Supply**:
   - USB cable for ESP8266
   - External 5V power for servo (if needed)

5. **Miscellaneous**:
   - Jumper wires
   - Breadboard (optional)
   - Camera mount/bracket

### Wiring Diagram

```
ESP8266 (NodeMCU)          Servo Motor
┌─────────────┐           ┌──────────┐
│             │           │          │
│         D4  ├───────────┤ Signal   │ (Orange/Yellow wire)
│             │           │          │
│         5V  ├───────────┤ VCC      │ (Red wire)
│             │           │          │
│         GND ├───────────┤ GND      │ (Brown/Black wire)
│             │           │          │
└─────────────┘           └──────────┘

Camera mounted on servo motor
```

**Important Notes:**
- Connect servo VCC to 5V (or external 5V if servo draws too much current)
- Connect servo GND to ESP8266 GND
- Connect servo Signal to D4 (GPIO2)
- If servo jitters, use external 5V power supply

---

## 💻 Software Requirements

### 1. Arduino IDE Setup

**Install Arduino IDE:**
- Download from: https://www.arduino.cc/en/software
- Install version 2.0 or later

**Add ESP8266 Board Support:**

1. Open Arduino IDE
2. Go to: File → Preferences
3. Add to "Additional Board Manager URLs":
   ```
   http://arduino.esp8266.com/stable/package_esp8266com_index.json
   ```
4. Go to: Tools → Board → Boards Manager
5. Search for "esp8266"
6. Install "esp8266 by ESP8266 Community"

**Install Required Libraries:**

1. Go to: Tools → Manage Libraries
2. Install these libraries:
   - **PubSubClient** by Nick O'Leary (for MQTT)
   - **Servo** (usually pre-installed)

### 2. MQTT Broker Setup

**Option A: Install Mosquitto (Recommended)**

**Windows:**
```bash
# Download installer from: https://mosquitto.org/download/
# Or use Chocolatey:
choco install mosquitto

# Start broker:
net start mosquitto
```

**macOS:**
```bash
# Install via Homebrew:
brew install mosquitto

# Start broker:
brew services start mosquitto

# Or run manually:
mosquitto
```

**Linux:**
```bash
# Ubuntu/Debian:
sudo apt-get update
sudo apt-get install mosquitto mosquitto-clients

# Start broker:
sudo systemctl start mosquitto
sudo systemctl enable mosquitto

# Check status:
sudo systemctl status mosquitto
```

**Option B: Use Public MQTT Broker (Testing Only)**
- broker.hivemq.com:1883
- test.mosquitto.org:1883
- **Warning:** Not secure, only for testing!

### 3. Python Dependencies

```bash
# Activate your virtual environment first
source .venv/bin/activate  # macOS/Linux
# or
.venv\Scripts\activate.bat  # Windows

# Install MQTT library
pip install paho-mqtt
```

---

## 🚀 Step-by-Step Setup

### Step 1: Configure Arduino Code

1. Open `arduino/esp8266_camera_tracker/esp8266_camera_tracker.ino`

2. **Modify WiFi credentials:**
   ```cpp
   const char* ssid = "YOUR_WIFI_SSID";
   const char* password = "YOUR_WIFI_PASSWORD";
   ```

3. **Set MQTT broker IP:**
   ```cpp
   const char* mqtt_server = "192.168.1.100";  // Your computer's IP
   ```
   
   **Find your computer's IP:**
   - Windows: `ipconfig` (look for IPv4 Address)
   - macOS: `ifconfig | grep inet` or System Preferences → Network
   - Linux: `ip addr show` or `hostname -I`

4. **Adjust servo settings (if needed):**
   ```cpp
   const int SERVO_PIN = D4;           // Change if using different pin
   const int SERVO_MIN_ANGLE = 0;      // Minimum servo angle
   const int SERVO_MAX_ANGLE = 180;    // Maximum servo angle
   const int SERVO_CENTER_ANGLE = 90;  // Center position
   ```

### Step 2: Upload to ESP8266

1. Connect ESP8266 to computer via USB
2. In Arduino IDE:
   - Tools → Board → ESP8266 Boards → NodeMCU 1.0 (ESP-12E Module)
   - Tools → Port → Select your ESP8266 port (COM3, /dev/ttyUSB0, etc.)
   - Tools → Upload Speed → 115200
3. Click Upload button (→)
4. Wait for "Done uploading"
5. Open Serial Monitor (Tools → Serial Monitor)
6. Set baud rate to 115200
7. You should see:
   ```
   ESP8266 Camera Tracker Starting
   ✓ Servo initialized at center position
   Connecting to WiFi: YourNetwork
   ✓ WiFi connected!
   ✓ Connected to MQTT broker
   ```

### Step 3: Test MQTT Communication

**Test with command line tools:**

```bash
# Subscribe to camera status (in one terminal):
mosquitto_sub -h localhost -t "camera/status" -v

# Send test commands (in another terminal):
mosquitto_pub -h localhost -t "camera/track/command" -m "center"
mosquitto_pub -h localhost -t "camera/track/command" -m "left"
mosquitto_pub -h localhost -t "camera/track/command" -m "right"
mosquitto_pub -h localhost -t "camera/track/horizontal" -m "45"
mosquitto_pub -h localhost -t "camera/track/horizontal" -m "135"
```

**Test with Python:**

```bash
python -m src.mqtt_camera_controller
```

This will run a test sequence moving the camera.

### Step 4: Run Face Recognition with Tracking

```bash
# Make sure you have enrolled faces first:
python -m src.enroll

# Run recognition with MQTT tracking:
python -m src.recognize_with_tracking

# Or specify custom broker:
python -m src.recognize_with_tracking --broker 192.168.1.100 --port 1883

# Disable MQTT (normal recognition):
python -m src.recognize_with_tracking --no-mqtt
```

**When prompted:**
- Enter the name/number of the person to track
- The camera will automatically follow that person's face!

---

## 🎮 Usage

### Controls

| Key | Action |
|-----|--------|
| q | Quit |
| r | Reload database |
| l | Clear lock (stop tracking) |
| c | Center camera |
| f | Toggle fullscreen |
| + | Increase recognition threshold |
| - | Decrease recognition threshold |

### How It Works

1. **Face Detection**: System detects and recognizes faces
2. **Lock Person**: You select one person to track
3. **Movement Detection**: System detects when person moves left/right
4. **MQTT Command**: Sends movement command to ESP8266
5. **Servo Movement**: ESP8266 moves servo to track person
6. **Continuous Tracking**: Camera follows person smoothly

### MQTT Topics

| Topic | Direction | Purpose | Example |
|-------|-----------|---------|---------|
| `camera/track/horizontal` | Python → ESP8266 | Set specific angle (0-180°) | `90` |
| `camera/track/command` | Python → ESP8266 | Movement command | `left`, `right`, `center` |
| `camera/status` | ESP8266 → Python | Current servo position | `{"angle":90,"target":90,"moving":false}` |

---

## 🔧 Troubleshooting

### ESP8266 Issues

**Problem: ESP8266 won't connect to WiFi**
- Check SSID and password are correct
- Make sure WiFi is 2.4GHz (ESP8266 doesn't support 5GHz)
- Move ESP8266 closer to router
- Check Serial Monitor for error messages

**Problem: Servo jitters or doesn't move smoothly**
- Use external 5V power supply for servo
- Add capacitor (100µF) across servo power pins
- Reduce `MOVEMENT_DELAY` in code
- Check servo connections

**Problem: ESP8266 keeps resetting**
- Servo drawing too much current - use external power
- Check power supply is adequate (500mA+)
- Add decoupling capacitor near ESP8266

### MQTT Issues

**Problem: Cannot connect to MQTT broker**
- Check broker is running: `mosquitto -v`
- Check firewall allows port 1883
- Verify IP address is correct
- Try `localhost` if on same machine

**Problem: Messages not received**
- Check topic names match exactly (case-sensitive)
- Verify ESP8266 is subscribed to correct topics
- Use `mosquitto_sub` to monitor all topics: `mosquitto_sub -h localhost -t "#" -v`

### Python Issues

**Problem: `paho-mqtt` not found**
```bash
pip install paho-mqtt
```

**Problem: MQTT controller shows "not connected"**
- Start MQTT broker first
- Check broker IP and port
- Look for firewall blocking connection

### Camera Tracking Issues

**Problem: Camera moves opposite direction**
- In `mqtt_camera_controller.py`, swap left/right in `track_face_movement()`:
  ```python
  if movement_type == "move_left":
      return self.move_left()  # Changed from move_right()
  elif movement_type == "move_right":
      return self.move_right()  # Changed from move_left()
  ```

**Problem: Camera moves too much/too little**
- Adjust `SERVO_STEP_SIZE` in Arduino code (default: 5 degrees)
- Adjust `movement_threshold_x` in `activity_logger.py` (default: 30 pixels)
- Modify `TRACKING_SMOOTH_WINDOW` in `recognize_with_tracking.py` (default: 5 frames)

**Problem: Tracking is jerky**
- Increase `TRACKING_SMOOTH_WINDOW` for smoother tracking
- Increase `MOVEMENT_DELAY` in Arduino code
- Reduce detection sensitivity

---

## 📊 Configuration Options

### Arduino Configuration

Edit `esp8266_camera_tracker.ino`:

```cpp
// Servo movement speed
const int MOVEMENT_DELAY = 15;  // Lower = faster, Higher = smoother

// Movement step size
const int SERVO_STEP_SIZE = 5;  // Degrees per command

// Status update frequency
const unsigned long STATUS_UPDATE_INTERVAL = 1000;  // milliseconds
```

### Python Configuration

Edit `src/mqtt_camera_controller.py`:

```python
# Servo angle limits
self.min_angle = 0
self.max_angle = 180
self.center_angle = 90
```

Edit `src/recognize_with_tracking.py`:

```python
# Tracking smoothing (higher = smoother but slower response)
TRACKING_SMOOTH_WINDOW = 5

# Minimum movement to trigger update (as fraction of frame width)
if abs(smoothed_x - last_tracked_x) > frame_width * 0.05:  # 5% of width
```

Edit `src/activity_logger.py`:

```python
# Movement detection thresholds
self.movement_threshold_x = 30  # pixels
self.movement_threshold_y = 30  # pixels
self.movement_cooldown = 10     # frames between detections
```

---

## 🎯 Advanced Features

### Two-Axis Tracking (Pan & Tilt)

To add vertical tracking (tilt), you'll need:
- Second servo motor for tilt
- Modified Arduino code for two servos
- Updated Python code to send vertical commands

**Arduino modifications:**
```cpp
Servo panServo;   // Horizontal
Servo tiltServo;  // Vertical

const int PAN_PIN = D4;
const int TILT_PIN = D5;

// In setup():
panServo.attach(PAN_PIN);
tiltServo.attach(TILT_PIN);
```

### Security Features

**Add MQTT authentication:**

Arduino:
```cpp
const char* mqtt_user = "camera_tracker";
const char* mqtt_password = "secure_password";
```

Mosquitto config (`/etc/mosquitto/mosquitto.conf`):
```
allow_anonymous false
password_file /etc/mosquitto/passwd
```

Create password file:
```bash
mosquitto_passwd -c /etc/mosquitto/passwd camera_tracker
```

### Remote Access

**Use MQTT over TLS:**
- Generate SSL certificates
- Configure Mosquitto for TLS (port 8883)
- Update Arduino and Python code with certificates

---

## 📝 Example Use Cases

1. **Security Camera**: Track intruders automatically
2. **Video Conferencing**: Keep speaker centered in frame
3. **Live Streaming**: Follow presenter during talks
4. **Pet Monitoring**: Track your pet's movements
5. **Research**: Study human behavior and attention

---

## 🔗 Resources

- **ESP8266 Documentation**: https://arduino-esp8266.readthedocs.io/
- **MQTT Protocol**: https://mqtt.org/
- **Mosquitto Broker**: https://mosquitto.org/
- **Paho MQTT Python**: https://www.eclipse.org/paho/index.php?page=clients/python/index.php
- **Servo Library**: https://www.arduino.cc/reference/en/libraries/servo/

---

## 🆘 Getting Help

If you encounter issues:

1. Check Serial Monitor output from ESP8266
2. Monitor MQTT messages: `mosquitto_sub -h localhost -t "#" -v`
3. Test each component separately:
   - Servo movement (Arduino only)
   - MQTT connection (command line tools)
   - Face recognition (without MQTT)
4. Check this documentation's troubleshooting section

---

## ✨ Next Steps

After successful setup:

1. **Calibrate tracking**: Adjust thresholds for your environment
2. **Add tilt servo**: Enable vertical tracking
3. **Improve smoothing**: Fine-tune tracking parameters
4. **Add features**: Distance-based zoom, auto-framing, etc.
5. **Deploy**: Create standalone system with Raspberry Pi

---

**Happy tracking! 🎥📹**
