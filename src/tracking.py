"""
Pan tracking controller for the MQTT servo camera.

STATE MACHINE
─────────────
  SEARCHING  Locked person not detected.
             A background daemon thread sweeps 0→180→0→180... at
             SEARCH_SPEED, independently of the camera frame rate.
             Face detection does NOT affect this thread. The servo
             NEVER pauses, NEVER dwells at edges. The ONLY way to
             stop the sweep is to call reset() (target found).

  TRACKING   Locked person detected but NOT centred.
             P+D controller moves the servo toward the face every
             frame. Keeps moving until |error| <= CENTER_DEADBAND.
             Does NOT stop simply because a face is detected.

  CENTERED   Locked person detected AND within CENTER_DEADBAND.
             Servo holds. If person drifts past CENTER_DEADBAND_RESUME
             it resumes TRACKING. If person disappears → SEARCHING.

THREAD DESIGN
─────────────
  _sweep_worker runs in a daemon thread.
  It owns all servo motion while searching. The main (camera) thread
  NEVER calls move_to_angle() while the sweep thread is alive, so
  there is no contention and the sweep is continuous and uninterrupted.
  The thread sleeps for SEARCH_UPDATE_INTERVAL between steps and
  wakes immediately when _sweep_stop is set.
"""

import threading
from typing import Optional, Tuple, TYPE_CHECKING

from . import config
from .mqtt_camera_controller import MQTTCameraController

if TYPE_CHECKING:
    from .tracking_log import TrackingLogger


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


class PanTracker:

    def __init__(
        self,
        mqtt: Optional[MQTTCameraController] = None,
        logger: Optional["TrackingLogger"] = None,
    ):
        self.mqtt = mqtt
        self.log = logger

        # PID / tracking state
        self.smoothed_error: Optional[float] = None
        self.prev_error: float = 0.0
        self.integral: float = 0.0
        self.target_angle: float = float(config.SERVO_CENTER_ANGLE)
        self._smooth_angle: Optional[float] = None
        self._holding: bool = False
        self.frames_in_center: int = 0
        self.center_locked: bool = False
        self.last_error_sign: int = 0
        self.last_known_angle: float = float(config.SERVO_CENTER_ANGLE)
        self.search_manual: bool = False

        # Background sweep thread.
        # _sweep_stop is SET when not sweeping (Event.wait returns immediately
        # when set, which is how we make the thread exit fast).
        self._sweep_stop = threading.Event()
        self._sweep_stop.set()          # Not sweeping at startup
        self._sweep_thread: Optional[threading.Thread] = None
        self._sweep_from_zero: bool = True   # First sweep after reset() starts at 0°
        self._search_cancelled: bool = False  # Blocks search() until target lost

    # ── properties ────────────────────────────────────────────────────────────

    @property
    def current_angle(self) -> float:
        """ESP-reported physical angle, or our internal target if no MQTT."""
        if self.mqtt:
            return float(self.mqtt.current_angle)
        return self.target_angle

    @property
    def is_searching(self) -> bool:
        """True while the background sweep thread is alive."""
        return self._sweep_thread is not None and self._sweep_thread.is_alive()

    @property
    def search_cancelled(self) -> bool:
        """True after target acquisition until arm_search() is called."""
        return self._search_cancelled

    def normalized_error(self, face_center_x: float, frame_width: int) -> float:
        return (face_center_x - frame_width / 2.0) / (frame_width / 2.0)

    def in_center_zone(self, error: float) -> bool:
        return abs(error) < config.CENTERING_TOLERANCE

    # ── reset ─────────────────────────────────────────────────────────────────

    def reset(self) -> None:
        """
        Stop any active sweep and reset PID state for clean re-acquisition.
        Seeds the PID from the current physical position so tracking resumes
        smoothly from wherever the sweep left the camera.
        """
        self._stop_sweep()
        self.smoothed_error = None
        self.prev_error = 0.0
        self.integral = 0.0
        self.target_angle = float(self.current_angle)
        self._smooth_angle = float(self.current_angle)
        self._holding = False
        self.frames_in_center = 0
        self.center_locked = False
        self.search_manual = False
        self._sweep_from_zero = True   # Next search sweep begins at 0°
        self._search_cancelled = False

    # ── SEARCH — background thread ─────────────────────────────────────────

    def cancel_search(self, reason: str = "target acquired") -> Tuple[str, None]:
        """
        Immediately stop all search/sweep activity and freeze at current angle.

        This is the single entry point for target acquisition — it stops the PC
        sweep thread, cancels ESP search mode, and publishes a hold angle so
        stale waypoints cannot keep the servo moving.
        """
        self._search_cancelled = True
        self.search_manual = False
        self._stop_sweep()
        hold_angle = int(round(self.current_angle))
        self.target_angle = float(hold_angle)
        self._smooth_angle = float(hold_angle)
        self.smoothed_error = None
        self.prev_error = 0.0
        # Clear stale holding/centering state so the FIRST track() after
        # acquisition re-evaluates the dead-band from scratch: it will move to
        # centre if the face is off-centre, or hold if already centred.
        self._holding = False
        self.frames_in_center = 0
        self.center_locked = False
        if self.mqtt:
            self.mqtt.cancel_search(hold_angle)
        if self.log:
            self.log.servo_hold(hold_angle, reason)
        return ("holding", None)

    def hold(self, reason: str = "target spotted") -> Tuple[str, None]:
        """Alias for cancel_search — freeze servo immediately."""
        return self.cancel_search(reason)

    def search(self) -> Tuple[str, Optional[int]]:
        """
        Ensure the autonomous sweep thread is running.

        Idempotent and cheap: calling this every frame while in SEARCHING
        state is safe; it only launches the thread once. The sweep continues
        completely independently until reset() is called.
        """
        if self._search_cancelled:
            return ("holding", None)
        if not self.mqtt:
            if self.log:
                self.log.servo_hold(self.current_angle, "MQTT not connected — sweep paused")
            return ("searching", None)
        if not self.is_searching:
            self._start_sweep()
        return ("searching", None)

    def arm_search(self) -> None:
        """Re-enable search after the locked target is lost."""
        self._search_cancelled = False

    def _start_sweep(self) -> None:
        """Launch the background sweep thread."""
        self._sweep_stop.clear()          # Allow the thread to run
        self._sweep_thread = threading.Thread(
            target=self._sweep_worker,
            name="servo-sweep",
            daemon=True,                  # Dies automatically when main exits
        )
        self._sweep_thread.start()
        if self.log:
            self.log.search_sweeping(self.current_angle)

    def _stop_sweep(self) -> None:
        """
        Signal the sweep thread to stop and wait for it to exit.
        The thread wakes from its timed sleep within SEARCH_UPDATE_INTERVAL
        (~14 ms), so this blocks for at most ~20 ms.
        """
        self._sweep_stop.set()            # Wake the sleeping thread
        t = self._sweep_thread
        if t is not None and t.is_alive():
            t.join(timeout=0.5)           # At most 500 ms; actual < 20 ms
        self._sweep_thread = None

    def _sweep_worker(self) -> None:
        """
        Autonomous background sweep: 0° → 180° → 0° → 180° ...

        Runs at SEARCH_SPEED deg/s, completely independent of:
          - Camera frame rate
          - Detection / recognition speed
          - MQTT publish timing
          - Face detection results

        The loop never pauses at the edges. Direction reverses INSTANTLY
        when a limit is reached. The thread exits within one sleep interval
        after _sweep_stop is set.
        """
        lo = config.SEARCH_MIN_ANGLE        # 0
        hi = config.SEARCH_MAX_ANGLE        # 180
        step_deg = max(1, int(config.SEARCH_STEP))          # degrees per step
        step_sec = max(0.005, float(config.SEARCH_UPDATE_INTERVAL))  # seconds

        if self._sweep_from_zero:
            # Fresh loss after confirmed track — sweep from 0° as designed.
            if self.mqtt and self.mqtt.is_connected:
                self.mqtt.sweep_move(lo)
            pos = float(lo)
            direction = 1
            self._sweep_from_zero = False
        else:
            # Sweep thread restarted (e.g. brief track() flicker) — continue
            # from current angle so rotation never pauses or jumps backward.
            pos = _clamp(float(self.current_angle), lo, hi)
            direction = 1 if pos <= (lo + hi) / 2.0 else -1

        while not self._sweep_stop.is_set():
            # Advance position.
            pos += direction * step_deg

            # Instant direction reversal at limits — NO dwell, NO pause.
            if pos >= hi:
                pos = float(hi)
                direction = -1
            elif pos <= lo:
                pos = float(lo)
                direction = 1

            # Exit before publishing if search was cancelled while we slept.
            if self._sweep_stop.is_set() or self._search_cancelled:
                break

            # Publish directly, bypassing the main-thread rate limiter.
            if self.mqtt and self.mqtt.is_connected:
                self.mqtt.sweep_move(int(pos))

            # Interruptible sleep. Event.wait(timeout) returns immediately
            # when _sweep_stop is set, making the thread exit fast.
            self._sweep_stop.wait(step_sec)

    # ── TRACKING — main thread ─────────────────────────────────────────────

    def track(self, face_center_x: float, frame_width: int) -> Tuple[str, Optional[int]]:
        """
        PID-control the servo to centre the locked face.

        STOP CONDITION: the servo holds ONLY when |error| <= CENTER_DEADBAND.
        Off-centre detected face => servo KEEPS MOVING toward the target.
        """
        raw_error = self.normalized_error(face_center_x, frame_width)
        err_px = abs(face_center_x - frame_width / 2.0)

        # Ensure search is fully cancelled before any tracking command.
        if self.is_searching or (
            self.mqtt and self.mqtt._search_requested and not self._search_cancelled
        ):
            self.cancel_search("target confirmed — switching to tracking")

        # Remember exit direction for search bias on next loss.
        if abs(raw_error) > config.CENTERING_TOLERANCE:
            self.last_error_sign = 1 if raw_error > 0 else -1
        self.last_known_angle = self.current_angle

        # Centering counter.
        if self.in_center_zone(raw_error):
            self.frames_in_center += 1
            self.center_locked = self.frames_in_center >= config.FRAMES_TO_LOCK_CENTER
        else:
            self.frames_in_center = 0
            self.center_locked = False

        # ── Dead-band with hysteresis ─────────────────────────────────────
        # _holding = True ONLY when inside CENTER_DEADBAND.
        # Hysteresis: once centred, only resume when face drifts past
        # CENTER_DEADBAND_RESUME, preventing chatter at the boundary.
        if self._holding:
            # Currently centred — resume chasing only if drifted far enough.
            if err_px > config.CENTER_DEADBAND_RESUME:
                self._holding = False
        else:
            # Currently moving — stop only when inside the inner band.
            if err_px <= config.CENTER_DEADBAND:
                self._holding = True

        if self._holding:
            label = "centered" if self.center_locked else "tracking"
            if self.log:
                self.log.servo_hold(self.current_angle, f"centred ({err_px:.0f}px <= {config.CENTER_DEADBAND}px)")
            return (label, None)

        # ── P+D position controller ───────────────────────────────────────
        a = config.SMOOTHING_FACTOR
        if self.smoothed_error is None:
            self.smoothed_error = raw_error
        else:
            self.smoothed_error = a * raw_error + (1.0 - a) * self.smoothed_error
        error = self.smoothed_error

        derivative = error - self.prev_error
        self.prev_error = error

        delta = (
            config.SERVO_PID_KP * error
            + config.SERVO_PID_KD * derivative
        ) * config.SERVO_DIRECTION_SIGN

        # Guarantee ≥1° correction when off-centre so the servo never stalls
        # before reaching the dead-band.
        if -1.0 < delta < 0.0:
            delta = -1.0
        elif 0.0 < delta < 1.0:
            delta = 1.0

        # Rate limit: small incremental steps — no jumps.
        delta = _clamp(delta, -config.SERVO_MAX_SPEED, config.SERVO_MAX_SPEED)

        # Integrate onto our OWN target (decoupled from the lagging ESP angle).
        self.target_angle = _clamp(
            self.target_angle + delta,
            config.SERVO_MIN_ANGLE,
            config.SERVO_MAX_ANGLE,
        )

        # Output EMA — one more smoothing layer.
        alpha = config.SERVO_OUTPUT_SMOOTHING
        if self._smooth_angle is None:
            self._smooth_angle = self.target_angle
        else:
            self._smooth_angle += alpha * (self.target_angle - self._smooth_angle)

        command_angle = int(round(self._smooth_angle))

        if not self.mqtt:
            return ("tracking", None)

        from_angle = self.current_angle
        published = self.mqtt.move_to_angle(command_angle)
        # Nudge only when clearly outside the resume band — avoids oscillation
        # near the deadband from forced 1° corrections.
        if (
            not published
            and err_px > config.CENTER_DEADBAND_RESUME
            and abs(raw_error) > config.CENTERING_TOLERANCE
        ):
            nudge = command_angle + (1 if raw_error > 0 else -1)
            nudge = int(_clamp(nudge, config.SERVO_MIN_ANGLE, config.SERVO_MAX_ANGLE))
            if nudge != self.mqtt.commanded_angle:
                published = self.mqtt.move_to_angle(nudge, force=True)
                if published:
                    command_angle = nudge

        if published:
            if self.log:
                side = "right" if raw_error > 0 else "left"
                self.log.servo_move(
                    from_angle, command_angle,
                    f"centering ({side}, err={raw_error:+.2f})",
                )
        elif self.log:
            self.log.servo_hold(from_angle, "already at target or rate-limited")

        return ("tracking", command_angle if published else None)

    # ── manual controls ───────────────────────────────────────────────────────

    def toggle_search(self) -> None:
        """Toggle manual search (keyboard shortcut 's')."""
        self.search_manual = not self.search_manual
        if self.search_manual:
            self.arm_search()
            self.search()
        else:
            self.cancel_search("manual search off")

    def force_center(self) -> None:
        """Center immediately (keyboard shortcut 'c')."""
        self.reset()
        self.target_angle = float(config.SERVO_CENTER_ANGLE)
        self._smooth_angle = float(config.SERVO_CENTER_ANGLE)
        if self.mqtt:
            self.mqtt.center()

    def shutdown(self) -> None:
        """
        Stop ALL servo motion on program exit.

        Halts the background sweep thread and commands the ESP to leave
        search mode and hold its current angle, so the camera does not keep
        sweeping after the tracking process is stopped.
        """
        self._search_cancelled = True
        self.search_manual = False
        self._stop_sweep()
        if self.mqtt:
            hold_angle = int(round(self.current_angle))
            self.mqtt.cancel_search(hold_angle)
            self.mqtt.go_idle(hold_angle)
