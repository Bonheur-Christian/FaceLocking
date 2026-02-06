"""
Action detection module: smile, blink (and optional face movement).
Uses MediaPipe Face Mesh for full landmarks. Shared by recognize.py and lock.py.
"""

from typing import List, Optional, Tuple, Dict, Any
import cv2
import numpy as np

try:
    import mediapipe as mp
except ImportError:
    mp = None

from . import config


def get_face_mesh_landmarks(frame: np.ndarray) -> Optional[List[Any]]:
    """
    Run MediaPipe Face Mesh on frame; return first face landmark list or None.
    Caller must have at least one face in frame for meaningful results.
    """
    if mp is None:
        return None
    H, W = frame.shape[:2]
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    mesh = mp.solutions.face_mesh.FaceMesh(
        static_image_mode=False,
        max_num_faces=1,
        refine_landmarks=True,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5,
    )
    results = mesh.process(rgb)
    mesh.close()
    if not results.multi_face_landmarks:
        return None
    return results.multi_face_landmarks[0].landmark


def _ear_from_landmarks(landmarks_list: List[Any], indices: Tuple[int, ...], W: int, H: int) -> float:
    """Eye Aspect Ratio from 6 landmark indices (lower = more closed)."""
    pts = []
    for i in indices:
        lm = landmarks_list[i]
        pts.append((lm.x * W, lm.y * H))
    p1, p2, p3, p4, p5, p6 = [np.array(p) for p in pts]
    v1 = np.linalg.norm(p2 - p6)
    v2 = np.linalg.norm(p3 - p5)
    h = np.linalg.norm(p1 - p4)
    if h < 1e-6:
        return 0.5
    return (v1 + v2) / (2.0 * h)


def _mouth_width_from_landmarks(
    landmarks_list: List[Any], left_idx: int, right_idx: int, W: int, H: int
) -> float:
    """Mouth width in pixels."""
    l = landmarks_list[left_idx]
    r = landmarks_list[right_idx]
    return float(np.hypot((r.x - l.x) * W, (r.y - l.y) * H))


def compute_ear(landmarks_list: List[Any], W: int, H: int) -> float:
    """Average Eye Aspect Ratio (both eyes). Lower = eyes more closed."""
    ear_left = _ear_from_landmarks(landmarks_list, config.LOCK_EAR_LEFT_INDICES, W, H)
    ear_right = _ear_from_landmarks(landmarks_list, config.LOCK_EAR_RIGHT_INDICES, W, H)
    return (ear_left + ear_right) / 2.0


def compute_mouth_width(landmarks_list: List[Any], W: int, H: int) -> float:
    """Mouth width in pixels."""
    return _mouth_width_from_landmarks(
        landmarks_list,
        config.LOCK_MOUTH_LEFT_INDEX,
        config.LOCK_MOUTH_RIGHT_INDEX,
        W,
        H,
    )


def detect_smile_blink(
    frame: np.ndarray,
    baseline_mouth_width: Optional[float],
    mouth_width_samples: List[float],
    last_action_frame: Dict[str, int],
    frame_idx: int,
    cooldown_frames: int = 10,
) -> Tuple[List[str], Optional[float], List[float]]:
    """
    Detect blink and smile from full-face landmarks.
    Returns:
        actions: list of "blink" and/or "smile" (empty if none this frame)
        new_baseline_mouth: updated baseline (median of recent samples) or None
        new_mouth_samples: updated list of recent mouth widths (caller can pass back next time)
    """
    actions: List[str] = []
    H, W = frame.shape[:2]
    landmarks_list = get_face_mesh_landmarks(frame)
    if landmarks_list is None:
        return actions, baseline_mouth_width, mouth_width_samples

    ear = compute_ear(landmarks_list, W, H)
    mouth_width = compute_mouth_width(landmarks_list, W, H)

    # Blink: EAR drops below threshold
    if ear < config.LOCK_EAR_BLINK_THRESHOLD:
        if frame_idx - last_action_frame.get("blink", -999) >= cooldown_frames:
            actions.append("blink")
            last_action_frame["blink"] = frame_idx

    # Smile: mouth width above baseline * ratio (need baseline first)
    mouth_width_samples = list(mouth_width_samples) + [mouth_width]
    if len(mouth_width_samples) > 30:
        mouth_width_samples = mouth_width_samples[-30:]
    if baseline_mouth_width is None and len(mouth_width_samples) >= 15:
        baseline_mouth_width = float(np.median(mouth_width_samples))
    if baseline_mouth_width is not None and baseline_mouth_width > 1.0:
        if mouth_width >= baseline_mouth_width * config.LOCK_SMILE_MOUTH_RATIO:
            if frame_idx - last_action_frame.get("smile", -999) >= cooldown_frames:
                actions.append("smile")
                last_action_frame["smile"] = frame_idx

    return actions, baseline_mouth_width, mouth_width_samples
