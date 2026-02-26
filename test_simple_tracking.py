#!/usr/bin/env python3
"""
Simple tracking test - bypasses face recognition to test MQTT/servo directly
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from src.mqtt_camera_controller import MQTTCameraController
import time

print("=" * 60)
print("Simple Tracking Test")
print("=" * 60)
print()

controller = MQTTCameraController()

print("Waiting for MQTT connection...")
time.sleep(2)

if not controller.is_connected:
    print("❌ Not connected to MQTT broker!")
    print()
    print("Make sure mosquitto is running:")
    print("  macOS: brew services start mosquitto")
    print("  Linux: sudo systemctl start mosquitto")
    print("  Windows: net start mosquitto")
    sys.exit(1)

print("✅ Connected to MQTT broker")
print()
print("Testing servo movements...")
print()

# Test 1: Center
print("1. Centering...")
controller.center()
time.sleep(2)

# Test 2: Move left 5 times
print("2. Moving left 5 times...")
for i in range(5):
    print(f"   Left {i+1}/5")
    controller.move_left()
    time.sleep(1)

# Test 3: Move right 5 times
print("3. Moving right 5 times...")
for i in range(5):
    print(f"   Right {i+1}/5")
    controller.move_right()
    time.sleep(1)

# Test 4: Specific angles
print("4. Testing specific angles...")
for angle in [45, 90, 135, 90]:
    print(f"   Moving to {angle}°")
    controller.move_to_angle(angle)
    time.sleep(2)

# Test 5: Simulate face tracking
print("5. Simulating face tracking...")
frame_width = 640
positions = [
    (160, "Left side"),
    (320, "Center"),
    (480, "Right side"),
    (320, "Back to center")
]

for pos_x, description in positions:
    print(f"   Face at {description} (x={pos_x})")
    controller.track_face_position(pos_x, frame_width)
    time.sleep(2)

# Final center
print("6. Returning to center...")
controller.center()
time.sleep(2)

print()
print("=" * 60)
print("✅ Test Complete!")
print("=" * 60)
print()
print("If servo moved correctly, MQTT and hardware are working.")
print("If face tracking still doesn't work, the issue is in movement detection.")
print()
print("Next steps:")
print("  1. Run: python debug_mqtt_tracking.py")
print("  2. In another terminal: python -m src.recognize_with_tracking")
print("  3. Lock to your face and move left/right")
print("  4. Watch for MQTT messages in debug terminal")
print()

controller.disconnect()
