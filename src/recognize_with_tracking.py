"""
Live face recognition with MQTT camera tracking.
Tracks locked person and sends servo commands to ESP8266.
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
from .activity_logger import ActivityLogger
from .mqtt_camera_controller import MQTTCameraController


def load_database():
    """Load enrolled face database."""
    if not config.DB_NPZ_PATH.exists():
        print("ERROR: Database not found. Run enrollment first.")
        return {}
    
    data = np.load(str(config.DB_NPZ_PATH), allow_pickle=True)
    return {k: data[k].astype(np.float32) for k in data.files}


def choose_lock_identity(names: list) -> Optional[str]:
    """Prompt user to choose one identity to lock to."""
    if not names:
        return None
    print("\nEnrolled identities:")
    for i, n in enumerate(names, 1):
        print(f"  {i}. {n}")
    print("Lock/track one person? Enter number or name (or Enter for none): ", end="")
    try:
        raw = input().strip()
    except EOFError:
        return None
    if not raw:
        return None
    
    if raw.isdigit():
        idx = int(raw)
        if 1 <= idx <= len(names):
            return names[idx - 1]
        return None
    
    if raw in names:
        return raw
    
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


def main(
    start_fullscreen: bool = False,
    enable_mqtt: bool = True,
    mqtt_broker: str = None,
    mqtt_port: int = None
):
    """
    Live recognition with MQTT camera tracking.
    
    Args:
        start_fullscreen: If True, start in fullscreen mode
        enable_mqtt: Enable MQTT camera tracking
        mqtt_broker: MQTT broker hostname/IP (None = use config default)
        mqtt_port: MQTT broker port (None = use config default)
    """
    # Use config defaults if not specified
    if mqtt_broker is None:
        mqtt_broker = config.MQTT_BROKER_HOST
    if mqtt_port is None:
        mqtt_port = config.MQTT_BROKER_PORT
    
    db = load_database()
    
    if not db:
        print("ERROR: No enrolled identities found. Run enrollment first.")
        return False
    
    print(f"✓ Loaded {len(db)} enrolled identities")
    
    detector = HaarMediaPipeFaceDetector(min_size=config.HAAR_MIN_SIZE)
    aligner = FaceAligner()
    embedder = ArcFaceEmbedder(config.ARCFACE_MODEL_PATH)
    
    names = sorted(db.keys())
    embeddings_matrix = np.stack([db[n].reshape(-1) for n in names], axis=0)
    
    lock_name: Optional[str] = choose_lock_identity(names)
    
    # Initialize MQTT camera controller
    mqtt_controller: Optional[MQTTCameraController] = None
    if enable_mqtt and lock_name:
        print(f"\n🎥 Initializing MQTT camera tracking...")
        try:
            mqtt_controller = MQTTCameraController(
                broker_host=mqtt_broker,
                broker_port=mqtt_port
            )
            import time
            time.sleep(1)  # Wait for connection
            if mqtt_controller.is_connected:
                print("✓ Camera tracking enabled!")
                mqtt_controller.center()  # Center camera at start
            else:
                print("⚠ MQTT not connected - tracking disabled")
                mqtt_controller = None
        except Exception as e:
            print(f"⚠ Could not initialize MQTT: {e}")
            mqtt_controller = None
    
    # Initialize activity logger
    activity_logger: Optional[ActivityLogger] = None
    if lock_name:
        print(f"Lock: {lock_name} (camera will track this person)")
        print(f"✓ Activity history will be saved to: {config.HISTORY_DIR}/")
        activity_logger = ActivityLogger(lock_name, config.HISTORY_DIR)
    else:
        print("Lock: (none) – all enrolled identities shown by name")
    
    # Camera setup
    cap = None
    for attempt in range(3):
        cap = cv2.VideoCapture(config.CAMERA_INDEX)
        if cap.isOpened():
            break
        cap.release()
        if attempt < 2:
            print(f"Attempt {attempt + 1}/3: Camera not ready, retrying...")
            import time
            time.sleep(1)
    
    if not cap or not cap.isOpened():
        print("ERROR: Cannot open camera after 3 attempts.")
        return False
    
    # Get frame dimensions for tracking calculations
    ret, test_frame = cap.read()
    if not ret:
        print("ERROR: Cannot read from camera")
        return False
    frame_height, frame_width = test_frame.shape[:2]
    print(f"✓ Camera resolution: {frame_width}x{frame_height}")
    
    threshold = config.DEFAULT_DISTANCE_THRESHOLD
    
    print("\n🎬 Live Recognition with Camera Tracking")
    print("Controls:")
    print("  q  - Quit")
    print("  r  - Reload database")
    print("  l  - Clear lock")
    print("  f  - Toggle fullscreen")
    print("  c  - Center camera")
    print("  s  - Toggle search mode on/off")
    print("  +  - Increase threshold")
    print("  -  - Decrease threshold")
    
    # Action detection state
    baseline_mouth_width: Optional[float] = None
    mouth_width_samples: List[float] = []
    last_action_frame: Dict[str, int] = {}
    frame_idx = 0
    action_display: List[Tuple[str, int]] = []
    ACTION_DISPLAY_DURATION = 20
    
    # Tracking state
    last_tracked_x = None
    tracking_smoothing = []  # Smooth tracking over multiple frames
    TRACKING_SMOOTH_WINDOW = 5
    
    # Search mode state (when person not found)
    search_mode = False
    frames_without_person = 0
    FRAMES_BEFORE_SEARCH = 30  # Start searching after 30 frames (~3 seconds at 10 FPS)
    last_search_time = 0
    SEARCH_INTERVAL = 2.0  # Move to next position every 2 seconds
    current_search_angle = 90
    
    # Fullscreen state
    is_fullscreen = start_fullscreen
    window_name = "Live Recognition + Tracking"
    
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL | cv2.WINDOW_KEEPRATIO)
    cv2.resizeWindow(window_name, 1920, 1080)
    
    if start_fullscreen:
        cv2.setWindowProperty(window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
        print("Starting in FULLSCREEN mode")
    
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
            
            # Smile / blink detection
            detected_actions = []
            if faces and hasattr(action_module, "detect_smile_blink"):
                cooldown = getattr(config, "LOCK_ACTION_COOLDOWN_FRAMES", 10)
                detected_actions, baseline_mouth_width, mouth_width_samples = action_module.detect_smile_blink(
                    frame, baseline_mouth_width, mouth_width_samples,
                    last_action_frame, frame_idx, cooldown_frames=cooldown,
                )
                for act in detected_actions:
                    action_display.append((act.capitalize() + "!", ACTION_DISPLAY_DURATION))
            
            action_display = [(label, n - 1) for label, n in action_display if n > 1]
            
            locked_person_found = False
            locked_face_center = None
            
            for face_idx, face in enumerate(faces):
                aligned, _ = aligner.align(frame, face.landmarks)
                query_emb, _ = embedder.embed(aligned)
                
                dists = np.array([cosine_distance(query_emb, embeddings_matrix[i]) for i in range(len(names))])
                best_idx = int(np.argmin(dists))
                best_dist = dists[best_idx]
                best_match_name = names[best_idx]
                
                accepted = best_dist <= threshold
                if accepted:
                    name = best_match_name
                    confidence = 1.0 - best_dist
                    color = (0, 255, 0)
                    
                    if lock_name and best_match_name == lock_name:
                        display_name = f"{name} (TRACKING)"
                        is_locked_person = True
                        locked_person_found = True
                        locked_face_center = ((face.x1 + face.x2) / 2, (face.y1 + face.y2) / 2)
                    else:
                        display_name = name
                        is_locked_person = False
                else:
                    name = "Unknown"
                    display_name = "Unknown"
                    confidence = 0
                    color = (0, 0, 255)
                    is_locked_person = False
                
                # Handle locked person
                if is_locked_person:
                    # Log activities
                    if activity_logger:
                        face_center = ((face.x1 + face.x2) / 2, (face.y1 + face.y2) / 2)
                        
                        for act in detected_actions:
                            activity_logger.log_activity(act, frame_idx, face_center)
                        
                        movements = activity_logger.detect_and_log_movement(face_center, frame_idx)
                        for movement in movements:
                            action_display.append((movement.replace("_", " ").title() + "!", ACTION_DISPLAY_DURATION))
                            
                            # Send MQTT command for camera tracking
                            print(f"🎯 Movement detected: {movement}")
                            if mqtt_controller:
                                print(f"   MQTT controller exists: {mqtt_controller.is_connected}")
                                if mqtt_controller.is_connected:
                                    mqtt_controller.track_face_movement(movement)
                                else:
                                    print("   ⚠️  MQTT controller NOT connected!")
                            else:
                                print("   ⚠️  MQTT controller is None!")
                    
                    # Update camera position based on face location
                    if mqtt_controller and mqtt_controller.is_connected:
                        face_center_x = (face.x1 + face.x2) / 2
                        
                        # Smooth tracking
                        tracking_smoothing.append(face_center_x)
                        if len(tracking_smoothing) > TRACKING_SMOOTH_WINDOW:
                            tracking_smoothing.pop(0)
                        
                        smoothed_x = sum(tracking_smoothing) / len(tracking_smoothing)
                        
                        # Only update if significant movement
                        if last_tracked_x is None or abs(smoothed_x - last_tracked_x) > frame_width * 0.05:
                            mqtt_controller.track_face_position(smoothed_x, frame_width)
                            last_tracked_x = smoothed_x
                    
                    # Draw tracking visualization
                    cv2.rectangle(vis, (face.x1, face.y1), (face.x2, face.y2), (0, 255, 255), 3)
                    for (x, y) in face.landmarks.astype(int):
                        cv2.rectangle(vis, (int(x) - 3, int(y) - 3), (int(x) + 3, int(y) + 3), (0, 255, 255), 1)
                    
                    cv2.putText(
                        vis, f"{display_name} ({best_dist:.3f})", (face.x1, max(0, face.y1 - 10)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2
                    )
                    
                    # Draw confidence bar
                    bar_w = 100
                    bar_h = 20
                    bar_x = face.x1
                    bar_y = face.y1 - 35
                    cv2.rectangle(vis, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h), (200, 200, 200), 1)
                    if accepted:
                        filled_w = int(bar_w * confidence)
                        cv2.rectangle(vis, (bar_x, bar_y), (bar_x + filled_w, bar_y + bar_h), (0, 255, 255), -1)
                
                elif accepted:
                    cv2.putText(
                        vis, display_name, (face.x1, max(0, face.y1 - 10)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2
                    )
                else:
                    cv2.rectangle(vis, (face.x1, face.y1), (face.x2, face.y2), color, 2)
                    cv2.putText(
                        vis, display_name, (face.x1, max(0, face.y1 - 10)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2
                    )
            
            # Draw tracking indicator
            if locked_face_center and mqtt_controller and mqtt_controller.is_connected:
                cx, cy = int(locked_face_center[0]), int(locked_face_center[1])
                cv2.circle(vis, (cx, cy), 10, (0, 255, 255), 2)
                cv2.line(vis, (cx - 15, cy), (cx + 15, cy), (0, 255, 255), 2)
                cv2.line(vis, (cx, cy - 15), (cx, cy + 15), (0, 255, 255), 2)
            
            # Search mode: sweep camera when locked person not found
            if lock_name and mqtt_controller and mqtt_controller.is_connected:
                if locked_person_found:
                    # Person found - reset search mode
                    if search_mode:
                        print("✓ Person found - stopping search")
                        search_mode = False
                    frames_without_person = 0
                else:
                    # Person not found - increment counter
                    frames_without_person += 1
                    
                    if frames_without_person >= FRAMES_BEFORE_SEARCH:
                        if not search_mode:
                            print("🔍 Person lost - starting search mode")
                            search_mode = True
                            last_search_time = time.time()
                        
                        # Perform sweep at intervals
                        current_time = time.time()
                        if current_time - last_search_time >= SEARCH_INTERVAL:
                            current_search_angle = mqtt_controller.search_sweep(current_search_angle)
                            last_search_time = current_time
                            print(f"🔄 Searching... moving to {current_search_angle}°")
            
            # Display search mode indicator
            if search_mode:
                search_text = f"🔍 SEARCHING... ({frames_without_person} frames)"
                cv2.putText(
                    vis, search_text, (10, vis.shape[0] - 170),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2
                )
            
            # Header
            lock_status = f"Lock: {lock_name}" if lock_name else "Lock: (none)"
            mqtt_status = "📡 MQTT: ON" if (mqtt_controller and mqtt_controller.is_connected) else "📡 MQTT: OFF"
            header = f"{lock_status} | {mqtt_status} | Thresh: {threshold:.2f} | IDs: {len(names)} | FPS: {fps:.1f}"
            cv2.putText(
                vis, header, (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2
            )
            
            # Action labels
            y_action = 58
            for label, _ in action_display:
                cv2.putText(
                    vis, label, (10, y_action),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2
                )
                y_action += 28
            
            # Activity statistics
            if activity_logger:
                stats = activity_logger.get_statistics()
                y_stat = vis.shape[0] - 140
                cv2.putText(
                    vis, "Activity Log:", (10, y_stat),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2
                )
                y_stat += 22
                cv2.putText(
                    vis, f"Blinks: {stats['counts']['blink']}", (10, y_stat),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1
                )
                y_stat += 20
                cv2.putText(
                    vis, f"Smiles: {stats['counts']['smile']}", (10, y_stat),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1
                )
                y_stat += 20
                cv2.putText(
                    vis, f"Move L/R: {stats['counts']['move_left']}/{stats['counts']['move_right']}", (10, y_stat),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1
                )
            
            # Camera servo status
            if mqtt_controller and mqtt_controller.is_connected:
                servo_status = mqtt_controller.get_status()
                if servo_status:
                    y_servo = vis.shape[0] - 40
                    angle = servo_status.get('angle', '?')
                    cv2.putText(
                        vis, f"Servo: {angle}°", (10, y_servo),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2
                    )
            
            # Controls hint
            cv2.putText(
                vis, "q=quit r=reload l=clear c=center s=search f=fullscreen +/-=threshold", (10, vis.shape[0] - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1
            )
            
            cv2.imshow(window_name, vis)
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break
            elif key == ord("r"):
                db = load_database()
                names = sorted(db.keys())
                embeddings_matrix = np.stack([db[n].reshape(-1) for n in names], axis=0)
                if lock_name and lock_name not in names:
                    lock_name = None
                print(f"✓ Reloaded {len(db)} identities")
            elif key == ord("l"):
                if activity_logger:
                    activity_logger.save_summary()
                    activity_logger = None
                lock_name = None
                if mqtt_controller:
                    mqtt_controller.center()
                print("Lock cleared")
            elif key == ord("c"):
                if mqtt_controller and mqtt_controller.is_connected:
                    mqtt_controller.center()
                    search_mode = False
                    frames_without_person = 0
                    print("Camera centered")
            elif key == ord("s"):
                # Toggle search mode manually
                if mqtt_controller and mqtt_controller.is_connected:
                    search_mode = not search_mode
                    if search_mode:
                        print("🔍 Search mode: ON (manual)")
                        frames_without_person = FRAMES_BEFORE_SEARCH
                        last_search_time = time.time()
                    else:
                        print("⏸️  Search mode: OFF")
                        frames_without_person = 0
                        mqtt_controller.center()
            elif key == ord("f"):
                is_fullscreen = not is_fullscreen
                if is_fullscreen:
                    cv2.setWindowProperty(window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
                else:
                    cv2.setWindowProperty(window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_NORMAL)
            elif key in (ord("+"), ord("=")):
                threshold = min(1.0, threshold + 0.01)
                print(f"Threshold: {threshold:.2f}")
            elif key == ord("-"):
                threshold = max(0.0, threshold - 0.01)
                print(f"Threshold: {threshold:.2f}")
    
    finally:
        if activity_logger:
            activity_logger.save_summary()
        
        if mqtt_controller:
            mqtt_controller.center()  # Center camera before exit
            mqtt_controller.disconnect()
        
        cap.release()
        cv2.destroyAllWindows()
    
    print("✓ Recognition ended.")
    return True


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Live face recognition with MQTT camera tracking")
    parser.add_argument("--fullscreen", "-f", action="store_true", help="Start in fullscreen mode")
    parser.add_argument("--no-mqtt", action="store_true", help="Disable MQTT tracking")
    parser.add_argument("--broker", default="localhost", help="MQTT broker hostname/IP")
    parser.add_argument("--port", type=int, default=1883, help="MQTT broker port")
    args = parser.parse_args()
    
    success = main(
        start_fullscreen=args.fullscreen,
        enable_mqtt=not args.no_mqtt,
        mqtt_broker=args.broker,
        mqtt_port=args.port
    )
    sys.exit(0 if success else 1)
