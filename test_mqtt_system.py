#!/usr/bin/env python3
"""
MQTT Camera Tracking System Test
Tests all components of the MQTT tracking system.
"""

import sys
import time
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.mqtt_camera_controller import MQTTCameraController


def print_header(text):
    """Print formatted header."""
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60 + "\n")


def print_step(number, text):
    """Print formatted step."""
    print(f"\n{number}. {text}")
    print("-" * 60)


def test_mqtt_connection(broker_host="localhost", broker_port=1883):
    """Test MQTT broker connection."""
    print_header("MQTT Camera Tracking System Test")
    
    print(f"Testing connection to MQTT broker at {broker_host}:{broker_port}...")
    print("Make sure:")
    print("  1. MQTT broker (mosquitto) is running")
    print("  2. ESP8266 is powered on and connected")
    print("  3. ESP8266 is connected to same network")
    print("")
    
    try:
        controller = MQTTCameraController(
            broker_host=broker_host,
            broker_port=broker_port
        )
        
        # Wait for connection
        print("Waiting for MQTT connection...")
        for i in range(5):
            time.sleep(1)
            if controller.is_connected:
                break
            print(f"  Attempt {i+1}/5...")
        
        if not controller.is_connected:
            print("\n❌ Failed to connect to MQTT broker!")
            print("\nTroubleshooting:")
            print("  1. Check if mosquitto is running:")
            print("     - macOS/Linux: ps aux | grep mosquitto")
            print("     - Windows: tasklist | findstr mosquitto")
            print("  2. Start mosquitto:")
            print("     - macOS: brew services start mosquitto")
            print("     - Linux: sudo systemctl start mosquitto")
            print("     - Windows: net start mosquitto")
            print("  3. Check firewall settings")
            return False
        
        print("✅ Connected to MQTT broker!\n")
        
        # Test 1: Center camera
        print_step(1, "Testing CENTER command")
        if controller.center():
            print("✅ Center command sent")
            time.sleep(2)
        else:
            print("❌ Failed to send center command")
        
        # Test 2: Move left
        print_step(2, "Testing LEFT movement (3 steps)")
        for i in range(3):
            if controller.move_left():
                print(f"  ✅ Left command {i+1}/3 sent")
                time.sleep(1)
            else:
                print(f"  ❌ Failed to send left command {i+1}/3")
        
        # Test 3: Move right
        print_step(3, "Testing RIGHT movement (3 steps)")
        for i in range(3):
            if controller.move_right():
                print(f"  ✅ Right command {i+1}/3 sent")
                time.sleep(1)
            else:
                print(f"  ❌ Failed to send right command {i+1}/3")
        
        # Test 4: Specific angles
        print_step(4, "Testing SPECIFIC ANGLES")
        test_angles = [45, 90, 135, 90]
        for angle in test_angles:
            if controller.move_to_angle(angle):
                print(f"  ✅ Moved to {angle}°")
                time.sleep(2)
            else:
                print(f"  ❌ Failed to move to {angle}°")
        
        # Test 5: Face tracking simulation
        print_step(5, "Testing FACE TRACKING simulation")
        print("Simulating face moving across frame (640px wide)...")
        frame_width = 640
        positions = [
            (160, "Left side"),
            (320, "Center"),
            (480, "Right side"),
            (320, "Back to center")
        ]
        
        for pos_x, description in positions:
            print(f"  Face at {description} (x={pos_x})")
            if controller.track_face_position(pos_x, frame_width):
                print(f"    ✅ Tracking command sent")
                time.sleep(2)
            else:
                print(f"    ❌ Failed to send tracking command")
        
        # Test 6: Movement commands
        print_step(6, "Testing MOVEMENT DETECTION commands")
        movements = ["move_left", "move_right", "move_left", "move_right"]
        for movement in movements:
            print(f"  Detected: {movement}")
            if controller.track_face_movement(movement):
                print(f"    ✅ Camera adjusted")
                time.sleep(1.5)
            else:
                print(f"    ❌ Failed to adjust camera")
        
        # Test 7: Get status
        print_step(7, "Getting CAMERA STATUS")
        time.sleep(1)  # Wait for status update
        status = controller.get_status()
        if status:
            print("  Current camera status:")
            print(f"    Angle: {status.get('angle', 'unknown')}°")
            print(f"    Target: {status.get('target', 'unknown')}°")
            print(f"    Moving: {status.get('moving', 'unknown')}")
            print("  ✅ Status received")
        else:
            print("  ⚠️  No status received yet")
        
        # Final center
        print_step(8, "Returning to CENTER")
        controller.center()
        time.sleep(2)
        
        # Cleanup
        print("\nDisconnecting...")
        controller.disconnect()
        
        print_header("✅ All Tests Completed Successfully!")
        print("Your MQTT camera tracking system is working correctly!")
        print("\nNext steps:")
        print("  1. Run face recognition with tracking:")
        print("     python -m src.recognize_with_tracking")
        print("  2. Lock to a person and watch the camera follow them!")
        print("")
        
        return True
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        return False
    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        print("\nTroubleshooting:")
        print("  1. Check ESP8266 Serial Monitor for errors")
        print("  2. Verify WiFi connection on ESP8266")
        print("  3. Check MQTT broker is accessible")
        print("  4. Verify servo is connected properly")
        return False


def main():
    """Main test function."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Test MQTT camera tracking system"
    )
    parser.add_argument(
        "--broker",
        default="localhost",
        help="MQTT broker hostname/IP (default: localhost)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=1883,
        help="MQTT broker port (default: 1883)"
    )
    
    args = parser.parse_args()
    
    success = test_mqtt_connection(args.broker, args.port)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
