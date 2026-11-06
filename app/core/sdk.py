"""ctypes binding to te_bridge.dll (the flat C wrapper over the i3system SDK)
and the real-camera backend built on it."""
from __future__ import annotations

import ctypes as C
import os
import sys
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
        # The V2 mini supports only the plain AGC RecvImage: the SDK's output
        # pipeline (noise filters, edge) and the raw float frame used by i3
        # enhancement return -11, so those filters are applied here instead.
        self.app_filters = model == MODEL_V2MINI
        self._prev = None            # temporal filter state
        self._range = None           # smoothed display range

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
        sn = C.create_string_buffer(128)
        L.tb_serial(self.h, sn, 128)
        serial = sn.value.decode(errors="replace").strip()
        if not serial.isprintable() or "\ufffd" in serial:
            serial = ""
        if not serial and self.model in SHUTTER_MODELS:
            num = L.tb_serial_num(self.h)
            serial = str(num) if num else ""
        fw = L.tb_firmware(self.h)
        return {
            "source": f"USB #{self.dev_index}",
            "model": MODEL_NAMES.get(self.model, f"model {self.model}"),
            "serial": serial or "—",
            "firmware": f"0x{fw:08X}" if fw else "—",
            "width": self.w, "height": self.hgt,
            "sdk": SDK_VERSION, "simulated": False,
            "shutter": self.model in SHUTTER_MODELS,
        }

    def close(self):
        if self.h:
            self.bridge.lib.tb_close(self.h)
            self.h = None

    # --------------------------------------------------------- acquisition
    def set_output(self, tnf: bool, snf: bool, edge: float, enhance: bool):
        self._out = dict(tnf=tnf, snf=snf, edge=edge, enhance=enhance)
        if self.app_filters:
            self._prev = None
            return
        proc = tnf or snf or abs(edge - 1.0) > 1e-3
        self.bridge.lib.tb_set_output(self.h, 1, int(proc), int(tnf), int(snf), float(edge))

    def grab(self):
        """Returns (code, image16 HxW uint16, temps HxW float32)."""
        L, n = self.bridge.lib, self.w * self.hgt
        o = self._out
        if self.app_filters:
            code = L.tb_recv_agc(self.h, _p(self._img))
        elif o["enhance"]:
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
        if self.app_filters:
            img = self._filter(img.astype(np.float32))
        temps = self._temp.reshape(self.hgt, self.w).copy()
        return code, img, temps

    def _filter(self, f: np.ndarray) -> np.ndarray:
        """Display filters done in the app for models without SDK post-processing.
        Also stretches the SDK's AGC output, which only fills part of the 16-bit range."""
        o = self._out
        if o["tnf"]:
            if self._prev is not None and self._prev.shape == f.shape:
                # Motion-adaptive: average static pixels, follow moving ones.
                d = f - self._prev
                noise = 1.5 * float(np.median(np.abs(d[::4, ::4]))) + 1.0
                k = np.clip(np.abs(d) / (3.0 * noise), 0.25, 1.0)
                f = self._prev + k * d
            self._prev = f
        if o["snf"]:
            f = cv2.bilateralFilter(f, 5, 0.02 * (float(f.max()) - float(f.min()) + 1.0), 3)
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
        return img16

    def diag(self) -> str:
        return self.bridge.last_diag()

    # ------------------------------------------------------------ controls
    def set_emissivity(self, e: float):
        self.bridge.lib.tb_set_emissivity(self.h, float(e))

    def fpa_temp(self) -> float | None:
        v = self.bridge.lib.tb_fpa_temp(self.h)
        # The TE-Q2 and TE-V2 mini report implausible values (-10 to -15 deg C) - hide them.
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

    def nuc(self) -> bool:
        self._prev = self._range = None
        return self.bridge.lib.tb_nuc(self.h) == 1

    def lens_calibration(self) -> bool:
        return self.bridge.lib.tb_lens_offset_cal(self.h) == 1

    def update_dead(self) -> bool:
        return self.bridge.lib.tb_update_dead(self.h) == 1

    def save_calibration(self, path: str) -> bool:
        return self.bridge.lib.tb_save_cal(self.h, path.encode("mbcs")) == 1

    def load_calibration(self, path: str) -> bool:
        return self.bridge.lib.tb_load_cal(self.h, path.encode("mbcs")) == 1
