"""
MQTT camera controller — publishes pan commands to ESP8266 servo firmware.
"""

import json
import threading
import time
from typing import Optional

import paho.mqtt.client as mqtt

from . import config


class MQTTCameraController:
    """Control camera servo via MQTT."""

    def __init__(
        self,
        broker_host: str = None,
        broker_port: int = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ):
        self.broker_host = broker_host or config.MQTT_BROKER_HOST
        self.broker_port = broker_port or config.MQTT_BROKER_PORT
        self.username = username if username is not None else config.MQTT_USERNAME
        self.password = password if password is not None else config.MQTT_PASSWORD

        self.topic_horizontal = config.MQTT_TOPIC_HORIZONTAL
        self.topic_command = config.MQTT_TOPIC_COMMAND
        self.topic_status = config.MQTT_TOPIC_STATUS

        # reported_angle: last value from ESP status (physical position)
        # commanded_angle: last angle successfully published (avoid duplicate sends)
        self.reported_angle = config.SERVO_CENTER_ANGLE
        self.commanded_angle = config.SERVO_CENTER_ANGLE
        self.is_connected = False
        self.last_status: dict = {}
        self._last_publish_ms = 0.0
        self._last_status_time = 0.0

        # Servo mode mirror.  The ESP runs an autonomous sweep in "search" mode;
        # the PC only needs to send the mode-change command ONCE (with periodic
        # re-assertion in case a packet is dropped) instead of streaming
        # waypoints.  This keeps MQTT traffic minimal and the sweep perfectly
        # smooth because motion is generated on the ESP, not over the network.
        self.reported_mode: str = "track"
        self._search_requested = False
        self._last_search_cmd_ms = 0.0
        self._publish_lock = threading.Lock()

        self.client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id="FaceLocking_Controller",
        )
        if self.username and self.password:
            self.client.username_pw_set(self.username, self.password)

        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message
        self.client.reconnect_delay_set(min_delay=1, max_delay=30)

        try:
            self.client.connect(self.broker_host, self.broker_port, keepalive=config.MQTT_KEEPALIVE)
            self.client.loop_start()
            print(f"✓ MQTT connecting to {self.broker_host}:{self.broker_port}")
        except Exception as exc:
            print(f"✗ MQTT connection failed: {exc}")

    def _on_connect(self, client, userdata, flags, rc, properties=None):
        if rc == 0:
            self.is_connected = True
            client.subscribe(self.topic_status, qos=config.MQTT_QOS)
            print(f"✓ MQTT connected, subscribed to {self.topic_status}")
        else:
            print(f"✗ MQTT connect failed rc={rc}")

    def _on_disconnect(self, client, userdata, *args):
        # paho VERSION2 calls: (client, userdata, disconnect_flags, reason_code,
        # properties). Older/other versions pass (client, userdata, rc). Accept
        # *args so a signature mismatch can never crash the network loop thread
        # (which would silently stop all publishes and status updates).
        self.is_connected = False
        self.reported_mode = "track"  # don't assume ESP is still sweeping
        reason = args[-2] if len(args) >= 2 else (args[0] if args else "?")
        print(f"⚠ MQTT disconnected (reason={reason}) — auto-reconnecting...")

    def _on_message(self, client, userdata, msg):
        if msg.topic != self.topic_status:
            return
        try:
            payload = msg.payload.decode()
            if payload.startswith("{"):
                self.last_status = json.loads(payload)
            else:
                self.last_status = {"raw": payload}
            angle = self.last_status.get("angle")
            if angle is not None:
                self.reported_angle = int(angle)
                self._last_status_time = time.time()
            mode = self.last_status.get("mode")
            if mode is not None:
                self.reported_mode = str(mode)
        except Exception:
            pass

    @property
    def current_angle(self) -> int:
        """Best estimate of physical servo angle (ESP status when available)."""
        return self.reported_angle

    def _rate_limited(self) -> bool:
        now = time.time() * 1000.0
        if now - self._last_publish_ms < config.MQTT_MIN_COMMAND_INTERVAL_MS:
            return True
        self._last_publish_ms = now
        return False

    def _publish(self, topic: str, payload: str) -> bool:
        if not self.is_connected:
            return False
        if self._rate_limited():
            return False
        result = self.client.publish(topic, payload, qos=config.MQTT_QOS)
        return result.rc == mqtt.MQTT_ERR_SUCCESS

    def move_to_angle(self, angle: int, force: bool = False) -> bool:
        """
        Rate-limited angle publish for the tracking thread.

        Dedup skips identical commanded angles UNLESS *force* is True or the
        ESP-reported position still differs (command was sent but servo has
        not caught up yet).
        """
        angle = int(max(config.SERVO_MIN_ANGLE, min(config.SERVO_MAX_ANGLE, angle)))
        with self._publish_lock:
            if not force and angle == self.commanded_angle:
                if abs(angle - self.reported_angle) <= 2:
                    return False
            ok = self._publish(self.topic_horizontal, str(angle))
            if ok:
                self.commanded_angle = angle
            return ok

    def sweep_move(self, angle: int) -> bool:
        """
        Direct angle publish for the background sweep thread.

        Bypasses the tracking rate limiter; sweep timing is controlled by the
        thread's own sleep interval. Serialized via _publish_lock so tracking
        and search never publish simultaneously.
        """
        angle = int(max(config.SERVO_MIN_ANGLE, min(config.SERVO_MAX_ANGLE, angle)))
        if not self.is_connected:
            return False
        with self._publish_lock:
            result = self.client.publish(self.topic_horizontal, str(angle), qos=0)
            ok = result.rc == mqtt.MQTT_ERR_SUCCESS
            if ok:
                self.commanded_angle = angle
            return ok

    def send_command(self, command: str) -> bool:
        return self._publish(self.topic_command, command)

    def start_search(self) -> bool:
        """
        Ask the ESP to run its autonomous continuous sweep.

        Idempotent: the command is sent once when search begins and then
        re-asserted at most every SEARCH_CMD_RESEND_SEC so a dropped packet
        cannot leave the servo frozen.  The actual 0->180->0 motion is
        generated on the ESP, independent of MQTT timing.
        """
        if not self.is_connected:
            return False
        now = time.time()
        # Pure time-based throttle: re-assert "search" at most every
        # SEARCH_CMD_RESEND_SEC. We do NOT gate on reported mode, because a
        # firmware that does not echo {"mode":...} would otherwise make us
        # republish (and log) every single frame.
        if self._search_requested and (now - self._last_search_cmd_ms) < config.SEARCH_CMD_RESEND_SEC:
            return False
        # Publish directly (do not use angle rate-limiter / dedup path).
        result = self.client.publish(self.topic_command, "search", qos=config.MQTT_QOS)
        ok = result.rc == mqtt.MQTT_ERR_SUCCESS
        if ok:
            self._search_requested = True
            self._last_search_cmd_ms = now
        return ok

    def stop_search(self, hold_angle: Optional[int] = None) -> bool:
        """Stop the ESP sweep and hold the current position (TRACK mode)."""
        return self.cancel_search(hold_angle)

    def cancel_search(self, hold_angle: Optional[int] = None) -> bool:
        """
        Atomically cancel search/sweep and freeze the servo.

        Sends TRACK mode to the ESP (exits autonomous MODE_SEARCH) and publishes
        a hold angle so the ESP stops chasing stale sweep waypoints immediately.
        """
        self._search_requested = False
        if not self.is_connected:
            return False
        angle = hold_angle if hold_angle is not None else self.reported_angle
        angle = int(max(config.SERVO_MIN_ANGLE, min(config.SERVO_MAX_ANGLE, angle)))
        with self._publish_lock:
            track_result = self.client.publish(
                self.topic_command, "track", qos=config.MQTT_QOS,
            )
            hold_result = self.client.publish(
                self.topic_horizontal, str(angle), qos=config.MQTT_QOS,
            )
            ok = (
                track_result.rc == mqtt.MQTT_ERR_SUCCESS
                and hold_result.rc == mqtt.MQTT_ERR_SUCCESS
            )
            if ok:
                self.commanded_angle = angle
                self._last_publish_ms = time.time() * 1000.0
            return ok

    def hold_at_angle(self, angle: int, force: bool = True) -> bool:
        """Publish a single hold angle without changing search mode flags."""
        angle = int(max(config.SERVO_MIN_ANGLE, min(config.SERVO_MAX_ANGLE, angle)))
        with self._publish_lock:
            if not force and angle == self.commanded_angle:
                if abs(angle - self.reported_angle) <= 2:
                    return False
            if not self.is_connected:
                return False
            result = self.client.publish(
                self.topic_horizontal, str(angle), qos=config.MQTT_QOS,
            )
            ok = result.rc == mqtt.MQTT_ERR_SUCCESS
            if ok:
                self.commanded_angle = angle
                self._last_publish_ms = time.time() * 1000.0
            return ok

    def move_left(self, step: int = None) -> bool:
        step = step or config.SERVO_STEP_SIZE
        # Use commanded_angle (last sent) — reported_angle lags ESP status by ~250ms.
        return self.move_to_angle(self.commanded_angle - step)

    def move_right(self, step: int = None) -> bool:
        step = step or config.SERVO_STEP_SIZE
        return self.move_to_angle(self.commanded_angle + step)

    def center(self) -> bool:
        return self.move_to_angle(config.SERVO_CENTER_ANGLE)

    def wait_for_connection(self, timeout_sec: float = 5.0) -> bool:
        """Block until connected or timeout (connect is async via loop_start)."""
        deadline = time.time() + timeout_sec
        while time.time() < deadline:
            if self.is_connected:
                return True
            time.sleep(0.1)
        return self.is_connected

    def close(self) -> None:
        try:
            self.client.loop_stop()
            self.client.disconnect()
        except Exception:
            pass
