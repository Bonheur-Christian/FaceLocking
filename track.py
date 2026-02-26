#!/usr/bin/env python3
"""
Quick shortcut to run face recognition with tracking.
Just run: python track.py
"""

import sys
from src.recognize_with_tracking import main

if __name__ == "__main__":
    # Parse simple arguments
    fullscreen = "--fullscreen" in sys.argv or "-f" in sys.argv
    no_mqtt = "--no-mqtt" in sys.argv
    
    # Run with defaults from config
    success = main(
        start_fullscreen=fullscreen,
        enable_mqtt=not no_mqtt
    )
    
    sys.exit(0 if success else 1)
