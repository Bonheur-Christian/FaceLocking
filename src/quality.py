"""
Face-quality gates shared by enrollment and runtime recognition.

Rejecting low-quality faces (blurry, tiny, partial, extreme pose) is the single
biggest lever on recognition accuracy: a clean gallery of sharp, frontal,
well-sized faces produces tight, discriminative embeddings, while a few bad
samples poison a person's template.
"""

from typing import Optional, Tuple

import cv2
import numpy as np

from . import config


def blur_variance(image_bgr: np.ndarray) -> float:
    """Variance of the Laplacian — higher = sharper. Low values mean blur."""
    if image_bgr is None or image_bgr.size == 0:
        return 0.0
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY) if image_bgr.ndim == 3 else image_bgr
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def inter_ocular_distance(landmarks: np.ndarray) -> float:
    """Pixel distance between the two eye landmarks (rows 0 and 1)."""
    return float(np.linalg.norm(landmarks[1] - landmarks[0]))


def pose_ratio(landmarks: np.ndarray) -> float:
    """
    Frontal-ness measure in [0, ~1+]: horizontal offset of the nose from the
    eye midpoint, normalized by inter-ocular distance. ~0 = frontal, large =
    turned head / profile.
    """
    eye_mid_x = (landmarks[0, 0] + landmarks[1, 0]) / 2.0
    nose_x = landmarks[2, 0]
    iod = inter_ocular_distance(landmarks)
    if iod < 1e-3:
        return 1.0
    return abs(nose_x - eye_mid_x) / iod


def assess_enrollment(
    aligned_bgr: np.ndarray,
    landmarks: np.ndarray,
    bbox: Tuple[int, int, int, int],
) -> Tuple[bool, str]:
    """
    Decide whether a face is good enough to ENROLL.

    Returns (ok, reason). reason describes the rejection when ok is False.
    """
    x1, y1, x2, y2 = bbox
    face_w = x2 - x1
    if face_w < config.ENROLL_MIN_FACE_PX:
        return False, f"face too small ({face_w}px)"

    iod = inter_ocular_distance(landmarks)
    if iod < config.ENROLL_MIN_EYE_DIST_PX:
        return False, f"eyes too close ({iod:.0f}px) — face too far/tiny"

    pr = pose_ratio(landmarks)
    if pr > config.ENROLL_MAX_POSE_RATIO:
        return False, f"extreme head angle (pose={pr:.2f})"

    bv = blur_variance(aligned_bgr)
    if bv < config.ENROLL_BLUR_MIN_VAR:
        return False, f"too blurry (var={bv:.0f})"

    return True, "ok"


def is_sharp_enough_for_recognition(aligned_bgr: np.ndarray) -> bool:
    """Lenient blur gate used during live recognition."""
    return blur_variance(aligned_bgr) >= config.RECOGNITION_BLUR_MIN_VAR


def is_duplicate(
    new_emb: np.ndarray,
    kept_embeddings,
    threshold: Optional[float] = None,
) -> bool:
    """True if new_emb is near-identical to any already-kept embedding."""
    if threshold is None:
        threshold = config.ENROLL_DUP_SIMILARITY
    if not len(kept_embeddings):
        return False
    q = new_emb.reshape(-1).astype(np.float32)
    for e in kept_embeddings:
        if float(np.dot(q, e.reshape(-1).astype(np.float32))) > threshold:
            return True
    return False
