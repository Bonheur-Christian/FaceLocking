"""
Project initialization script.
Creates complete directory structure from scratch.
Safe to run multiple times.
"""

from pathlib import Path
from src import config


def init_project():
    """Create complete project structure."""
    print("\n" + "="*70)
    print(" Face Recognition Project Initialization")
    print("="*70)
    
    # Create all directories
    print("\nCreating directory structure...")
    config.ensure_dirs()
    
    # Verify structure
    required_dirs = [
        config.DATA_DIR,
        config.DB_DIR,
        config.ENROLL_DIR,
        config.DEBUG_ALIGNED_DIR,
        config.MODELS_DIR,
    ]
    
    for d in required_dirs:
        if d.exists():
            print(f"  ✓ {d}")
        else:
            print(f"  ERROR: {d} not created")
            return False
    
    print("\n" + "="*70)
    print(" ✓ Project initialization complete!")
    print("="*70)
    print("\nProject structure:")
    print("""
face-recognition-5pt/
├── data/
│   ├── db/              (database files)
│   ├── enroll/          (enrollment images)
│   └── debug_aligned/   (aligned face crops)
├── models/              (ONNX models)
├── src/                 (Python modules)
├── requirements.txt
├── setup.bat / setup.sh
└── README.md
    """)
    
    print("\nNext steps:")
    print("  1. Run: python download_model.py")
    print("  2. Run: python -m src.camera")
    print("  3. Run: python -m src.enroll")
    print("  4. Run: python -m src.recognize")
    
    return True


if __name__ == "__main__":
    import sys
    success = init_project()
    sys.exit(0 if success else 1)
