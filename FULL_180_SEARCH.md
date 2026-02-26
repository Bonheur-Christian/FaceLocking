# Full 180° Search Mode

## ✅ Updated Search Pattern

Your camera now performs a **complete 180-degree sweep** when searching for the locked person!

## 🔄 Search Pattern

### Positions (12 total)

```
0° → 30° → 60° → 90° → 120° → 150° → 180° → 150° → 120° → 90° → 60° → 30° → 0° (repeat)
```

### Visual Representation

```
    0°                    90°                    180°
    ↓                      ↓                      ↓
    ◄──────────────────────┼──────────────────────►
    Far Left            Center              Far Right
```

### Coverage

- **Full horizontal sweep**: 0° to 180°
- **12 positions**: Every 30 degrees
- **Bidirectional**: Sweeps left-to-right, then right-to-left
- **Continuous**: Repeats until person found

## ⏱️ Timing

- **Wait before search**: 3 seconds (30 frames)
- **Time at each position**: 2 seconds
- **Movement time**: ~0.5 seconds between positions
- **Complete cycle**: ~24 seconds

### Timeline Example

```
0s:   Person lost
3s:   Search starts → Move to 0°
5.5s: At 0° (holding)
8s:   Move to 30°
10.5s: At 30° (holding)
13s:  Move to 60°
...
27s:  Back to 0° (cycle complete, repeat)
```

## 🎯 How It Works

1. **Person detected** → Normal tracking
2. **Person lost** → Counter starts
3. **After 3 seconds** → Search mode activates
4. **Camera sweeps** → 0° → 30° → 60° → ... → 180°
5. **Continues back** → 180° → 150° → 120° → ... → 0°
6. **Person found** → Search stops, tracking resumes
7. **Not found** → Pattern repeats

## 🎮 Controls

| Action | Key | Result |
|--------|-----|--------|
| Manual search | s | Start/stop search immediately |
| Center camera | c | Stop search, return to 90° |
| Quit | q | Exit and save logs |

## 📊 Visual Feedback

### On Screen

```
🔍 SEARCHING... (45 frames)
Servo: 60°
```

### Terminal

```
🔍 Person lost - starting search mode
🔄 Searching... moving to 0°
🔄 Searching... moving to 30°
🔄 Searching... moving to 60°
🔄 Searching... moving to 90°
🔄 Searching... moving to 120°
🔄 Searching... moving to 150°
🔄 Searching... moving to 180°
🔄 Searching... moving to 150°
...
✓ Person found - stopping search
```

### Arduino Serial Monitor

```
📨 Received [camera/track/horizontal]: 0
→ Moving to: 0
✓ Reached target position: 0
📨 Received [camera/track/horizontal]: 30
→ Moving to: 30
✓ Reached target position: 30
...
```

## ⚙️ Configuration

### Change Search Speed

**Faster (1 second per position):**
```python
# In src/recognize_with_tracking.py
SEARCH_INTERVAL = 1.0  # Was 2.0
```

**Slower (3 seconds per position):**
```python
SEARCH_INTERVAL = 3.0  # Was 2.0
```

### Change Search Pattern

**Fewer positions (faster sweep):**
```python
# In src/mqtt_camera_controller.py
sweep_positions = [0, 45, 90, 135, 180, 90]  # 6 positions
```

**More positions (thorough sweep):**
```python
sweep_positions = [0, 15, 30, 45, 60, 75, 90, 105, 120, 135, 150, 165, 180, 
                   165, 150, 135, 120, 105, 90, 75, 60, 45, 30, 15]  # 24 positions
```

**Quick 3-position scan:**
```python
sweep_positions = [0, 90, 180, 90]  # Just left, center, right
```

### Start Search Faster

```python
# In src/recognize_with_tracking.py
FRAMES_BEFORE_SEARCH = 10  # Start after 1 second (was 30)
```

### Start Search Slower

```python
FRAMES_BEFORE_SEARCH = 60  # Start after 6 seconds (was 30)
```

## 🚀 Try It Now!

```bash
python -m src.recognize_with_tracking --broker YOUR_BROKER_IP
```

1. Lock to your face
2. Walk to the far left (0°)
3. Wait 3 seconds
4. Watch camera sweep from 0° all the way to 180°
5. Walk to the far right (180°)
6. Camera will find you!

## 📈 Performance

- **Coverage**: 100% of 180° field of view
- **Search time**: 24 seconds per complete cycle
- **Detection rate**: High (checks 12 positions)
- **Power usage**: Moderate (servo moves frequently)

## 💡 Tips

### For Large Rooms

Use full sweep with more positions:
```python
sweep_positions = [0, 20, 40, 60, 80, 100, 120, 140, 160, 180, 
                   160, 140, 120, 100, 80, 60, 40, 20]
```

### For Small Rooms

Use limited range:
```python
sweep_positions = [45, 60, 75, 90, 105, 120, 135, 120, 105, 90, 75, 60]
```

### For Fast Response

Reduce interval and positions:
```python
SEARCH_INTERVAL = 0.5  # 0.5 seconds
sweep_positions = [0, 60, 120, 180, 120, 60]  # 6 positions
```

## 🔍 Troubleshooting

### Search Too Slow

**Problem**: Takes too long to find person

**Solutions:**
1. Reduce `SEARCH_INTERVAL` to 1.0 second
2. Use fewer positions: `[0, 45, 90, 135, 180, 90]`
3. Increase servo speed in Arduino code

### Search Too Fast

**Problem**: Camera moves too quickly, jerky

**Solutions:**
1. Increase `SEARCH_INTERVAL` to 3.0 seconds
2. Reduce servo speed in Arduino code
3. Add more positions for smoother motion

### Doesn't Cover Full Range

**Problem**: Servo doesn't reach 0° or 180°

**Check:**
1. Arduino code servo limits:
   ```cpp
   const int SERVO_MIN_ANGLE = 0;
   const int SERVO_MAX_ANGLE = 180;
   ```
2. Mechanical limits of your servo
3. Camera mount doesn't block movement

### Person Not Found During Search

**Problem**: Camera searches but doesn't detect person

**Solutions:**
1. Improve lighting
2. Adjust recognition threshold (press '+' key)
3. Re-enroll the person
4. Check person is within camera's field of view

## 📚 Related Documentation

- **Search Mode Details**: `SEARCH_MODE_FEATURE.md`
- **Visual Diagram**: `SEARCH_PATTERN_DIAGRAM.txt`
- **All Features**: `FEATURES_SUMMARY.md`
- **Setup Guide**: `MQTT_CAMERA_TRACKING.md`

## ✨ Summary

✅ **Full 180° coverage** - No blind spots in front of camera
✅ **12 positions** - Thorough search pattern
✅ **Bidirectional sweep** - Efficient scanning
✅ **Configurable** - Adjust speed and positions
✅ **Automatic** - Starts 3 seconds after person lost
✅ **Manual control** - Press 's' to trigger anytime

**Your camera now searches the entire 180° field of view to find the locked person!** 🎥🔍
