/*
 * ESP8266 Camera Tracker with Servo Motor
 *
 * Controls a pan servo that tracks a locked face based on MQTT commands from
 * the Python face-recognition system.
 *
 * ============================================================================
 * STATE MACHINE
 * ============================================================================
 *
 *  BOOT
 *   └─> INITIALIZE  (WiFi + MQTT setup)
 *        └─> IDLE   (default; servo stationary at center angle)
 *                 │
 *            [start_tracking received]
 *                 │
 *              SESSION ACTIVE
 *              ┌──────────────────────────────┐
 *              │  IDLE     : no motion         │
 *              │  TRACKING : servo → target    │
 *              │  SEARCHING: autonomous sweep  │
 *              │  CENTERED : servo holds       │
 *              └──────────────────────────────┘
 *                 │
 *            [stop_tracking / watchdog / crash LWT]
 *                 │
 *              IDLE  (servo freezes immediately, no sweep)
 *
 * ============================================================================
 * SERVO MODES (runs in loop(), INDEPENDENT of MQTT arrival timing)
 * ============================================================================
 *   MODE_IDLE    : DEFAULT state.  Servo is completely stationary. No tracking,
 *                  no sweeping.  Servo only leaves IDLE after a valid command
 *                  arrives inside an ACTIVE SESSION.
 *   MODE_TRACK   : Smoothly drive currentAngle -> targetAngle (1 deg / step).
 *                  targetAngle is set by the PC on `camera/track/horizontal`.
 *   MODE_SEARCH  : Autonomous continuous sweep 0 -> 180 -> 0 -> 180 ...
 *                  Started by the PC sending "search". Motion is generated
 *                  ON THE ESP so it is smooth regardless of MQTT jitter.
 *
 * ============================================================================
 * SESSION MANAGEMENT
 * ============================================================================
 *   - ESP ignores ALL motion commands until a valid session is active.
 *   - Session activated by "start_tracking" command on camera/track/command.
 *   - Session terminated by "stop_tracking" command (or LWT from PC crash).
 *   - Watchdog: if no command arrives for SESSION_WATCHDOG_MS, session ends
 *     and servo returns to IDLE automatically.
 *   - Session commands ("start_tracking" / "stop_tracking") are accepted even
 *     during the STARTUP_IGNORE_MS window so the PC can activate promptly.
 *
 * ============================================================================
 * STARTUP SAFETY
 * ============================================================================
 *   - Default mode: MODE_IDLE, sessionActive: false (no motion).
 *   - On connect, ESP clears retained messages on command topics BEFORE
 *     subscribing, so retained/stale messages can never move the servo.
 *   - All inbound messages (except session commands) are dropped for
 *     STARTUP_IGNORE_MS after subscribing to absorb broker-queued messages.
 *   - Empty / non-numeric / out-of-range messages are rejected.
 *   - Random client ID prevents QOS-1 message replay from previous sessions.
 *
 * Hardware:
 *   - ESP8266 (NodeMCU / Wemos D1 Mini)
 *   - Servo on SERVO_PIN, VCC 5V, common GND
 *
 * MQTT Topics:
 *   - camera/track/horizontal : target angle 0-180
 *   - camera/track/command    : "start_tracking" | "stop_tracking" | "search"
 *                               "track" | "center" | "left" | "right" | "idle"
 *   - camera/status           : ESP publishes status JSON
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
const char* topic_command    = "camera/track/command";
const char* topic_status     = "camera/status";

// Servo settings
const int SERVO_PIN         = 12;   // GPIO12
const int SERVO_MIN_ANGLE   = 0;
const int SERVO_MAX_ANGLE   = 180;
const int SERVO_CENTER_ANGLE = 90;
const int SERVO_STEP_SIZE   = 10;   // nudge step for left/right commands

// Motion timing — 1 degree every N ms gives smooth, jitter-free motion.
// 7ms/deg ≈ 140 deg/s: fast target acquisition, still smooth.
const unsigned long SERVO_TRACK_STEP_MS  = 7;
const unsigned long SERVO_SEARCH_STEP_MS = 7;

// Debug — event-level logging only (state changes, commands, movement reasons).
#define DEBUG true

// Ignore non-session MQTT messages for this long after (re)subscribing.
// Guarantees retained/stale/startup messages cannot move the servo at boot.
const unsigned long STARTUP_IGNORE_MS = 2000;

// Session watchdog: if no valid command arrives for this long the session is
// considered dead and the servo returns to IDLE automatically.
const unsigned long SESSION_WATCHDOG_MS = 5000;

// ============================================================================
// STATE
// ============================================================================

enum ServoMode { MODE_IDLE, MODE_TRACK, MODE_SEARCH };

WiFiClient   espClient;
PubSubClient client(espClient);
Servo        cameraServo;

// Servo state
ServoMode    mode         = MODE_IDLE;
int          currentAngle = SERVO_CENTER_ANGLE;
int          targetAngle  = SERVO_CENTER_ANGLE;
int          sweepDir     = 1;   // +1 toward MAX, -1 toward MIN

// Session state — the ONLY gate that allows motion commands through
bool         sessionActive       = false;
unsigned long lastSessionCommandMs = 0;

// Timing
unsigned long lastServoStepMs          = 0;
unsigned long lastStatusUpdate         = 0;
unsigned long lastReconnectAttemptMs   = 0;
unsigned long subscribeMs              = 0;   // when last (re)subscribed

const unsigned long STATUS_UPDATE_INTERVAL    = 250;
const unsigned long MQTT_RECONNECT_INTERVAL_MS = 3000;

// ============================================================================
// HELPERS
// ============================================================================

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
  Serial.print(" | session=");
  Serial.print(sessionActive ? "ON" : "OFF");
  Serial.print(" state=");
  Serial.print(modeName(mode));
  Serial.print(" angle=");
  Serial.print(currentAngle);
  Serial.print(" target=");
  Serial.println(targetAngle);
}

// True while the startup/retained ignore window is active.
bool inStartupIgnoreWindow() {
  return (millis() - subscribeMs) < STARTUP_IGNORE_MS;
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

  // Initialise servo to centre, then HOLD (IDLE). No session active.
  cameraServo.attach(SERVO_PIN);
  cameraServo.write(SERVO_CENTER_ANGLE);
  currentAngle = SERVO_CENTER_ANGLE;
  targetAngle  = SERVO_CENTER_ANGLE;
  mode         = MODE_IDLE;
  sessionActive = false;
  lastSessionCommandMs = millis();
  lastServoStepMs      = millis();
  logState("BOOT: servo at center, IDLE, no session");

  setup_wifi();
  client.setServer(mqtt_server, mqtt_port);
  client.setCallback(mqtt_callback);

  Serial.println("\nSetup complete. IDLE — waiting for START_TRACKING from PC.\n");
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
  if (client.connected()) return;

  unsigned long now = millis();
  if (now - lastReconnectAttemptMs < MQTT_RECONNECT_INTERVAL_MS) return;
  lastReconnectAttemptMs = now;

  Serial.print("Connecting to MQTT broker...");

  // Random client ID prevents broker from replaying QOS-1 messages from a
  // previous session to us when we reconnect after a reboot.
  String clientId = "ESP8266_CameraTracker_";
  clientId += String(random(0xffff), HEX);

  if (client.connect(clientId.c_str(), mqtt_user, mqtt_password)) {
    Serial.println(" connected!");

    // Clear any RETAINED messages on command topics BEFORE subscribing.
    // An empty retained payload deletes the broker's stored message so a
    // stale retained "search"/angle from a previous session cannot replay.
    client.publish(topic_horizontal, "", true);
    client.publish(topic_command,    "", true);

    client.subscribe(topic_horizontal);
    client.subscribe(topic_command);

    // Reset session: a new MQTT connection means we lost the previous session
    // (e.g. ESP rebooted). The PC will re-send start_tracking from its
    // _on_connect callback, re-establishing the session cleanly.
    sessionActive = false;
    lastSessionCommandMs = millis();

    // Begin the startup ignore window: drop everything for STARTUP_IGNORE_MS.
    // Session commands ("start_tracking"/"stop_tracking") are still accepted
    // during this window so the PC can activate promptly.
    subscribeMs = millis();
    logState("MQTT connected: cleared retained, subscribed, waiting for session");

    publishStatus();
  } else {
    Serial.print(" failed, rc=");
    Serial.println(client.state());
  }
}

// ============================================================================
// MESSAGE PARSING
// ============================================================================

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
  if (trimmed.length() == 0) return -1;
  if (trimmed.startsWith("{")) {
    int keyPos = trimmed.indexOf("\"angle\"");
    if (keyPos >= 0) {
      int colonPos = trimmed.indexOf(':', keyPos);
      if (colonPos >= 0) {
        String num = trimmed.substring(colonPos + 1);
        num.trim();
        int end = 0;
        while (end < (int)num.length() &&
               (isDigit(num.charAt(end)) ||
                (end == 0 && (num.charAt(0) == '-' || num.charAt(0) == '+')))) {
          end++;
        }
        num = num.substring(0, end);
        if (!isNumericString(num)) return -1;
        return num.toInt();
      }
    }
    return -1;
  }
  if (!isNumericString(trimmed)) return -1;
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
        int quoteEnd   = trimmed.indexOf('"', quoteStart + 1);
        if (quoteStart >= 0 && quoteEnd > quoteStart) {
          return trimmed.substring(quoteStart + 1, quoteEnd);
        }
      }
    }
    return "";
  }
  return trimmed;
}

// ============================================================================
// STATE TRANSITIONS
// ============================================================================

void enterTrackMode(int angle) {
  angle = constrain(angle, SERVO_MIN_ANGLE, SERVO_MAX_ANGLE);
  targetAngle = angle;
  lastSessionCommandMs = millis();  // feed watchdog
  if (mode != MODE_TRACK) {
    mode = MODE_TRACK;
    logState("-> MODE_TRACK");
    publishStatus();
  }
}

void enterSearchMode() {
  lastSessionCommandMs = millis();  // feed watchdog
  if (mode != MODE_SEARCH) {
    mode = MODE_SEARCH;
    sweepDir = (currentAngle <= (SERVO_MIN_ANGLE + SERVO_MAX_ANGLE) / 2) ? 1 : -1;
    logState("-> MODE_SEARCH");
    publishStatus();
  }
}

void enterIdleMode(const char* reason) {
  sessionActive = false;
  mode          = MODE_IDLE;
  targetAngle   = currentAngle;   // freeze at current physical position
  logState(reason);
  publishStatus();
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

  // ── 1) Reject empty payloads (includes our own retained-clear publishes) ──
  if (length == 0 || message.length() == 0) {
    if (DEBUG) Serial.println("   ignored: empty message");
    return;
  }

  // ── 2) SESSION CONTROL — accepted even during the startup ignore window ──
  //    These commands are the ONLY ones that bypass both the startup guard
  //    and the session gate, so the PC can activate/deactivate at any time.
  if (strcmp(topic, topic_command) == 0) {
    String cmd = parseCommandFromMessage(message);
    cmd.toLowerCase();
    cmd.trim();

    if (cmd == "start_tracking") {
      // Activate session: servo is now allowed to receive motion commands.
      // Mode stays IDLE until the first real motion command arrives.
      sessionActive        = true;
      lastSessionCommandMs = millis();
      mode                 = MODE_IDLE;   // hold until first real command
      targetAngle          = currentAngle;
      if (DEBUG) Serial.println("   SESSION STARTED -> waiting for motion commands");
      logState("-> SESSION ACTIVE (start_tracking)");
      publishStatus();
      return;
    }

    if (cmd == "stop_tracking") {
      // Deactivate session immediately: freeze servo, return to IDLE.
      // This is also sent as Last Will Testament by the PC on crash.
      if (DEBUG) Serial.println("   SESSION STOPPED -> IDLE");
      enterIdleMode("-> SESSION ENDED (stop_tracking)");
      return;
    }
  }

  // ── 3) Startup / retained guard: drop everything except session commands ──
  if (inStartupIgnoreWindow()) {
    if (DEBUG) Serial.println("   ignored: startup guard window active");
    return;
  }

  // ── 4) Session gate: no session → no motion ──────────────────────────────
  if (!sessionActive) {
    if (DEBUG) Serial.println("   ignored: no active tracking session");
    return;
  }

  // ── 5) Valid command inside an active session — feed the watchdog ─────────
  lastSessionCommandMs = millis();

  // ── 6) Horizontal angle → always tracking mode toward that angle ──────────
  if (strcmp(topic, topic_horizontal) == 0) {
    int angle = parseAngleFromMessage(message);
    if (angle < SERVO_MIN_ANGLE || angle > SERVO_MAX_ANGLE) {
      if (DEBUG) Serial.println("   ignored: invalid/out-of-range angle");
      return;
    }
    if (DEBUG) {
      Serial.print("   angle=");
      Serial.print(angle);
      Serial.println(" -> TRACK");
    }
    enterTrackMode(angle);
    return;
  }

  // ── 7) Command string ─────────────────────────────────────────────────────
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
      enterTrackMode(currentAngle);   // hold here, cancel sweep
    } else if (command == "center") {
      enterTrackMode(SERVO_CENTER_ANGLE);
    } else if (command == "idle") {
      // Explicit park within session (stops motion but keeps session alive).
      mode        = MODE_IDLE;
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

  // IDLE: completely stationary. No writes, no tracking, no sweep.
  if (mode == MODE_IDLE) return;

  if (mode == MODE_SEARCH) {
    if (now - lastServoStepMs < SERVO_SEARCH_STEP_MS) return;
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
  if (currentAngle == targetAngle) return;
  if (now - lastServoStepMs < SERVO_TRACK_STEP_MS) return;
  lastServoStepMs = now;

  currentAngle += (currentAngle < targetAngle) ? 1 : -1;
  cameraServo.write(currentAngle);

  if (currentAngle == targetAngle) {
    publishStatus();
  }
}

// ============================================================================
// SESSION WATCHDOG — runs every loop()
// ============================================================================

void checkSessionWatchdog() {
  if (!sessionActive) return;
  unsigned long now = millis();
  if (now - lastSessionCommandMs > SESSION_WATCHDOG_MS) {
    Serial.print("[");
    Serial.print(now);
    Serial.print("ms] WATCHDOG: no command for ");
    Serial.print(SESSION_WATCHDOG_MS);
    Serial.println("ms -> session ended, returning to IDLE");
    enterIdleMode("-> WATCHDOG TIMEOUT -> IDLE");
  }
}

// ============================================================================
// PUBLISH STATUS
// ============================================================================

void publishStatus() {
  bool moving = (mode == MODE_SEARCH) ||
                (mode == MODE_TRACK && currentAngle != targetAngle);
  String status =
      "{\"angle\":"   + String(currentAngle) +
      ",\"target\":"  + String(targetAngle) +
      ",\"mode\":\""  + String(modeName(mode)) + "\"" +
      ",\"moving\":"  + (moving ? "true" : "false") +
      ",\"session\":" + (sessionActive ? "true" : "false") + "}";
  client.publish(topic_status, status.c_str());
}

// ============================================================================
// MAIN LOOP
// ============================================================================

void loop() {
  ensureMqttConnected();
  client.loop();

  // Check watchdog before running servo to stop immediately if timed out.
  checkSessionWatchdog();

  updateServo();

  unsigned long now = millis();
  if (now - lastStatusUpdate > STATUS_UPDATE_INTERVAL) {
    publishStatus();
    lastStatusUpdate = now;
  }
}
