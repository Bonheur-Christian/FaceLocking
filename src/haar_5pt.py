"""
Combined Haar + MediaPipe FaceMesh 5-point detector.
Provides robust face detection with landmark confirmation.
"""

from dataclasses import dataclass
from typing import Optional, List, Tuple
import cv2
import numpy as np

try:
    import mediapipe as mp
except ImportError:
    mp = None

from . import config


@dataclass
class FaceDetection:
    """Face detection result with 5 landmarks."""
    x1: int
    y1: int
    x2: int
    y2: int
    score: float
    landmarks: np.ndarray  # (5, 2) float32


class HaarMediaPipeFaceDetector:
    """Robust face detector using Haar + MediaPipe FaceMesh."""
    
    def __init__(self, min_size=config.HAAR_MIN_SIZE):
        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        self.haar = cv2.CascadeClassifier(cascade_path)
        
        if self.haar.empty():
            raise RuntimeError(f"Failed to load Haar cascade from {cascade_path}")
        
        if mp is None:
            raise RuntimeError("mediapipe not installed. Run: pip install mediapipe")
        
        self.mesh = mp.solutions.face_mesh.FaceMesh(
            static_image_mode=config.FACEMESH_STATIC_MODE,
            max_num_faces=5,  # Support up to 5 faces simultaneously
            refine_landmarks=config.FACEMESH_REFINE_LANDMARKS,
            min_detection_confidence=config.FACEMESH_MIN_DETECTION_CONFIDENCE,
            min_tracking_confidence=config.FACEMESH_MIN_TRACKING_CONFIDENCE,
        )
        
        self.min_size = min_size
    
    def _bbox_from_landmarks(self, kps):
        """Build face-like bbox from 5 landmarks with padding."""
        x_min = float(np.min(kps[:, 0]))
        x_max = float(np.max(kps[:, 0]))
        y_min = float(np.min(kps[:, 1]))
        y_max = float(np.max(kps[:, 1]))
        
        w = max(1.0, x_max - x_min)
        h = max(1.0, y_max - y_min)
        
        x1 = x_min - config.ALIGNMENT_PAD_X * w
        x2 = x_max + config.ALIGNMENT_PAD_X * w
        y1 = y_min - config.ALIGNMENT_PAD_Y_TOP * h
        y2 = y_max + config.ALIGNMENT_PAD_Y_BOT * h
        
        return np.array([x1, y1, x2, y2], dtype=np.float32)
    
    def _clip_bbox(self, bbox, H, W):
        """Clip bounding box to image boundaries."""
        x1, y1, x2, y2 = bbox.astype(np.float32)
        x1 = max(0, min(W - 1, x1))
        y1 = max(0, min(H - 1, y1))
        x2 = max(0, min(W - 1, x2))
        y2 = max(0, min(H - 1, y2))
        return int(x1), int(y1), int(x2), int(y2)
    
    def _validate_landmarks_geometry(self, kps):
        """Sanity check on landmark positions."""
        eye_dist = np.linalg.norm(kps[1] - kps[0])
        if eye_dist < config.MIN_EYE_DISTANCE:
            return False
        
        # Mouth should be below nose
        if not (kps[3, 1] > kps[2, 1] and kps[4, 1] > kps[2, 1]):
            return False
        
        return True
    
    def detect(self, frame):
        """
        Detect faces in frame. Supports multiple faces simultaneously.
        
        Args:
            frame: BGR image
        
        Returns:
            List of FaceDetection objects
        """
        H, W = frame.shape[:2]
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Haar detection
        haar_faces = self.haar.detectMultiScale(
            gray,
            scaleFactor=config.HAAR_SCALE_FACTOR,
            minNeighbors=config.HAAR_MIN_NEIGHBORS,
            minSize=self.min_size,
        )
        
        if len(haar_faces) == 0:
            return []
        
        # FaceMesh confirmation - process all faces
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.mesh.process(rgb)
        
        if not results.multi_face_landmarks:
            return []
        
        # Process each MediaPipe face and match to Haar detections
        detected_faces = []
        
        for face_landmarks in results.multi_face_landmarks:
            # Extract 5 landmarks
            landmarks_full = face_landmarks.landmark
            
            kps = []
            indices = [
                config.LANDMARK_INDICES["left_eye"],
                config.LANDMARK_INDICES["right_eye"],
                config.LANDMARK_INDICES["nose_tip"],
                config.LANDMARK_INDICES["mouth_left"],
                config.LANDMARK_INDICES["mouth_right"],
            ]
            
            for idx in indices:
                lm = landmarks_full[idx]
                kps.append([lm.x * W, lm.y * H])
            
            kps = np.array(kps, dtype=np.float32)
            
            # Enforce ordering
            if kps[0, 0] > kps[1, 0]:
                kps[[0, 1]] = kps[[1, 0]]
            if kps[3, 0] > kps[4, 0]:
                kps[[3, 4]] = kps[[4, 3]]
            
            # Validate geometry
            if not self._validate_landmarks_geometry(kps):
                continue
            
            # Find which Haar box this face belongs to (if any)
            matched_haar = None
            best_overlap = 0
            
            for x, y, w, h in haar_faces:
                # Check if landmarks are inside this Haar box
                if config.KPS_MUST_BE_IN_HAAR_BOX:
                    margin = config.KPS_IN_BOX_MARGIN
                    x1m = x - margin * w
                    y1m = y - margin * h
                    x2m = x + (1.0 + margin) * w
                    y2m = y + (1.0 + margin) * h
                    
                    inside = (
                        (kps[:, 0] >= x1m) & (kps[:, 0] <= x2m) &
                        (kps[:, 1] >= y1m) & (kps[:, 1] <= y2m)
                    )
                    
                    overlap = inside.mean()
                    if overlap > best_overlap and overlap >= config.KPS_IN_BOX_MIN_RATIO:
                        best_overlap = overlap
                        matched_haar = (x, y, w, h)
            
            # Skip if no matching Haar box found
            if matched_haar is None and config.KPS_MUST_BE_IN_HAAR_BOX:
                continue
            
            # Build bbox from landmarks
            bbox = self._bbox_from_landmarks(kps)
            x1, y1, x2, y2 = self._clip_bbox(bbox, H, W)
            
            detected_faces.append(
                FaceDetection(
                    x1=x1, y1=y1, x2=x2, y2=y2,
                    score=1.0,
                    landmarks=kps.astype(np.float32)
                )
            )
        
        return detected_faces
