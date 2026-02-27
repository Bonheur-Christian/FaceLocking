/*
 * ESP8266 Camera Tracker with Servo Motor
 * 
 * This Arduino sketch controls a servo motor to track a person's face
 * based on MQTT commands received from the Python face recognition system.
 * 
 * Hardware:
 * - ESP8266 (NodeMCU, Wemos D1 Mini, etc.)
 * - Servo motor (SG90 or similar)
 * - Camera mounted on servo
 * 
 * Connections:
 * - Servo Signal -> D4 (GPIO2)
 * - Servo VCC -> 5V
 * - Servo GND -> GND
 * 
 * MQTT Topics:
 * - camera/track/horizontal - Receives horizontal position (0-180 degrees)
 * - camera/track/command - Receives movement commands (left, right, center)
 * - camera/status - Publishes current servo position
 */

#include <ESP8266WiFi.h>
#include <PubSubClient.h>
#include <Servo.h>

// ============================================================================
// CONFIGURATION - MODIFY THESE VALUES
// ============================================================================

// WiFi credentials
const char* ssid = "RCA-A";
const char* password = "RCA@2024";

// MQTT Broker settings
const char* mqtt_server = "157.173.101.159";  // Your MQTT broker IP
const int mqtt_port = 1883;
const char* mqtt_user = "";  // Leave empty if no authentication
const char* mqtt_password = "";

// MQTT Topics
const char* topic_horizontal = "camera/track/horizontal";
const char* topic_command = "camera/track/command";
const char* topic_status = "camera/status";

// Servo settings
const int SERVO_PIN = 2;  // GPIO2
const int SERVO_MIN_ANGLE = 0;
const int SERVO_MAX_ANGLE = 180;
const int SERVO_CENTER_ANGLE = 0;
const int SERVO_STEP_SIZE = 10;  // Degrees per movement command

// Movement smoothing
const int MOVEMENT_DELAY = 15;  // ms delay between servo steps for smooth movement

// Debug mode
#define DEBUG true

// ============================================================================
// GLOBAL VARIABLES
// ============================================================================

WiFiClient espClient;
PubSubClient client(espClient);
Servo cameraServo;

int currentAngle = SERVO_CENTER_ANGLE;
int targetAngle = SERVO_CENTER_ANGLE;
unsigned long lastStatusUpdate = 0;
const unsigned long STATUS_UPDATE_INTERVAL = 1000;  // Send status every 1 second

// ============================================================================
// SETUP
// ============================================================================

void setup() {
  Serial.begin(115200);
  delay(100);

  Serial.println("\n\n=================================");
  Serial.println("ESP8266 Camera Tracker Starting");
  Serial.println("=================================\n");

  // Initialize servo
  cameraServo.attach(SERVO_PIN);
  cameraServo.write(SERVO_CENTER_ANGLE);
  currentAngle = SERVO_CENTER_ANGLE;
  targetAngle = SERVO_CENTER_ANGLE;
  Serial.println("✓ Servo initialized at center position");

  // Connect to WiFi
  setup_wifi();

  // Setup MQTT
  client.setServer(mqtt_server, mqtt_port);
  client.setCallback(mqtt_callback);

  Serial.println("\n✓ Setup complete!");
  Serial.println("Waiting for MQTT commands...\n");
}

// ============================================================================
// WIFI SETUP
// ============================================================================

void setup_wifi() {
  delay(10);
  Serial.print("Connecting to WiFi: ");
  Serial.println(ssid);

  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);

  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 30) {
    delay(500);
    Serial.print(".");
    attempts++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\n✓ WiFi connected!");
    Serial.print("  IP address: ");
    Serial.println(WiFi.localIP());
    Serial.print("  Signal strength: ");
    Serial.print(WiFi.RSSI());
    Serial.println(" dBm");
  } else {
    Serial.println("\n✗ WiFi connection failed!");
    Serial.println("  Please check your credentials and try again");
  }
}

// ============================================================================
// MQTT RECONNECT
// ============================================================================

void reconnect() {
  while (!client.connected()) {
    Serial.print("Connecting to MQTT broker...");

    String clientId = "ESP8266_CameraTracker_";
    clientId += String(random(0xffff), HEX);

    if (client.connect(clientId.c_str(), mqtt_user, mqtt_password)) {
      Serial.println(" connected!");

      // Subscribe to topics
      client.subscribe(topic_horizontal);
      client.subscribe(topic_command);

      Serial.println("✓ Subscribed to topics:");
      Serial.print("  - ");
      Serial.println(topic_horizontal);
      Serial.print("  - ");
      Serial.println(topic_command);

      // Publish initial status
      publishStatus();

    } else {
      Serial.print(" failed, rc=");
      Serial.print(client.state());
      Serial.println(" retrying in 5 seconds...");
      delay(5000);
    }
  }
}

// ============================================================================
// MQTT CALLBACK - Handle incoming messages
// ============================================================================

void mqtt_callback(char* topic, byte* payload, unsigned int length) {
  // Convert payload to string
  String message = "";
  for (unsigned int i = 0; i < length; i++) {
    message += (char)payload[i];
  }

  Serial.print("📨 Received [");
  Serial.print(topic);
  Serial.print("]: ");
  Serial.println(message);

  // Handle horizontal position (0-180 degrees)
  if (strcmp(topic, topic_horizontal) == 0) {
    int angle = message.toInt();
    if (angle >= SERVO_MIN_ANGLE && angle <= SERVO_MAX_ANGLE) {
      targetAngle = angle;

      if (DEBUG) {
        Serial.print("📌 Current Angle: ");
        Serial.print(currentAngle);
        Serial.print(" | New Target: ");
        Serial.println(targetAngle);
      }

      Serial.print("→ Target angle set to: ");
      Serial.println(targetAngle);
    } else {
      Serial.println("✗ Invalid angle (must be 0-180)");
    }
  }

  // Handle movement commands (left, right, center)
  else if (strcmp(topic, topic_command) == 0) {
    message.toLowerCase();

    if (message == "left" || message == "move_left") {
      targetAngle = constrain(currentAngle - SERVO_STEP_SIZE, SERVO_MIN_ANGLE, SERVO_MAX_ANGLE);
      Serial.print("← Moving left to: ");
      Serial.println(targetAngle);
    } else if (message == "right" || message == "move_right") {
      targetAngle = constrain(currentAngle + SERVO_STEP_SIZE, SERVO_MIN_ANGLE, SERVO_MAX_ANGLE);
      Serial.print("→ Moving right to: ");
      Serial.println(targetAngle);
    } else if (message == "center") {
      targetAngle = SERVO_CENTER_ANGLE;
      Serial.print("⊙ Centering to: ");
      Serial.println(targetAngle);
    } else {
      Serial.print("✗ Unknown command: ");
      Serial.println(message);
    }
  }
}

// ============================================================================
// SMOOTH SERVO MOVEMENT
// ============================================================================
void updateServoPosition() {

  if (currentAngle != targetAngle) {

    if (DEBUG) {
      Serial.print("🔄 Moving | Current: ");
      Serial.print(currentAngle);
      Serial.print(" -> Target: ");
      Serial.println(targetAngle);
    }

    // Determine direction
    if (currentAngle < targetAngle) {
      currentAngle++;
      if (DEBUG) Serial.println("➡ Direction: RIGHT (+1)");
    } else if (currentAngle > targetAngle) {
      currentAngle--;
      if (DEBUG) Serial.println("⬅ Direction: LEFT (-1)");
    }

    cameraServo.write(currentAngle);

    if (DEBUG) {
      Serial.print("📍 Servo now at: ");
      Serial.println(currentAngle);
    }

    delay(MOVEMENT_DELAY);

    // Movement completed
    if (currentAngle == targetAngle) {
      Serial.println("✅ Movement Complete");
      Serial.print("🎯 Final Position: ");
      Serial.println(currentAngle);
      publishStatus();
    }
  }
}

// ============================================================================
// PUBLISH STATUS
// ============================================================================

void publishStatus() {
  String status = "{\"angle\":" + String(currentAngle) + 
                  ",\"target\":" + String(targetAngle) + 
                  ",\"moving\":" + (currentAngle != targetAngle ? "true" : "false") + "}";

  client.publish(topic_status, status.c_str());

  if (DEBUG) {
    Serial.print("📤 Published Status: ");
    Serial.println(status);
  }
}

// ============================================================================
// MAIN LOOP
// ============================================================================

void loop() {
  // Maintain MQTT connection
  if (!client.connected()) {
    reconnect();
  }
  client.loop();

  // Update servo position smoothly
  updateServoPosition();

  // Publish status periodically
  unsigned long now = millis();
  if (now - lastStatusUpdate > STATUS_UPDATE_INTERVAL) {
    publishStatus();
    lastStatusUpdate = now;
  }
}
