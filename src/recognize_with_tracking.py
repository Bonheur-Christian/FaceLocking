"""
Live face recognition with MQTT pan tracking and autonomous lost-target search.

State machine
-------------
IDLE        : no identity selected to lock (recognition still runs).
TRACKING    : locked target visible, servo actively centering it.
LOCKED      : locked target visible and centered/stable.
LOST_TARGET : locked track not visible (misses > 0) or gone — search starts immediately.
SEARCHING   : autonomous direction-aware servo sweep; recognition hunts the
              ORIGINAL locked identity only. Never locks anyone else.
REACQUIRING : target seen on a new track ID; waiting SEARCH_REACQUIRE_FRAMES
              stable matches before re-binding the lock.

Transitions
-----------
  TRACKING/LOCKED ──(misses>0 or track gone)──> LOST_TARGET ──> SEARCHING
  SEARCHING ──(same track ID visible+recognized)──> TRACKING
  SEARCHING ──(new track ID, N frames)──> REACQUIRING ──> TRACKING

Performance & multi-face strategy
---------------------------------
Detection runs every frame (smooth boxes). ArcFace embedding is the expensive
step, so the FaceTracker caches recognition per persistent track ID and only
re-embeds on an interval (more often for the locked track). The lock is bound
to a track ID, which prevents identity/lock switching when other known faces
appear.
"""

import sys
import time
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np

from . import config
from . import actions as action_module
from .activity_logger import ActivityLogger
from .align import FaceAligner
from .embed import ArcFaceEmbedder
from .haar_5pt import HaarMediaPipeFaceDetector
from .face_tracker import FaceTracker
from .mqtt_camera_controller import MQTTCameraController
from .recognition_core import (
    build_gallery,
    choose_lock_identity,
    draw_tracks,
    load_database,
    open_camera,
    recognize_face,
)
from .tracking import PanTracker
from .tracking_log import TrackingLogger
from .camera_utils import CameraStream
from .dashboard_state import DashboardState, faces_from_tracks
from .dashboard_server import get_state, start_dashboard_server


def _find_spotted_target(lock_name: str, visible) -> Optional[object]:
    """Best visible track that matches the locked identity."""
    best = None
    for tr in visible:
        if tr.accepted and tr.name == lock_name and tr.misses == 0:
            if best is None or tr.best_dist < best.best_dist:
                best = tr
    return best


def _in_search_mode(
    lock_name: Optional[str],
    state: str,
    lost_since: Optional[float],
) -> bool:
    """True only while actively sweeping — never during REACQUIRING/TRACKING/LOCKED."""
    return bool(
        lock_name
        and lost_since is not None
        and state in ("SEARCHING", "LOST_TARGET")
    )


def _activate_search(
    pan: PanTracker,
    tlog: TrackingLogger,
    lock_name: str,
    state: str,
    lost_since: Optional[float],
) -> Tuple[str, float]:
    """Start or continue autonomous sweep; log once on first entry."""
    now = time.time()
    if lost_since is None:
        lost_since = now
    if state not in ("SEARCHING", "LOST_TARGET"):
        direction = (
            "right" if pan.last_error_sign > 0
            else "left" if pan.last_error_sign < 0
            else "center"
        )
        tlog.search_started(lock_name, pan.last_known_angle, direction)
    pan.arm_search()
    pan.search()
    return "SEARCHING", lost_since


def _draw_debug_overlay(
    vis: np.ndarray,
    state: str,
    lock_name: Optional[str],
    servo_angle,
    face_count: int,
    recog_fps: float,
    track_fps: float,
    mqtt_ok: bool,
    threshold: float,
    lost_for: float,
) -> None:
    """On-screen diagnostics panel (Issue #8)."""
    lines = [
        f"State: {state}",
        f"Locked: {lock_name or '(none)'}",
        f"Servo: {servo_angle}",
        f"Faces: {face_count}",
        f"Recog FPS: {recog_fps:.1f}",
        f"Track FPS: {track_fps:.1f}",
        f"MQTT: {'OK' if mqtt_ok else '--'}",
        f"Thresh: {threshold:.2f}",
    ]
    if state in ("SEARCHING", "LOST_TARGET", "REACQUIRING"):
        lines.append(f"Lost for: {lost_for:.1f}s")

    font = cv2.FONT_HERSHEY_SIMPLEX
    pad = 6
    line_h = 20
    panel_w = 210
    panel_h = line_h * len(lines) + pad
    overlay = vis.copy()
    cv2.rectangle(overlay, (0, 0), (panel_w, panel_h), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.45, vis, 0.55, 0, vis)

    state_color = {
        "LOCKED": config.COLOR_LOCKED,
        "TRACKING": (0, 255, 255),
        "LOST_TARGET": config.COLOR_LOST,
        "SEARCHING": config.COLOR_LOST,
        "REACQUIRING": (0, 200, 255),
        "IDLE": (200, 200, 200),
    }.get(state, config.COLOR_HUD)

    y = pad + 14
    for i, t in enumerate(lines):
        color = state_color if i == 0 else config.COLOR_HUD
        cv2.putText(vis, t, (pad, y), font, 0.5, color, 1, cv2.LINE_AA)
        y += line_h


def _draw_search_banner(vis: np.ndarray, lock_name: str) -> None:
    text = f"SEARCHING FOR TARGET: {lock_name}"
    font = cv2.FONT_HERSHEY_SIMPLEX
    (tw, th), _ = cv2.getTextSize(text, font, 0.8, 2)
    x = (vis.shape[1] - tw) // 2
    y = 40
    cv2.rectangle(vis, (x - 10, y - th - 8), (x + tw + 10, y + 8), config.COLOR_LOST, -1)
    cv2.putText(vis, text, (x, y), font, 0.8, (0, 0, 0), 2, cv2.LINE_AA)


def main(
    start_fullscreen: bool = False,
    enable_mqtt: bool = True,
    mqtt_broker: str = None,
    mqtt_port: int = None,
    enable_dashboard: bool = None,
    headless: bool = None,
) -> bool:
    db = load_database()
    if not db:
        print("ERROR: No enrolled identities. Run: python -m src.enroll")
        return False

    print(f"✓ Loaded {len(db)} enrolled identities")

    detector = HaarMediaPipeFaceDetector(min_size=config.HAAR_MIN_SIZE)
    aligner = FaceAligner()
    embedder = ArcFaceEmbedder(config.ARCFACE_MODEL_PATH)

    names = sorted(db.keys())
    gallery, gallery_owner = build_gallery(db, names)
    total_embs = int(gallery.shape[0])
    print(f"✓ Gallery: {total_embs} embeddings across {len(names)} identities")

    lock_name: Optional[str] = choose_lock_identity(names)
    if not lock_name:
        print("WARNING: No lock selected. Running recognition only (IDLE).")

    if enable_dashboard is None:
        enable_dashboard = config.DASHBOARD_ENABLED
    if headless is None:
        headless = config.DASHBOARD_HEADLESS and enable_dashboard

    dashboard: Optional[DashboardState] = None
    if enable_dashboard:
        try:
            dashboard = get_state()
            start_dashboard_server(state=dashboard)
        except ImportError as exc:
            print(f"✗ Dashboard disabled: {exc}")
            enable_dashboard = False
        except OSError as exc:
            print(f"✗ Dashboard failed to bind port {config.DASHBOARD_PORT}: {exc}")
            enable_dashboard = False

    mqtt: Optional[MQTTCameraController] = None
    if enable_mqtt:
        mqtt = MQTTCameraController(broker_host=mqtt_broker, broker_port=mqtt_port)
        if not mqtt.wait_for_connection(timeout_sec=5.0):
            print("✗ MQTT NOT CONNECTED — servo will NOT move.")
            print(f"  Broker: {mqtt_broker or config.MQTT_BROKER_HOST}:{mqtt_port or config.MQTT_BROKER_PORT}")
            print("  Fix: run python test_mqtt_system.py  OR  python test_simple_tracking.py")
            print("  Check: broker IP reachable, ESP8266 on same WiFi, firmware flashed.")
        else:
            # start_tracking is sent automatically by _on_connect; center() is
            # the first motion command of the new session.  The ESP will process
            # it after its startup ignore window expires (if just rebooted) or
            # immediately if already past the window.
            mqtt.center()
            print("✓ MQTT ready — tracking session active, servo centering")
    tracker = FaceTracker()
    tlog = TrackingLogger(dashboard=dashboard)
    pan = PanTracker(mqtt=mqtt, logger=tlog)

    activity_logger: Optional[ActivityLogger] = None
    if lock_name:
        activity_logger = ActivityLogger(lock_name, config.HISTORY_DIR)

    cam = open_camera()
    if cam is None:
        print("ERROR: Cannot open camera.")
        print("Run: python -m src.camera_utils to find the correct camera index.")
        return False

    threshold = config.RECOGNITION_THRESHOLD
    baseline_mouth_width = None
    mouth_width_samples: List[float] = []
    last_action_frame: Dict[str, int] = {}
    frame_idx = 0
    action_display: List[Tuple[str, int]] = []
    ACTION_DISPLAY_DURATION = 15

    lost_since: Optional[float] = None
    locked_unrecog_since: Optional[float] = None  # track visible but not recognised as target
    prev_locked_track_id: Optional[int] = None
    reacquire_track_id: Optional[int] = None
    reacquire_frame_count: int = 0
    state = "IDLE"

    # FPS accounting (tracking = loop rate, recognition = embeddings/sec).
    t_loop = time.time()
    loop_count = 0
    track_fps = 0.0
    recog_events = 0
    t_recog = time.time()
    recog_fps = 0.0
    last_frame = None
    camera_warning_frames = 0

    window_name = "Face Tracking"
    show_window = not headless
    if show_window:
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL | cv2.WINDOW_KEEPRATIO)
        cv2.resizeWindow(window_name, config.DISPLAY_WINDOW_WIDTH, config.DISPLAY_WINDOW_HEIGHT)
        if start_fullscreen:
            cv2.setWindowProperty(window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

    print("\nFace Recognition + MQTT Tracking + Search")
    if enable_dashboard:
        print(f"Dashboard: http://{config.DASHBOARD_HOST}:{config.DASHBOARD_PORT}")
    print("Controls: q=quit  r=reload  l=unlock  k=lock  s=search  c=center  f=fullscreen  +/-=threshold")
    if config.TRACKING_LOG_ENABLED:
        print("Tracking logs: ON (set TRACKING_LOG_ENABLED=False in config.py to disable)")
        if lock_name:
            tlog.lock_armed(lock_name)

    try:
        while True:
            ret, frame = cam.read()
            if not ret:
                if last_frame is None:
                    time.sleep(0.05)
                    continue
                frame = last_frame.copy()
                camera_warning_frames += 1
                if camera_warning_frames == 1:
                    print("⚠ Camera frame lost — retrying (tracking continues)...")
            else:
                last_frame = frame
                camera_warning_frames = 0

            frame_idx += 1
            loop_count += 1
            frame_w = frame.shape[1]

            # --- Detect + associate (every frame while searching for lock) ---
            search_active = _in_search_mode(lock_name, state, lost_since) or (
                pan.is_searching and not pan.search_cancelled
            )
            tracking_active = (
                bool(tracker.visible_tracks())
                or tracker.locked_track_id is not None
                or bool(lock_name)
                or search_active
                or pan.search_manual
            )
            if search_active:
                # Full-rate detection while sweeping — faster reacquire.
                run_detect = True
            elif tracking_active:
                run_detect = frame_idx % config.DETECT_EVERY_N_FRAMES_FACE == 0
            else:
                run_detect = frame_idx % config.DETECT_EVERY_N_FRAMES_IDLE == 0
            if run_detect:
                detections = detector.detect(frame)[: config.MAX_FACES]
                visible = tracker.update(detections, frame_idx, frame_w)
            else:
                visible = tracker.visible_tracks()
            faces_present = bool(visible)

            # --- Recognition pass (locked track first; budget caps cost) -----
            locked = tracker.locked_track
            ordered = sorted(
                visible,
                key=lambda t: (t.track_id != tracker.locked_track_id, t.track_id),
            )
            # During active search, only re-recognise the formerly locked track
            # so the budget is not wasted on bystanders.
            is_searching_now = state in ("SEARCHING", "LOST_TARGET")
            budget = config.MAX_FACES_TO_PROCESS
            for tr in ordered:
                if budget <= 0:
                    break
                is_lk = tr.track_id == tracker.locked_track_id
                if is_searching_now and not is_lk:
                    # During search still process unknown faces — they might be the target
                    # returning with a new track ID — but deprioritise known bystanders.
                    if tr.accepted and tr.name != lock_name:
                        continue
                if tr.needs_recognition(frame_idx, is_lk, faces_present=faces_present):
                    name, dist, accepted = recognize_face(
                        frame, tr.landmarks, aligner, embedder,
                        gallery, gallery_owner, names, threshold,
                    )
                    tr.apply_recognition(name, dist, accepted, frame_idx)
                    recog_events += 1
                    budget -= 1

            # --- Lock acquisition / reacquisition ----------------------------
            spotted = _find_spotted_target(lock_name, visible) if lock_name else None
            if lock_name and spotted is not None:
                # ── TARGET ACQUIRED: cancel search instantly (same frame) ───
                if _in_search_mode(lock_name, state, lost_since) or pan.is_searching:
                    pan.cancel_search("locked person verified")
                    lost_since = None  # exit search mode immediately

                if reacquire_track_id == spotted.track_id:
                    reacquire_frame_count += 1
                else:
                    reacquire_track_id = spotted.track_id
                    reacquire_frame_count = 1

                need_frames = 1  # bind immediately once verified above threshold
                if reacquire_frame_count >= need_frames:
                    if tracker.locked_track_id != spotted.track_id:
                        tracker.locked_track_id = spotted.track_id
                        locked_unrecog_since = None
                        tlog.target_reacquiring(
                            lock_name, spotted.track_id,
                            spotted.center, spotted.confidence, pan.current_angle,
                        )
                        print(f"✓ Re-locked onto {lock_name} (track #{spotted.track_id})")
                    reacquire_track_id = None
                    reacquire_frame_count = 0
            elif lock_name:
                reacquire_track_id = None
                reacquire_frame_count = 0

            locked = tracker.locked_track

            # Visible = currently matched to a detection this frame (misses == 0).
            locked_visible = locked is not None and locked.misses == 0
            locked_confirmed = (
                locked_visible
                and locked.accepted
                and locked.name == lock_name
            )

            # --- Servo control + state machine -----------------------------
            if not lock_name:
                state = "IDLE"
                lost_since = None
                locked_unrecog_since = None
                prev_locked_track_id = None
                # No lock target → camera must be completely still. Stop any
                # sweep that was running before the lock was cleared.
                if pan.is_searching or pan.search_manual:
                    pan.cancel_search("no lock — camera idle")
                tlog.idle()

            elif locked_confirmed:
                # ── Target verified — track to center or hold steady ────────
                if state in ("SEARCHING", "LOST_TARGET", "REACQUIRING") or (
                    prev_locked_track_id is None and lost_since is not None
                ) or prev_locked_track_id != locked.track_id:
                    tlog.target_visible(
                        lock_name, locked.track_id, locked.center,
                        locked.confidence, pan.current_angle,
                    )
                lost_since = None
                locked_unrecog_since = None
                reacquire_track_id = None
                reacquire_frame_count = 0
                prev_locked_track_id = locked.track_id
                label, _ = pan.track(locked.center[0], frame_w)
                state = "LOCKED" if label == "centered" else "TRACKING"

            elif spotted is not None:
                # ── Verified but lock not yet bound — keep steady ───────────
                if pan.is_searching or _in_search_mode(lock_name, state, lost_since):
                    pan.cancel_search("locked person verified — awaiting bind")
                lost_since = None
                locked_unrecog_since = None
                state = "REACQUIRING"

            elif _in_search_mode(lock_name, state, lost_since):
                # ── No sighting yet — keep sweeping ─────────────────────────
                locked_unrecog_since = None
                state, lost_since = _activate_search(
                    pan, tlog, lock_name, state, lost_since,
                )

            elif locked is not None and not locked_visible:
                # ── Stale / occluded track (misses > 0) — do NOT chase ghost
                locked_unrecog_since = None
                if lost_since is None:
                    lost_since = time.time()
                    prev_locked_track_id = None
                    tracker.release_lock()
                    tlog.target_lost(lock_name)
                state, lost_since = _activate_search(
                    pan, tlog, lock_name, state, lost_since,
                )

            elif locked is not None and not locked_confirmed:
                # ── Track visible but identity not confirmed (not searching)
                if locked_unrecog_since is None:
                    locked_unrecog_since = time.time()
                unrecog_for = time.time() - locked_unrecog_since

                if unrecog_for < config.LOST_TARGET_UNRECOGNIZED_SEC:
                    pan.track(locked.center[0], frame_w)
                    state = "TRACKING"
                    tlog.target_still_missing(lock_name, unrecog_for)
                else:
                    if lost_since is None:
                        lost_since = time.time()
                        prev_locked_track_id = None
                        tracker.release_lock()
                        tlog.target_lost(lock_name)
                    state, lost_since = _activate_search(
                        pan, tlog, lock_name, state, lost_since,
                    )

            else:
                # ── No locked track — sweep immediately
                locked_unrecog_since = None
                if lost_since is None:
                    lost_since = time.time()
                    prev_locked_track_id = None
                    tracker.release_lock()
                    tlog.target_lost(lock_name)
                state, lost_since = _activate_search(
                    pan, tlog, lock_name, state, lost_since,
                )

            # --- Activity logging for the locked, visible target -----------
            if (
                lock_name and activity_logger and locked_confirmed
                and frame_idx % config.ACTION_DETECT_EVERY_N_FRAMES == 0
                and locked is not None and locked.full_landmarks
            ):
                detected_actions, baseline_mouth_width, mouth_width_samples = action_module.detect_smile_blink(
                    frame, baseline_mouth_width, mouth_width_samples,
                    last_action_frame, frame_idx,
                    cooldown_frames=config.LOCK_ACTION_COOLDOWN_FRAMES,
                    landmarks_list=locked.full_landmarks,
                )
                for act in detected_actions:
                    activity_logger.log_activity(act, frame_idx, locked.center)
                    action_display.append((act.capitalize() + "!", ACTION_DISPLAY_DURATION))
                for mv in activity_logger.detect_and_log_movement(locked.center, frame_idx):
                    action_display.append((mv.replace("_", " ").title() + "!", ACTION_DISPLAY_DURATION))

            action_display = [(label, n - 1) for label, n in action_display if n > 1]

            # --- FPS counters ----------------------------------------------
            now = time.time()
            if now - t_loop >= 1.0:
                track_fps = loop_count / (now - t_loop)
                loop_count = 0
                t_loop = now
            if now - t_recog >= 1.0:
                recog_fps = recog_events / (now - t_recog)
                recog_events = 0
                t_recog = now

            # --- Render ----------------------------------------------------
            vis = frame
            searching_ui = state in ("SEARCHING", "LOST_TARGET", "REACQUIRING")
            draw_tracks(vis, visible, tracker.locked_track_id, searching=searching_ui)
            if searching_ui and lock_name:
                _draw_search_banner(vis, lock_name)

            servo_angle = f"{int(round(pan.current_angle))}" if mqtt else "-"
            _draw_debug_overlay(
                vis, state, lock_name, servo_angle, len(visible),
                recog_fps, track_fps, bool(mqtt and mqtt.is_connected),
                threshold, (time.time() - lost_since) if lost_since else 0.0,
            )

            y_action = vis.shape[0] - 16 * len(action_display) - 8
            for lbl, _ in action_display:
                cv2.putText(vis, lbl, (vis.shape[1] - 160, y_action),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2, cv2.LINE_AA)
                y_action += 18

            if dashboard:
                dashboard.update_frame(vis)
                dashboard.update_telemetry(
                    state=state,
                    lock_name=lock_name,
                    servo_angle=float(pan.current_angle),
                    servo_min=config.SEARCH_MIN_ANGLE,
                    servo_max=config.SEARCH_MAX_ANGLE,
                    mqtt_connected=bool(mqtt and mqtt.is_connected),
                    face_count=len(visible),
                    track_fps=track_fps,
                    recog_fps=recog_fps,
                    threshold=threshold,
                    lost_for=(time.time() - lost_since) if lost_since else 0.0,
                    search_manual=pan.search_manual,
                    faces=faces_from_tracks(visible, tracker.locked_track_id),
                    enrolled_count=len(names),
                    frame_idx=frame_idx,
                )

            if show_window:
                cv2.imshow(window_name, vis)

            # --- Keyboard --------------------------------------------------
            if show_window:
                key = cv2.waitKey(1) & 0xFF
                if not CameraStream.is_window_open(window_name):
                    print("\nDisplay window closed — exiting.")
                    break
            else:
                key = 0xFF
                time.sleep(0.001)
            if key == ord("q"):
                break
            if key == ord("r"):
                db = load_database()
                names = sorted(db.keys())
                gallery, gallery_owner = build_gallery(db, names)
                if lock_name and lock_name not in names:
                    lock_name = None
                    tracker.release_lock()
                    pan.reset()
                print(f"✓ Reloaded {len(db)} identities")
            elif key == ord("l"):
                if activity_logger:
                    activity_logger.save_summary()
                    activity_logger = None
                lock_name = None
                tracker.release_lock()
                pan.reset()
                lost_since = None
                locked_unrecog_since = None
                prev_locked_track_id = None
                reacquire_track_id = None
                reacquire_frame_count = 0
                print("Lock cleared")
            elif key == ord("k"):
                new_lock = choose_lock_identity(names)
                if new_lock:
                    lock_name = new_lock
                    tracker.release_lock()
                    pan.reset()
                    lost_since = None
                    locked_unrecog_since = None
                    prev_locked_track_id = None
                    reacquire_track_id = None
                    reacquire_frame_count = 0
                    if activity_logger is None:
                        activity_logger = ActivityLogger(lock_name, config.HISTORY_DIR)
                    print(f"Lock target set to {lock_name}")
            elif key == ord("s"):
                pan.toggle_search()
                print(f"Manual search: {'ON' if pan.search_manual else 'OFF'}")
            elif key == ord("c"):
                pan.force_center()
                print("Camera centered")
            elif key == ord("f"):
                prop = cv2.WND_PROP_FULLSCREEN
                cur = cv2.getWindowProperty(window_name, prop)
                cv2.setWindowProperty(
                    window_name, prop,
                    cv2.WINDOW_FULLSCREEN if cur != cv2.WINDOW_FULLSCREEN else cv2.WINDOW_NORMAL,
                )
            elif key in (ord("+"), ord("=")):
                threshold = min(1.0, threshold + 0.01)
            elif key == ord("-"):
                threshold = max(0.0, threshold - 0.01)

    finally:
        # ── Shutdown order ────────────────────────────────────────────────
        # 1. pan.shutdown(): stops PC sweep thread, sends go_idle() + stop_session()
        #    which publishes track + hold_angle + stop_tracking to the ESP.
        # 2. mqtt.close(): sends stop_tracking again (idempotent), flushes the
        #    paho queue so all QOS-1 messages are delivered, then disconnects.
        #    On a clean disconnect the broker suppresses the LWT — the explicit
        #    stop_tracking we sent is the definitive shutdown signal.
        try:
            pan.shutdown()
        except Exception as exc:
            print(f"⚠ Servo shutdown error: {exc}")
        if activity_logger:
            activity_logger.save_summary()
        if mqtt:
            mqtt.close()
        detector.close()
        cam.release()
        if show_window:
            cv2.destroyAllWindows()

    print("✓ Tracking ended.")
    return True


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Face recognition with MQTT camera tracking")
    parser.add_argument("--fullscreen", "-f", action="store_true")
    parser.add_argument("--no-mqtt", action="store_true", help="Disable MQTT servo control")
    parser.add_argument("--broker", type=str, default=None, help="MQTT broker IP")
    parser.add_argument("--port", type=int, default=None, help="MQTT broker port")
    parser.add_argument("--dashboard", "-d", action="store_true", help="Enable web dashboard")
    parser.add_argument("--headless", action="store_true", help="Dashboard only (no OpenCV window)")
    args = parser.parse_args()

    ok = main(
        start_fullscreen=args.fullscreen,
        enable_mqtt=not args.no_mqtt,
        mqtt_broker=args.broker,
        mqtt_port=args.port,
        enable_dashboard=args.dashboard,
        headless=args.headless,
    )
    sys.exit(0 if ok else 1)
