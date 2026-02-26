# Troubleshooting: Servo Not Moving When Face Moves

## Quick Diagnosis

Run this command in a separate terminal BEFORE starting face recognition:

```bash
python debug_mqtt_tracking.py
```

Then in another terminal, run:

```bash
python -m src.recognize_with_tracking
```

Move your face left and right. You should see MQTT messages in the debug terminal.

---

## Common Issues & Solutions

### Issue 1: MQTT Not Connected

**Symptoms:**
- Header shows "📡 MQTT: OFF"
- No MQTT messages in debug tool

**Check:**
```bash
# Is mosquitto running?
ps aux | grep mosquitto  # macOS/Linux
tasklist | findstr mosquitto  # Windows
```

**Solution:**
```bash
# Start mosquitto
brew services start mosquitto  # macOS
sudo systemctl start mosquitto  # Linux
net start mosquitto  # Windows
```

---

### Issue 2: Movement Not Detected

**Symptoms:**
- Face is locked (yellow box)
- You move but no "Move Left!" or "Move Right!" appears
- No MQTT messages sent

**Cause:** Movement threshold too high or cooldown too long

**Solution 1: Reduce movement threshold**

Edit `src/activity_logger.py`:

```python
# Find these lines (around line 40):
self.movement_threshold_x = 30  # pixels

# Change to:
self.movement_threshold_x = 15  # More sensitive (lower = more sensitive)
```

**Solution 2: Reduce cooldown**

Edit `src/activity_logger.py`:

```python
# Find this line (around line 42):
self.movement_cooldown = 10  # frames between movement detections

# Change to:
self.movement_cooldown = 5  # Faster response
```

**Solution 3: Check if activity_logger is initialized**

The code only sends movement commands if `activity_logger` exists. Make sure you selected a person to lock when prompted!

---

### Issue 3: MQTT Messages Sent But Servo Doesn't Move

**Symptoms:**
- Debug tool shows messages like "camera/track/command: left"
- ESP8266 Serial Monitor shows "📨 Received [camera/track/command]: left"
- But servo doesn't move

**Check ESP8266 Serial Monitor:**

Look for these messages:
```
📨 Received [camera/track/command]: left
← Moving left to: 85
✓ Reached target position: 85
```

**If you see "Moving left" but servo doesn't move:**

**Hardware Issue:**
1. Check servo is connected to D4 (GPIO2)
2. Check servo power (5V and GND)
3. Try external 5V power for servo
4. Test servo with simple Arduino sketch

**If you DON'T see "Moving left":**

**Software Issue - Check Arduino code:**

The servo might already be at minimum/maximum angle.

Edit `arduino/esp8266_camera_tracker/esp8266_camera_tracker.ino`:

```cpp
// Find these lines (around line 50):
const int SERVO_MIN_ANGLE = 0;
const int SERVO_MAX_ANGLE = 180;
const int SERVO_STEP_SIZE = 5;

// Try larger steps for testing:
const int SERVO_STEP_SIZE = 15;  // Bigger movements
```

---

### Issue 4: Camera Moves Opposite Direction

**Symptoms:**
- You move left, camera moves left (should move right to follow)
- You move right, camera moves right (should move left to follow)

**Solution:**

Edit `src/mqtt_camera_controller.py` (around line 120):

```python
def track_face_movement(self, movement_type: str) -> bool:
    """Send movement command based on detected face movement."""
    if not self.is_connected:
        return False
    
    if movement_type == "move_left":
        return self.move_right()  # SWAP: Change to move_left()
    elif movement_type == "move_right":
        return self.move_left()   # SWAP: Change to move_right()
    
    return False
```

Change to:

```python
def track_face_movement(self, movement_type: str) -> bool:
    """Send movement command based on detected face movement."""
    if not self.is_connected:
        return False
    
    if movement_type == "move_left":
        return self.move_left()   # Same direction
    elif movement_type == "move_right":
        return self.move_right()  # Same direction
    
    return False
```

---

### Issue 5: Tracking Too Slow or Jerky

**Symptoms:**
- Servo moves but very slowly
- Tracking lags behind face movement

**Solution 1: Increase servo speed**

Edit Arduino code:

```cpp
const int MOVEMENT_DELAY = 15;  // Lower = faster

// Change to:
const int MOVEMENT_DELAY = 5;  // Much faster
```

**Solution 2: Increase step size**

```cpp
const int SERVO_STEP_SIZE = 5;  // degrees per command

// Change to:
const int SERVO_STEP_SIZE = 10;  // Bigger steps
```

**Solution 3: Reduce smoothing**

Edit `src/recognize_with_tracking.py` (around line 175):

```python
TRACKING_SMOOTH_WINDOW = 5  # frames to average

# Change to:
TRACKING_SMOOTH_WINDOW = 2  # Less smoothing, faster response
```

---

### Issue 6: No Person Locked

**Symptoms:**
- Face recognition works
- But no yellow box around your face
- Header shows "Lock: (none)"

**Cause:** You didn't select a person to lock

**Solution:**

When you run `python -m src.recognize_with_tracking`, you'll see:

```
Enrolled identities:
  1. Alice
  2. Bob
Lock/track one person? Enter number or name (or Enter for none):
```

**You MUST enter a name or number!** Don't just press Enter.

Type: `1` or `Alice` and press Enter.

---

### Issue 7: Face Not Recognized

**Symptoms:**
- Red box around face (Unknown)
- No tracking happens

**Solution:**

1. **Enroll your face first:**
   ```bash
   python -m src.enroll
   ```

2. **Adjust threshold:**
   - Press `+` key during recognition to increase threshold
   - Or edit `src/config.py`:
     ```python
     DEFAULT_DISTANCE_THRESHOLD = 0.34  # Increase to 0.40 for easier matching
     ```

---

## Step-by-Step Debugging

### Step 1: Verify MQTT Broker

```bash
# Terminal 1: Start mosquitto (if not running)
mosquitto -v

# Terminal 2: Test publish/subscribe
mosquitto_sub -h localhost -t "test" -v

# Terminal 3: Publish test message
mosquitto_pub -h localhost -t "test" -m "hello"
```

You should see "hello" in Terminal 2.

### Step 2: Verify ESP8266 Connection

Open Arduino Serial Monitor (115200 baud). You should see:

```
✓ WiFi connected!
✓ Connected to MQTT broker
✓ Subscribed to topics:
  - camera/track/horizontal
  - camera/track/command
```

If not, check WiFi credentials and MQTT broker IP in Arduino code.

### Step 3: Test Servo Manually

```bash
# Send test commands
mosquitto_pub -h localhost -t "camera/track/command" -m "center"
mosquitto_pub -h localhost -t "camera/track/command" -m "left"
mosquitto_pub -h localhost -t "camera/track/command" -m "right"
mosquitto_pub -h localhost -t "camera/track/horizontal" -m "45"
mosquitto_pub -h localhost -t "camera/track/horizontal" -m "135"
```

Servo should move. If not, hardware issue.

### Step 4: Test Python MQTT Controller

```bash
python -m src.mqtt_camera_controller
```

This runs a test sequence. Servo should move through various positions.

### Step 5: Monitor MQTT During Face Recognition

```bash
# Terminal 1: Monitor MQTT
python debug_mqtt_tracking.py

# Terminal 2: Run face recognition
python -m src.recognize_with_tracking
```

Move your face and watch for messages in Terminal 1.

### Step 6: Check Activity Logger

Add debug prints to see if movement is detected.

Edit `src/activity_logger.py` (around line 100):

```python
def detect_and_log_movement(self, face_center, frame_number):
    movements = []
    
    if self.previous_face_center is None:
        self.previous_face_center = face_center
        return movements
    
    prev_x, prev_y = self.previous_face_center
    curr_x, curr_y = face_center
    
    dx = curr_x - prev_x
    dy = curr_y - prev_y
    
    # ADD THIS DEBUG LINE:
    print(f"DEBUG: dx={dx:.1f}, dy={dy:.1f}, threshold={self.movement_threshold_x}")
    
    # Detect horizontal movement
    if abs(dx) > self.movement_threshold_x:
        # ... rest of code
```

This will show you if movement is being detected.

---

## Quick Fixes Summary

### Make Tracking More Sensitive

**In `src/activity_logger.py`:**
```python
self.movement_threshold_x = 15  # Lower = more sensitive (was 30)
self.movement_cooldown = 5      # Faster response (was 10)
```

### Make Servo Move Faster

**In Arduino code:**
```cpp
const int MOVEMENT_DELAY = 5;   // Faster (was 15)
const int SERVO_STEP_SIZE = 10; // Bigger steps (was 5)
```

### Make Tracking More Responsive

**In `src/recognize_with_tracking.py`:**
```python
TRACKING_SMOOTH_WINDOW = 2  # Less smoothing (was 5)

# And change this line (around line 290):
if last_tracked_x is None or abs(smoothed_x - last_tracked_x) > frame_width * 0.02:
    # Changed from 0.05 to 0.02 (more sensitive)
```

---

## Expected Behavior

When working correctly, you should see:

1. **On screen:**
   - Yellow box around your face
   - "TRACKING" label
   - "Move Left!" or "Move Right!" when you move
   - Servo angle updating in bottom left

2. **In debug terminal:**
   ```
   📨 [camera/track/command] left
   📨 [camera/status] {"angle":85,"target":80,"moving":true}
   📨 [camera/track/command] right
   📨 [camera/status] {"angle":90,"target":95,"moving":true}
   ```

3. **In ESP8266 Serial Monitor:**
   ```
   📨 Received [camera/track/command]: left
   ← Moving left to: 85
   ✓ Reached target position: 85
   ```

4. **Servo motor:**
   - Moves smoothly left/right
   - Follows your face movement
   - Camera stays pointed at you

---

## Still Not Working?

### Create a minimal test:

```python
# test_simple_tracking.py
from src.mqtt_camera_controller import MQTTCameraController
import time

controller = MQTTCameraController()
time.sleep(2)

if controller.is_connected:
    print("Testing movements...")
    
    controller.center()
    time.sleep(2)
    
    for i in range(5):
        print(f"Move left {i+1}")
        controller.move_left()
        time.sleep(1)
    
    for i in range(5):
        print(f"Move right {i+1}")
        controller.move_right()
        time.sleep(1)
    
    controller.center()
    print("Done!")
else:
    print("Not connected to MQTT!")

controller.disconnect()
```

Run: `python test_simple_tracking.py`

If this works but face tracking doesn't, the issue is in movement detection, not MQTT/servo.

---

## Get Help

If still not working, provide:

1. Output from `python debug_mqtt_tracking.py`
2. ESP8266 Serial Monitor output
3. Python terminal output
4. Answer these questions:
   - Does `test_mqtt_system.py` work?
   - Does `python -m src.mqtt_camera_controller` work?
   - Do manual mosquitto_pub commands work?
   - Is your face locked (yellow box)?
   - Do you see "Move Left!" / "Move Right!" on screen?
