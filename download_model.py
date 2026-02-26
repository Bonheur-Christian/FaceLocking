"""
Model download utility.
Downloads ArcFace ONNX model from InsightFace.
"""

import sys
import os
import subprocess
from pathlib import Path

from src import config


def download_model():
    """Download ArcFace ONNX model."""
    print("\n" + "="*70)
    print(" ArcFace ONNX Model Download")
    print("="*70)
    print("\nThis will download the ArcFace/InsightFace w600k_r50.onnx model")
    print("Size: ~170 MB")
    print("Source: InsightFace official repository")
    print()
    
    choice = input("Download now? (y/n): ").strip().lower()
    if choice != "y":
        print("Download cancelled.")
        return False
    
    config.ensure_dirs()
    
    # Download link
    url = "https://sourceforge.net/projects/insightface.mirror/files/v0.7/buffalo_l.zip/download"
    zip_path = Path("buffalo_l.zip")
    
    print(f"\nDownloading from: {url}")
    
    # Use curl or wget
    if os.name == "nt":  # Windows
        cmd = f'powershell -Command "Invoke-WebRequest -Uri \'{url}\' -OutFile \'{zip_path}\'"'
    else:  # macOS/Linux
        cmd = f"curl -L -o {zip_path} {url}"
    
    print(f"Command: {cmd}")
    result = os.system(cmd)
    
    if result != 0:
        print("ERROR: Download failed.")
        print("\nAlternative: Download manually from:")
        print(f"  {url}")
        print("\nThen extract and place w600k_r50.onnx in models/ directory")
        return False
    
    # Extract
    print("\nExtracting...")
    if os.name == "nt":
        import zipfile
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall()
    else:
        os.system(f"unzip -o {zip_path}")
    
    # Copy model
    src_model = Path("w600k_r50.onnx")
    dst_model = config.ARCFACE_MODEL_PATH
    
    if src_model.exists():
        import shutil
        shutil.copy(str(src_model), str(dst_model))
        print(f"\n✓ Model copied to: {dst_model}")
    else:
        print(f"ERROR: Model file not found: {src_model}")
        return False
    
    # Cleanup
    print("\nCleaning up...")
    for f in ["buffalo_l.zip", "w600k_r50.onnx", "1k3d68.onnx", "2d106det.onnx",
              "det_10g.onnx", "genderage.onnx"]:
        if Path(f).exists():
            Path(f).unlink()
    
    print("\n" + "="*70)
    print("✓ Model downloaded and installed successfully!")
    print("="*70)
    return True


if __name__ == "__main__":
    success = download_model()
    sys.exit(0 if success else 1)
