"""The ten i3system colour palettes as 256-entry RGB lookup tables.

Built from the SDK's own ApplyColorMap so on-screen colours match the camera
vendor's software; falls back to OpenCV maps if the SDK cannot be loaded.
"""
from __future__ import annotations

import cv2
import numpy as np

from .sdk import Bridge

NAMES = ["White Hot", "Black Hot", "Iron", "Blue-Red", "Medical",
         "Purple", "Purple-Yellow", "Dark Blue", "Cyan", "Rainbow"]

_FALLBACK = [None, None, cv2.COLORMAP_INFERNO, cv2.COLORMAP_JET, cv2.COLORMAP_TURBO,
             cv2.COLORMAP_MAGMA, cv2.COLORMAP_PLASMA, cv2.COLORMAP_OCEAN,
             cv2.COLORMAP_WINTER, cv2.COLORMAP_RAINBOW]

_luts: list[np.ndarray] | None = None
source = "fallback"


def luts() -> list[np.ndarray]:
    """List of (256, 3) uint8 RGB arrays, one per palette."""
    global _luts, source
    if _luts is not None:
        return _luts
    ramp = np.arange(256, dtype=np.uint8).reshape(1, 256)
    out = []
    bridge = Bridge.get()
    for i, cmap in enumerate(_FALLBACK):
        if bridge is not None:
            bgr = bridge.colormap(ramp, i)[0]
        elif i == 0:
            bgr = np.repeat(ramp[0, :, None], 3, 1)
        elif i == 1:
            bgr = np.repeat(255 - ramp[0, :, None], 3, 1)
        else:
            bgr = cv2.applyColorMap(ramp, cmap)[0]
        out.append(np.ascontiguousarray(bgr[:, ::-1]))
    source = "i3system SDK" if bridge is not None else "fallback"
    _luts = out
    return out
