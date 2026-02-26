# Activity Logging Feature

## Overview

The face recognition system now includes comprehensive activity logging for the **locked person**. When you lock to a specific person during recognition, the system automatically tracks and logs their activities including:

- **Blinks** - Eye blink detection
- **Smiles** - Smile detection
- **Face Movement** - Left/Right/Up/Down movements

All activities are saved with timestamps and can be analyzed later.

## How It Works

### 1. **Start Recognition with Lock**

Run the recognition system and select a person to lock:

```bash
python -m src.recognize
```

When prompted, enter the name or number of the person you want to track:

```
Enrolled identities:
  1. Bonheur
  2. ashraf
  3. calvin
Lock/highlight one person? Enter number or name (or Enter for none): 1
```

### 2. **Activity Tracking**

Once locked, the system automatically:

- ✓ Logs every blink detected
- ✓ Logs every smile detected
- ✓ Tracks face position and detects movements
- ✓ Shows real-time activity statistics on screen
- ✓ Saves all data to CSV file with timestamps

### 3. **Visual Feedback**

On screen you'll see:

**For the Locked Person:**

- Green rectangle around face
- Landmark squares (5 points)
- Name with "(locked)" label
- Confidence bar

**Activity Display:**

- Real-time activity notifications (Blink!, Smile!, Move Left!, etc.)
- Activity statistics panel showing counts:
  - Blinks: X
  - Smiles: Y
  - Move L/R: X/Y
  - Move U/D: X/Y

**For Other Recognized People:**

- Just their name text (no rectangle)

### 4. **Saving Logs**

Logs are automatically saved when you:

- Press `q` to quit
- Press `l` to clear the lock
- Exit the program

## Log Files

Activity logs are saved in: `data/activity_logs/`

For each session, two files are created:

### 1. **CSV Log** (Detailed Timeline)

Format: `{person_name}_{timestamp}_activities.csv`

Example: `Bonheur_20260207_143022_activities.csv`

**Contents:**

```csv
timestamp,frame_number,activity_type,face_center_x,face_center_y,details
2026-02-07T14:30:25.123,150,blink,320.5,240.2,
2026-02-07T14:30:26.456,180,smile,322.1,241.5,
2026-02-07T14:30:28.789,240,move_right,365.8,240.0,dx=43.7px
2026-02-07T14:30:30.012,300,blink,368.2,239.5,
```

**Columns:**

- `timestamp`: ISO format timestamp
- `frame_number`: Frame number in video stream
- `activity_type`: blink, smile, move_left, move_right, move_up, move_down
- `face_center_x`: X coordinate of face center
- `face_center_y`: Y coordinate of face center
- `details`: Additional information (e.g., movement distance)

### 2. **JSON Summary** (Session Overview)

Format: `{person_name}_{timestamp}_summary.json`

Example: `Bonheur_20260207_143022_summary.json`

**Contents:**

```json
{
  "person_name": "Bonheur",
  "session_start": "2026-02-07T14:30:22.123456",
  "session_end": "2026-02-07T14:35:45.789012",
  "session_duration_seconds": 323.67,
  "activity_counts": {
    "blink": 45,
    "smile": 12,
    "move_left": 8,
    "move_right": 7,
    "move_up": 3,
    "move_down": 5
  },
  "total_activities": 80,
  "csv_log": "data/activity_logs/Bonheur_20260207_143022_activities.csv"
}
```

## Viewing and Analyzing Logs

### Interactive Log Viewer

Use the built-in log viewer to analyze saved activities:

```bash
python src/view_activity_logs.py
```

This will:

1. List all available activity logs
2. Show summary information
3. Allow you to view details or analyze patterns

**Example Output:**

```
======================================================================
AVAILABLE ACTIVITY LOGS
======================================================================

1. Bonheur
   Session: 2026-02-07 14:30:22
   Duration: 323.7s
   Total Activities: 80
   Top: blink:45, smile:12, move_left:8

2. ashraf
   Session: 2026-02-07 15:15:10
   Duration: 156.2s
   Total Activities: 42
   Top: blink:28, move_right:10, smile:4

======================================================================

Options:
  Enter a number to view details
  Enter a number followed by 'a' to analyze (e.g., '1a')
  Enter 'q' to quit

Your choice: 1
```

### View Details

Enter a log number to see detailed timeline:

```
ACTIVITY TIMELINE (last 20 activities):
----------------------------------------------------------------------

Time         Frame    Activity        Position             Details
----------------------------------------------------------------------
14:30:25     150      Blink           (320, 240)
14:30:26     180      Smile           (322, 242)
14:30:28     240      Move Right      (366, 240)           dx=43.7px
14:30:30     300      Blink           (368, 240)
...
```

### Analyze Patterns

Enter a log number followed by 'a' (e.g., `1a`) to analyze patterns:

```
ACTIVITY PATTERN ANALYSIS: Bonheur
======================================================================

Activity Breakdown:
  Blink: 45 times (avg interval: 7.2s)
  Smile: 12 times (avg interval: 26.9s)
  Move Left: 8 times (avg interval: 40.5s)
  Move Right: 7 times (avg interval: 46.2s)
  Move Up: 3 times (avg interval: 107.9s)
  Move Down: 5 times (avg interval: 64.7s)

Movement Analysis:
  Total Movements: 23
  Horizontal (L/R): 8/7
  Vertical (U/D): 3/5
======================================================================
```

## Configuration

Activity detection parameters can be adjusted in `src/config.py`:

### Movement Detection

```python
# In activity_logger.py (can be made configurable)
movement_threshold_x = 30  # pixels for horizontal movement
movement_threshold_y = 30  # pixels for vertical movement
movement_cooldown = 10     # frames between detections
```

### Blink Detection

```python
LOCK_EAR_BLINK_THRESHOLD = 0.2  # Eye aspect ratio threshold
```

### Smile Detection

```python
LOCK_SMILE_MOUTH_RATIO = 1.2  # Mouth width expansion ratio
```

### Action Cooldown

```python
LOCK_ACTION_COOLDOWN_FRAMES = 10  # Frames between same action
```

## Use Cases

### 1. **Security Monitoring**

Track person's activities during authentication or security checks.

### 2. **Behavioral Analysis**

Study facial expressions and movements for research purposes.

### 3. **User Engagement**

Monitor user attention and reactions during presentations or demos.

### 4. **Health Monitoring**

Track blink rates and head movements for fatigue detection.

### 5. **Testing & Debugging**

Verify that face detection and tracking work correctly.

## Tips

### For Better Movement Detection

- Keep the camera stable (avoid moving the camera itself)
- Ensure good lighting
- Have person move their head clearly left/right/up/down
- Movement threshold is currently 30 pixels - adjust if needed

### For Better Blink Detection

- Ensure face is well-lit
- Face should be mostly frontal
- MediaPipe Face Mesh must detect eye landmarks

### For Better Smile Detection

- System needs to establish baseline mouth width (takes ~15 frames)
- Clear smiles are detected better than subtle ones
- Ensure good frontal face view

## Keyboard Controls During Recognition

| Key | Action                         |
| --- | ------------------------------ |
| `q` | Quit (saves activity log)      |
| `l` | Clear lock (saves current log) |
| `r` | Reload database                |
| `f` | Toggle fullscreen              |
| `+` | Increase recognition threshold |
| `-` | Decrease recognition threshold |

## File Organization

```
data/
└── activity_logs/
    ├── Bonheur_20260207_143022_activities.csv
    ├── Bonheur_20260207_143022_summary.json
    ├── ashraf_20260207_151510_activities.csv
    ├── ashraf_20260207_151510_summary.json
    └── ...
```

## Troubleshooting

### No Activities Being Logged

**Issue**: Activity log shows 0 activities

**Solutions:**

- Make sure you locked to a specific person (not "none")
- Ensure the locked person is visible in camera
- Check that MediaPipe Face Mesh is working (blink/smile need it)
- Try more obvious actions (clear blinks, big smiles, large movements)

### Movement Not Detected

**Issue**: Face movements not being logged

**Solutions:**

- Move head more significantly (>30 pixels)
- Ensure camera is stable (not moving with the person)
- Check that face stays recognized during movement
- Adjust `movement_threshold_x/y` if needed

### Log Files Not Found

**Issue**: Can't find activity logs

**Solutions:**

- Check `data/activity_logs/` directory
- Ensure you locked to someone (logs only created when locked)
- Make sure program exited properly (logs saved on exit)
- Check file permissions on data directory

## Python API

### Using ActivityLogger Programmatically

```python
from src.activity_logger import ActivityLogger
from src import config

# Create logger for a person
logger = ActivityLogger("person_name", config.ACTIVITY_LOGS_DIR)

# Log an activity
logger.log_activity("blink", frame_number=100,
                   face_center=(320, 240),
                   details="")

# Detect and log movement
movements = logger.detect_and_log_movement((330, 245), frame_number=101)

# Get current statistics
stats = logger.get_statistics()
print(stats)

# Save summary when done
logger.save_summary()
```

## Future Enhancements

Potential additions to the activity logging system:

- [ ] Head pose estimation (looking left/right/up/down)
- [ ] Emotion detection (happy, sad, surprised, etc.)
- [ ] Gaze tracking (where person is looking)
- [ ] Yawn detection
- [ ] Speaking/mouth movement detection
- [ ] Real-time graphs and visualizations
- [ ] Export to different formats (Excel, PDF reports)
- [ ] Multiple person tracking simultaneously
- [ ] Video recording of logged activities

## Privacy & Ethics

**Important Considerations:**

- Activity logging records detailed behavioral data
- Always inform people they are being monitored
- Comply with local privacy laws and regulations
- Store logs securely and delete when no longer needed
- Use only for legitimate purposes
- Consider data minimization principles

---

**Last Updated**: February 7, 2026
