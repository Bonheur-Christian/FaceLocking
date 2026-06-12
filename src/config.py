"""
Configuration module for face recognition pipeline.
Centralized settings for all modules.
"""

from pathlib import Path
from typing import Tuple

# ============================================================================
# PROJECT PATHS
# ============================================================================

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DB_DIR = DATA_DIR / "db"
ENROLL_DIR = DATA_DIR / "enroll"
DEBUG_ALIGNED_DIR = DATA_DIR / "debug_aligned"
MODELS_DIR = PROJECT_ROOT / "models"

# History directory for locked person activity logs
HISTORY_DIR = DATA_DIR / "history"
ACTIVITY_LOGS_DIR = HISTORY_DIR  # Alias for backward compatibility

# Database files
DB_NPZ_PATH = DB_DIR / "face_db.npz"
DB_JSON_PATH = DB_DIR / "face_db.json"

# ONNX / MediaPipe model paths
ARCFACE_MODEL_PATH = MODELS_DIR / "embedder_arcface.onnx"
FACE_LANDMARKER_MODEL_PATH = MODELS_DIR / "face_landmarker.task"

# ============================================================================
# FACE DETECTION SETTINGS
# ============================================================================

HAAR_CASCADE_PATH = None  # None = use OpenCV default haarcascade_frontalface_default.xml
HAAR_SCALE_FACTOR = 1.15  # Larger step = fewer Haar passes (faster)
HAAR_MIN_NEIGHBORS = 4
HAAR_MIN_SIZE = (50, 50)
DETECT_FRAME_SCALE = 0.75  # Run detection on downscaled frame (big speedup)
HAAR_FLAGS = None  # cv2.CASCADE_SCALE_IMAGE if needed

# ============================================================================
# 5-POINT LANDMARK DETECTION (MediaPipe FaceMesh)
# ============================================================================

LANDMARK_INDICES = {
    "left_eye": 33,
    "right_eye": 263,
    "nose_tip": 1,
    "mouth_left": 61,
    "mouth_right": 291,
}

FACEMESH_STATIC_MODE = False
FACEMESH_MAX_NUM_FACES = 3
FACEMESH_REFINE_LANDMARKS = False  # Off = much faster; still accurate for 5-pt align
FACEMESH_MIN_DETECTION_CONFIDENCE = 0.5
FACEMESH_MIN_TRACKING_CONFIDENCE = 0.5

# ============================================================================
# FACE ALIGNMENT SETTINGS
# ============================================================================

ALIGNMENT_OUTPUT_SIZE: Tuple[int, int] = (112, 112)  # Standard for ArcFace
ALIGNMENT_PAD_X = 0.55
ALIGNMENT_PAD_Y_TOP = 0.85
ALIGNMENT_PAD_Y_BOT = 1.15
MIN_EYE_DISTANCE = 8.0  # Pixels; sanity check for geometry

# ============================================================================
# ARCFACE EMBEDDING SETTINGS
# ============================================================================

EMBEDDING_INPUT_SIZE = (112, 112)
EMBEDDING_DIM = 512
EMBEDDING_NORM_EPSILON = 1e-12
ONNX_EXECUTION_PROVIDER = "CPUExecutionProvider"
ONNX_INTRA_OP_THREADS = 4  # Parallel CPU inference for ArcFace

# Preprocessing constants (standard for ArcFace/InsightFace)
EMBEDDING_PREPROCESS_MEAN = 127.5
EMBEDDING_PREPROCESS_SCALE = 128.0

# ============================================================================
# ENROLLMENT SETTINGS
# ============================================================================

SAMPLES_NEEDED_FOR_ENROLLMENT = 20
MIN_SAMPLES_TO_SAVE = 5
MAX_EXISTING_CROPS_PER_PERSON = 300
AUTO_CAPTURE_INTERVAL_SECONDS = 0.25
SAVE_ENROLLMENT_CROPS = True

# ----------------------------------------------------------------------------
# ENROLLMENT QUALITY GATES — only high-quality samples are stored.
# ----------------------------------------------------------------------------
# Blur: variance of the Laplacian of the aligned crop. Below = too blurry.
ENROLL_BLUR_MIN_VAR = 45.0
# Face size in the ORIGINAL frame (reject tiny / far faces).
ENROLL_MIN_FACE_PX = 90          # min bbox width (px)
ENROLL_MIN_EYE_DIST_PX = 32      # min inter-ocular distance (px)
# Pose: how far the nose may sit from the eye-midline, as a fraction of the
# inter-ocular distance. Rejects extreme yaw / profile faces.
ENROLL_MAX_POSE_RATIO = 0.35
# Reject a new sample whose cosine similarity to an already-kept sample exceeds
# this (near-duplicate → adds no diversity). Keeps the template varied.
ENROLL_DUP_SIMILARITY = 0.965
# Cap on stored embeddings per person (diverse subset is kept).
ENROLL_MAX_EMBEDDINGS = 30

# ----------------------------------------------------------------------------
# RUNTIME RECOGNITION QUALITY GATE
# ----------------------------------------------------------------------------
# Skip embedding faces that are clearly too blurry to recognise reliably.
RECOGNITION_BLUR_MIN_VAR = 25.0

# ============================================================================
# RECOGNITION & THRESHOLD SETTINGS
# ============================================================================

DEFAULT_DISTANCE_THRESHOLD = 0.52  # Cosine distance; lower = stricter / more accurate
SIMILARITY_THRESHOLD = 0.70  # 1 - distance_threshold (for reference)
TARGET_FAR = 0.01  # 1% False Accept Rate for threshold tuning
THRESHOLD_SWEEP_RANGE = (0.10, 1.20, 0.01)  # (start, end, step)

# Aliases for the canonical recognition tuning interface (Issue #7)
RECOGNITION_THRESHOLD = DEFAULT_DISTANCE_THRESHOLD  # Accept identity if dist <= this
FACE_MATCH_THRESHOLD = 0.55  # Looser gate used to keep an existing lock alive
MAX_FACES = 5  # Maximum simultaneous faces to detect/recognize
RECOGNITION_INTERVAL = 4
RECOGNITION_INTERVAL_LOCKED = 2
RECOGNITION_INTERVAL_FACE = 4  # Re-embed every N frames while face visible
RECOGNITION_INTERVAL_LOCKED_FACE = 1   # Re-embed locked track every frame for fastest re-lock
RECOGNITION_INTERVAL_IDLE = 20
RECOGNITION_COOLDOWN_FRAMES = 4
RECOGNITION_COOLDOWN_FRAMES_FACE = 3
RECOGNITION_STABILIZE_WINDOW = 5  # Frames of voting history (temporal stability)
RECOGNITION_MIN_CONSISTENT = 3    # Consistent votes required to flip identity state

# Multi-embedding matching: each person stores several enrollment embeddings.
# A query is scored against a person using the mean of its TOP-K nearest
# stored embeddings (robust to pose variation; avoids single-sample outliers).
RECOGNITION_TOPK = 3

# ============================================================================
# RECOGNITION PIPELINE OPTIMIZATION
# ============================================================================

PROCESS_EVERY_N_FRAMES = 2
PROCESS_EVERY_N_FRAMES_FACE = 2  # Detect + embed every 2nd frame when face present
PROCESS_EVERY_N_FRAMES_IDLE = 6  # Slow scan when no face
PROCESS_EVERY_N_FRAMES_TRACKING = 2
DETECT_EVERY_N_FRAMES_FACE = 2  # Tracker fills gaps between detect passes
DETECT_EVERY_N_FRAMES_IDLE = 5
ACTION_DETECT_EVERY_N_FRAMES = 4  # Blink/smile less often
ROI_MARGIN_FACTOR = 0.25  # Expand ROI by this fraction of width/height
SMOOTHING_WINDOW = 5  # EMA smoothing for face center X
ACCEPT_HOLD_FRAMES = 10  # Keep boxes/labels alive between skipped frames
MAX_FACES_TO_PROCESS = 2  # Cap embed cost in crowded scenes
LOCK_CONFIDENCE_MAX_DISTANCE = 0.45  # Maintain lock while distance <= this
LOCK_RELEASE_DISTANCE = 0.58 # Drop lock if distance exceeds this

# ============================================================================
# CAMERA SETTINGS
# ============================================================================

CAMERA_INDEX = 1  # Use python -m src.camera_utils to find the right index
CAMERA_AUTO_DETECT = True  # Fall back to other indices if CAMERA_INDEX fails
CAMERA_FRAME_WIDTH = 640
CAMERA_FRAME_HEIGHT = 480
CAMERA_FPS_TARGET = 30
CAMERA_OPEN_VERIFY_FRAMES = 5  # Test reads when opening
CAMERA_READ_RETRIES = 5  # Per-frame read attempts before counting a failure
CAMERA_RECONNECT_AFTER_FAILS = 3  # Consecutive bad reads before reconnect
CAMERA_RECONNECT_DELAY_SEC = 0.35  # Pause before reopening the device

# ============================================================================
# DISPLAY SETTINGS
# ============================================================================

DISPLAY_FPS = True
DISPLAY_CONFIDENCE = True
DISPLAY_LANDMARKS = False  # Off = faster overlay drawing
DISPLAY_ALIGNED_PREVIEW = False
PREVIEW_THUMB_SIZE = 112
DISPLAY_WINDOW_WIDTH = 800
DISPLAY_WINDOW_HEIGHT = 450

# Font settings for OpenCV text rendering
FONT_FACE = 2  # cv2.FONT_HERSHEY_SIMPLEX
FONT_SCALE = 0.7
FONT_THICKNESS = 2
FONT_COLOR_OK = (0, 255, 0)  # Green (BGR)
FONT_COLOR_REJECT = (0, 0, 255)  # Red (BGR)
FONT_COLOR_TEXT = (255, 255, 255)  # White (BGR)

# ============================================================================
# FACE LOCKING (Term-02 Week-04)
# ============================================================================

LOCK_RELEASE_FRAMES = 45
LOCK_MOVEMENT_THRESHOLD_PX = 25
LOCK_EAR_BLINK_THRESHOLD = 0.22
LOCK_SMILE_MOUTH_RATIO = 1.18
LOCK_ACTION_COOLDOWN_FRAMES = 10
LOCK_EAR_LEFT_INDICES = (33, 160, 158, 133, 153, 144)
LOCK_EAR_RIGHT_INDICES = (362, 385, 387, 263, 373, 380)
LOCK_MOUTH_LEFT_INDEX = 61
LOCK_MOUTH_RIGHT_INDEX = 291

# ============================================================================
# MQTT CAMERA TRACKING SETTINGS
# ============================================================================

# MQTT Broker settings
MQTT_BROKER_HOST = "157.173.101.159"  # Your MQTT broker IP
MQTT_BROKER_PORT = 1883
MQTT_USERNAME = None  # Optional: Set if broker requires authentication
MQTT_PASSWORD = None  # Optional: Set if broker requires authentication

# MQTT Topics
MQTT_TOPIC_HORIZONTAL = "camera/track/horizontal"
MQTT_TOPIC_COMMAND = "camera/track/command"
MQTT_TOPIC_STATUS = "camera/status"
MQTT_KEEPALIVE = 30
MQTT_QOS = 1
MQTT_MIN_COMMAND_INTERVAL_MS = 20  # Tracking rate limiter (~50 cmds/sec max)

# ----------------------------------------------------------------------------
# SERVO CONTROL (must match ESP8266 firmware limits)
# ----------------------------------------------------------------------------
SERVO_MIN_ANGLE = 0    # Full pan range for tracking + search
SERVO_MAX_ANGLE = 180
SERVO_CENTER_ANGLE = 90
# Canonical aliases (Issue #7 "servo:" group)
MIN_ANGLE = SERVO_MIN_ANGLE
MAX_ANGLE = SERVO_MAX_ANGLE
CENTER_ANGLE = SERVO_CENTER_ANGLE

# Mounting sign: +1 if increasing angle pans the camera toward image-right,
# -1 if it pans toward image-left. Flip this if the camera chases the wrong way.
SERVO_DIRECTION_SIGN = 1

# ----------------------------------------------------------------------------
# PAN CONTROLLER (P + D on the smoothed normalized horizontal error)
# ----------------------------------------------------------------------------
# The controller is a POSITION controller that integrates onto the PC's OWN
# commanded target angle (NOT the lagging ESP-reported angle). This removes the
# transport-delay feedback loop that previously caused trembling / oscillation.
SERVO_PID_KP = 9.0    # Proportional gain on normalized error [-1, 1]
SERVO_PID_KI = 0.0    # Integral disabled (avoids windup; not needed for pan)
SERVO_PID_KD = 2.0    # Light derivative on the smoothed error (damping)
SERVO_PID_I_CLAMP = 8.0  # Max absolute integral contribution (deg) if KI used

# Rate limiting / smoothing
# SERVO_MAX_SPEED = max degrees the target may change PER UPDATE. Small steps
# give the "46,47,48..." incremental motion the spec requires and let the ESP
# keep up without queueing commands.
SERVO_MAX_SPEED = 5      # Max degrees per update (fast but smooth centering)
MAX_SPEED = SERVO_MAX_SPEED  # Alias (Issue #7)
SMOOTHING_FACTOR = 0.45  # EMA on raw error: lower = smoother (less jitter)
SERVO_OUTPUT_SMOOTHING = 0.55  # EMA alpha on the OUTPUT angle command
SERVO_STEP_SIZE = 5      # Manual nudge step (left/right keys, command mode)
SERVO_MAX_PAN_OFFSET = 90  # Max degrees from center when tracking

# ----------------------------------------------------------------------------
# CENTERING DEAD-BAND — the ONLY condition under which the servo may stop.
# ----------------------------------------------------------------------------
# The servo stops ONLY when a detected, locked face is within CENTER_DEADBAND
# pixels of the frame centre. Off-centre by more than this => KEEP MOVING.
CENTER_DEADBAND = 30          # Pixels: |error| <= this == "centered" -> stop
# Tiny hysteresis so the servo does not chatter exactly on the boundary: once
# centred it resumes chasing only after the face drifts past this wider band.
CENTER_DEADBAND_RESUME = 40   # Pixels: resume tracking once |error| exceeds this
# Backwards-compatible aliases.
CENTER_DEAD_ZONE = CENTER_DEADBAND
CENTER_DEAD_ZONE_OUTER = CENTER_DEADBAND_RESUME
SERVO_DEAD_ZONE_NORMALIZED = 0.06  # Legacy normalized fallback

# ----------------------------------------------------------------------------
# TRACKING BEHAVIOR
# ----------------------------------------------------------------------------
ENABLE_AUTO_CENTERING = True  # Continuous pan to keep locked face centered
CENTERING_TOLERANCE = 0.08    # Normalized half-width counted as "centered" (was 0.10)
FRAMES_TO_LOCK_CENTER = 6     # Frames inside center zone before "centered" state (was 8)

# Legacy step-based mode (kept for compatibility; PID path is preferred)
MOVEMENT_BASED_TRACKING = False
MOVEMENT_SENSITIVITY = 25
TRACKING_MOVEMENT_THRESHOLD = 0.05

# ----------------------------------------------------------------------------
# LOST-TARGET SEARCH & REACQUISITION (Issues #4, #5)
# ----------------------------------------------------------------------------
LOST_TARGET_TIMEOUT = 0.0        # Enter SEARCH immediately when target leaves frame (no servo freeze)
LOST_TARGET_FRAMES = 4           # Frames a track may be missing before it is dropped
# If locked track stays visible but is unrecognized for this long → treat as lost
LOST_TARGET_UNRECOGNIZED_SEC = 1.5

# Search sweep — full 0°–180° coverage, CONTINUOUS, never pausing.
#
# Primary path: the ESP firmware generates the sweep ON-BOARD (autonomous,
# perfectly smooth, immune to MQTT/WiFi timing, reverses instantly at the
# edges). The PC only sends the "search" command. FLASH THE FIRMWARE for this.
#
# Fallback path (firmware without autonomous search): the PC streams small,
# dense angle waypoints so motion stays as smooth as possible.
SEARCH_MIN_ANGLE = 0
SEARCH_MAX_ANGLE = 180

# --- Search sweep parameters -------------------------------------------------
# The sweep runs in a background daemon thread, completely independent of the
# camera frame rate, recognition speed, or MQTT publish timing.
#
#   SEARCH_STEP            degrees per step  (2° → smooth, no large skips)
#   SEARCH_UPDATE_INTERVAL seconds between steps (thread sleep interval)
#   SEARCH_SPEED           effective speed = SEARCH_STEP / SEARCH_UPDATE_INTERVAL
#
# Default: 2° every 14 ms ≈ 143 °/s. 0° → 180° in ~1.26 s.
SEARCH_STEP = 2                  # degrees per waypoint
SEARCH_UPDATE_INTERVAL = 0.014   # seconds between waypoints (14 ms)
SEARCH_SPEED = SEARCH_STEP / SEARCH_UPDATE_INTERVAL   # ~142.8 °/s (informational)
# Legacy aliases
SEARCH_SWEEP_SPEED = SEARCH_SPEED
SEARCH_SWEEP_STEP = SEARCH_STEP
SEARCH_PC_SWEEP_STEP = SEARCH_STEP

SEARCH_REACQUIRE_FRAMES = 2      # Confirmed frames before re-locking
SEARCH_ENDPOINT_DWELL_SEC = 0.0  # NEVER dwell at edges — reversal is instant
# Kept for backward compatibility only (not used by the thread-based sweep)
SEARCH_CMD_RESEND_SEC = 1.0
SEARCH_FALLBACK_DETECT_SEC = 0.4
SEARCH_ESP_MOTION_DELTA = 3
SEARCH_START_DIRECTION = "last"
SEARCH_EXPAND_ENABLED = False

# Legacy fixed sweep (used only if SEARCH_EXPAND_ENABLED is False)
FRAMES_BEFORE_SEARCH = 24
SEARCH_INTERVAL_SEC = 0.15
SEARCH_SWEEP_POSITIONS = [
    0, 15, 30, 45, 60, 75, 90, 105, 120, 135, 150, 165, 180,
    165, 150, 135, 120, 105, 90, 75, 60, 45, 30, 15, 0,
]

# ----------------------------------------------------------------------------
# BOUNDING-BOX COLORS (BGR) — Issue #2
# ----------------------------------------------------------------------------
COLOR_UNKNOWN = (0, 0, 255)     # Red
COLOR_KNOWN = (255, 0, 0)       # Blue (recognized, not locked)
COLOR_LOCKED = (0, 255, 0)      # Green (locked target)
COLOR_LOST = (0, 165, 255)      # Orange (lock lost / searching)
COLOR_HUD = (0, 255, 0)         # Debug overlay text

# ============================================================================
# DEBUG & LOGGING
# ============================================================================

DEBUG_MODE = False
VERBOSE_LOGGING = False
TRACKING_LOG_ENABLED = True  # Console logs for lock visibility and servo decisions
TRACKING_STATUS_INTERVAL_SEC = 2.0  # Min seconds between repeated hold/missing messages
SAVE_DEBUG_FRAMES = False

# ============================================================================
# WEB DASHBOARD
# ============================================================================

DASHBOARD_ENABLED = False
DASHBOARD_HOST = "127.0.0.1"  # Use 0.0.0.0 to view from other devices on LAN
DASHBOARD_PORT = 8765
DASHBOARD_STREAM_FPS = 12  # MJPEG stream rate (lower = less CPU)
DASHBOARD_SERVO_HISTORY = 40
DASHBOARD_HEADLESS = False  # True = no OpenCV window, browser only

# ============================================================================
# QUALITY CHECKS
# ============================================================================

REQUIRE_ALIGNED_CROP_SIZE = (112, 112)
MIN_FACE_BBOX_AREA = 60 * 60  # Minimum 60x60 for detection

# Geometry constraints
KPS_MUST_BE_IN_HAAR_BOX = True
KPS_IN_BOX_MARGIN = 0.35  # Generous margin
KPS_IN_BOX_MIN_RATIO = 0.60  # At least 60% of points inside box


def ensure_dirs() -> None:
    """Create all necessary directories if they don't exist."""
    DB_DIR.mkdir(parents=True, exist_ok=True)
    ENROLL_DIR.mkdir(parents=True, exist_ok=True)
    DEBUG_ALIGNED_DIR.mkdir(parents=True, exist_ok=True)
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)


if __name__ == "__main__":
    ensure_dirs()
    print("Configuration loaded and directories created.")
