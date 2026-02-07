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

# Database files
DB_NPZ_PATH = DB_DIR / "face_db.npz"
DB_JSON_PATH = DB_DIR / "face_db.json"

# ONNX Model paths
ARCFACE_MODEL_PATH = MODELS_DIR / "embedder_arcface.onnx"

# ============================================================================
# FACE DETECTION SETTINGS
# ============================================================================

HAAR_CASCADE_PATH = None  # None = use OpenCV default haarcascade_frontalface_default.xml
HAAR_SCALE_FACTOR = 1.1
HAAR_MIN_NEIGHBORS = 5
HAAR_MIN_SIZE = (70, 70)
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
FACEMESH_MAX_NUM_FACES = 1
FACEMESH_REFINE_LANDMARKS = True
FACEMESH_MIN_DETECTION_CONFIDENCE = 0.5
FACEMESH_MIN_TRACKING_CONFIDENCE = 0.5

# ============================================================================
# FACE ALIGNMENT SETTINGS
# ============================================================================

ALIGNMENT_OUTPUT_SIZE: Tuple[int, int] = (112, 112)  # Standard for ArcFace
ALIGNMENT_PAD_X = 0.55
ALIGNMENT_PAD_Y_TOP = 0.85
ALIGNMENT_PAD_Y_BOT = 1.15
MIN_EYE_DISTANCE = 12.0  # Pixels; sanity check for geometry

# ============================================================================
# ARCFACE EMBEDDING SETTINGS
# ============================================================================

EMBEDDING_INPUT_SIZE = (112, 112)
EMBEDDING_DIM = 512
EMBEDDING_NORM_EPSILON = 1e-12
ONNX_EXECUTION_PROVIDER = "CPUExecutionProvider"

# Preprocessing constants (standard for ArcFace/InsightFace)
EMBEDDING_PREPROCESS_MEAN = 127.5
EMBEDDING_PREPROCESS_SCALE = 128.0

# ============================================================================
# ENROLLMENT SETTINGS
# ============================================================================

SAMPLES_NEEDED_FOR_ENROLLMENT = 15
MIN_SAMPLES_TO_SAVE = 3
MAX_EXISTING_CROPS_PER_PERSON = 300
AUTO_CAPTURE_INTERVAL_SECONDS = 0.25
SAVE_ENROLLMENT_CROPS = True

# ============================================================================
# RECOGNITION & THRESHOLD SETTINGS
# ============================================================================

DEFAULT_DISTANCE_THRESHOLD = 0.34  # Cosine distance; adjust via +/- keys
SIMILARITY_THRESHOLD = 0.66  # 1 - distance_threshold (for reference)
TARGET_FAR = 0.01  # 1% False Accept Rate for threshold tuning
THRESHOLD_SWEEP_RANGE = (0.10, 1.20, 0.01)  # (start, end, step)

# ============================================================================
# RECOGNITION PIPELINE OPTIMIZATION
# ============================================================================

PROCESS_EVERY_N_FRAMES = 2  # Skip frames for detection (1 = every frame)
ROI_MARGIN_FACTOR = 0.25  # Expand ROI by this fraction of width/height
SMOOTHING_WINDOW = 5  # Temporal smoothing for stability
ACCEPT_HOLD_FRAMES = 3  # Hold "accepted" state for N frames

# ============================================================================
# CAMERA SETTINGS
# ============================================================================

CAMERA_INDEX = 0 # Default: first camera
CAMERA_FRAME_WIDTH = 640
CAMERA_FRAME_HEIGHT = 480
CAMERA_FPS_TARGET = 30

# ============================================================================
# DISPLAY SETTINGS
# ============================================================================

DISPLAY_FPS = True
DISPLAY_CONFIDENCE = True
DISPLAY_LANDMARKS = True
DISPLAY_ALIGNED_PREVIEW = True
PREVIEW_THUMB_SIZE = 112

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
HISTORY_DIR = DATA_DIR / "history"
LOCK_EAR_LEFT_INDICES = (33, 160, 158, 133, 153, 144)
LOCK_EAR_RIGHT_INDICES = (362, 385, 387, 263, 373, 380)
LOCK_MOUTH_LEFT_INDEX = 61
LOCK_MOUTH_RIGHT_INDEX = 291

# ============================================================================
# DEBUG & LOGGING
# ============================================================================

DEBUG_MODE = False
VERBOSE_LOGGING = False
SAVE_DEBUG_FRAMES = False

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
