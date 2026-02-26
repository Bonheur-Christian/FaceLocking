#!/usr/bin/env python3
"""
Debug MQTT Camera Tracking
Helps diagnose why servo isn't moving when face moves.
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import paho.mqtt.client as mqtt


def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print("✅ Connected to MQTT broker")
        client.subscribe("camera/#")
        print("✅ Subscribed to camera/* topics")
    else:
        print(f"❌ Connection failed with code {rc}")


def on_message(client, userdata, msg):
    print(f"📨 [{msg.topic}] {msg.payload.decode()}")


def main():
    print("=" * 60)
    print("MQTT Camera Tracking Debugger")
    print("=" * 60)
    print()
    print("This tool monitors MQTT messages to help debug tracking issues.")
    print()
    
    # Test 1: Check MQTT broker connection
    print("Test 1: Connecting to MQTT broker...")
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, "DebugTool")
    client.on_connect = on_connect
    client.on_message = on_message
    
    try:
        client.connect("localhost", 1883, 60)
    except Exception as e:
        print(f"❌ Cannot connect to MQTT broker: {e}")
        print()
        print("Solutions:")
        print("  1. Start mosquitto:")
        print("     - macOS: brew services start mosquitto")
        print("     - Linux: sudo systemctl start mosquitto")
        print("     - Windows: net start mosquitto")
        print("  2. Check if running: ps aux | grep mosquitto")
        return False
    
    print()
    print("=" * 60)
    print("Monitoring MQTT messages...")
    print("=" * 60)
    print()
    print("Now run: python -m src.recognize_with_tracking")
    print()
    print("Expected messages when face moves:")
    print("  - camera/track/command: left")
    print("  - camera/track/command: right")
    print("  - camera/track/horizontal: <angle>")
    print("  - camera/status: {\"angle\":...}")
    print()
    print("Press Ctrl+C to stop monitoring")
    print()
    
    try:
        client.loop_forever()
    except KeyboardInterrupt:
        print("\n\nStopping monitor...")
        client.disconnect()
        return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
