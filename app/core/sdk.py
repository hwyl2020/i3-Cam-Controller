"""ctypes binding to te_bridge.dll (the flat C wrapper over the i3system SDK)
and the real-camera backend built on it."""
from __future__ import annotations

import ctypes as C
import os
import sys
from pathlib import Path

import numpy as np

SDK_VERSION = "2.12.1"

MODEL_NAMES = {
    1: "TE-Q1", 2: "TE-V1", 3: "TE-EQ1", 4: "TE-EV1", 9: "TE-M1",
    12: "TE-EQ2", 13: "TE-EV2", 14: "TE-Q2", 15: "TE-V2", 17: "TE-V2 mini",
}
TYPE_B_MODELS = {1, 2, 9, 14, 15, 17}
MODEL_Q2 = 14

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
    """Real Thermal Expert Type B camera (TE-Q2 etc.) through the bridge."""

    simulated = False

    def __init__(self, model: int, dev_index: int):
        self.model = model
        self.dev_index = dev_index
        self.bridge = Bridge.get()
        if self.bridge is None:
            raise RuntimeError(f"Cannot load SDK bridge: {Bridge.load_error()}")
        self.h = None
        self._out = dict(tnf=False, snf=False, edge=1.0, enhance=False)

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
        self._img = np.zeros(n * 2, np.uint16)       # 4 bytes/pixel headroom
        self._raw = np.zeros(n, np.float32)
        self._temp = np.zeros(n, np.float32)
        sn = C.create_string_buffer(128)
        L.tb_serial(self.h, sn, 128)
        fw = L.tb_firmware(self.h)
        return {
            "source": f"USB #{self.dev_index}",
            "model": MODEL_NAMES.get(self.model, f"model {self.model}"),
            "serial": sn.value.decode(errors="replace") or "—",
            "firmware": f"0x{fw:08X}" if fw else "—",
            "width": self.w, "height": self.hgt,
            "sdk": SDK_VERSION, "simulated": False,
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
        """Returns (code, image16 HxW uint16, temps HxW float32)."""
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

    def diag(self) -> str:
        return self.bridge.last_diag()

    # ------------------------------------------------------------ controls
    def set_emissivity(self, e: float):
        self.bridge.lib.tb_set_emissivity(self.h, float(e))

    def fpa_temp(self) -> float | None:
        v = self.bridge.lib.tb_fpa_temp(self.h)
        # The TE-Q2 reports implausible values (around -10 deg C) - hide them.
        return v if 0.0 < v < 100.0 else None

    def nuc(self) -> bool:
        return self.bridge.lib.tb_nuc(self.h) == 1

    def lens_calibration(self) -> bool:
        return self.bridge.lib.tb_lens_offset_cal(self.h) == 1

    def update_dead(self) -> bool:
        return self.bridge.lib.tb_update_dead(self.h) == 1

    def save_calibration(self, path: str) -> bool:
        return self.bridge.lib.tb_save_cal(self.h, path.encode("mbcs")) == 1

    def load_calibration(self, path: str) -> bool:
        return self.bridge.lib.tb_load_cal(self.h, path.encode("mbcs")) == 1
