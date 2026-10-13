"""Main application window."""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import numpy as np
from PySide6.QtCore import QSettings, Qt, QTimer, QUrl
from PySide6.QtGui import QDesktopServices, QKeySequence, QShortcut
from PySide6.QtWidgets import (QComboBox, QDoubleSpinBox, QFileDialog, QFrame, QGridLayout,
                               QHBoxLayout, QLabel, QMainWindow, QPlainTextEdit, QPushButton,
                               QScrollArea, QSizePolicy, QVBoxLayout, QWidget)

from core import palettes
from core.engine import DEFAULTS, Engine
from core.recorder import Recorder
from core.sdk import MODEL_NAMES, MODEL_Q2, SDK_VERSION, Bridge, SdkCamera
from core.simulator import SimCamera
from . import theme
from .video_view import VideoView, fmt, to_unit
from .widgets import (Card, LabeledSlider, Segmented, StatChip, hint, palette_icon, row)

APP_NAME = "Thermal Studio"

EMISSIVITY_PRESETS = [
    ("Custom", None), ("Human skin", 0.98), ("Water", 0.96), ("Matte black paint", 0.95),
    ("Paper", 0.93), ("Concrete", 0.92), ("Plastic", 0.91), ("Wood", 0.90),
    ("Oxidized steel", 0.79), ("Anodized aluminium", 0.77), ("Brushed aluminium", 0.30),
]


def project_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parents[2]


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} — i3system TE-Q2")
        self.setWindowIcon(theme.app_icon())
        self.resize(1480, 900)
        self.setMinimumSize(1100, 700)

        self.store = QSettings("ThermalStudio", "TE-Q2")
        self.cfg = dict(DEFAULTS)
        self._restore_cfg()
        self.unit = self.store.value("unit", "C")
        self.captures = project_root() / "captures"

        self.engine: Engine | None = None
        self.connected = False
        self.info: dict = {}
        self.recorder = Recorder()
        self._last_stats_t = 0.0
        self._last_pk = None

        root = QWidget()
        root.setObjectName("Root")
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(self._build_header())
        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        body.addWidget(self._build_center(), 1)
        self.sidebar = self._build_sidebar()
        body.addWidget(self.sidebar)
        outer.addLayout(body, 1)

        self.statusBar().showMessage("Ready")
        self._build_shortcuts()
        self._apply_unit()
        self._set_state("idle")

        self.tick = QTimer(self)
        self.tick.timeout.connect(self._on_tick)
        self.tick.start(250)

        err = Bridge.load_error()
        if err:
            self.log("error", f"i3system SDK could not be loaded: {err}. Only the simulator is available.")
        else:
            self.log("info", f"i3system SDK {SDK_VERSION} loaded · palettes from {palettes.source}")
        self.refresh_sources()

    # ================================================================ header
    def _build_header(self) -> QWidget:
        w = QFrame()
        w.setObjectName("Header")
        w.setFixedHeight(64)
        lay = QHBoxLayout(w)
        lay.setContentsMargins(18, 8, 18, 8)
        lay.setSpacing(10)

        logo = QLabel()
        logo.setPixmap(theme.app_icon().pixmap(34, 34))
        lay.addWidget(logo)
        titles = QVBoxLayout()
        titles.setSpacing(0)
        t = QLabel(APP_NAME)
        t.setObjectName("AppTitle")
        s = QLabel("i3system Thermal Expert  ·  TE-Q2 control & live view")
        s.setObjectName("AppSub")
        titles.addWidget(t)
        titles.addWidget(s)
        lay.addLayout(titles)
        lay.addStretch(1)

        src = QLabel("Source")
        src.setObjectName("Key")
        lay.addWidget(src)
        self.source = QComboBox()
        self.source.setMinimumWidth(300)
        lay.addWidget(self.source)
        self.btn_refresh = QPushButton("Scan")
        self.btn_refresh.setToolTip("Rescan USB for cameras")
        self.btn_refresh.clicked.connect(self.refresh_sources)
        lay.addWidget(self.btn_refresh)
        self.btn_connect = QPushButton("Connect")
        self.btn_connect.setObjectName("Primary")
        self.btn_connect.setMinimumWidth(116)
        self.btn_connect.clicked.connect(self.toggle_connection)
        lay.addWidget(self.btn_connect)

        lay.addSpacing(8)
        self.pill = QLabel()
        self.pill.setMinimumWidth(130)
        self.pill.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self.pill)
        self.btn_present = QPushButton("⛶  Present")
        self.btn_present.setToolTip("Presentation mode – full screen, controls hidden (F11)")
        self.btn_present.clicked.connect(self.toggle_presentation)
        lay.addWidget(self.btn_present)
        return w

    # ================================================================ centre
    def _build_center(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(16, 14, 16, 0)
        lay.setSpacing(10)

        self.stats_bar = QWidget()
        sl = QHBoxLayout(self.stats_bar)
        sl.setContentsMargins(0, 0, 0, 0)
        sl.setSpacing(10)
        self.chip_max = StatChip("Max", theme.HOT)
        self.chip_min = StatChip("Min", theme.COLD)
        self.chip_center = StatChip("Center", "#FFFFFF")
        self.chip_avg = StatChip("Scene avg")
        self.chip_area = StatChip("Area max / avg", theme.ACCENT)
        self.chip_fpa = StatChip("Sensor (FPA)")
        for c in (self.chip_max, self.chip_min, self.chip_center, self.chip_avg, self.chip_area, self.chip_fpa):
            c.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            sl.addWidget(c)
        lay.addWidget(self.stats_bar)

        self.view = VideoView()
        self.view.unit = self.unit
        self.view.roi_changed.connect(self._update_stats_now)
        lay.addWidget(self.view, 1)

        self.toolbar = QFrame()
        self.toolbar.setObjectName("ToolBar")
        tl = QHBoxLayout(self.toolbar)
        tl.setContentsMargins(0, 8, 0, 10)
        tl.setSpacing(6)
        self.btn_pause = self._tool("❚❚  Pause", "Freeze the live image (Space)", self.toggle_pause, True)
        self.btn_snap = self._tool("◉  Snapshot", "Save PNG (+ temperature CSV) (S)", self.snapshot)
        self.btn_rec = self._tool("●  Record", "Record MP4 video (R)", self.toggle_record, True)
        for b in (self.btn_pause, self.btn_snap, self.btn_rec):
            tl.addWidget(b)
        tl.addSpacing(12)
        tl.addWidget(self._sep())
        zl = QLabel("Zoom")
        zl.setObjectName("Key")
        tl.addWidget(zl)
        self.seg_zoom = Segmented([(1, "1×"), (2, "2×"), (4, "4×")], 1)
        self.seg_zoom.setFixedWidth(130)
        self.seg_zoom.changed.connect(self.set_zoom)
        tl.addWidget(self.seg_zoom)
        tl.addSpacing(6)
        self.btn_fh = self._tool("⇋  Mirror", "Flip image horizontally", lambda c: self.set_cfg(flip_h=c), True)
        self.btn_fv = self._tool("⇵  Flip", "Flip image vertically", lambda c: self.set_cfg(flip_v=c), True)
        self.btn_fh.setChecked(self.cfg["flip_h"])
        self.btn_fv.setChecked(self.cfg["flip_v"])
        tl.addWidget(self.btn_fh)
        tl.addWidget(self.btn_fv)
        tl.addWidget(self._sep())
        tl.addWidget(self._tool("✕  Clear marks", "Remove spot markers and area (C)", lambda *_: self.view.clear_marks()))
        tl.addStretch(1)
        h = hint("Click: pin spot  ·  Drag: measure area  ·  Right-click: clear")
        h.setWordWrap(False)
        tl.addWidget(h)
        lay.addWidget(self.toolbar)
        return w

    def _tool(self, text, tip, slot, checkable=False) -> QPushButton:
        b = QPushButton(text)
        b.setObjectName("Tool")
        b.setToolTip(tip)
        b.setCheckable(checkable)
        b.setCursor(Qt.CursorShape.PointingHandCursor)
        if checkable:
            b.toggled.connect(slot)
        else:
            b.clicked.connect(slot)
        return b

    def _sep(self) -> QFrame:
        f = QFrame()
        f.setFixedSize(1, 22)
        f.setStyleSheet(f"background:{theme.BORDER};")
        return f

    # =============================================================== sidebar
    def _build_sidebar(self) -> QWidget:
        side = QFrame()
        side.setObjectName("Sidebar")
        side.setFixedWidth(348)
        outer = QVBoxLayout(side)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        outer.addWidget(scroll)
        inner = QWidget()
        inner.setMaximumWidth(side.width() - 10)
        lay = QVBoxLayout(inner)
        lay.setContentsMargins(14, 14, 14, 14)
        lay.setSpacing(12)
        scroll.setWidget(inner)

        lay.addWidget(self._card_palette())
        lay.addWidget(self._card_image())
        lay.addWidget(self._card_measure())
        lay.addWidget(self._card_alarm())
        lay.addWidget(self._card_calibration())
        lay.addWidget(self._card_capture())
        lay.addWidget(self._card_device())
        lay.addWidget(self._card_log())
        lay.addStretch(1)
        return side

    def _card_palette(self):
        card = Card("Color palette")
        grid = QGridLayout()
        grid.setSpacing(6)
        self.palette_btns = []
        for i, (name, lut) in enumerate(zip(palettes.NAMES, palettes.luts())):
            b = QPushButton(name)
            b.setObjectName("Palette")
            b.setCheckable(True)
            b.setIcon(palette_icon(lut))
            b.setIconSize(palette_icon(lut).availableSizes()[0])
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setMinimumWidth(0)
            b.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
            b.clicked.connect(lambda _=False, k=i: self.set_palette(k))
            grid.addWidget(b, i // 2, i % 2)
            self.palette_btns.append(b)
        card.add(grid)
        self.palette_btns[self.cfg["palette"]].setChecked(True)
        return card

    def _card_image(self):
        card = Card("Image")
        k = QLabel("Temperature range")
        k.setObjectName("Key")
        card.add(k)
        self.seg_range = Segmented([("agc", "Auto (AGC)"), ("linear", "Linear"), ("manual", "Manual")],
                                   self.cfg["range_mode"])
        self.seg_range.changed.connect(self.set_range_mode)
        card.add(self.seg_range)
        self.spin_min = QDoubleSpinBox()
        self.spin_max = QDoubleSpinBox()
        for s in (self.spin_min, self.spin_max):
            s.setFixedWidth(88)
            s.setRange(-40, 600)
            s.setDecimals(1)
            s.setSingleStep(0.5)
            s.setKeyboardTracking(False)
            s.valueChanged.connect(self._manual_range_changed)
        lo, hi = QLabel("Min"), QLabel("Max")
        lo.setObjectName("Key")
        hi.setObjectName("Key")
        self.btn_fit = QPushButton("Fit")
        self.btn_fit.setToolTip("Set the manual range to the current scene min/max")
        self.btn_fit.clicked.connect(self.fit_range)
        card.add(row(lo, self.spin_min, hi, self.spin_max, None, self.btn_fit))
        card.add(hint("AGC maximises contrast. Linear / Manual give a true temperature scale."))

        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background:{theme.BORDER};")
        card.add(sep)

        from PySide6.QtWidgets import QCheckBox
        self.chk_tnf = QCheckBox("Temporal noise filter")
        self.chk_snf = QCheckBox("Spatial noise filter")
        self.chk_enh = QCheckBox("i3 image enhancement")
        self.chk_tnf.setChecked(self.cfg["tnf"])
        self.chk_snf.setChecked(self.cfg["snf"])
        self.chk_enh.setChecked(self.cfg["enhance"])
        self.chk_tnf.toggled.connect(lambda c: self.set_cfg(tnf=c))
        self.chk_snf.toggled.connect(lambda c: self.set_cfg(snf=c))
        self.chk_enh.toggled.connect(lambda c: self.set_cfg(enhance=c))
        self.chk_enh.setToolTip("SDK denoise + contrast + edge enhancement pipeline")
        for c in (self.chk_tnf, self.chk_snf, self.chk_enh):
            card.add(c)
        self.sl_edge = LabeledSlider("Edge enhancement", 0.0, 3.0, 0.1, self.cfg["edge"], "{:.1f}")
        self.sl_edge.valueChanged.connect(lambda v: self.set_cfg(edge=round(v, 2)))
        card.add(self.sl_edge)
        self._sync_range_controls()
        return card

    def _card_measure(self):
        card = Card("Measurement")
        self.sl_eps = LabeledSlider("Emissivity", 0.10, 1.00, 0.01, self.cfg["emissivity"])
        self.sl_eps.valueChanged.connect(self._emissivity_changed)
        card.add(self.sl_eps)
        self.cmb_eps = QComboBox()
        for name, v in EMISSIVITY_PRESETS:
            self.cmb_eps.addItem(name if v is None else f"{name}  ·  {v:.2f}", v)
        self.cmb_eps.currentIndexChanged.connect(self._eps_preset)
        ml = QLabel("Material")
        ml.setObjectName("Key")
        card.add(row(ml, self.cmb_eps))
        self._sync_eps_preset()

        ul = QLabel("Units")
        ul.setObjectName("Key")
        self.seg_unit = Segmented([("C", "°C"), ("F", "°F")], self.unit)
        self.seg_unit.setFixedWidth(120)
        self.seg_unit.changed.connect(self.set_unit)
        card.add(row(ul, None, self.seg_unit))

        from PySide6.QtWidgets import QCheckBox
        ov = QLabel("Overlays")
        ov.setObjectName("Key")
        card.add(ov)
        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(8)
        labels = [("center", "Center spot"), ("hot", "Hot spot"), ("cold", "Cold spot"),
                  ("cursor", "Cursor readout"), ("hud", "Info overlay"), ("bar", "Color bar")]
        for i, (key, text) in enumerate(labels):
            c = QCheckBox(text)
            c.setChecked(self.store.value(f"show_{key}", True, type=bool))
            self.view.show[key] = c.isChecked()
            c.toggled.connect(lambda v, k=key: self._set_overlay(k, v))
            grid.addWidget(c, i // 2, i % 2)
        card.add(grid)
        return card

    def _card_alarm(self):
        from PySide6.QtWidgets import QCheckBox
        card = Card("Temperature alarm")
        self.chk_alarm = QCheckBox("Highlight pixels above threshold")
        self.chk_alarm.setChecked(self.cfg["alarm"])
        self.chk_alarm.toggled.connect(lambda c: self.set_cfg(alarm=c))
        card.add(self.chk_alarm)
        self.spin_alarm = QDoubleSpinBox()
        self.spin_alarm.setRange(-40, 1000)
        self.spin_alarm.setDecimals(1)
        self.spin_alarm.setKeyboardTracking(False)
        self.spin_alarm.valueChanged.connect(self._alarm_changed)
        tl = QLabel("Threshold")
        tl.setObjectName("Key")
        card.add(row(tl, None, self.spin_alarm))
        card.add(hint("Hot regions are painted magenta and a flashing banner appears."))
        return card

    def _card_calibration(self):
        card = Card("Calibration")
        self.btn_nuc = QPushButton("Flat-field correction (NUC)")
        self.btn_nuc.clicked.connect(lambda: self.run_cam_task("NUC", lambda c: (c.nuc(), "")))
        self.btn_lens = QPushButton("Lens offset calibration")
        self.btn_lens.clicked.connect(lambda: self.run_cam_task("Lens offset calibration",
                                                                lambda c: (c.lens_calibration(), "")))
        self.btn_dead = QPushButton("Detect bad pixels")
        self.btn_dead.clicked.connect(lambda: self.run_cam_task("Bad-pixel update",
                                                                lambda c: (c.update_dead(), "")))
        self.btn_savecal = QPushButton("Save…")
        self.btn_loadcal = QPushButton("Load…")
        self.btn_savecal.clicked.connect(self.save_calibration)
        self.btn_loadcal.clicked.connect(self.load_calibration)
        card.add(self.btn_nuc)
        card.add(self.btn_lens)
        card.add(self.btn_dead)
        cl = QLabel("Calibration file")
        cl.setObjectName("Key")
        card.add(row(cl, None, self.btn_savecal, self.btn_loadcal))
        card.add(hint("Point the camera at a uniform surface (e.g. a wall or lens cap) before "
                      "running NUC or lens calibration."))
        self.cal_buttons = [self.btn_nuc, self.btn_lens, self.btn_dead, self.btn_savecal, self.btn_loadcal]
        return card

    def _card_capture(self):
        from PySide6.QtWidgets import QCheckBox
        card = Card("Capture")
        self.chk_csv = QCheckBox("Also save temperature CSV")
        self.chk_csv.setToolTip("Every snapshot also writes the full per-pixel temperature map as CSV")
        self.chk_csv.setChecked(self.store.value("save_csv", True, type=bool))
        card.add(self.chk_csv)
        b = QPushButton("Open captures folder")
        b.clicked.connect(self.open_captures)
        card.add(b)
        self.lbl_capture = hint(f"Saved to {self.captures}")
        card.add(self.lbl_capture)
        return card

    def _card_device(self):
        card = Card("Device")
        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(6)
        self.dev = {}
        fields = [("source", "Source"), ("model", "Model"), ("serial", "Serial no."),
                  ("firmware", "Firmware"), ("res", "Resolution"), ("fps", "Frame rate"),
                  ("fpa", "Sensor temp"), ("sdk", "SDK")]
        for i, (key, text) in enumerate(fields):
            k = QLabel(text)
            k.setObjectName("Key")
            v = QLabel("—")
            v.setObjectName("Value")
            v.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            grid.addWidget(k, i, 0)
            grid.addWidget(v, i, 1)
            self.dev[key] = v
        grid.setColumnStretch(1, 1)
        self.dev["sdk"].setText(SDK_VERSION)
        card.add(grid)
        return card

    def _card_log(self):
        card = Card("Event log")
        self.logbox = QPlainTextEdit()
        self.logbox.setReadOnly(True)
        self.logbox.setMaximumBlockCount(300)
        self.logbox.setFixedHeight(150)
        card.add(self.logbox)
        return card

    # ============================================================ shortcuts
    def _build_shortcuts(self):
        def sc(key, fn):
            s = QShortcut(QKeySequence(key), self)
            s.activated.connect(fn)
        sc("F11", self.toggle_presentation)
        sc("Esc", lambda: self.isFullScreen() and self.toggle_presentation())
        sc("Space", lambda: self.btn_pause.toggle())
        sc("S", self.snapshot)
        sc("R", lambda: self.btn_rec.toggle())
        sc("P", lambda: self.set_palette((self.cfg["palette"] + 1) % len(palettes.NAMES)))
        sc("C", self.view.clear_marks)
        sc("1", lambda: self.set_zoom(1))
        sc("2", lambda: self.set_zoom(2))
        sc("4", lambda: self.set_zoom(4))

    # ============================================================== sources
    def refresh_sources(self):
        prev = self.source.currentData()
        self.source.clear()
        bridge = Bridge.get()
        found = []
        if bridge is not None:
            try:
                found = bridge.scan()
            except Exception as exc:  # noqa: BLE001
                self.log("warn", f"USB scan failed: {exc}")
        for d in found:
            # Type B cameras (Q2) are not identified by the scan: model comes back 0.
            model = d["model"] if d["model"] in MODEL_NAMES else MODEL_Q2
            ident = f"  ·  ID {d['core_id']}" if d["core_id"] else ""
            self.source.addItem(f"●  {MODEL_NAMES[model]}  ·  USB #{d['index']}{ident}",
                                {"kind": "sdk", "model": model, "index": d["index"]})
        if bridge is not None:
            for i in range(2):
                self.source.addItem(f"TE-Q2 direct open  ·  USB #{i}",
                                    {"kind": "sdk", "model": MODEL_Q2, "index": i})
        self.source.addItem("Demo simulator (no camera)", {"kind": "sim"})
        if found:
            self.log("ok", f"Found {len(found)} camera(s) on USB")
            self.source.setCurrentIndex(0)
        else:
            self.log("info", "No camera found by USB scan – direct open or simulator available")
            last = self.store.value("source_kind", "sim")
            idx = self.source.count() - 1 if last == "sim" or prev is None else 0
            if prev is not None:
                for i in range(self.source.count()):
                    if self.source.itemData(i) == prev:
                        idx = i
            self.source.setCurrentIndex(idx)

    def toggle_connection(self):
        if self.engine is not None:
            self.disconnect_camera()
            return
        src = self.source.currentData()
        if src is None:
            return
        if src["kind"] == "sim":
            factory = SimCamera
        else:
            model, index = src["model"], src["index"]
            factory = lambda: SdkCamera(model, index)  # noqa: E731
        self.store.setValue("source_kind", src["kind"])
        self.engine = Engine(self)
        self.engine.packet.connect(self.on_packet)
        self.engine.opened.connect(self.on_opened)
        self.engine.closed.connect(self.on_closed)
        self.engine.log.connect(self.log)
        self.engine.task_done.connect(self.on_task_done)
        self.engine.update(**self.cfg)
        self._set_state("connecting")
        self.view.clear("Connecting…", "Opening the camera and reading its calibration data")
        self.log("info", f"Connecting to {self.source.currentText()}")
        self.engine.start_camera(factory)

    def disconnect_camera(self):
        if self.engine is None:
            return
        self.btn_connect.setEnabled(False)
        self.engine.stop_camera()

    # ============================================================ callbacks
    def on_opened(self, info: dict):
        self.connected = True
        self.info = info
        self.view.info = info
        self.dev["source"].setText(info["source"])
        self.dev["model"].setText(info["model"])
        self.dev["serial"].setText(info["serial"])
        self.dev["firmware"].setText(info["firmware"])
        self.dev["res"].setText(f"{info['width']} × {info['height']}")
        self._set_state("live", "Simulator" if info.get("simulated") else "Live")
        self.statusBar().showMessage(f"Streaming from {info['model']}")

    def on_closed(self, reason: str):
        if self.recorder.active:
            self.btn_rec.setChecked(False)
        eng, self.engine = self.engine, None
        if eng is not None:
            eng.wait(2000)
            eng.deleteLater()
        self.connected = False
        self.view.frozen = False
        self.btn_pause.setChecked(False)
        for k in ("source", "model", "serial", "firmware", "res", "fps", "fpa"):
            self.dev[k].setText("—")
        if reason:
            self._set_state("error")
            self.view.clear("Camera error", reason)
            self.log("error", reason)
            self.statusBar().showMessage("Camera error – see event log")
        else:
            self._set_state("idle")
            self.view.clear("Disconnected", "Choose a source above and press Connect")
            self.log("info", "Disconnected")
            self.statusBar().showMessage("Disconnected")

    def on_packet(self, pk):
        self._last_pk = pk
        self.view.set_packet(pk)
        if self.recorder.active:
            img = self.view.render_composite(2.0)
            if img is not None:
                self.recorder.write(img)
        now = time.perf_counter()
        if now - self._last_stats_t > 0.2:
            self._last_stats_t = now
            self._update_stats(pk)

    def _update_stats_now(self):
        if self.view.packet is not None:
            self._update_stats(self.view.packet)

    def _update_stats(self, pk):
        u = self.unit
        st = pk.stats
        self.chip_max.set(fmt(st.get("max"), u))
        self.chip_min.set(fmt(st.get("min"), u))
        self.chip_center.set(fmt(st.get("center"), u))
        self.chip_avg.set(fmt(st.get("mean"), u))
        r = self.view.roi_stats()
        self.chip_area.set(f"{fmt(r['max'], u)} / {fmt(r['mean'], u, False)}" if r else "drag on image")
        self.chip_fpa.setVisible(pk.fpa is not None)    # TE-Q2 has no usable FPA reading
        self.chip_fpa.set(fmt(pk.fpa, u) if pk.fpa is not None else "—")
        self.dev["fps"].setText(f"{pk.fps:.1f} fps")
        self.dev["fpa"].setText(fmt(pk.fpa, u) if pk.fpa is not None else "—")

    def on_task_done(self, name: str, ok: bool, msg: str):
        for b in self.cal_buttons:
            b.setEnabled(self.connected)
        level = "ok" if ok else "error"
        text = f"{name} {'completed' if ok else 'failed'}" + (f": {msg}" if msg else "")
        self.log(level, text)
        self.statusBar().showMessage(text, 6000)

    def _on_tick(self):
        if self.recorder.active:
            e = self.recorder.elapsed()
            self.view.rec_elapsed = e
            m, s = divmod(int(e), 60)
            self.btn_rec.setText(f"■  Stop  {m:02d}:{s:02d}")
        if self.view.frozen or (self._last_pk is not None and self._last_pk.alarm):
            self.view.update()
        en = self.connected
        self.btn_snap.setEnabled(en)
        self.btn_rec.setEnabled(en)
        self.btn_pause.setEnabled(en)
        if self.engine is None:
            self.btn_connect.setEnabled(True)

    # ============================================================== actions
    def set_cfg(self, **kw):
        self.cfg.update(kw)
        if self.engine is not None:
            self.engine.update(**kw)
        for k, v in kw.items():
            self.store.setValue(f"cfg/{k}", v)

    def set_palette(self, i: int):
        self.palette_btns[i].setChecked(True)
        for j, b in enumerate(self.palette_btns):
            if j != i:
                b.setChecked(False)
        self.set_cfg(palette=i)

    def set_range_mode(self, mode: str):
        self.seg_range.set(mode)
        self.set_cfg(range_mode=mode)
        self._sync_range_controls()

    def _sync_range_controls(self):
        manual = self.cfg["range_mode"] == "manual"
        for w in (self.spin_min, self.spin_max, self.btn_fit):
            w.setEnabled(manual)

    def _manual_range_changed(self, _):
        lo, hi = self._u2c(self.spin_min.value()), self._u2c(self.spin_max.value())
        if hi - lo < 0.5:
            hi = lo + 0.5
        self.set_cfg(tmin=lo, tmax=hi)

    def fit_range(self):
        pk = self.view.packet
        if pk is None or not pk.stats:
            return
        self._set_spins(pk.stats["min"], pk.stats["max"])
        self.set_cfg(tmin=pk.stats["min"], tmax=pk.stats["max"])

    def _emissivity_changed(self, v):
        self.set_cfg(emissivity=round(v, 2))
        self._sync_eps_preset()

    def _eps_preset(self, idx):
        v = self.cmb_eps.itemData(idx)
        if v is not None and abs(v - self.sl_eps.value()) > 1e-3:
            self.sl_eps.setValue(v)

    def _sync_eps_preset(self):
        v = round(self.sl_eps.value(), 2)
        idx = 0
        for i in range(1, self.cmb_eps.count()):
            if abs(self.cmb_eps.itemData(i) - v) < 1e-3:
                idx = i
                break
        self.cmb_eps.blockSignals(True)
        self.cmb_eps.setCurrentIndex(idx)
        self.cmb_eps.blockSignals(False)

    def _alarm_changed(self, v):
        t = self._u2c(v)
        self.view.alarm_threshold = t
        self.set_cfg(alarm_threshold=t)

    def _set_overlay(self, key, on):
        self.view.show[key] = on
        self.store.setValue(f"show_{key}", on)
        self.view.update()

    def set_unit(self, unit):
        self.unit = unit
        self.store.setValue("unit", unit)
        self._apply_unit()

    def _apply_unit(self):
        self.view.unit = self.unit
        self.seg_unit.set(self.unit) if hasattr(self, "seg_unit") else None
        self._set_spins(self.cfg["tmin"], self.cfg["tmax"])
        self.spin_alarm.blockSignals(True)
        self.spin_alarm.setSuffix(f" °{self.unit}")
        self.spin_alarm.setValue(to_unit(self.cfg["alarm_threshold"], self.unit))
        self.spin_alarm.blockSignals(False)
        self.view.alarm_threshold = self.cfg["alarm_threshold"]
        self._update_stats_now()
        self.view.update()

    def _set_spins(self, lo_c, hi_c):
        for s, v in ((self.spin_min, lo_c), (self.spin_max, hi_c)):
            s.blockSignals(True)
            s.setSuffix(f" °{self.unit}")
            s.setValue(to_unit(v, self.unit))
            s.blockSignals(False)

    def _u2c(self, v):
        return (v - 32) * 5 / 9 if self.unit == "F" else v

    def set_zoom(self, z):
        self.seg_zoom.set(z)
        self.view.zoom = z
        self.view.update()

    def toggle_pause(self, on):
        self.view.frozen = on
        self.btn_pause.setText("▶  Resume" if on else "❚❚  Pause")
        self.view.update()

    def _stamp(self) -> str:
        model = (self.info.get("model") or "TE").split(" ")[0].replace("-", "")
        return f"{model}_{time.strftime('%Y%m%d_%H%M%S')}"

    def snapshot(self):
        if not self.connected or self.view.packet is None:
            return
        self.captures.mkdir(parents=True, exist_ok=True)
        base = self.captures / self._stamp()
        img = self.view.render_composite(2.0)
        img.save(str(base) + ".png")
        saved = [base.name + ".png"]
        pk = self.view.packet
        if self.chk_csv.isChecked() and pk.temps is not None:
            np.savetxt(str(base) + ".csv", pk.temps, fmt="%.2f", delimiter=",",
                       header=f"{self.info.get('model','')} temperature map, deg C, "
                              f"{pk.temps.shape[1]}x{pk.temps.shape[0]}, emissivity {self.cfg['emissivity']}")
            saved.append(base.name + ".csv")
        self.store.setValue("save_csv", self.chk_csv.isChecked())
        self.log("ok", "Snapshot saved: " + ", ".join(saved))
        self.statusBar().showMessage(f"Snapshot saved to {self.captures}", 5000)

    def toggle_record(self, on):
        if on:
            if not self.connected:
                self.btn_rec.setChecked(False)
                return
            self.captures.mkdir(parents=True, exist_ok=True)
            path = self.captures / (self._stamp() + ".mp4")
            fps = self.view.packet.fps if self.view.packet else 9
            self.recorder.start(path, fps)
            self.view.recording = True
            self.btn_rec.setObjectName("Danger")
            self.log("info", f"Recording started ({self.recorder.fps:.0f} fps)")
        else:
            path = self.recorder.stop()
            self.view.recording = False
            self.view.rec_elapsed = 0
            self.btn_rec.setObjectName("Tool")
            self.btn_rec.setText("●  Record")
            if path:
                self.log("ok", f"Recording saved: {path.name} ({self.recorder.frames} frames)")
                self.statusBar().showMessage(f"Recording saved to {path}", 6000)
        self.btn_rec.style().unpolish(self.btn_rec)
        self.btn_rec.style().polish(self.btn_rec)

    def open_captures(self):
        self.captures.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.captures)))

    def run_cam_task(self, name, fn):
        if self.engine is None or not self.connected:
            return
        for b in self.cal_buttons:
            b.setEnabled(False)
        self.log("info", f"{name} running…")
        self.statusBar().showMessage(f"{name} running – keep the camera still")
        self.engine.run_task(name, lambda cam: (lambda r: (bool(r[0]), r[1]))(fn(cam)))

    def save_calibration(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save calibration", str(self.captures / "calibration.dat"),
                                              "Calibration (*.dat);;All files (*)")
        if path:
            self.run_cam_task("Save calibration", lambda c: (c.save_calibration(path), os.path.basename(path)))

    def load_calibration(self):
        path, _ = QFileDialog.getOpenFileName(self, "Load calibration", str(self.captures),
                                              "Calibration (*.dat *.npy);;All files (*)")
        if path:
            self.run_cam_task("Load calibration", lambda c: (c.load_calibration(path), os.path.basename(path)))

    def toggle_presentation(self):
        if self.isFullScreen():
            self.showNormal()
            self.findChild(QFrame, "Header").show()
            self.sidebar.show()
            self.toolbar.show()
            self.statusBar().show()
        else:
            self.findChild(QFrame, "Header").hide()
            self.sidebar.hide()
            self.toolbar.hide()
            self.statusBar().hide()
            self.showFullScreen()
            self.statusBar().showMessage("Presentation mode – press Esc or F11 to exit", 4000)

    # ================================================================ misc
    def _set_state(self, state: str, text: str | None = None):
        colors = {"idle": (theme.FAINT, "Not connected"), "connecting": (theme.WARN, "Connecting…"),
                  "live": (theme.OK, "Live"), "error": (theme.DANGER, "Error")}
        c, default = colors[state]
        self.pill.setText(f"●  {text or default}")
        self.pill.setStyleSheet(
            f"color:{c}; background: rgba(255,255,255,0.03); border:1px solid {c};"
            f"border-radius: 13px; padding: 4px 12px; font-weight:600;")
        live = state == "live"
        connecting = state == "connecting"
        self.btn_connect.setText("Disconnect" if (live or connecting) else "Connect")
        self.btn_connect.setObjectName("Danger" if (live or connecting) else "Primary")
        self.btn_connect.setEnabled(not connecting)
        self.btn_connect.style().unpolish(self.btn_connect)
        self.btn_connect.style().polish(self.btn_connect)
        self.source.setEnabled(not (live or connecting))
        self.btn_refresh.setEnabled(not (live or connecting))
        for b in getattr(self, "cal_buttons", []):
            b.setEnabled(live)

    def log(self, level: str, msg: str):
        colors = {"ok": theme.OK, "warn": theme.WARN, "error": theme.DANGER, "info": theme.MUTED}
        ts = time.strftime("%H:%M:%S")
        safe = msg.replace("&", "&amp;").replace("<", "&lt;")
        self.logbox.appendHtml(f'<span style="color:{theme.FAINT}">{ts}</span> '
                               f'<span style="color:{colors.get(level, theme.MUTED)}">{safe}</span>')

    def _restore_cfg(self):
        for k, v in DEFAULTS.items():
            raw = self.store.value(f"cfg/{k}", v)
            try:
                if isinstance(v, bool):
                    raw = raw if isinstance(raw, bool) else str(raw).lower() == "true"
                else:
                    raw = type(v)(raw)
            except (TypeError, ValueError):
                raw = v
            self.cfg[k] = raw

    def closeEvent(self, e):
        if self.recorder.active:
            self.recorder.stop()
        if self.engine is not None:
            self.engine.closed.disconnect()
            self.engine.stop_camera()
        super().closeEvent(e)
