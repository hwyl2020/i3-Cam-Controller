"""Synthetic thermal camera with the same interface as SdkCamera.

Renders a plausible indoor scene (wall, window, person, hot mug, laptop) in
degrees C, then mimics the SDK pipeline: AGC, noise filters, edge enhancement,
fixed-pattern noise that NUC removes, and bad pixels that the bad-pixel
update removes. Lets the UI be developed and demoed with no hardware.
"""
from __future__ import annotations

import time

import cv2
import numpy as np

from .sdk import SDK_VERSION

W, H = 384, 288
FPS = 25.0


def agc16(temps: np.ndarray) -> np.ndarray:
    """Histogram-equalisation AGC similar in spirit to the camera's."""
    lo, hi = np.percentile(temps, (0.5, 99.5))
    x = np.clip((temps - lo) / max(hi - lo, 0.1), 0, 1)
    x8 = (x * 255).astype(np.uint8)
    eq = cv2.equalizeHist(x8).astype(np.float32) / 255.0
    mix = 0.55 * x + 0.45 * eq                      # plateau-limited look
    return (mix * 65535).astype(np.uint16)


class SimCamera:
    simulated = True

    def __init__(self):
        rng = np.random.default_rng(7)
        self.rng = rng
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        self.xx, self.yy = xx, yy
        self.ambient = 23.0
        # Static scene ------------------------------------------------------
        bg = 22.0 + 1.6 * (yy / H) + 0.4 * np.sin(xx / 60.0)
        bg[:110, 250:370] = 14.5 + 1.5 * (yy[:110, 250:370] / 110)        # window
        bg[105:112, 245:375] = 19.0                                       # frame
        bg[215:, :] = 24.5 + 0.8 * (xx[215:, :] / W)                      # desk
        laptop = (xx > 20) & (xx < 140) & (yy > 228) & (yy < 270)
        bg[laptop] = 33.0 + 7.0 * np.exp(-((xx[laptop] - 120) ** 2) / 300)
        self.static = cv2.GaussianBlur(bg.astype(np.float32), (7, 7), 2)
        self.true_eps = 0.95
        self.emissivity = 0.95
        self.fpn = np.zeros((H, W), np.float32)
        self.dead = [(int(rng.integers(5, W - 5)), int(rng.integers(5, H - 5))) for _ in range(7)]
        self.dead_on = True
        self.out = dict(tnf=False, snf=False, edge=1.0, enhance=False)
        self.prev = None
        self.t0 = time.perf_counter()
        self.next_t = self.t0

    # ---------------------------------------------------------------- life
    def open(self) -> dict:
        time.sleep(0.6)  # the real camera reads flash calibration on open
        return {"source": "Simulator", "model": "TE-Q2 (simulated)", "serial": "SIM-0000-Q2",
                "firmware": "—", "width": W, "height": H, "sdk": SDK_VERSION, "simulated": True}

    def close(self):
        pass

    def set_output(self, tnf, snf, edge, enhance):
        self.out = dict(tnf=tnf, snf=snf, edge=edge, enhance=enhance)

    def diag(self) -> str:
        return "simulator"

    # --------------------------------------------------------------- scene
    def _scene(self, t: float) -> np.ndarray:
        xx, yy = self.xx, self.yy
        s = self.static.copy()
        # person: head + shoulders, drifting left/right
        cx = 175 + 45 * np.sin(t * 0.35)
        cy = 120 + 4 * np.sin(t * 0.9)
        body = ((xx - cx) / 78) ** 2 + ((yy - (cy + 125)) / 70) ** 2 < 1
        s[body] = 30.5 + 0.6 * np.sin(yy[body] / 9)
        neck = (np.abs(xx - cx) < 16) & (yy > cy + 30) & (yy < cy + 62)
        s[neck] = 34.2
        head = ((xx - cx) / 36) ** 2 + ((yy - cy) / 46) ** 2 < 1
        d = np.sqrt(((xx - cx) / 36) ** 2 + ((yy - cy) / 46) ** 2)
        s[head] = 36.4 - 2.2 * d[head] ** 2
        hair = head & (yy < cy - 22)
        s[hair] = 29.0
        for ex in (-12, 12):                                          # eyes / tear ducts
            eye = ((xx - (cx + ex)) ** 2 + (yy - (cy - 4)) ** 2) < 16
            s[eye] = 36.9
        # mug of coffee, slowly cooling and steaming
        mx, my = 300, 225
        mug = (np.abs(xx - mx) < 17) & (yy > my - 22) & (yy < my + 18)
        s[mug] = 61.0 - 3.0 * ((t / 60.0) % 1)
        steam = np.exp(-(((xx - mx - 4 * np.sin(yy / 8 + t * 3)) / 7) ** 2)) \
            * np.clip((my - 22 - yy) / 50, 0, 1) * np.clip(1 - (my - 22 - yy) / 70, 0, 1)
        s += 9.0 * steam
        return cv2.GaussianBlur(s, (5, 5), 1.2)

    def _apparent(self, true_t: np.ndarray) -> np.ndarray:
        """What the camera reports for the chosen emissivity."""
        k = 273.15
        amb4 = (self.ambient + k) ** 4
        rad = self.true_eps * (true_t + k) ** 4 + (1 - self.true_eps) * amb4
        e = max(self.emissivity, 0.05)
        obj4 = np.maximum((rad - (1 - e) * amb4) / e, 1.0)
        return obj4 ** 0.25 - k

    # --------------------------------------------------------- acquisition
    def grab(self):
        now = time.perf_counter()
        if now < self.next_t:
            time.sleep(self.next_t - now)
        self.next_t = max(self.next_t + 1 / FPS, time.perf_counter() - 0.5)
        t = time.perf_counter() - self.t0

        temps = self._apparent(self._scene(t))
        temps += self.rng.normal(0, 0.06, temps.shape).astype(np.float32)
        # fixed pattern noise slowly builds until a NUC is run
        self.fpn += self.rng.normal(0, 0.0004, (1, W)).astype(np.float32) * 25
        self.fpn = np.clip(self.fpn, -0.8, 0.8)
        temps = temps + self.fpn
        if self.dead_on:
            for x, y in self.dead:
                temps[y, x] += 9.0                      # visible specks, below the mug

        img = temps.copy()
        o = self.out
        if o["tnf"]:
            if self.prev is not None and self.prev.shape == img.shape:
                img = 0.35 * img + 0.65 * self.prev
            self.prev = img.copy()
        else:
            self.prev = None
        if o["snf"]:
            img = cv2.bilateralFilter(img.astype(np.float32), 5, 1.5, 3)
        img16 = agc16(img)
        if o["enhance"]:
            clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(6, 6))
            img16 = clahe.apply((img16 >> 8).astype(np.uint8)).astype(np.uint16) << 8
        if abs(o["edge"] - 1.0) > 1e-3:
            f = img16.astype(np.float32)
            blur = cv2.GaussianBlur(f, (0, 0), 1.6)
            img16 = np.clip(f + (o["edge"] - 1.0) * 1.5 * (f - blur), 0, 65535).astype(np.uint16)
        return 1, img16, temps.astype(np.float32)

    # ------------------------------------------------------------ controls
    def set_emissivity(self, e):
        self.emissivity = float(e)

    def fpa_temp(self):
        return 31.4 + 0.4 * np.sin((time.perf_counter() - self.t0) / 40)

    def nuc(self):
        time.sleep(0.8)
        self.fpn[:] = 0
        return True

    def lens_calibration(self):
        time.sleep(0.8)
        return True

    def update_dead(self):
        time.sleep(0.5)
        self.dead_on = False
        return True

    def save_calibration(self, path):
        np.save(path if path.endswith(".npy") else path + ".npy", self.fpn)
        return True

    def load_calibration(self, path):
        try:
            self.fpn = np.load(path).astype(np.float32)
            return True
        except Exception:
            return False
