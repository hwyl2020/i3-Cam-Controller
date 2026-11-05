"""ctypes binding to te_bridge.dll (the flat C wrapper over the i3system SDK)
and the real-camera backend built on it."""
from __future__ import annotations

import ctypes as C
import os
import sys
import time
from pathlib import Path

import cv2
import numpy as np

SDK_VERSION = "2.12.1"

MODEL_NAMES = {
    1: "TE-Q1", 2: "TE-V1", 3: "TE-EQ1", 4: "TE-EV1", 9: "TE-M1",
    12: "TE-EQ2", 13: "TE-EV2", 14: "TE-Q2", 15: "TE-V2", 17: "TE-V2 mini",
}
TYPE_B_MODELS = {1, 2, 9, 14, 15, 17}
MODEL_Q2 = 14
MODEL_V2MINI = 17
# The USB scan reports model 0 for Type B cameras, so these are offered explicitly.
DIRECT_OPEN_MODELS = (MODEL_Q2, MODEL_V2MINI)
# Models with an automatic shutter (SetShutterMode / Time / Temperature).
SHUTTER_MODELS = {15, 17}

SHUTTER_TEMP, SHUTTER_TIME, SHUTTER_MANUAL = 0, 1, 2
SHUTTER_TIME_RANGE = (1, 120)     # units of 30 s
SHUTTER_TEMP_RANGE = (1, 10)      # temperature-change limit
SHUTTER_CODES = {0: "OK", -7: "transfer failed", -11: "not supported by this model",
                 -1: "camera not open", -3: "SDK exception"}

RECV_CODES = {
    1: "OK", 2: "image not ready", 3: "image size mismatch",
    4: "data read fail", 7: "flash data not read",
    -1: "camera not open", -3: "SDK exception",
}


def bin_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent)) / "bin"
    return Path(__file__).resolve().parent.parent / "bin"


class Bridge:
    """Loads te_bridge.dll once and declares the C signatures."""

    _instance: "Bridge | None" = None
    _error: str | None = None

    @classmethod
    def get(cls) -> "Bridge | None":
        if cls._instance is None and cls._error is None:
            try:
                cls._instance = cls()
            except OSError as exc:
                cls._error = str(exc)
        return cls._instance

    @classmethod
    def load_error(cls) -> str | None:
        cls.get()
        return cls._error

    def __init__(self):
        d = bin_dir()
        os.add_dll_directory(str(d))
        lib = C.CDLL(str(d / "te_bridge.dll"))
        vp, i, u, f = C.c_void_p, C.c_int, C.c_uint, C.c_float
        sig = {
            "tb_scan": (i, [vp, vp, vp, i]),
            "tb_last_diag": (i, [C.POINTER(i), C.POINTER(i), C.POINTER(i), C.c_char_p, i]),
            "tb_open": (vp, [i, i]),
            "tb_close": (None, [vp]),
            "tb_width": (i, [vp]),
            "tb_height": (i, [vp]),
            "tb_serial": (i, [vp, C.c_char_p, i]),
            "tb_firmware": (u, [vp]),
            "tb_serial_num": (u, [vp]),
            "tb_set_shutter_mode": (i, [vp, i]),
            "tb_set_shutter_time": (i, [vp, i]),
            "tb_set_shutter_temp": (i, [vp, i]),
            "tb_recv_agc": (i, [vp, vp]),
            "tb_recv_raw": (i, [vp, vp]),
            "tb_recv_processed": (i, [vp, vp]),
            "tb_raw_frame": (i, [vp, vp]),
            "tb_set_output": (None, [vp, i, i, i, i, f]),
            "tb_enhance": (i, [vp, vp, vp]),
            "tb_entire_temp": (i, [vp, vp]),
            "tb_calc_temp": (f, [vp, i, i]),
            "tb_set_emissivity": (None, [vp, f]),
            "tb_fpa_temp": (f, [vp]),
            "tb_nuc": (i, [vp]),
            "tb_lens_offset_cal": (i, [vp]),
            "tb_update_dead": (i, [vp]),
            "tb_add_dead": (i, [vp, i, i]),
            "tb_save_cal": (i, [vp, C.c_char_p]),
            "tb_load_cal": (i, [vp, C.c_char_p]),
            "tb_colormap": (None, [vp, vp, i, i, i]),
        }
        for name, (res, args) in sig.items():
            fn = getattr(lib, name)
            fn.restype = res
            fn.argtypes = args
        self.lib = lib

    def scan(self) -> list[dict]:
        idx, mdl, cid = (C.c_int * 32)(), (C.c_int * 32)(), (C.c_uint * 32)()
        n = self.lib.tb_scan(idx, mdl, cid, 32)
        return [{"index": idx[k], "model": mdl[k], "core_id": cid[k]} for k in range(max(n, 0))]

    def last_diag(self) -> str:
        op, res, dev = C.c_int(), C.c_int(), C.c_int()
        buf = C.create_string_buffer(160)
        if self.lib.tb_last_diag(C.byref(op), C.byref(res), C.byref(dev), buf, 160):
            return f"{buf.value.decode(errors='replace')} (code {res.value}, device {dev.value})"
        return "no diagnostic"

    def colormap(self, gray: np.ndarray, color: int) -> np.ndarray:
        gray = np.ascontiguousarray(gray, dtype=np.uint8)
        h, w = gray.shape
        out = np.empty((h, w, 3), np.uint8)
        self.lib.tb_colormap(out.ctypes.data, gray.ctypes.data, color, w, h)
        return out


def _p(a: np.ndarray):
    return a.ctypes.data


class SdkCamera:
    """Real Thermal Expert Type B camera (TE-Q2, TE-V2 mini etc.) through the bridge."""

    simulated = False

    def __init__(self, model: int, dev_index: int):
        self.model = model
        self.dev_index = dev_index
        self.bridge = Bridge.get()
        if self.bridge is None:
            raise RuntimeError(f"Cannot load SDK bridge: {Bridge.load_error()}")
        self.h = None
        self._out = dict(tnf=False, snf=False, edge=1.0, enhance=False)
        # On the Windows x64 SDK 2.12.1 the V2 mini only delivers uncorrected
        # frames through GetRawFrame (its RecvImage variants fail and its
        # NUC/dead corrections are no-ops or blank the image), so the
        # corrections are done here and no temperatures are available.
        self.raw_mode = model == MODEL_V2MINI
        self._offset = None          # flat-field offset map (NUC)
        self._dead = None            # bad-pixel mask, found on the first frame
        self._prev = None            # temporal filter state
        self._range = None           # smoothed display range
        self.nuc_note = ""           # advice from the last NUC

    # ---------------------------------------------------------------- life
    def open(self) -> dict:
        if self.model not in TYPE_B_MODELS:
            raise RuntimeError(f"{MODEL_NAMES.get(self.model, self.model)} is a Type A model "
                               "and is not supported by this app")
        L = self.bridge.lib
        self.h = L.tb_open(self.model, self.dev_index)
        if not self.h:
            raise RuntimeError(f"Open failed – {self.bridge.last_diag()}")
        self.w, self.hgt = L.tb_width(self.h), L.tb_height(self.h)
        n = self.w * self.hgt
        # 4 bytes/pixel headroom, plus spare rows: the V2 mini sends metadata after the image.
        self._img = np.zeros(n * 2 + 8 * self.w, np.uint16)
        self._raw = np.zeros(n + 4 * self.w, np.float32)
        self._temp = np.zeros(n, np.float32)
        # GetRawFrame: 2 header words, the image, then spare room (as in the SDK sample).
        self._rawbuf = np.zeros(self.w * (self.hgt + 2) + 256, np.uint16)
        sn = C.create_string_buffer(128)
        L.tb_serial(self.h, sn, 128)
        serial = sn.value.decode(errors="replace").strip()
        if not serial.isprintable() or "\ufffd" in serial:
            serial = ""
        if not serial and self.model in SHUTTER_MODELS:
            num = L.tb_serial_num(self.h)
            serial = str(num) if num else ""
        fw = L.tb_firmware(self.h)
        if self.raw_mode and self._cal_path().exists():
            # The last flat field (NUC) taken with this camera type.
            try:
                self._load_raw_cal(self._cal_path())
            except (OSError, ValueError, KeyError):
                pass
        return {
            "source": f"USB #{self.dev_index}",
            "model": MODEL_NAMES.get(self.model, f"model {self.model}") + (" (image only)" if self.raw_mode else ""),
            "serial": serial or "—",
            "firmware": f"0x{fw:08X}" if fw else "—",
            "width": self.w, "height": self.hgt,
            "sdk": SDK_VERSION, "simulated": False,
            "shutter": self.model in SHUTTER_MODELS,
            "radiometric": not self.raw_mode,
            "nuc_loaded": self._offset is not None,
        }

    def close(self):
        if self.h:
            self.bridge.lib.tb_close(self.h)
            self.h = None

    # --------------------------------------------------------- acquisition
    def set_output(self, tnf: bool, snf: bool, edge: float, enhance: bool):
        self._out = dict(tnf=tnf, snf=snf, edge=edge, enhance=enhance)
        proc = tnf or snf or abs(edge - 1.0) > 1e-3
        self.bridge.lib.tb_set_output(self.h, 1, int(proc), int(tnf), int(snf), float(edge))

    def grab(self):
        """Returns (code, image16 HxW uint16, temps HxW float32 or None)."""
        if self.raw_mode:
            return self._grab_raw()
        L, n = self.bridge.lib, self.w * self.hgt
        o = self._out
        if o["enhance"]:
            code = L.tb_recv_raw(self.h, _p(self._raw))
            if code == 1:
                L.tb_enhance(self.h, _p(self._img), _p(self._raw))
        elif o["tnf"] or o["snf"] or abs(o["edge"] - 1.0) > 1e-3:
            code = L.tb_recv_processed(self.h, _p(self._img))
        else:
            code = L.tb_recv_agc(self.h, _p(self._img))
        if code != 1:
            return code, None, None
        L.tb_entire_temp(self.h, _p(self._temp))
        img = self._img[:n].reshape(self.hgt, self.w).copy()
        temps = self._temp.reshape(self.hgt, self.w).copy()
        return code, img, temps

    def _raw_frame(self) -> np.ndarray | None:
        code = self.bridge.lib.tb_raw_frame(self.h, _p(self._rawbuf))
        if code != 1:
            return None
        n = self.w * self.hgt
        return self._rawbuf[2:2 + n].reshape(self.hgt, self.w).astype(np.float32)

    def _grab_raw(self):
        f = self._raw_frame()
        if f is None:
            return 4, None, None
        if self._dead is None:
            self._dead = self._find_dead(f)
        if self._offset is not None:
            f -= self._offset
        if self._dead.any():
            f[self._dead] = cv2.medianBlur(f, 5)[self._dead]
        f = self._despeckle(self._destripe(f))
        o = self._out
        if o["tnf"]:
            if self._prev is not None and self._prev.shape == f.shape:
                # Motion-adaptive: average static pixels, follow moving ones.
                d = f - self._prev
                noise = 1.5 * float(np.median(np.abs(d[::4, ::4]))) + 1.0
                k = np.clip(np.abs(d) / (3.0 * noise), 0.25, 1.0)
                f = self._prev + k * d
            self._prev = f
        else:
            self._prev = None
        if o["snf"]:
            f = cv2.bilateralFilter(f, 5, 12.0, 3)
        lo, hi = np.percentile(f[::4, ::4], (0.5, 99.5))
        # Ease the display range so the brightness does not pump frame to frame.
        if self._range is not None:
            lo = 0.85 * self._range[0] + 0.15 * lo
            hi = 0.85 * self._range[1] + 0.15 * hi
        self._range = (lo, hi)
        img = np.clip((f - lo) / max(hi - lo, 1.0), 0, 1)
        if abs(o["edge"] - 1.0) > 1e-3:
            blur = cv2.GaussianBlur(img, (0, 0), 1.6)
            img = np.clip(img + (o["edge"] - 1.0) * (img - blur), 0, 1)
        img16 = (img * 65535).astype(np.uint16)
        if o["enhance"]:
            img16 = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8)).apply(img16)
        return 1, img16, None

    @staticmethod
    def _destripe(f: np.ndarray, limit: float = 40.0) -> np.ndarray:
        """Remove small column and row offsets, estimated from each pixel's
        difference to its horizontal (vertical) neighbours. Pixels near scene
        edges - differences above +-limit, far stronger than the sensor's
        residual stripes - are left out, so an edge cannot leak into a line."""
        hp = f - cv2.GaussianBlur(f, (9, 1), 2.0)
        ok = (np.abs(hp) < limit).astype(np.float32)
        f = f - ((hp * ok).sum(0) / (ok.sum(0) + 1.0))[None, :]
        hp = f - cv2.GaussianBlur(f, (1, 9), 2.0)
        ok = (np.abs(hp) < limit).astype(np.float32)
        return f - ((hp * ok).sum(1) / (ok.sum(1) + 1.0))[:, None]

    @staticmethod
    def _despeckle(f: np.ndarray) -> np.ndarray:
        """Replace isolated outlier pixels (e.g. pixels with a deviating gain
        that stand out away from the NUC temperature) by their 3x3 median."""
        med = cv2.medianBlur(f, 3)
        d = f - med
        mad = float(np.median(np.abs(d[::4, ::4]))) + 1.0
        bad = np.abs(d) > max(8.0 * mad, 30.0)
        f[bad] = med[bad]
        return f

    @staticmethod
    def _find_dead(f: np.ndarray, tstd: np.ndarray | None = None) -> np.ndarray:
        """Pixels stuck at the ends of the 14-bit range, far off their
        neighbours or (given a per-pixel temporal std) flickering."""
        dev = np.abs(f - cv2.medianBlur(f, 5))
        mad = float(np.median(dev)) or 1.0
        dead = (f <= 0) | (f >= 16383) | (dev > 15 * mad + 50)
        if tstd is not None:
            dead |= tstd > 6 * float(np.median(tstd)) + 3
        return dead

    def _mean_raw(self, count: int = 32, timeout: float = 5.0):
        """(mean, temporal std) of `count` raw frames, or (None, None)."""
        s = ss = None
        got, t0 = 0, time.perf_counter()
        while got < count and time.perf_counter() - t0 < timeout:
            f = self._raw_frame()
            if f is None:
                time.sleep(0.003)
                continue
            f = f.astype(np.float64)
            s, ss = (f, f * f) if s is None else (s + f, ss + f * f)
            got += 1
        if not got:
            return None, None
        mean = s / got
        std = np.sqrt(np.maximum(ss / got - mean * mean, 0))
        return mean.astype(np.float32), std.astype(np.float32)

    def _cal_path(self) -> Path:
        base = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "ThermalStudio"
        return base / f"v2mini_nuc_{self.w}x{self.hgt}.npz"

    def _save_raw_cal(self, path) -> bool:
        with open(path, "wb") as fh:
            np.savez(fh, offset=self._offset if self._offset is not None else np.zeros(0),
                     dead=self._dead if self._dead is not None else np.zeros(0, bool))
        return True

    def _load_raw_cal(self, path) -> bool:
        d = np.load(path)
        shape = (self.hgt, self.w)
        ok = False
        if d["offset"].shape == shape:
            self._offset, ok = d["offset"].astype(np.float32), True
        if d["dead"].shape == shape:
            self._dead, ok = d["dead"].astype(bool), True
        self._prev = self._range = None
        return ok

    def diag(self) -> str:
        return self.bridge.last_diag()

    # ------------------------------------------------------------ controls
    def set_emissivity(self, e: float):
        self.bridge.lib.tb_set_emissivity(self.h, float(e))

    def fpa_temp(self) -> float | None:
        v = self.bridge.lib.tb_fpa_temp(self.h)
        # Some models (TE-Q2) report implausible values (around -10 deg C) - hide them.
        return v if 0.0 < v < 100.0 else None

    def set_shutter(self, mode: int, value: int) -> tuple[bool, str]:
        """Automatic shutter (V2 / V2 mini). value: period in 30 s units for
        time mode, temperature-change limit for temperature mode."""
        L = self.bridge.lib
        code = L.tb_set_shutter_mode(self.h, mode)
        if code == 0 and mode == SHUTTER_TIME:
            code = L.tb_set_shutter_time(self.h, int(value))
        elif code == 0 and mode == SHUTTER_TEMP:
            code = L.tb_set_shutter_temp(self.h, int(value))
        return code == 0, "" if code == 0 else f"code {code}: {SHUTTER_CODES.get(code, 'unknown')}"

    def nuc(self, uniform: bool = False) -> bool:
        if self.raw_mode and uniform:
            # Flat field from a uniform surface filling the view: the averaged
            # frame is the sensor's pattern at every scale. Kept for the next connect.
            self.nuc_note = ""
            mean, std = self._mean_raw(60)
            if mean is None:
                return False
            dead = self._find_dead(mean, std)
            mean[dead] = cv2.medianBlur(mean, 5)[dead]
            self._dead = dead
            self._offset = mean - float(np.median(mean))
            self._prev = self._range = None
            try:
                self._cal_path().parent.mkdir(parents=True, exist_ok=True)
                self._save_raw_cal(self._cal_path())
            except OSError:
                pass
            return True
        if self.raw_mode:
            # Scene-based flat field: while the camera moves (or looks at a
            # uniform surface) the scene's fine detail changes from frame to
            # frame, but the per-pixel offsets stay put, so the temporal median
            # of the high-pass image is the fixed pattern. Kept for the next connect.
            self.nuc_note = ""
            hps, changes, prev, t0 = [], [], None, time.perf_counter()
            while time.perf_counter() - t0 < 4.0:
                f = self._raw_frame()
                if f is None:
                    time.sleep(0.002)
                    continue
                if prev is not None:
                    changes.append(float(np.abs(f[::4, ::4] - prev[::4, ::4]).mean()))
                prev = f
                # sigma 8 also catches the sensor's blotchy mid-scale pattern
                # (sigma 3 left it; 16 starts to wash out the scene).
                hps.append((f - cv2.GaussianBlur(f, (0, 0), 8.0)).astype(np.float16))
            if len(hps) < 20:
                return False
            H = np.stack(hps).astype(np.float32)
            fpn = np.median(H, axis=0)
            resid = np.median(np.abs(H - fpn), axis=0)      # per-pixel temporal noise
            motion = float(np.median(changes))              # ~4 still, ~18 when panning
            dead = self._find_dead(fpn + 8192.0)
            dead |= resid > 6 * float(np.median(resid)) + 3
            # Whole defective columns (the V2 mini's last column is one).
            cres = np.median(H - fpn, axis=(0, 1))
            cmad = float(np.median(np.abs(cres - np.median(cres)))) + 1.0
            dead[:, np.abs(cres - np.median(cres)) > 10 * cmad] = True
            colfp = np.median(fpn, axis=0)
            cdev = np.abs(colfp - np.median(colfp))
            dead[:, cdev > 10 * (float(np.median(cdev)) + 1.0)] = True
            self._dead = dead
            fpn[dead] = 0.0
            self._offset = fpn
            self._prev = self._range = None
            if motion < 8.0:
                self.nuc_note = ("little change seen - if the camera was still on a detailed scene, "
                                 "repeat while moving it or with the lens covered")
            try:
                self._cal_path().parent.mkdir(parents=True, exist_ok=True)
                self._save_raw_cal(self._cal_path())
            except OSError:
                pass
            return True
        return self.bridge.lib.tb_nuc(self.h) == 1

    def lens_calibration(self) -> bool:
        if self.raw_mode:
            return False
        return self.bridge.lib.tb_lens_offset_cal(self.h) == 1

    def update_dead(self) -> bool:
        if self.raw_mode:
            mean, std = self._mean_raw()
            if mean is None:
                return False
            if self._offset is not None:
                mean = mean - self._offset
            self._dead = self._find_dead(mean, std)
            return True
        return self.bridge.lib.tb_update_dead(self.h) == 1

    def save_calibration(self, path: str) -> bool:
        if self.raw_mode:
            return self._save_raw_cal(path)
        return self.bridge.lib.tb_save_cal(self.h, path.encode("mbcs")) == 1

    def load_calibration(self, path: str) -> bool:
        if self.raw_mode:
            return self._load_raw_cal(path)
        return self.bridge.lib.tb_load_cal(self.h, path.encode("mbcs")) == 1
