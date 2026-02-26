# Quick Commands & Shortcuts

## ✨ Super Simple Commands

Now you can use these short commands instead of the long ones!

### Option 1: Python Script (Recommended)

```bash
python track.py
```

That's it! No need to specify broker IP anymore.

### Option 2: Bash Script (Linux/macOS)

```bash
./track.sh
```

Even shorter!

### Option 3: Direct Module (Still works)

```bash
python -m src.recognize_with_tracking
```

Uses default broker from config.

---

## 🎯 All Available Commands

### Face Recognition with Tracking

```bash
# Simple (uses config defaults)
python track.py

# With fullscreen
python track.py --fullscreen
python track.py -f

# Without MQTT (just recognition)
python track.py --no-mqtt

# Bash shortcut
./track.sh
./track.sh --fullscreen
```

### Face Enrollment

```bash
python -m src.enroll
```

### Testing

```bash
# Test complete system
python test_mqtt_system.py

# Test servo only
python test_simple_tracking.py

# Debug MQTT messages
python debug_mqtt_tracking.py
```

### View Activity Logs

```bash
python src/view_activity_logs.py
```

---

## ⚙️ Configuration

Your broker IP is now saved in `src/config.py`:

```python
MQTT_BROKER_HOST = "157.173.101.159"  # Your broker
MQTT_BROKER_PORT = 1883
```

### Change Broker IP

Edit `src/config.py` and change:

```python
MQTT_BROKER_HOST = "YOUR_NEW_IP"
```

Or use command line (overrides config):

```bash
python -m src.recognize_with_tracking --broker NEW_IP --port 1883
```

---

## 📝 Command Comparison

### Before (Long)

```bash
python -m src.recognize_with_tracking --broker 157.173.101.159 --port 1883
```

### After (Short)

```bash
python track.py
```

**Saved 54 characters!** 🎉

---

## 🚀 Quick Start Workflow

```bash
# 1. Enroll your face (one time)
python -m src.enroll

# 2. Run tracking (every time)
python track.py

# 3. Lock to your face when prompted
# Enter your name or number

# 4. Move around and watch camera follow you!
```

---

## 🎮 Keyboard Controls (During Tracking)

| Key | Action |
|-----|--------|
| q | Quit |
| s | Toggle search mode |
| c | Center camera |
| l | Clear lock |
| f | Fullscreen |
| + | Increase threshold |
| - | Decrease threshold |

---

## 💡 Pro Tips

### Create an Alias (Linux/macOS)

Add to your `~/.bashrc` or `~/.zshrc`:

```bash
alias track='python track.py'
alias track-fs='python track.py --fullscreen'
alias enroll='python -m src.enroll'
```

Then just run:

```bash
track
track-fs
enroll
```

### Create a Desktop Shortcut (Linux)

Create `~/Desktop/FaceTracking.desktop`:

```ini
[Desktop Entry]
Type=Application
Name=Face Tracking
Exec=/path/to/your/project/track.sh
Icon=camera
Terminal=true
```

Double-click to run!

### Create a Batch File (Windows)

Create `track.bat`:

```batch
@echo off
python track.py
pause
```

Double-click to run!

---

## 🔧 Advanced Usage

### Override Config Temporarily

```bash
# Use different broker (doesn't change config)
python -m src.recognize_with_tracking --broker 192.168.1.50

# Disable MQTT temporarily
python track.py --no-mqtt

# Start in fullscreen
python track.py -f
```

### Multiple Configurations

Create different config files:

```bash
# config_home.py
MQTT_BROKER_HOST = "192.168.1.100"

# config_office.py
MQTT_BROKER_HOST = "10.0.0.50"
```

Then copy the one you need:

```bash
cp config_home.py src/config.py
python track.py
```

---

## 📊 Command Reference

### Main Commands

| Command | Description | Example |
|---------|-------------|---------|
| `python track.py` | Run tracking with defaults | `python track.py` |
| `./track.sh` | Bash shortcut | `./track.sh -f` |
| `python -m src.enroll` | Enroll new face | `python -m src.enroll` |
| `python test_mqtt_system.py` | Test everything | `python test_mqtt_system.py` |

### Options

| Option | Short | Description |
|--------|-------|-------------|
| `--fullscreen` | `-f` | Start in fullscreen |
| `--no-mqtt` | - | Disable MQTT tracking |
| `--broker IP` | - | Override broker IP |
| `--port PORT` | - | Override broker port |

### Examples

```bash
# Basic
python track.py

# Fullscreen
python track.py -f
python track.py --fullscreen

# No MQTT
python track.py --no-mqtt

# Custom broker (temporary)
python -m src.recognize_with_tracking --broker 10.0.0.5

# Bash shortcut with fullscreen
./track.sh --fullscreen
```

---

## 🎯 Common Workflows

### Daily Use

```bash
# Just run this every time
python track.py
```

### First Time Setup

```bash
# 1. Enroll
python -m src.enroll

# 2. Test
python test_mqtt_system.py

# 3. Run
python track.py
```

### Troubleshooting

```bash
# Test MQTT
python debug_mqtt_tracking.py

# Test servo
python test_simple_tracking.py

# Check config
cat src/config.py | grep MQTT_BROKER
```

### Development

```bash
# Test without MQTT
python track.py --no-mqtt

# Test with different broker
python -m src.recognize_with_tracking --broker localhost

# View logs
python src/view_activity_logs.py
```

---

## 📱 Mobile/Remote Access

If you want to run from another machine:

```bash
# SSH into your machine
ssh user@your-machine

# Navigate to project
cd /path/to/project

# Run tracking
python track.py
```

---

## 🔄 Update Broker IP

### Method 1: Edit Config (Permanent)

```bash
# Edit the file
nano src/config.py

# Change this line:
MQTT_BROKER_HOST = "NEW_IP_HERE"

# Save and exit (Ctrl+X, Y, Enter)
```

### Method 2: Command Line (Temporary)

```bash
# Just for this run
python -m src.recognize_with_tracking --broker NEW_IP
```

### Method 3: Environment Variable

```bash
# Set environment variable
export MQTT_BROKER="192.168.1.100"

# Modify track.py to read it
# (requires code change)
```

---

## 📚 Related Files

- `track.py` - Python shortcut script
- `track.sh` - Bash shortcut script
- `src/config.py` - Configuration file (broker IP here)
- `src/recognize_with_tracking.py` - Main tracking code

---

## ✨ Summary

**Before:**
```bash
python -m src.recognize_with_tracking --broker 157.173.101.159 --port 1883
```

**After:**
```bash
python track.py
```

**Even Shorter:**
```bash
./track.sh
```

**With Alias:**
```bash
track
```

🎉 **Much easier!**

---

## 🆘 Help

If you forget the commands:

```bash
# Show help
python -m src.recognize_with_tracking --help

# Or just look at this file
cat QUICK_COMMANDS.md
```

---

**Now you can run face tracking with just `python track.py`!** 🚀
