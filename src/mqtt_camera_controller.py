"""
MQTT Camera Controller
Publishes camera movement commands to ESP8266 servo controller.
"""

import json
import time
from typing import Optional
import paho.mqtt.client as mqtt


class MQTTCameraController:
    """Control camera servo via MQTT."""
    
    def __init__(
        self,
        broker_host: str = "157.173.101.159",
        broker_port: int = 1883,
        username: Optional[str] = None,
        password: Optional[str] = None
    ):
        """
        Initialize MQTT camera controller.
        
        Args:
            broker_host: MQTT broker hostname/IP
            broker_port: MQTT broker port (default 1883)
            username: MQTT username (optional)
            password: MQTT password (optional)
        """
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.username = username
        self.password = password
        
        # MQTT topics
        self.topic_horizontal = "camera/track/horizontal"
        self.topic_command = "camera/track/command"
        self.topic_status = "camera/status"
        
        # Camera state
        self.current_angle = 90  # Center position
        self.is_connected = False
        self.last_status = {}
        
        # Movement parameters
        self.min_angle = 0
        self.max_angle = 180
        self.center_angle = 90
        
        # Initialize MQTT client
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="FaceRecognition_Controller")
        
        if username and password:
            self.client.username_pw_set(username, password)
        
        # Set callbacks
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message
        
        # Connect to broker
        try:
            self.client.connect(broker_host, broker_port, keepalive=60)
            self.client.loop_start()
            print(f"✓ MQTT Controller initialized")
            print(f"  Broker: {broker_host}:{broker_port}")
        except Exception as e:
            print(f"✗ Failed to connect to MQTT broker: {e}")
            print(f"  Make sure broker is running at {broker_host}:{broker_port}")
    
    def _on_connect(self, client, userdata, flags, rc, properties=None):
        """Callback when connected to MQTT broker."""
        if rc == 0:
            self.is_connected = True
            print("✓ Connected to MQTT broker")
            # Subscribe to status topic
            self.client.subscribe(self.topic_status)
            print(f"  Subscribed to: {self.topic_status}")
        else:
            print(f"✗ Connection failed with code {rc}")
    
    def _on_disconnect(self, client, userdata, rc):
        """Callback when disconnected from MQTT broker."""
        self.is_connected = False
        if rc != 0:
            print(f"⚠ Unexpected disconnection from MQTT broker (code {rc})")
    
    def _on_message(self, client, userdata, msg):
        """Callback when message received."""
        try:
            if msg.topic == self.topic_status:
                status = json.loads(msg.payload.decode())
                self.last_status = status
                self.current_angle = status.get("angle", self.current_angle)
        except Exception as e:
            print(f"Error parsing status message: {e}")
    
    def move_to_angle(self, angle: int) -> bool:
        """
        Move camera to specific angle.
        
        Args:
            angle: Target angle (0-180 degrees)
            
        Returns:
            True if command sent successfully
        """
        if not self.is_connected:
            print("⚠ Not connected to MQTT broker")
            return False
        
        # Constrain angle
        angle = max(self.min_angle, min(self.max_angle, angle))
        
        try:
            self.client.publish(self.topic_horizontal, str(angle))
            print(f"→ Camera angle: {angle}°")
            return True
        except Exception as e:
            print(f"✗ Failed to send angle command: {e}")
            return False
    
    def move_left(self) -> bool:
        """Move camera left."""
        if not self.is_connected:
            return False
        
        try:
            self.client.publish(self.topic_command, "left")
            print("← Camera moving left")
            return True
        except Exception as e:
            print(f"✗ Failed to send left command: {e}")
            return False
    
    def move_right(self) -> bool:
        """Move camera right."""
        if not self.is_connected:
            return False
        
        try:
            self.client.publish(self.topic_command, "right")
            print("→ Camera moving right")
            return True
        except Exception as e:
            print(f"✗ Failed to send right command: {e}")
            return False
    
    def center(self) -> bool:
        """Center camera."""
        if not self.is_connected:
            return False
        
        try:
            self.client.publish(self.topic_command, "center")
            print("⊙ Camera centering")
            return True
        except Exception as e:
            print(f"✗ Failed to send center command: {e}")
            return False
    
    def search_sweep(self, current_angle: int = None) -> int:
        """
        Perform search sweep pattern across full 180 degrees.
        Returns next angle to move to.
        
        Args:
            current_angle: Current servo angle (None = use stored angle)
            
        Returns:
            Next angle for sweep pattern
        """
        if current_angle is None:
            current_angle = self.current_angle
        
        # Full 180-degree sweep pattern: 0 -> 30 -> 60 -> 90 -> 120 -> 150 -> 180 -> 150 -> 120 -> 90 -> 60 -> 30 -> 0
        sweep_positions = [0, 30, 60, 90, 120, 150, 180, 150, 120, 90, 60, 30]
        
        # Find closest position in sweep pattern
        closest_idx = 0
        min_diff = abs(sweep_positions[0] - current_angle)
        for i, pos in enumerate(sweep_positions):
            diff = abs(pos - current_angle)
            if diff < min_diff:
                min_diff = diff
                closest_idx = i
        
        # Move to next position in pattern
        next_idx = (closest_idx + 1) % len(sweep_positions)
        next_angle = sweep_positions[next_idx]
        
        self.move_to_angle(next_angle)
        return next_angle
    
    def track_face_position(self, face_center_x: float, frame_width: int) -> bool:
        """
        Calculate and send servo angle based on face position.
        
        Args:
            face_center_x: X coordinate of face center
            frame_width: Width of video frame
            
        Returns:
            True if command sent successfully
        """
        if not self.is_connected:
            return False
        
        # Calculate normalized position (0.0 = left, 0.5 = center, 1.0 = right)
        normalized_x = face_center_x / frame_width
        
        # Map to servo angle (0-180 degrees)
        # Note: You may need to invert this depending on your servo orientation
        target_angle = int(normalized_x * (self.max_angle - self.min_angle) + self.min_angle)
        
        return self.move_to_angle(target_angle)
    
    def track_face_movement(self, movement_type: str) -> bool:
        """
        Send movement command based on detected face movement.
        
        Args:
            movement_type: "move_left", "move_right", etc.
            
        Returns:
            True if command sent successfully
        """
        if not self.is_connected:
            print("⚠️  MQTT not connected - cannot send command")
            return False
        
        print(f"📤 Sending MQTT command for: {movement_type}")
        
        if movement_type == "move_left":
            return self.move_right()  # Camera moves opposite to face
        elif movement_type == "move_right":
            return self.move_left()  # Camera moves opposite to face
        
        return False
    
    def get_status(self) -> dict:
        """Get last known camera status."""
        return self.last_status.copy()
    
    def disconnect(self):
        """Disconnect from MQTT broker."""
        if self.is_connected:
            self.client.loop_stop()
            self.client.disconnect()
            print("✓ Disconnected from MQTT broker")


# Example usage
if __name__ == "__main__":
    # Initialize controller
    controller = MQTTCameraController(
        broker_host="localhost",  # Change to your broker IP
        broker_port=1883
    )
    
    # Wait for connection
    time.sleep(2)
    
    if controller.is_connected:
        print("\nTesting camera movements...")
        
        # Test center
        print("\n1. Centering camera...")
        controller.center()
        time.sleep(2)
        
        # Test left movement
        print("\n2. Moving left...")
        for i in range(3):
            controller.move_left()
            time.sleep(1)
        
        # Test right movement
        print("\n3. Moving right...")
        for i in range(3):
            controller.move_right()
            time.sleep(1)
        
        # Test specific angles
        print("\n4. Testing specific angles...")
        for angle in [45, 90, 135]:
            print(f"   Moving to {angle}°...")
            controller.move_to_angle(angle)
            time.sleep(2)
        
        # Get status
        print("\n5. Camera status:")
        status = controller.get_status()
        print(f"   {status}")
        
        print("\n✓ Test complete!")
    else:
        print("\n✗ Could not connect to MQTT broker")
        print("  Make sure mosquitto or another MQTT broker is running")
    
    controller.disconnect()
