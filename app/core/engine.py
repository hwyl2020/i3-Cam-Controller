"""Acquisition thread: owns the camera, pulls frames, renders them to RGB and
publishes Packets to the UI. All SDK calls happen on this one thread; the UI
talks to it through settings updates and a command queue."""
from __future__ import annotations

import queue
import threading
import time
from dataclasses import dataclass, field

import numpy as np
from PySide6.QtCore import QThread, Signal

from . import palettes
from .sdk import RECV_CODES

ALARM_RGB = np.array([255, 40, 160], np.float32)


@dataclass
class Packet:
    rgb: np.ndarray                 # H x W x 3 uint8
    temps: np.ndarray | None        # H x W float32, deg C
    lo: float                       # temperature at the bottom of the colour bar
    hi: float                       # temperature at the top
    linear: bool                    # colour bar is linear in temperature
    palette: int
    stats: dict = field(default_factory=dict)
    fps: float = 0.0
    index: int = 0
    fpa: float | None = None
    alarm: bool = False


DEFAULTS = dict(
    palette=2, range_mode="agc", tmin=20.0, tmax=40.0,
    flip_h=False, flip_v=False, emissivity=0.95,
    tnf=False, snf=False, edge=1.0, enhance=False,
    alarm=False, alarm_threshold=50.0,
)


class Engine(QThread):
    packet = Signal(object)
    opened = Signal(dict)
    closed = Signal(str)                 # reason ('' on a normal stop)
    log = Signal(str, str)               # level, message
    task_done = Signal(str, bool, str)   # task name, ok, message

    def __init__(self, parent=None):
        super().__init__(parent)
        self._lock = threading.Lock()
        self._settings = dict(DEFAULTS)
        self._dirty_output = True
        self._dirty_eps = True
        self._tasks: queue.Queue = queue.Queue()
        self._stop = threading.Event()
        self._factory = None
        self.camera = None

    # ---------------------------------------------------------------- API
    def start_camera(self, factory):
        """factory() -> camera object; called on the worker thread."""
        self._factory = factory
        self._stop.clear()
        self.start()

    def stop_camera(self):
        self._stop.set()
        self.wait(5000)

    def update(self, **kw):
        with self._lock:
            self._settings.update(kw)
            if {"tnf", "snf", "edge", "enhance"} & kw.keys():
                self._dirty_output = True
            if "emissivity" in kw:
                self._dirty_eps = True

    def settings(self) -> dict:
        with self._lock:
            return dict(self._settings)

    def run_task(self, name: str, fn):
        """fn(camera) -> (ok, message); executed between frames."""
        self._tasks.put((name, fn))

    # ------------------------------------------------------------- thread
    def run(self):
        try:
            cam = self._factory()
            info = cam.open()
        except Exception as exc:  # noqa: BLE001 - report anything to the UI
            self.log.emit("error", f"Connection failed: {exc}")
            self.closed.emit(str(exc))
            return
        self.camera = cam
        self._dirty_output = self._dirty_eps = True
        self.opened.emit(info)
        self.log.emit("ok", f"Connected to {info['model']} ({info['source']}), "
                            f"{info['width']}×{info['height']}")
        reason = ""
        try:
            reason = self._loop(cam)
        finally:
            try:
                cam.close()
            except Exception:  # noqa: BLE001
                pass
            self.camera = None
            self.closed.emit(reason)

    # The TE-Q2 delivers ~9 frames/s; between frames RecvImage returns
    # immediately with code 4 ("data read fail") or 2 ("not ready"). Those are
    # polling misses, not errors - only a long gap without any frame is.
    STALL_WARN_S = 3.0
    STALL_FAIL_S = 12.0

    def _loop(self, cam) -> str:
        index = 0
        times: list[float] = []
        fpa, fpa_t = None, 0.0
        last_ok = time.perf_counter()
        warned = False
        while not self._stop.is_set():
            self._apply_settings(cam)
            self._drain_tasks(cam)

            code, img16, temps = cam.grab()
            if code != 1:
                gap = time.perf_counter() - last_ok
                if gap > self.STALL_FAIL_S:
                    return (f"No frames from the camera for {gap:.0f} s (code {code}: "
                            f"{RECV_CODES.get(code, 'unknown')}). Last USB diagnostic: {cam.diag()}")
                if gap > self.STALL_WARN_S and not warned:
                    warned = True
                    self.log.emit("warn", f"No frame for {gap:.0f} s (code {code}) – {cam.diag()}")
                time.sleep(0.003)
                continue
            if warned:
                warned = False
                self.log.emit("ok", "Frames are arriving again")
            index += 1
            now = time.perf_counter()
            last_ok = now
            times.append(now)
            times = [t for t in times if now - t < 2.0]
            fps = (len(times) - 1) / (times[-1] - times[0]) if len(times) > 2 else 0.0
            if now - fpa_t > 1.0:
                fpa, fpa_t = cam.fpa_temp(), now
            self.packet.emit(self._render(img16, temps, fps, index, fpa))
        return ""

    def _apply_settings(self, cam):
        with self._lock:
            s = self._settings
            out = self._dirty_output
            eps = self._dirty_eps
            self._dirty_output = self._dirty_eps = False
        if out:
            cam.set_output(s["tnf"], s["snf"], s["edge"], s["enhance"])
        if eps:
            cam.set_emissivity(s["emissivity"])

    def _drain_tasks(self, cam):
        while True:
            try:
                name, fn = self._tasks.get_nowait()
            except queue.Empty:
                return
            try:
                ok, msg = fn(cam)
            except Exception as exc:  # noqa: BLE001
                ok, msg = False, str(exc)
            self.task_done.emit(name, ok, msg)

    # ---------------------------------------------------------- rendering
    def _render(self, img16, temps, fps, index, fpa) -> Packet:
        s = self.settings()
        if s["flip_h"]:
            img16, temps = img16[:, ::-1], temps[:, ::-1] if temps is not None else None
        if s["flip_v"]:
            img16, temps = img16[::-1], temps[::-1] if temps is not None else None

        stats = {}
        if temps is not None:
            h, w = temps.shape
            imax, imin = int(np.argmax(temps)), int(np.argmin(temps))
            stats = dict(max=float(temps.flat[imax]), max_xy=(imax % w, imax // w),
                         min=float(temps.flat[imin]), min_xy=(imin % w, imin // w),
                         mean=float(temps.mean()), center=float(temps[h // 2, w // 2]))

        mode = s["range_mode"] if temps is not None else "agc"
        if mode == "agc":
            gray = (img16 >> 8).astype(np.uint8)
            lo, hi = stats.get("min", 0.0), stats.get("max", 0.0)
        else:
            if mode == "manual":
                lo, hi = s["tmin"], s["tmax"]
            else:
                lo, hi = np.percentile(temps, (0.2, 99.8))
                lo, hi = float(lo), float(hi)
            span = max(hi - lo, 0.1)
            gray = (np.clip((temps - lo) / span, 0, 1) * 255).astype(np.uint8)

        lut = palettes.luts()[s["palette"]]
        rgb = lut[gray]

        alarm = False
        if s["alarm"] and temps is not None:
            mask = temps >= s["alarm_threshold"]
            if mask.any():
                alarm = True
                rgb = rgb.copy()
                rgb[mask] = (0.25 * rgb[mask] + 0.75 * ALARM_RGB).astype(np.uint8)

        return Packet(rgb=np.ascontiguousarray(rgb), temps=np.ascontiguousarray(temps) if temps is not None else None,
                      lo=lo, hi=hi, linear=mode != "agc", palette=s["palette"],
                      stats=stats, fps=fps, index=index, fpa=fpa, alarm=alarm)
