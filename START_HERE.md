"""
START HERE - Project Navigation Guide

This file helps you navigate the complete Face Recognition project.

═══════════════════════════════════════════════════════════════════════════
FIRST TIME? START HERE
═══════════════════════════════════════════════════════════════════════════

1. Read: README.md (comprehensive guide)
   → Installation, usage, troubleshooting

2. Quick Reference: QUICKSTART.md
   → Validation checklist, commands, settings

3. Review: PROJECT_SUMMARY.py (run this)
   → Full project overview and architecture

4. Install:
   Windows: setup.bat
   macOS/Linux: bash setup.sh

5. Download Model:
   python download_model.py

6. Validate:
   python -m src.camera

═══════════════════════════════════════════════════════════════════════════
FILE GUIDE
═══════════════════════════════════════════════════════════════════════════

DOCUMENTATION:
README.md ........................ Full guide (2000+ lines)
QUICKSTART.md .................... Quick reference card
PROJECT_SUMMARY.py .............. Project overview (run this!)
START_HERE.md .................... This file

SETUP & UTILITIES:
setup.bat / setup.sh ............. Automated environment setup
download_model.py ................ Download ArcFace model
init_project.py .................. Initialize directories
verify.py ........................ Check project integrity

CONFIGURATION:
requirements.txt ................. Python dependencies (pinned)
.gitignore ....................... Git configuration

CORE PIPELINE MODULES (src/):
config.py ........................ All settings (150+ lines)
camera.py ........................ Camera validation
detect.py ........................ Haar face detection
landmarks.py ..................... MediaPipe 5-point extraction
align.py ......................... Face alignment
embed.py ......................... ArcFace embedding extraction
haar_5pt.py ...................... Combined detector (robust)
enroll.py ........................ Enrollment pipeline
evaluate.py ...................... Threshold evaluation
recognize.py ..................... Live recognition

DATA DIRECTORIES (auto-created):
data/db/ ......................... Database (face_db.npz, face_db.json)
data/enroll/ ..................... Enrollment samples per person
data/debug_aligned/ .............. Aligned face crops (debugging)
models/ .......................... ONNX models

═══════════════════════════════════════════════════════════════════════════
QUICK WORKFLOW
═══════════════════════════════════════════════════════════════════════════

1. SETUP (first time only)
   Windows: setup.bat
   macOS/Linux: bash setup.sh

2. DOWNLOAD MODEL (first time only)
   python download_model.py

3. VALIDATE CAMERA (sanity check)
   python -m src.camera

4. VALIDATE EACH STAGE (one by one)
   python -m src.detect
   python -m src.landmarks
   python -m src.align
   python -m src.embed

5. ENROLL PEOPLE (create database)
   python -m src.enroll
   → Enter name, capture 15+ samples, press S

6. FIND OPTIMAL THRESHOLD (tune recognition)
   python -m src.evaluate

7. RUN RECOGNITION (live detection)
   python -m src.recognize
   → Use +/- to adjust threshold, R to reload

═══════════════════════════════════════════════════════════════════════════
KEY SETTINGS (in src/config.py)
═══════════════════════════════════════════════════════════════════════════

Face Detection:
HAAR_SCALE_FACTOR = 1.1 # Lower = stricter
HAAR_MIN_SIZE = (70, 70) # Minimum face size

Recognition:
DEFAULT_DISTANCE_THRESHOLD = 0.34 # Adjust for your needs
TARGET_FAR = 0.01 # Target 1% false accepts

Enrollment:
SAMPLES_NEEDED_FOR_ENROLLMENT = 15 # More = better
AUTO_CAPTURE_INTERVAL_SECONDS = 0.25 # Faster = less control

All settings are documented inline in config.py!

═══════════════════════════════════════════════════════════════════════════
VALIDATION CHECKLIST (Run in order)
═══════════════════════════════════════════════════════════════════════════

✓ python -m src.camera → Live video with FPS
✓ python -m src.detect → Green boxes around faces
✓ python -m src.landmarks → 5 green dots on face
✓ python -m src.align → Two windows: original + aligned
✓ python -m src.embed → Embedding shape (512,)

If all pass, system is ready for enrollment!

═══════════════════════════════════════════════════════════════════════════
TROUBLESHOOTING QUICK LINKS
═══════════════════════════════════════════════════════════════════════════

Camera won't open:
→ See README.md "Troubleshooting" section
→ Check system settings > privacy > camera

Model not found:
→ Run: python download_model.py

Face not detected:
→ Get closer to camera
→ Improve lighting
→ Check with: python -m src.landmarks

Poor recognition:
→ Run: python -m src.evaluate
→ Enroll more samples (15+)
→ Use +/- keys during recognition to tune

Database issues:
→ Delete data/db/face_db.npz
→ Re-enroll from scratch

═══════════════════════════════════════════════════════════════════════════
PROJECT STRUCTURE
═══════════════════════════════════════════════════════════════════════════

face-recognition-5pt/
├── README.md (→ READ THIS FIRST)
├── QUICKSTART.md (→ Quick reference)
├── PROJECT_SUMMARY.py (→ Run: python PROJECT_SUMMARY.py)
├── START_HERE.md (→ This file)
│
├── setup.bat / setup.sh (→ Run first)
├── download_model.py (→ Run second)
│
├── src/ (→ 11 Python modules)
│ ├── config.py (→ All settings here)
│ ├── camera.py, detect.py, landmarks.py, align.py, embed.py
│ ├── haar_5pt.py, enroll.py, evaluate.py, recognize.py
│
├── data/ (→ User data, auto-created)
│ ├── db/ (face database)
│ ├── enroll/ (enrollment samples)
│ └── debug_aligned/ (debugging)
│
├── models/ (→ Download here)
│ └── embedder_arcface.onnx

═══════════════════════════════════════════════════════════════════════════
NEXT STEPS
═══════════════════════════════════════════════════════════════════════════

1. Read README.md (full guide, 2000+ lines)
2. Run setup.bat (Windows) or bash setup.sh (macOS/Linux)
3. Run python download_model.py
4. Run validation checklist (camera, detect, landmarks, etc.)
5. Run python -m src.enroll (add people)
6. Run python -m src.recognize (live recognition)

═══════════════════════════════════════════════════════════════════════════
SYSTEM REQUIREMENTS
═══════════════════════════════════════════════════════════════════════════

✓ Python 3.9+
✓ Webcam (USB or built-in)
✓ ~500 MB disk space
✓ Modern CPU (2015+)
✓ Windows, macOS, or Linux

No GPU required! Runs efficiently on CPU.

═══════════════════════════════════════════════════════════════════════════
KEY FEATURES
═══════════════════════════════════════════════════════════════════════════

✓ Modular - test each stage independently
✓ CPU-first - efficient on standard hardware
✓ Explainable - understand every step
✓ Debuggable - clear error messages
✓ Documented - 2000+ line README
✓ Production-ready - senior-level code
✓ Cross-platform - Windows, macOS, Linux
✓ Easy to extend - add custom modules

═══════════════════════════════════════════════════════════════════════════
PERFORMANCE
═══════════════════════════════════════════════════════════════════════════

Real-time recognition: 8-10 FPS (on modern CPU)
Memory usage: ~300 MB
Database size: <5 MB per 100 people

═══════════════════════════════════════════════════════════════════════════

Questions? Check README.md for comprehensive guide!
Ready to start? Run: python PROJECT_SUMMARY.py

"""

if **name** == "**main**":
print(**doc**)
