# Understanding MQTT Status Messages

## What You're Seeing

```
📤 Published Status: {"angle":90,"target":90,"moving":false}
📤 Published Status: {"angle":90,"target":90,"moving":false}
📤 Published Status: {"angle":90,"target":90,"moving":false}
```

## This is Normal! ✅

The ESP8266 publishes its status every second automatically. This is **by design** and indicates:

- ✅ ESP8266 is powered and running
- ✅ WiFi connection is active
- ✅ MQTT connection is established
- ✅ Servo is at position 90° (center)
- ✅ Servo is not currently moving
- ✅ System is ready to receive commands

## Why Does It Do This?

### 1. Heartbeat
Confirms the ESP8266 is alive and connected. If messages stop, you know something is wrong.

### 2. State Monitoring
Python can always query the current servo position without sending a command.

### 3. Debugging
Easy to verify the system is working correctly.

### 4. Reconnection Detection
Helps detect if MQTT connection drops and reconnects.

## Status Message Format

```json
{
  "angle": 90,      // Current servo position (0-180)
  "target": 90,     // Target position servo is moving to
  "moving": false   // true if servo is currently moving
}
```

### Examples

**Servo at rest:**
```json
{"angle":90,"target":90,"moving":false}
```

**Servo moving to new position:**
```json
{"angle":85,"target":45,"moving":true}
```

**Servo reached target:**
```json
{"angle":45,"target":45,"moving":false}
```

## How to Reduce Status Messages

### Option 1: Increase Update Interval (Recommended)

Edit `arduino/esp8266_camera_tracker/esp8266_camera_tracker.ino`:

**Find this line (around line 60):**
```cpp
const unsigned long STATUS_UPDATE_INTERVAL = 1000;  // Send status every 1 second
```

**Change to:**
```cpp
const unsigned long STATUS_UPDATE_INTERVAL = 5000;  // Send status every 5 seconds
```

Or even less frequent:
```cpp
const unsigned long STATUS_UPDATE_INTERVAL = 10000;  // Send status every 10 seconds
```

Then re-upload the code to ESP8266.

### Option 2: Only Publish on Movement

Edit the Arduino code to only publish when servo actually moves.

**Find the `updateServoPosition()` function (around line 180):**

```cpp
void updateServoPosition() {
  if (currentAngle != targetAngle) {
    // Move one degree at a time for smooth motion
    if (currentAngle < targetAngle) {
      currentAngle++;
    } else if (currentAngle > targetAngle) {
      currentAngle--;
    }
    
    cameraServo.write(currentAngle);
    delay(MOVEMENT_DELAY);
    
    // Publish status when movement completes
    if (currentAngle == targetAngle) {
      Serial.print("✓ Reached target position: ");
      Serial.println(currentAngle);
      publishStatus();
    }
  }
}
```

**And in the `loop()` function, comment out periodic publishing:**

```cpp
void loop() {
  // Maintain MQTT connection
  if (!client.connected()) {
    reconnect();
  }
  client.loop();
  
  // Update servo position smoothly
  updateServoPosition();
  
  // OPTIONAL: Comment out these lines to disable periodic status updates
  // unsigned long now = millis();
  // if (now - lastStatusUpdate > STATUS_UPDATE_INTERVAL) {
  //   publishStatus();
  //   lastStatusUpdate = now;
  // }
}
```

Now status will only be published when:
- ESP8266 first connects to MQTT
- Servo completes a movement

### Option 3: Disable Status Publishing Completely

If you don't need status updates at all:

**Comment out all `publishStatus()` calls:**

```cpp
void reconnect() {
  while (!client.connected()) {
    // ... connection code ...
    if (client.connect(clientId.c_str(), mqtt_user, mqtt_password)) {
      // ... subscription code ...
      
      // Publish initial status
      // publishStatus();  // COMMENTED OUT
      
    } else {
      // ... retry code ...
    }
  }
}

void updateServoPosition() {
  if (currentAngle != targetAngle) {
    // ... movement code ...
    
    if (currentAngle == targetAngle) {
      Serial.print("✓ Reached target position: ");
      Serial.println(currentAngle);
      // publishStatus();  // COMMENTED OUT
    }
  }
}

void loop() {
  // ... connection code ...
  
  updateServoPosition();
  
  // Publish status periodically
  // unsigned long now = millis();
  // if (now - lastStatusUpdate > STATUS_UPDATE_INTERVAL) {
  //   publishStatus();  // COMMENTED OUT
  //   lastStatusUpdate = now;
  // }
}
```

## How to Monitor Status Messages

### View in Terminal

```bash
# Subscribe to status topic
mosquitto_sub -h localhost -t "camera/status" -v
```

### View in Python

The Python controller automatically receives and stores status:

```python
from src.mqtt_camera_controller import MQTTCameraController

controller = MQTTCameraController()
time.sleep(2)  # Wait for status update

status = controller.get_status()
print(f"Current angle: {status.get('angle')}°")
print(f"Target angle: {status.get('target')}°")
print(f"Moving: {status.get('moving')}")
```

### Ignore Status Messages

If you don't want to see them in Serial Monitor, you can remove the print statements:

**In `publishStatus()` function:**

```cpp
void publishStatus() {
  String status = "{\"angle\":" + String(currentAngle) + 
                  ",\"target\":" + String(targetAngle) + 
                  ",\"moving\":" + (currentAngle != targetAngle ? "true" : "false") + "}";
  
  client.publish(topic_status, status.c_str());
  // Remove this line to stop printing to Serial Monitor:
  // Serial.print("📤 Published Status: ");
  // Serial.println(status);
}
```

## Recommended Settings

### For Development/Testing
```cpp
const unsigned long STATUS_UPDATE_INTERVAL = 1000;  // 1 second
```
**Why:** Frequent updates help with debugging

### For Production Use
```cpp
const unsigned long STATUS_UPDATE_INTERVAL = 5000;  // 5 seconds
```
**Why:** Less network traffic, still responsive

### For Battery-Powered
```cpp
const unsigned long STATUS_UPDATE_INTERVAL = 30000;  // 30 seconds
```
**Why:** Conserve power

### For Minimal Traffic
Only publish on movement (Option 2 above)
**Why:** Absolute minimum MQTT messages

## Impact on System

### Network Traffic

**1 second interval:**
- ~60 messages per minute
- ~3.6 KB/minute (negligible)

**5 second interval:**
- ~12 messages per minute
- ~720 bytes/minute (very low)

### Power Consumption

Status publishing has **minimal impact** on power:
- MQTT message: <1mA for <10ms
- WiFi already active for receiving commands
- Servo motor uses 100x more power

### Performance

Status updates have **no noticeable impact** on:
- Face recognition speed
- Servo response time
- System responsiveness

## Troubleshooting

### Status Messages Stopped

**Problem:** No status messages appearing

**Possible causes:**
1. ESP8266 lost WiFi connection
2. MQTT broker stopped
3. ESP8266 crashed/reset
4. Power issue

**Solutions:**
1. Check ESP8266 Serial Monitor
2. Verify mosquitto is running: `ps aux | grep mosquitto`
3. Check WiFi signal strength
4. Power cycle ESP8266

### Status Shows Wrong Angle

**Problem:** Status shows angle 90 but servo is at different position

**Possible causes:**
1. Servo lost power during movement
2. Mechanical obstruction
3. Servo calibration issue

**Solutions:**
1. Send center command: `mosquitto_pub -h localhost -t "camera/track/command" -m "center"`
2. Check servo connections
3. Verify servo can move freely

### Too Many Messages

**Problem:** Serial Monitor flooded with status messages

**Solution:** Increase `STATUS_UPDATE_INTERVAL` as shown above

## Summary

✅ **Status messages are normal and useful**
✅ **They confirm system is working**
✅ **You can adjust frequency or disable them**
✅ **They have minimal impact on performance**
✅ **Recommended: Keep them at 5-second interval**

The status messages are a **feature, not a bug**! They help you monitor your system and debug issues.

---

**Quick Fix:** If messages bother you, change `STATUS_UPDATE_INTERVAL` to `5000` (5 seconds) in the Arduino code.
