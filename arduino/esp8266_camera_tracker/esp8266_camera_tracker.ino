/*
 * ESP8266 Camera Tracker with Servo Motor
 *
 * Controls a pan servo that tracks a locked face based on MQTT commands from
 * the Python face-recognition system.
 *
 * ----------------------------------------------------------------------------
 * SERVO STATE MACHINE (runs in loop(), INDEPENDENT of MQTT arrival timing)
 * ----------------------------------------------------------------------------
 *   MODE_IDLE    : DEFAULT state at power-up. Servo is stationary and holds
 *                  its initialised angle. NO tracking, NO sweeping. The servo
 *                  only leaves IDLE after a VALID command arrives from the PC.
 *   MODE_TRACK   : smoothly drive currentAngle -> targetAngle (1 deg / step).
 *                  targetAngle is set by the PC on `camera/track/horizontal`.
 *   MODE_SEARCH  : autonomous continuous sweep 0 -> 180 -> 0 -> 180 ... with
 *                  small incremental steps. Started by the PC sending the
 *                  command "search". The sweep is generated ON THE ESP, so it
 *                  is perfectly smooth regardless of WiFi/MQTT jitter or loss.
 *
 * Any horizontal angle command, or "track"/"center"/"left"/"right", switches
 * the servo back to MODE_TRACK. This is what stops the sweep the instant the
 * PC re-acquires the target.
 *
 * STARTUP SAFETY
 * ----------------------------------------------------------------------------
 *   - Default mode is MODE_IDLE (no motion).
 *   - On connect the ESP CLEARS any retained messages on its command topics
 *     and then ignores ALL inbound messages for STARTUP_IGNORE_MS so that
 *     retained / stale / startup messages can never move the servo.
 *   - Empty / non-numeric / out-of-range messages are rejected.
 *
 * Hardware:
 * - ESP8266 (NodeMCU / Wemos D1 Mini)
 * - Servo on SERVO_PIN, VCC 5V, common GND
 *
 * MQTT Topics:
 * - camera/track/horizontal : target angle 0-180 (plain int or {"angle":N})
 * - camera/track/command    : "search" | "track" | "center" | "left" | "right"
 * - camera/status           : ESP publishes {"angle":N,"target":N,"mode":"..."}
 */

#include <ESP8266WiFi.h>
#include <PubSubClient.h>
#include <Servo.h>

// ============================================================================
// CONFIGURATION
// ============================================================================

const char* ssid = "EdNet";
const char* password = "Huawei@123";

// const char* ssid = "how";
// const char* password = "00000000";

const char* mqtt_server = "157.173.101.159";
const int mqtt_port = 1883;
const char* mqtt_user = "";
const char* mqtt_password = "";

const char* topic_horizontal = "camera/track/horizontal";
const char* topic_command = "camera/track/command";
const char* topic_status = "camera/status";

// Servo settings
const int SERVO_PIN = 12;  // GPIO12
const int SERVO_MIN_ANGLE = 0;
const int SERVO_MAX_ANGLE = 180;
const int SERVO_CENTER_ANGLE = 90;
const int SERVO_STEP_SIZE = 10;  // nudge step for left/right commands

// Motion timing — one degree every N ms gives smooth, jitter-free motion.
// Lower = faster. 7ms/deg ~= 140 deg/s: fast target acquisition, still smooth.
const unsigned long SERVO_TRACK_STEP_MS = 7;    // ~140 deg/s while tracking
const unsigned long SERVO_SEARCH_STEP_MS = 7;   // ~140 deg/s while sweeping

// Debug — event-level logging only (state changes, commands, movement reasons).
// Safe to leave ON: we never print inside the per-degree servo step, so the
// motion loop is not stalled.
#define DEBUG true

// Ignore ALL inbound MQTT messages for this long after (re)subscribing. The
// broker delivers retained messages immediately on subscribe, so this window
// guarantees retained/stale/startup messages cannot move the servo at boot.
const unsigned long STARTUP_IGNORE_MS = 2000;

// ============================================================================
// STATE
// ============================================================================

enum ServoMode { MODE_IDLE, MODE_TRACK, MODE_SEARCH };

WiFiClient espClient;
PubSubClient client(espClient);
Servo cameraServo;

// DEFAULT STATE = IDLE: the servo stays put until a valid PC command arrives.
ServoMode mode = MODE_IDLE;
int currentAngle = SERVO_CENTER_ANGLE;
int targetAngle = SERVO_CENTER_ANGLE;
int sweepDir = 1;  // +1 -> moving toward MAX, -1 -> moving toward MIN

unsigned long lastServoStepMs = 0;
unsigned long lastStatusUpdate = 0;
unsigned long lastReconnectAttemptMs = 0;
unsigned long subscribeMs = 0;        // when we last (re)subscribed
bool commandAccepted = false;         // true once a valid command has activated motion
const unsigned long STATUS_UPDATE_INTERVAL = 250;  // keep PC angle estimate fresh
const unsigned long MQTT_RECONNECT_INTERVAL_MS = 3000;

const char* modeName(ServoMode m) {
  switch (m) {
    case MODE_IDLE:   return "idle";
    case MODE_TRACK:  return "track";
    case MODE_SEARCH: return "search";
  }
  return "?";
}

void logState(const char* event) {
  if (!DEBUG) return;
  Serial.print("[");
  Serial.print(millis());
  Serial.print("ms] ");
  Serial.print(event);
  Serial.print(" | state=");
  Serial.print(modeName(mode));
  Serial.print(" angle=");
  Serial.print(currentAngle);
  Serial.print(" target=");
  Serial.println(targetAngle);
}

// ============================================================================
// SETUP
// ============================================================================

void setup() {
  Serial.begin(115200);
  delay(100);
  Serial.println("\n\n=================================");
  Serial.println("ESP8266 Camera Tracker Starting");
  Serial.println("=================================\n");

  // One-time fixed-angle initialisation to the centre, then HOLD (IDLE).
  cameraServo.attach(SERVO_PIN);
  cameraServo.write(SERVO_CENTER_ANGLE);
  currentAngle = SERVO_CENTER_ANGLE;
  targetAngle = SERVO_CENTER_ANGLE;
  mode = MODE_IDLE;                 // default: stationary, no track, no search
  commandAccepted = false;
  lastServoStepMs = millis();
  logState("boot: servo initialised to center, IDLE");

  setup_wifi();
  client.setServer(mqtt_server, mqtt_port);
  client.setCallback(mqtt_callback);

  Serial.println("\nSetup complete. IDLE — waiting for a valid PC command.\n");
}

// ============================================================================
// WIFI
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
    Serial.print("\nWiFi connected. IP: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("\nWiFi connection failed!");
  }
}

// ============================================================================
// MQTT RECONNECT
// ============================================================================

void ensureMqttConnected() {
  if (client.connected()) {
    return;
  }
  unsigned long now = millis();
  if (now - lastReconnectAttemptMs < MQTT_RECONNECT_INTERVAL_MS) {
    return;
  }
  lastReconnectAttemptMs = now;

  Serial.print("Connecting to MQTT broker...");
  String clientId = "ESP8266_CameraTracker_";
  clientId += String(random(0xffff), HEX);

  if (client.connect(clientId.c_str(), mqtt_user, mqtt_password)) {
    Serial.println(" connected!");

    // Clear any RETAINED messages on the command topics BEFORE subscribing, so
    // a stale retained "search"/angle from a previous session cannot be
    // replayed to us and start motion at boot. An empty retained payload
    // deletes the broker's retained message.
    client.publish(topic_horizontal, "", true);
    client.publish(topic_command, "", true);

    client.subscribe(topic_horizontal);
    client.subscribe(topic_command);

    // Begin the startup ignore window: drop everything for STARTUP_IGNORE_MS.
    subscribeMs = millis();
    logState("mqtt connected: cleared retained, subscribed, ignoring inbound msgs");

    publishStatus();
  } else {
    Serial.print(" failed, rc=");
    Serial.println(client.state());
  }
}

// ============================================================================
// MESSAGE PARSING
// ============================================================================

// Returns a valid angle [0..180], or -1 if the message is empty / non-numeric /
// malformed. NOTE: a plain "0" is valid, but "" or "abc" must NOT become 0.
bool isNumericString(const String& s) {
  if (s.length() == 0) return false;
  for (unsigned int i = 0; i < s.length(); i++) {
    char c = s.charAt(i);
    bool signOk = (i == 0 && (c == '+' || c == '-'));
    if (!isDigit(c) && !signOk) return false;
  }
  return true;
}

int parseAngleFromMessage(const String& message) {
  String trimmed = message;
  trimmed.trim();
  if (trimmed.length() == 0) return -1;          // reject empty/retained-cleared
  if (trimmed.startsWith("{")) {
    int keyPos = trimmed.indexOf("\"angle\"");
    if (keyPos >= 0) {
      int colonPos = trimmed.indexOf(':', keyPos);
      if (colonPos >= 0) {
        String num = trimmed.substring(colonPos + 1);
        num.trim();
        // Strip any trailing JSON punctuation.
        int end = 0;
        while (end < (int)num.length() &&
               (isDigit(num.charAt(end)) || (end == 0 && (num.charAt(0) == '-' || num.charAt(0) == '+')))) {
          end++;
        }
        num = num.substring(0, end);
        if (!isNumericString(num)) return -1;
        return num.toInt();
      }
    }
    return -1;
  }
  if (!isNumericString(trimmed)) return -1;       // reject non-numeric plain text
  return trimmed.toInt();
}

String parseCommandFromMessage(const String& message) {
  String trimmed = message;
  trimmed.trim();
  if (trimmed.startsWith("{")) {
    int keyPos = trimmed.indexOf("\"command\"");
    if (keyPos >= 0) {
      int colonPos = trimmed.indexOf(':', keyPos);
      if (colonPos >= 0) {
        int quoteStart = trimmed.indexOf('"', colonPos + 1);
        int quoteEnd = trimmed.indexOf('"', quoteStart + 1);
        if (quoteStart >= 0 && quoteEnd > quoteStart) {
          return trimmed.substring(quoteStart + 1, quoteEnd);
        }
      }
    }
    return "";
  }
  return trimmed;
}

// Switch to tracking mode aimed at a specific angle.
void enterTrackMode(int angle) {
  angle = constrain(angle, SERVO_MIN_ANGLE, SERVO_MAX_ANGLE);
  targetAngle = angle;
  commandAccepted = true;
  if (mode != MODE_TRACK) {
    mode = MODE_TRACK;
    logState("-> MODE_TRACK (valid command)");
    publishStatus();
  }
}

void enterSearchMode() {
  commandAccepted = true;
  if (mode != MODE_SEARCH) {
    mode = MODE_SEARCH;
    // Continue sweeping from the current physical position; pick the direction
    // with the most travel room so we never start by slamming an endpoint.
    sweepDir = (currentAngle <= (SERVO_MIN_ANGLE + SERVO_MAX_ANGLE) / 2) ? 1 : -1;
    logState("-> MODE_SEARCH (valid command)");
    publishStatus();
  }
}

// True while the startup/retained ignore window is active.
bool inStartupIgnoreWindow() {
  return (millis() - subscribeMs) < STARTUP_IGNORE_MS;
}

// ============================================================================
// MQTT CALLBACK
// ============================================================================

void mqtt_callback(char* topic, byte* payload, unsigned int length) {
  String message = "";
  for (unsigned int i = 0; i < length; i++) {
    message += (char)payload[i];
  }

  if (DEBUG) {
    Serial.print("[");
    Serial.print(millis());
    Serial.print("ms] RX [");
    Serial.print(topic);
    Serial.print("]: '");
    Serial.print(message);
    Serial.println("'");
  }

  // 1) Reject empty payloads (includes our own retained-clear publishes).
  if (length == 0 || message.length() == 0) {
    if (DEBUG) Serial.println("   ignored: empty message");
    return;
  }

  // 2) Startup / retained guard: ignore everything in the ignore window so a
  //    retained or stale message delivered at connect cannot move the servo.
  if (inStartupIgnoreWindow()) {
    if (DEBUG) Serial.println("   ignored: startup/retained guard window");
    return;
  }

  // Horizontal angle => always tracking mode toward that angle.
  if (strcmp(topic, topic_horizontal) == 0) {
    int angle = parseAngleFromMessage(message);
    if (angle < SERVO_MIN_ANGLE || angle > SERVO_MAX_ANGLE) {
      if (DEBUG) Serial.println("   ignored: invalid/out-of-range angle");
      return;
    }
    if (DEBUG) {
      Serial.print("   cmd=angle ");
      Serial.print(angle);
      Serial.println(" -> TRACK");
    }
    enterTrackMode(angle);
    return;
  }

  // Commands.
  if (strcmp(topic, topic_command) == 0) {
    String command = parseCommandFromMessage(message);
    command.toLowerCase();
    command.trim();

    if (command.length() == 0) {
      if (DEBUG) Serial.println("   ignored: empty/unknown command");
      return;
    }

    if (DEBUG) {
      Serial.print("   cmd=");
      Serial.println(command);
    }

    if (command == "search" || command == "sweep") {
      enterSearchMode();
    } else if (command == "track" || command == "stop") {
      enterTrackMode(currentAngle);  // hold here, stop sweeping
    } else if (command == "center") {
      enterTrackMode(SERVO_CENTER_ANGLE);
    } else if (command == "idle") {
      mode = MODE_IDLE;              // explicit park: stop all motion, hold
      targetAngle = currentAngle;
      logState("-> MODE_IDLE (command)");
      publishStatus();
    } else if (command == "left" || command == "move_left") {
      enterTrackMode(currentAngle - SERVO_STEP_SIZE);
    } else if (command == "right" || command == "move_right") {
      enterTrackMode(currentAngle + SERVO_STEP_SIZE);
    } else {
      if (DEBUG) Serial.println("   ignored: unrecognised command");
    }
  }
}

// ============================================================================
// SERVO STATE MACHINE — incremental, smooth, runs every loop()
// ============================================================================

void updateServo() {
  unsigned long now = millis();

  // IDLE: servo is completely stationary. No writes, no tracking, no sweep.
  // The servo holds whatever angle it was initialised/left at.
  if (mode == MODE_IDLE) {
    return;
  }

  if (mode == MODE_SEARCH) {
    if (now - lastServoStepMs < SERVO_SEARCH_STEP_MS) {
      return;
    }
    lastServoStepMs = now;

    currentAngle += sweepDir;
    if (currentAngle >= SERVO_MAX_ANGLE) {
      currentAngle = SERVO_MAX_ANGLE;
      sweepDir = -1;
    } else if (currentAngle <= SERVO_MIN_ANGLE) {
      currentAngle = SERVO_MIN_ANGLE;
      sweepDir = 1;
    }
    cameraServo.write(currentAngle);
    return;
  }

  // MODE_TRACK
  if (currentAngle == targetAngle) {
    return;
  }
  if (now - lastServoStepMs < SERVO_TRACK_STEP_MS) {
    return;
  }
  lastServoStepMs = now;

  currentAngle += (currentAngle < targetAngle) ? 1 : -1;
  cameraServo.write(currentAngle);

  if (currentAngle == targetAngle) {
    publishStatus();
  }
}

// ============================================================================
// PUBLISH STATUS
// ============================================================================

void publishStatus() {
  bool moving = (mode == MODE_SEARCH) ||
                (mode == MODE_TRACK && currentAngle != targetAngle);
  String status = "{\"angle\":" + String(currentAngle) +
                  ",\"target\":" + String(targetAngle) +
                  ",\"mode\":\"" + String(modeName(mode)) + "\"" +
                  ",\"moving\":" + (moving ? "true" : "false") + "}";
  client.publish(topic_status, status.c_str());
}

// ============================================================================
// MAIN LOOP
// ============================================================================

void loop() {
  ensureMqttConnected();
  client.loop();

  updateServo();

  unsigned long now = millis();
  if (now - lastStatusUpdate > STATUS_UPDATE_INTERVAL) {
    publishStatus();
    lastStatusUpdate = now;
  }
}
