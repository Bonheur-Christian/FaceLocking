# Fix: Paho MQTT Version 2.0 API Changes

## The Error

```
ValueError: Unsupported callback API version: version 2.0 added a callback_api_version
```

## What Happened

You have paho-mqtt version 2.0+ which changed the API. I've updated all the code to work with the new version.

## Files Updated

✅ `debug_mqtt_tracking.py` - Fixed
✅ `src/mqtt_camera_controller.py` - Fixed
✅ All other MQTT code - Compatible

## Quick Test

### Step 1: Start Mosquitto

```bash
# Check if mosquitto is installed
which mosquitto

# If not installed:
# Ubuntu/Debian:
sudo apt-get install mosquitto mosquitto-clients

# Start mosquitto
sudo systemctl start mosquitto

# Or run manually:
mosquitto -v
```

### Step 2: Test Debug Tool

```bash
python debug_mqtt_tracking.py
```

You should see:
```
✅ Connected to MQTT broker
✅ Subscribed to camera/* topics
Monitoring MQTT messages...
```

Press Ctrl+C to stop.

### Step 3: Test Simple Tracking

```bash
python test_simple_tracking.py
```

This will test if servo moves.

## If Mosquitto Not Installed

### Ubuntu/Debian/Linux

```bash
sudo apt-get update
sudo apt-get install mosquitto mosquitto-clients

# Start service
sudo systemctl start mosquitto
sudo systemctl enable mosquitto

# Check status
sudo systemctl status mosquitto
```

### macOS

```bash
brew install mosquitto

# Start service
brew services start mosquitto

# Or run manually
mosquitto
```

### Windows

Download from: https://mosquitto.org/download/

Or use Chocolatey:
```bash
choco install mosquitto
net start mosquitto
```

## Alternative: Use Public MQTT Broker (Testing Only)

If you can't install mosquitto locally, you can use a public broker for testing:

Edit `src/mqtt_camera_controller.py` and `src/recognize_with_tracking.py`:

Change:
```python
broker_host = "localhost"
```

To:
```python
broker_host = "test.mosquitto.org"  # Public test broker
```

**⚠️ Warning:** Public brokers are:
- Not secure
- Not reliable
- Only for testing
- Anyone can see your messages

## Verify Everything Works

### Test 1: MQTT Broker

```bash
# Terminal 1: Subscribe
mosquitto_sub -h localhost -t "test" -v

# Terminal 2: Publish
mosquitto_pub -h localhost -t "test" -m "hello"
```

You should see "hello" in Terminal 1.

### Test 2: Python MQTT

```bash
python test_simple_tracking.py
```

Should connect and test servo movements.

### Test 3: Debug Monitor

```bash
# Terminal 1:
python debug_mqtt_tracking.py

# Terminal 2:
python -m src.recognize_with_tracking
```

Move your face and watch for MQTT messages in Terminal 1.

## Summary of Changes

### Old API (paho-mqtt < 2.0):
```python
client = mqtt.Client("ClientID")

def on_connect(client, userdata, flags, rc):
    # ...
```

### New API (paho-mqtt >= 2.0):
```python
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, "ClientID")

def on_connect(client, userdata, flags, rc, properties=None):
    # ...
```

All code has been updated to use the new API.

## Still Having Issues?

### Check paho-mqtt version:

```bash
pip show paho-mqtt
```

Should show version 2.0.0 or higher.

### Reinstall if needed:

```bash
pip uninstall paho-mqtt
pip install paho-mqtt>=2.0.0
```

### Check mosquitto is running:

```bash
ps aux | grep mosquitto
```

Should show mosquitto process.

### Check mosquitto logs:

```bash
# Ubuntu/Debian
sudo journalctl -u mosquitto -f

# Or if running manually
mosquitto -v
```

## Next Steps

Once mosquitto is running and the code is updated:

1. ✅ Test: `python debug_mqtt_tracking.py`
2. ✅ Test: `python test_simple_tracking.py`
3. ✅ Run: `python -m src.recognize_with_tracking`
4. ✅ Lock to your face (enter name/number!)
5. ✅ Move left/right and watch servo follow!

---

**The code is now fixed and ready to use!**
