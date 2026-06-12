#!/usr/bin/env python3
"""Shortcut: face recognition + MQTT camera tracking."""

import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
_VENV_PY = _ROOT / ".venv" / "bin" / "python"


def _reexec_in_venv_if_needed() -> None:
    """Use project .venv when system Python lacks dependencies (e.g. cv2)."""
    if not _VENV_PY.exists():
        return
    if Path(sys.executable).resolve() == _VENV_PY.resolve():
        return
    try:
        import cv2  # noqa: F401
    except ModuleNotFoundError:
        os.execv(str(_VENV_PY), [str(_VENV_PY), str(__file__), *sys.argv[1:]])


_reexec_in_venv_if_needed()

from src.recognize_with_tracking import main

if __name__ == "__main__":
    fullscreen = "--fullscreen" in sys.argv or "-f" in sys.argv
    no_mqtt = "--no-mqtt" in sys.argv
    dashboard = "--dashboard" in sys.argv or "-d" in sys.argv
    headless = "--headless" in sys.argv
    success = main(
        start_fullscreen=fullscreen,
        enable_mqtt=not no_mqtt,
        enable_dashboard=dashboard,
        headless=headless,
    )
    sys.exit(0 if success else 1)
