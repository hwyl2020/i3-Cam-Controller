"""MP4 recording of the composed view (thermal image + overlays + colour bar)."""
from __future__ import annotations

import time
from pathlib import Path

import cv2
import numpy as np
from PySide6.QtGui import QImage


def qimage_to_bgr(img: QImage) -> np.ndarray:
    img = img.convertToFormat(QImage.Format.Format_RGB888)
    w, h, bpl = img.width(), img.height(), img.bytesPerLine()
    arr = np.frombuffer(img.constBits(), np.uint8, count=bpl * h).reshape(h, bpl)
    return cv2.cvtColor(arr[:, : w * 3].reshape(h, w, 3), cv2.COLOR_RGB2BGR)


class Recorder:
    """The writer is created lazily on the first frame so the video size
    always matches what is actually rendered."""

    def __init__(self):
        self.writer = None
        self.path: Path | None = None
        self.size = None
        self.fps = 9.0
        self.started = 0.0
        self.frames = 0
        self.active = False

    def start(self, path: Path, fps: float):
        self.path = path
        self.fps = float(max(5, min(round(fps) or 9, 60)))
        self.writer = None
        self.size = None
        self.frames = 0
        self.started = time.time()
        self.active = True

    def write(self, img: QImage):
        if not self.active:
            return
        bgr = qimage_to_bgr(img)
        if self.writer is None:
            self.started = time.time()
            h, w = bgr.shape[:2]
            self.size = (w - w % 2, h - h % 2)
            self.writer = cv2.VideoWriter(str(self.path), cv2.VideoWriter_fourcc(*"mp4v"),
                                          self.fps, self.size)
        if (bgr.shape[1], bgr.shape[0]) != self.size:
            bgr = cv2.resize(bgr, self.size)
        # keep the video in real time: repeat or drop frames against the wall clock
        due = int((time.time() - self.started) * self.fps) + 1
        for _ in range(min(due - self.frames, int(self.fps))):
            self.writer.write(bgr)
            self.frames += 1

    def stop(self) -> Path | None:
        was = self.active
        self.active = False
        if self.writer is not None:
            self.writer.release()
            self.writer = None
        return self.path if was and self.frames else None

    def elapsed(self) -> float:
        return time.time() - self.started if self.active else 0.0
