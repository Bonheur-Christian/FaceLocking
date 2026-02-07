# Live Recognition Window Usage Guide

## Window Display Options

The live recognition window now supports multiple display modes to span your entire screen:

### 1. **Standard Large Window (Default)**

```bash
python -m src.recognize
```

- Opens a large resizable window (1920x1080)
- Can be maximized using your OS window controls
- Can be resized by dragging edges
- Maintains aspect ratio

### 2. **Fullscreen Mode**

#### Option A: Start in Fullscreen

```bash
python -m src.recognize --fullscreen
# or
python -m src.recognize -f
```

#### Option B: Toggle Fullscreen During Use

- Press `f` key while the window is active to toggle fullscreen on/off
- Works whether you started in windowed or fullscreen mode

### 3. **Manual Maximize**

- Click the maximize button in your window manager (Linux/Windows/Mac)
- The window will expand to fill your screen while keeping window decorations

## Window Features

### Window Flags

- `cv2.WINDOW_NORMAL`: Allows resizing and maximizing
- `cv2.WINDOW_KEEPRATIO`: Maintains proper aspect ratio when resizing

### Default Size

- Initial size: 1920x1080 (Full HD)
- Automatically fits content properly

## Keyboard Controls

| Key | Action                                        |
| --- | --------------------------------------------- |
| `f` | Toggle fullscreen mode                        |
| `q` | Quit application                              |
| `r` | Reload face database                          |
| `l` | Clear lock (recognize all people)             |
| `+` | Increase threshold (more permissive matching) |
| `-` | Decrease threshold (stricter matching)        |

## Multi-Person Recognition

The system now supports recognizing **multiple people simultaneously**:

1. **No Lock Mode** (press Enter when prompted):
   - All enrolled people are recognized by name
   - Only names are shown above faces (no rectangles)

2. **Lock Mode** (enter a name/number when prompted):
   - Locked person: Gets green rectangle + landmark squares + detailed info
   - Other recognized people: Only show their names (no rectangle)
   - Unknown people: Red rectangle and "Unknown" label

## Tips for Best Display

1. **For maximum screen coverage**: Start with `--fullscreen` flag or press `f` after starting
2. **For multi-monitor setups**: Drag window to desired monitor before maximizing/fullscreen
3. **For specific size**: Resize window manually after it opens
4. **Aspect ratio**: Window automatically maintains proper aspect ratio

## Troubleshooting

### Window Too Small

- Press `f` for fullscreen
- Or maximize using window manager controls

### Window Not Responding

- Make sure the window has focus (click on it)
- Check that keyboard inputs are being received

### Performance in Fullscreen

- Fullscreen mode may use more GPU resources
- If experiencing lag, try windowed maximized mode instead
