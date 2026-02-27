# Search Start Position - Always Begins at 0°

## ✅ Fixed: Search Now Starts from 0°

The camera will now **always start searching from 0° (far left)** regardless of where it was pointing before.

## 🔄 Search Behavior

### Before Fix

```
Camera at 169° → Person lost → Search starts at 169° → Only searches 169° to 180°
❌ Incomplete search!
```

### After Fix

```
Camera at 169° → Person lost → Moves to 0° → Searches 0° → 30° → 60° → ... → 180°
✅ Complete 180° search!
```

## 📊 Search Sequence

### Automatic Search (Person Lost)

```
1. Person detected at any angle (e.g., 169°)
2. Person lost
3. Wait 3 seconds (30 frames)
4. 📍 Move to 0° (start position)
5. 🔄 Begin sweep: 0° → 30° → 60° → 90° → 120° → 150° → 180°
6. 🔄 Continue: 180° → 150° → 120° → 90° → 60° → 30° → 0°
7. Repeat until person found
```

### Manual Search (Press 's' Key)

```
1. Camera at any angle (e.g., 135°)
2. Press 's' key
3. 📍 Immediately move to 0° (start position)
4. 🔄 Begin sweep: 0° → 30° → 60° → ... → 180°
5. Continue until 's' pressed again or person found
```

## 🎯 Visual Timeline

```
Time:     0s      3s      5s      7s      9s      11s     13s     15s
          ↓       ↓       ↓       ↓       ↓       ↓       ↓       ↓
Event:    Lost    Wait    →0°     →30°    →60°    →90°    →120°   →150°

Position: 169°    169°    0°      30°     60°     90°     120°    150°
          ↑       ↑       ↑       ↑       ↑       ↑       ↑       ↑
          Person  Waiting Moving  Search  Search  Search  Search  Search
          lost    period  to      begins  continues...
                          start
```

## 📍 Start Position Details

### Why Start at 0°?

1. **Consistent behavior** - Always starts from same position
2. **Full coverage** - Ensures complete 180° sweep
3. **Predictable** - You know where camera will look first
4. **Efficient** - Systematic left-to-right scan

### Alternative Start Positions

If you want to start from a different position, edit `src/recognize_with_tracking.py`:

**Start from center (90°):**
```python
# Around line 370
mqtt_controller.move_to_angle(90)  # Change from 0 to 90
current_search_angle = 90
```

**Start from right (180°):**
```python
mqtt_controller.move_to_angle(180)  # Change from 0 to 180
current_search_angle = 180
```

**Start from last known position:**
```python
# Remove the move_to_angle line
# current_search_angle will use last position
```

## 🎮 Terminal Output

When search starts, you'll see:

```
🔍 Person lost - starting search mode
📍 Moving to start position (0°)...
🔄 Searching... moving to 0°
🔄 Searching... moving to 30°
🔄 Searching... moving to 60°
🔄 Searching... moving to 90°
...
```

## 🔧 Configuration

### Change Start Position

Edit `src/recognize_with_tracking.py` (around line 370 and 490):

```python
# For automatic search
if not search_mode:
    print("🔍 Person lost - starting search mode")
    print("📍 Moving to start position (0°)...")
    search_mode = True
    mqtt_controller.move_to_angle(0)  # ← Change this number
    current_search_angle = 0           # ← And this number
    last_search_time = time.time()

# For manual search (press 's')
if search_mode:
    print("🔍 Search mode: ON (manual)")
    print("📍 Moving to start position (0°)...")
    mqtt_controller.move_to_angle(0)  # ← Change this number
    current_search_angle = 0           # ← And this number
    frames_without_person = FRAMES_BEFORE_SEARCH
    last_search_time = time.time()
```

### Examples

**Start from center:**
```python
mqtt_controller.move_to_angle(90)
current_search_angle = 90
```

**Start from right:**
```python
mqtt_controller.move_to_angle(180)
current_search_angle = 180
```

**Start from 45°:**
```python
mqtt_controller.move_to_angle(45)
current_search_angle = 45
```

## 📊 Search Patterns from Different Start Positions

### Start at 0° (Default - Left to Right)

```
0° → 30° → 60° → 90° → 120° → 150° → 180° → 150° → 120° → 90° → 60° → 30° → 0°
```

### Start at 90° (Center Outward)

```
90° → 120° → 150° → 180° → 150° → 120° → 90° → 60° → 30° → 0° → 30° → 60° → 90°
```

### Start at 180° (Right to Left)

```
180° → 150° → 120° → 90° → 60° → 30° → 0° → 30° → 60° → 90° → 120° → 150° → 180°
```

## 🎯 Use Cases

### Start at 0° (Default)

**Best for:**
- Systematic left-to-right search
- When person usually on the left
- Predictable behavior

### Start at 90° (Center)

**Best for:**
- Person usually in center
- Quick check of main area first
- Balanced search pattern

### Start at 180° (Right)

**Best for:**
- Person usually on the right
- Right-to-left preference
- Reverse search pattern

## 🔍 Troubleshooting

### Camera Still Doesn't Start at 0°

**Check:**
1. Wait for the move to complete (~2 seconds)
2. Check Arduino Serial Monitor for:
   ```
   📨 Received [camera/track/horizontal]: 0
   → Moving to: 0
   ✓ Reached target position: 0
   ```
3. Verify servo can physically reach 0°

**If servo can't reach 0°:**
- Check mechanical limits
- Adjust start position to 10° or 15°
- Check servo calibration

### Search Starts but Skips 0°

**Possible cause:** `SEARCH_INTERVAL` too short

**Solution:**
```python
# In src/recognize_with_tracking.py
SEARCH_INTERVAL = 2.5  # Give more time at start position
```

### Camera Moves to 0° but Doesn't Search

**Check:**
1. Terminal shows "🔄 Searching..." messages
2. MQTT connection is active
3. `search_mode` is True

**Debug:**
Add print statement:
```python
print(f"DEBUG: search_mode={search_mode}, current_angle={current_search_angle}")
```

## ✨ Summary

✅ **Search always starts at 0°** (far left)
✅ **Ensures complete 180° coverage**
✅ **Works for both automatic and manual search**
✅ **Configurable start position**
✅ **Predictable and consistent behavior**

**Now your camera will always perform a complete 180° search starting from 0°!** 🎥🔍
