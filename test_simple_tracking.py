#!/usr/bin/env python3
"""
MQTT servo hardware test — no camera required.

Moves the servo through large, obvious angles (0° → 180° → 90°) and prints
whether each command was published AND whether the ESP8266 reported movement.

Run from the project root:
    python test_simple_tracking.py

Before running:
  1. Stop any other FaceLocking process (track.py, dashboard, etc.)
  2. ESP8266 powered, flashed, on same WiFi as configured in the .ino file
  3. Servo signal wire on GPIO12 (SERVO_PIN in firmware)
"""

import sys
import time

from src import config
from src.mqtt_camera_controller import MQTTCameraController


def wait_for_angle(ctrl: MQTTCameraController, target: int, timeout: float = 8.0) -> bool:
    """Wait until ESP status reports the servo reached *target* (±3°)."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if abs(ctrl.reported_angle - target) <= 3:
            return True
        time.sleep(0.15)
    return False


def move_and_verify(ctrl: MQTTCameraController, label: str, angle: int) -> bool:
    """Publish an angle, report success, wait for ESP confirmation."""
    before = ctrl.reported_angle
    ok = ctrl.move_to_angle(angle)
    print(f"\n→ {label}: publish angle={angle}°  sent={'YES' if ok else 'NO (dedup or disconnected)'}")
    if not ok and abs(angle - ctrl.commanded_angle) <= 1:
        print("  (skipped: already at this commanded angle)")

    if not ctrl.is_connected:
        print("  ✗ MQTT disconnected")
        return False

  # Give ESP time to start moving (1°/7ms → full sweep is fast; 3s is plenty)
    reached = wait_for_angle(ctrl, angle, timeout=6.0)
    after = ctrl.reported_angle
    moving = ctrl.last_status.get("moving", "?")
    print(f"  ESP status: angle={after}°  target={ctrl.last_status.get('target', '?')}  moving={moving}")

    if reached:
        print(f"  ✓ Servo reached ~{angle}° (was {before}°)")
        return True

    if after != before:
        print(f"  ~ Partial move: {before}° → {after}° (target was {angle}°)")
        print("    Check: servo power (5V), signal on GPIO12, mechanical bind")
        return False

    print("  ✗ NO MOVEMENT detected on ESP status topic")
    print("    Possible causes:")
    print("      • Servo not wired to GPIO12 or no 5V power")
    print("      • ESP8266 not running / wrong WiFi in firmware")
    print("      • Another process (track.py) flooding conflicting commands")
    return False


def main() -> bool:
    print("=" * 60)
    print(" MQTT Servo Hardware Test")
    print("=" * 60)
    print(f"Broker : {config.MQTT_BROKER_HOST}:{config.MQTT_BROKER_PORT}")
    print(f"Topics : {config.MQTT_TOPIC_HORIZONTAL}")
    print(f"         {config.MQTT_TOPIC_STATUS}")
    print()
    print("IMPORTANT: stop track.py / any other FaceLocking process first.")
    print()

    ctrl = MQTTCameraController()
    if not ctrl.wait_for_connection(timeout_sec=8.0):
        print("✗ Cannot connect to MQTT broker")
        print("  Check broker IP, firewall, and network.")
        return False

    print("✓ Connected to broker")

    # Wait for first ESP status (proves ESP is online)
    print("\nWaiting for ESP status (max 5s)...")
    t0 = time.time()
    while time.time() - t0 < 5.0:
        if ctrl._last_status_time > 0:
            break
        time.sleep(0.2)

    if ctrl._last_status_time == 0:
        print("✗ No messages on camera/status — ESP8266 is NOT connected to this broker")
        print("  Fix: power ESP, check WiFi SSID/password in esp8266_camera_tracker.ino")
        print(f"       broker must be {config.MQTT_BROKER_HOST}:{config.MQTT_BROKER_PORT}")
        ctrl.close()
        return False

    print(f"✓ ESP online — current angle {ctrl.reported_angle}°")
    if "mode" not in ctrl.last_status:
        print("  (older firmware — no 'mode' field; basic angle commands still work)")

    # Large obvious moves — easy to see physically
    results = []
    for label, angle in [
        ("Go to 0° (full left)", 0),
        ("Go to 180° (full right)", 180),
        ("Go to 90° (center)", 90),
    ]:
        results.append(move_and_verify(ctrl, label, angle))
        time.sleep(0.5)

    ctrl.close()
    print("\n" + "=" * 60)
    if all(results):
        print("✓ ALL MOVES CONFIRMED — MQTT + servo hardware OK")
        return True

    print("✗ SOME MOVES FAILED — see messages above")
    print("  Run in another terminal: python debug_mqtt_tracking.py")
    print("  Then run this test again and watch live MQTT traffic.")
    return False


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
