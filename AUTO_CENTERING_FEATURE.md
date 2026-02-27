# Auto-Centering Feature

## ✨ Overview

The camera now automatically **centers on the locked person** and **stops moving** once they're in the center zone, providing a stable, focused view.

## 🎯 How It Works

### 1. Search Phase
```
Person lost → Search 0° to 180° → Person found!
```

### 2. Centering Phase
```
Person found → Track to center → Hold in center zone → LOCK!
```

### 3. Locked Phase
```
Person centered → Camera stops moving → Stable view
Person moves out → Resume tracking → Re-center
```

## 📊 Behavior Flow

```
┌─────────────────┐
│  Person Lost    │
│  (Searching)    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Person Found!  │
│  (Start Track)  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Moving to      │
│  Center Zone    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  In Center?     │
└────────┬────────┘
         │ Yes (15 frames)
         ▼
┌─────────────────┐
│  🎯 CENTERED    │
│  & LOCKED!      │
│  (Camera stops) │
└────────┬────────┘
         │
         ▼
    ┌────────────┐
    │ Person     │
    │ Moves Out? │
    └────┬───────┘
         │ Yes
         ▼
    Resume Tracking
```

## 🎮 Visual Indicators

### On Screen Display

**Centering in Progress:**
```
⏳ Centering... (8/15)
```
Shows progress toward lock (8 out of 15 frames)

**Centered and Locked:**
```
🎯 CENTERED & LOCKED (15 frames)
[Green rectangle showing center zone]
```

**Center Zone Indicator:**
- Green rectangle in middle of screen
- "CENTER ZONE" label
- Person must stay within this zone

### Terminal Output

```
✓ Person found - stopping search
🎯 Centering on person...
🎯 Person CENTERED and LOCKED!
   Holding position - person is in center zone
```

If person moves:
```
⚠️  Person moved - resuming tracking
```

## ⚙️ Configuration

### Adjust Center Zone Size

Edit `src/config.py`:

```python
# Default: 10% of frame width
CENTERING_TOLERANCE = 0.1

# Larger zone (easier to center):
CENTERING_TOLERANCE = 0.15  # 15% of frame

# Smaller zone (more precise):
CENTERING_TOLERANCE = 0.05  # 5% of frame
```

### Adjust Lock Time

```python
# Default: 15 frames (~1.5 seconds at 10 FPS)
FRAMES_TO_LOCK_CENTER = 15

# Faster lock:
FRAMES_TO_LOCK_CENTER = 10  # 1 second

# Slower lock (more stable):
FRAMES_TO_LOCK_CENTER = 30  # 3 seconds
```

### Disable Auto-Centering

```python
# Keep tracking continuously without locking
ENABLE_AUTO_CENTERING = False
```

## 📐 Center Zone Calculation

### Frame Width: 640px

```
CENTERING_TOLERANCE = 0.1 (10%)
Center zone = 640 * 0.1 = 64px on each side

Frame layout:
0px                320px (center)              640px
├──────────────────┼──────────────────────────┤
                   │←─ 64px ─┼─ 64px ─→│
                   └─────────┴─────────┘
                      CENTER ZONE
                      (128px wide)
```

### Frame Width: 1920px (HD)

```
CENTERING_TOLERANCE = 0.1 (10%)
Center zone = 1920 * 0.1 = 192px on each side

Frame layout:
0px                960px (center)              1920px
├──────────────────┼──────────────────────────┤
                   │←─ 192px ─┼─ 192px ─→│
                   └──────────┴──────────┘
                      CENTER ZONE
                      (384px wide)
```

## 🎯 Use Cases

### 1. Video Conferencing
```
Person enters → Camera finds them → Centers → Locks
Result: Stable, professional view
```

### 2. Presentation Recording
```
Speaker moves → Camera tracks → Centers on speaker → Holds
Result: Focused on speaker, not constantly moving
```

### 3. Security Monitoring
```
Intruder detected → Camera tracks → Centers → Locks for clear view
Result: Best view for identification
```

### 4. Live Streaming
```
Streamer moves → Camera follows → Centers → Stable shot
Result: Professional, non-jerky video
```

## 🔧 Advanced Configuration

### Very Tight Centering (Precise)

```python
# In src/config.py
CENTERING_TOLERANCE = 0.03  # 3% of frame (very small zone)
FRAMES_TO_LOCK_CENTER = 20   # Hold longer for stability
```

**Result:** Very precise centering, but takes longer to lock

### Loose Centering (Fast)

```python
CENTERING_TOLERANCE = 0.20  # 20% of frame (large zone)
FRAMES_TO_LOCK_CENTER = 5    # Lock quickly
```

**Result:** Fast locking, but less precise centering

### Continuous Tracking (No Lock)

```python
ENABLE_AUTO_CENTERING = False
```

**Result:** Camera always follows, never stops moving

## 📊 Timing Examples

### At 10 FPS (typical)

```
FRAMES_TO_LOCK_CENTER = 15
Lock time = 15 frames / 10 FPS = 1.5 seconds
```

### At 30 FPS (high speed)

```
FRAMES_TO_LOCK_CENTER = 15
Lock time = 15 frames / 30 FPS = 0.5 seconds
```

### Recommended Settings

| FPS | FRAMES_TO_LOCK_CENTER | Lock Time |
|-----|----------------------|-----------|
| 5   | 10                   | 2.0s      |
| 10  | 15                   | 1.5s      |
| 15  | 20                   | 1.3s      |
| 30  | 30                   | 1.0s      |

## 🎬 Complete Workflow Example

### Scenario: Person walks into room

```
Time  Event                          Camera Action
────────────────────────────────────────────────────────
0s    Person enters room             Searching at 45°
2s    Person walks to left           Searching at 90°
4s    Person detected at 30°         Stop search!
5s    Person at 30°                  Move camera to 30°
6s    Person moving to center        Track to 60°
7s    Person at center (320px)       Track to 90°
8s    Person in center zone          Hold... (1/15)
9s    Person still centered          Hold... (8/15)
10s   Person still centered          Hold... (15/15)
10s   🎯 LOCKED!                     Camera stops
15s   Person moves slightly          Still in zone, stay locked
20s   Person moves far left          Exit zone, resume tracking
21s   Person back in center          Re-centering... (5/15)
23s   🎯 LOCKED again!               Camera stops
```

## 🔍 Troubleshooting

### Camera Never Locks

**Problem:** Person keeps moving, never stays centered

**Solutions:**
1. Increase center zone:
   ```python
   CENTERING_TOLERANCE = 0.15  # Larger zone
   ```
2. Reduce lock time:
   ```python
   FRAMES_TO_LOCK_CENTER = 10  # Lock faster
   ```

### Camera Locks Too Easily

**Problem:** Locks even when person not perfectly centered

**Solutions:**
1. Decrease center zone:
   ```python
   CENTERING_TOLERANCE = 0.05  # Smaller zone
   ```
2. Increase lock time:
   ```python
   FRAMES_TO_LOCK_CENTER = 25  # More frames required
   ```

### Camera Keeps Moving

**Problem:** Never stops, always tracking

**Check:**
1. Is person actually in center zone?
2. Is person moving constantly?
3. Check terminal for "CENTERED" message

**Solutions:**
- Increase `CENTERING_TOLERANCE`
- Ask person to stay still for 2 seconds
- Check camera is level (not tilted)

### Person Moves, Camera Doesn't Follow

**Problem:** Locked too tightly, doesn't respond to movement

**Solution:**
```python
# Make zone smaller so person exits faster
CENTERING_TOLERANCE = 0.08
```

## 📈 Performance Impact

### CPU Usage
- **Minimal** - Just distance calculation
- No additional processing

### Servo Movement
- **Reduced** - Servo stops when centered
- Less wear on servo motor
- Lower power consumption when locked

### Network Traffic
- **Reduced** - Fewer MQTT messages when locked
- Only sends commands when tracking

## ✨ Benefits

✅ **Stable View** - Camera stops moving when person centered
✅ **Professional** - No constant camera movement
✅ **Efficient** - Less servo wear, lower power
✅ **Focused** - Best view of locked person
✅ **Automatic** - No manual adjustment needed
✅ **Smart** - Resumes tracking if person moves

## 🎯 Summary

**Search → Find → Center → Lock → Hold**

1. **Search**: Full 180° sweep when person lost
2. **Find**: Detect locked person
3. **Center**: Move camera to center person in frame
4. **Lock**: Hold position when person in center zone
5. **Hold**: Keep camera still while person centered
6. **Resume**: Track again if person moves out of zone

**Your camera now intelligently centers on the person and holds that position!** 🎥🎯
