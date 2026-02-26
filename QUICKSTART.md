# Quick Reference Card

## Installation (One-Time)

### Windows

```batch
setup.bat
python download_model.py
```

### macOS/Linux

```bash
bash setup.sh
python download_model.py
```

---

## Validation Checklist

Run these in order. Each should display green success indicators.

```bash
python -m src.camera        # ✓ Live video with FPS
python -m src.detect        # ✓ Green boxes around faces
python -m src.landmarks     # ✓ 5 green dots on face
python -m src.align         # ✓ Two windows: original + 112×112 aligned
python -m src.embed         # ✓ Embedding shape (512,) and norm ~1.0
```

---

## Usage Pipeline

### 1. Enroll Person

```bash
python -m src.enroll
# > Enter name: Alice
# > Press SPACE to capture (15+ samples)
# > Press S to save
```

### 2. Tune Threshold

```bash
python -m src.evaluate
# Outputs: Recommended threshold based on genuine/impostor distances
```

### 3. Live Recognition

```bash
python -m src.recognize
# > Shows live faces with names
# > Press +/- to adjust threshold
# > Press R to reload database
```

---

## Key Files

| File           | Purpose                                 |
| -------------- | --------------------------------------- |
| `config.py`    | All settings (thresholds, sizes, paths) |
| `camera.py`    | Camera test                             |
| `detect.py`    | Haar face detection                     |
| `landmarks.py` | MediaPipe 5-point extraction            |
| `align.py`     | Geometric alignment to 112×112          |
| `embed.py`     | ArcFace ONNX embedding                  |
| `haar_5pt.py`  | Combined detector (robust)              |
| `enroll.py`    | Create face database                    |
| `evaluate.py`  | Find optimal threshold                  |
| `recognize.py` | Real-time recognition                   |

---

## Database Structure

```
data/
├── db/
│   ├── face_db.npz        ← Embeddings (binary)
│   └── face_db.json       ← Metadata (human-readable)
└── enroll/
    ├── Alice/
    │   ├── 1767874858183.jpg
    │   ├── 1767874859974.jpg
    │   └── ...
    └── Bob/
        ├── 1767874944225.jpg
        └── ...
```

---

## Common Settings

### Adjust in `config.py`:

```python
# Stricter face detection
HAAR_MIN_SIZE = (100, 100)          # Larger minimum face

# More/fewer enrollment samples
SAMPLES_NEEDED_FOR_ENROLLMENT = 10  # Default: 15

# Recognition threshold
DEFAULT_DISTANCE_THRESHOLD = 0.34   # Lower = stricter
# Typical range: 0.25 (strict) to 0.45 (loose)

# Faster auto-capture
AUTO_CAPTURE_INTERVAL_SECONDS = 0.15  # Default: 0.25
```

---

## Troubleshooting

| Problem                | Solution                               |
| ---------------------- | -------------------------------------- |
| Camera won't open      | Check settings > privacy > camera      |
| Face not detected      | Get closer, improve lighting           |
| Poor recognition       | Enroll more samples (15+)              |
| Too many false accepts | Press `-` or lower threshold in config |
| Too many false rejects | Press `+` or raise threshold in config |
| Model not found        | `python download_model.py`             |

---

## Performance Targets

| Stage       | Expected FPS         |
| ----------- | -------------------- |
| Camera      | 30                   |
| Detection   | 20-25                |
| Landmarks   | 20-25                |
| Alignment   | 25-30                |
| Embedding   | **8-12** (slowest)   |
| Recognition | **8-10** (real-time) |

---

## Architecture (Simple)

```
Camera Frame
    ↓
Haar Detection (Bounding box)
    ↓
MediaPipe FaceMesh (5 landmarks)
    ↓
Similarity Transform (Align to 112×112)
    ↓
ArcFace ONNX (512-dim embedding)
    ↓
Cosine Distance to DB
    ↓
Name or "Unknown"
```

---

## Contact & Questions

Refer to **README.md** for:

- Full installation guide
- Detailed troubleshooting
- Educational methodology
- References & papers
- Security & privacy info

---

**Version**: 1.0.0  
**Author**: Gabriel Baziramwabo  
**Last Updated**: January 2026
