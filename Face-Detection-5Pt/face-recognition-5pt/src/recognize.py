"""
Live face recognition module.
Real-time face matching against enrolled database.
"""

import sys
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import cv2
import numpy as np


from . import config
from .haar_5pt import HaarMediaPipeFaceDetector
from .align import FaceAligner
from .embed import ArcFaceEmbedder

from . import actions as action_module


def load_database():
    """Load enrolled face database."""
    if not config.DB_NPZ_PATH.exists():
        print("ERROR: Database not found. Run enrollment first.")
        return {}
    
    data = np.load(str(config.DB_NPZ_PATH), allow_pickle=True)
    return {k: data[k].astype(np.float32) for k in data.files}


def choose_lock_identity(names: list) -> Optional[str]:
    """
    Prompt user to choose one identity to lock to, or none (recognize all).
    Returns the name to lock to, or None to accept all enrolled.
    """
    if not names:
        return None
    print("\nEnrolled identities:")
    for i, n in enumerate(names, 1):
        print(f"  {i}. {n}")
    print("Lock/highlight one person? Enter number or name (or Enter for none): ", end="")
    try:
        raw = input().strip()
    except EOFError:
        return None
    if not raw:
        return None
    # By number (1-based)
    if raw.isdigit():
        idx = int(raw)
        if 1 <= idx <= len(names):
            return names[idx - 1]
        return None
    # By name (exact match)
    if raw in names:
        return raw
    # Case-insensitive fallback
    low = raw.lower()
    for n in names:
        if n.lower() == low:
            return n
    print(f"Unknown name '{raw}'. Proceeding with all identities.")
    return None


def cosine_distance(a: np.ndarray, b: np.ndarray) -> float:
    """Compute cosine distance."""
    a = a.reshape(-1).astype(np.float32)
    b = b.reshape(-1).astype(np.float32)
    similarity = float(np.dot(a, b))
    return 1.0 - similarity


def main():
    """Live recognition pipeline."""
    db = load_database()
    
    if not db:
        print("ERROR: No enrolled identities found. Run enrollment first.")
        return False
    
    print(f"✓ Loaded {len(db)} enrolled identities")
    
    detector = HaarMediaPipeFaceDetector(min_size=config.HAAR_MIN_SIZE)
    aligner = FaceAligner()
    embedder = ArcFaceEmbedder(config.ARCFACE_MODEL_PATH)
    
    # Pre-stack embeddings for fast matching
    names = sorted(db.keys())
    embeddings_matrix = np.stack([db[n].reshape(-1) for n in names], axis=0)
    
    # Optional: lock = highlight one person as "(locked)" while still recognizing everyone
    lock_name: Optional[str] = choose_lock_identity(names)
    if lock_name:
        print(f"Lock: {lock_name} (they will show as '... (locked)'; others still recognized by name)")
    else:
        print("Lock: (none) – all enrolled identities shown by name")
    
    cap = cv2.VideoCapture(config.CAMERA_INDEX)
    if not cap.isOpened():
        print("ERROR: Cannot open camera.")
        return False
    
    threshold = config.DEFAULT_DISTANCE_THRESHOLD
    
    print("\nLive Recognition (smile & blink detection enabled)")
    print("Controls:")
    print("  q  - Quit")
    print("  r  - Reload database")
    print("  l  - Clear lock (accept all)")
    print("  +  - Increase threshold (more accepts)")
    print("  -  - Decrease threshold (fewer accepts)")
    
    # Action detection state (smile / blink)
    baseline_mouth_width: Optional[float] = None
    mouth_width_samples: List[float] = []
    last_action_frame: Dict[str, int] = {}
    frame_idx = 0
    action_display: List[Tuple[str, int]] = []  # (label, frames_remaining)
    ACTION_DISPLAY_DURATION = 20  # show "Blink!" / "Smile!" for this many frames
    
    try:
        import time
        t0 = time.time()
        frame_count = 0
        fps = 0
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            frame_idx += 1
            frame_count += 1
            elapsed = time.time() - t0
            if elapsed >= 1.0:
                fps = frame_count / elapsed
                frame_count = 0
                t0 = time.time()
            
            vis = frame.copy()
            faces = detector.detect(frame)
            
            # Smile / blink detection (uses MediaPipe Face Mesh on full frame)
            if faces and hasattr(action_module, "detect_smile_blink"):
                cooldown = getattr(config, "LOCK_ACTION_COOLDOWN_FRAMES", 10)
                detected, baseline_mouth_width, mouth_width_samples = action_module.detect_smile_blink(
                    frame, baseline_mouth_width, mouth_width_samples,
                    last_action_frame, frame_idx, cooldown_frames=cooldown,
                )
                for act in detected:
                    action_display.append((act.capitalize() + "!", ACTION_DISPLAY_DURATION))
            # Decay action display
            action_display = [(label, n - 1) for label, n in action_display if n > 1]
            
            for face_idx, face in enumerate(faces):
                # Draw bbox + landmarks
                cv2.rectangle(vis, (face.x1, face.y1), (face.x2, face.y2), (0, 255, 0), 2)
                
                for (x, y) in face.landmarks.astype(int):
                    cv2.circle(vis, (int(x), int(y)), 2, (0, 255, 0), -1)
                
                # Align + embed
                aligned, _ = aligner.align(frame, face.landmarks)
                query_emb, _ = embedder.embed(aligned)
                
                # Match
                dists = np.array([cosine_distance(query_emb, embeddings_matrix[i]) for i in range(len(names))])
                best_idx = int(np.argmin(dists))
                best_dist = dists[best_idx]
                best_match_name = names[best_idx]
                
                # Decision: recognize all enrolled people; lock only adds a "(locked)" label for the chosen one
                accepted = best_dist <= threshold
                if accepted:
                    name = best_match_name
                    confidence = 1.0 - best_dist
                    color = (0, 255, 0)
                    # When locked, mark the locked person so you can still see who else is recognized
                    if lock_name and best_match_name == lock_name:
                        display_name = f"{name} (locked)"
                    else:
                        display_name = name
                else:
                    name = "Unknown"
                    display_name = "Unknown"
                    confidence = 0
                    color = (0, 0, 255)
                
                # Draw label
                cv2.putText(
                    vis, f"{display_name} ({best_dist:.3f})", (face.x1, max(0, face.y1 - 10)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2
                )
                
                # Draw confidence bar
                bar_w = 100
                bar_h = 20
                bar_x = face.x1
                bar_y = face.y1 - 35
                cv2.rectangle(vis, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h), (200, 200, 200), 1)
                if accepted:
                    filled_w = int(bar_w * confidence)
                    cv2.rectangle(vis, (bar_x, bar_y), (bar_x + filled_w, bar_y + bar_h), color, -1)
            
            # Header (show lock status)
            lock_status = f"Lock: {lock_name}" if lock_name else "Lock: (none)"
            header = f"{lock_status} | Thresh: {threshold:.2f} | IDs: {len(names)} | FPS: {fps:.1f}"
            cv2.putText(
                vis, header, (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2
            )
            
            # Action labels (smile / blink) – show for a short time after detection
            y_action = 58
            for label, _ in action_display:
                cv2.putText(
                    vis, label, (10, y_action),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2
                )
                y_action += 28
            
            # Controls hint
            cv2.putText(
                vis, "q=quit r=reload l=clear lock +/-=threshold", (10, vis.shape[0] - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1
            )
            
            cv2.imshow("Live Recognition", vis)
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break
            elif key == ord("r"):
                db = load_database()
                names = sorted(db.keys())
                embeddings_matrix = np.stack([db[n].reshape(-1) for n in names], axis=0)
                if lock_name and lock_name not in names:
                    lock_name = None
                    print("Lock cleared (locked person no longer in database)")
                print(f"✓ Reloaded {len(db)} identities")
            elif key == ord("l"):
                lock_name = None
                print("Lock cleared – no one highlighted as locked")
            elif key in (ord("+"), ord("=")):
                threshold = min(1.0, threshold + 0.01)
                print(f"Threshold: {threshold:.2f}")
            elif key == ord("-"):
                threshold = max(0.0, threshold - 0.01)
                print(f"Threshold: {threshold:.2f}")
    
    finally:
        cap.release()
        cv2.destroyAllWindows()
    
    print("✓ Recognition ended.")
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
