"""
Verification script to check project integrity.
Run this to verify all files are in place.
"""

import sys
from pathlib import Path


def verify_project():
    """Verify project structure and files."""
    print("\n" + "="*70)
    print(" Project Integrity Verification")
    print("="*70 + "\n")
    
    root = Path(__file__).parent
    
    # Check directories
    print("Checking directories...")
    required_dirs = [
        "src",
        "data/db",
        "data/enroll",
        "data/debug_aligned",
        "models",
    ]
    
    all_ok = True
    for d in required_dirs:
        path = root / d
        if path.exists():
            print(f"  ✓ {d}/")
        else:
            print(f"  ✗ {d}/ (MISSING)")
            all_ok = False
    
    # Check Python files
    print("\nChecking Python modules...")
    required_files = [
        "src/__init__.py",
        "src/config.py",
        "src/camera.py",
        "src/detect.py",
        "src/landmarks.py",
        "src/align.py",
        "src/embed.py",
        "src/haar_5pt.py",
        "src/enroll.py",
        "src/evaluate.py",
        "src/recognize.py",
        "src/lock.py",
    ]
    
    for f in required_files:
        path = root / f
        if path.exists():
            print(f"  ✓ {f}")
        else:
            print(f"  ✗ {f} (MISSING)")
            all_ok = False
    
    # Check configuration files
    print("\nChecking configuration files...")
    config_files = [
        "requirements.txt",
        "setup.bat",
        "setup.sh",
        "download_model.py",
        "init_project.py",
        ".gitignore",
        "README.md",
        "QUICKSTART.md",
    ]
    
    for f in config_files:
        path = root / f
        if path.exists():
            print(f"  ✓ {f}")
        else:
            print(f"  ✗ {f} (MISSING)")
            all_ok = False
    
    # Summary
    print("\n" + "="*70)
    if all_ok:
        print(" ✓ All files present!")
        print("="*70)
        print("\nNext steps:")
        print("  1. Windows: setup.bat")
        print("     macOS/Linux: bash setup.sh")
        print("  2. python download_model.py")
        print("  3. python -m src.camera")
        print("  4. python -m src.enroll")
        print("  5. python -m src.recognize")
        return True
    else:
        print(" ✗ Some files are missing!")
        print("="*70)
        print("\nRun: python init_project.py")
        return False


if __name__ == "__main__":
    success = verify_project()
    sys.exit(0 if success else 1)
