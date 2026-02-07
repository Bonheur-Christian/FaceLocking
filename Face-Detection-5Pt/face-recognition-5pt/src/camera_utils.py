#!/usr/bin/env python3
"""
Camera detection utility for finding working camera device.
"""

import cv2
import os
from pathlib import Path


def find_working_camera(max_index: int = 10, timeout_ms: int = 100) -> int:
    """
    Find the first working camera index.
    
    Args:
        max_index: Maximum index to test (default 10)
        timeout_ms: Timeout for camera initialization in ms
        
    Returns:
        Camera index if found, -1 otherwise
    """
    print("Searching for working camera...")
    
    for idx in range(max_index):
        cap = cv2.VideoCapture(idx)
        if cap.isOpened():
            # Try to read a frame to confirm it actually works
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            ret, frame = cap.read()
            cap.release()
            if ret:
                print(f"✓ Found working camera at index {idx}")
                return idx
        cap.release()
    
    return -1


def get_available_devices() -> list:
    """Get list of available /dev/video* devices."""
    devices = []
    for i in range(10):
        dev_path = f"/dev/video{i}"
        if os.path.exists(dev_path):
            devices.append((i, dev_path))
    return devices


if __name__ == "__main__":
    print("Available V4L2 devices:")
    for idx, path in get_available_devices():
        print(f"  {path}")
    
    print("\nTesting camera indices...")
    working_idx = find_working_camera()
    
    if working_idx >= 0:
        print(f"\n✓ Recommended CAMERA_INDEX in config.py: {working_idx}")
    else:
        print("\n✗ No working camera found!")
