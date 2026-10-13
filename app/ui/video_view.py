"""Live thermal view: image, measurement overlays, colour bar and HUD.

The same paint routine draws the on-screen view and the off-screen composite
used for snapshots and recordings, so captures look exactly like the screen.
"""
from __future__ import annotations

import time

import numpy as np
from PySide6.QtCore import QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import (QBrush, QColor, QFont, QImage, QLinearGradient, QPainter,
                           QPainterPath, QPen, QPolygonF)
from PySide6.QtWidgets import QMenu, QWidget

from core import palettes
from . import theme

BAR_W = 64          # colour bar column width (px, at scale 1)
MAX_PINS = 6


def to_unit(t: float, unit: str) -> float:
    return t * 9 / 5 + 32 if unit == "F" else t


def fmt(t: float | None, unit: str, deg=True) -> str:
    if t is None or not np.isfinite(t):
        return "—"
    return f"{to_unit(t, unit):.1f}°{unit}" if deg else f"{to_unit(t, unit):.1f}"


class VideoView(QWidget):
    roi_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.setMinimumSize(480, 320)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.packet = None
        self.qimg: QImage | None = None
        self.zoom = 1
        self.pins: list[tuple[int, int]] = []
        self.roi: tuple[int, int, int, int] | None = None
        self.hover: tuple[int, int] | None = None
        self.show = dict(center=True, hot=True, cold=True, cursor=True, hud=True, bar=True)
        self.unit = "C"
        self.info: dict = {}
        self.rec_elapsed = 0.0
        self.recording = False
        self._flash_t = 0.0
        self.frozen = False
        self.alarm_threshold = 50.0
        self.placeholder = ("No camera connected",
                            "Choose a source above and press Connect")
        self._drag_start = None
        self._drag_now = None
        self._img_rect = QRectF()
        self._src = QRectF()

    # --------------------------------------------------------------- data
    def set_packet(self, pk):
        if self.frozen:
            return
        self.packet = pk
        h, w, _ = pk.rgb.shape
        self.qimg = QImage(pk.rgb.data, w, h, 3 * w, QImage.Format.Format_RGB888)
        self.update()

    def flash(self):
        """Brief white flash as capture feedback (screen only, not in files)."""
        self._flash_t = time.perf_counter()
        for ms in range(0, 360, 30):
            QTimer.singleShot(ms, self.update)

    def clear(self, title: str, subtitle: str = ""):
        self.packet = None
        self.qimg = None
        self.placeholder = (title, subtitle)
        self.update()

    def sensor_size(self):
        if self.packet is None:
            return None
        h, w = self.packet.rgb.shape[:2]
        return w, h

    def temp_at(self, x: int, y: int) -> float | None:
        pk = self.packet
        if pk is None or pk.temps is None:
            return None
        h, w = pk.temps.shape
        if 0 <= x < w and 0 <= y < h:
            return float(pk.temps[y, x])
        return None

    def roi_stats(self):
        pk = self.packet
        if pk is None or pk.temps is None or self.roi is None:
            return None
        x0, y0, x1, y1 = self.roi
        a = pk.temps[y0:y1 + 1, x0:x1 + 1]
        if a.size == 0:
            return None
        imax, imin = int(np.argmax(a)), int(np.argmin(a))
        w = a.shape[1]
        return dict(max=float(a.flat[imax]), min=float(a.flat[imin]), mean=float(a.mean()),
                    max_xy=(x0 + imax % w, y0 + imax // w), min_xy=(x0 + imin % w, y0 + imin // w))

    def clear_marks(self):
        self.pins.clear()
        self.roi = None
        self.roi_changed.emit()
        self.update()

    # ------------------------------------------------------------ geometry
    def _src_rect(self) -> QRectF:
        w, h = self.sensor_size()
        z = max(1, self.zoom)
        sw, sh = w / z, h / z
        return QRectF((w - sw) / 2, (h - sh) / 2, sw, sh)

    def _layout(self, area: QRectF, scale: float = 1.0):
        bar = BAR_W * scale if self.show["bar"] else 0
        w, h = self.sensor_size()
        avail = QRectF(area.x(), area.y(), area.width() - bar, area.height())
        s = min(avail.width() / w, avail.height() / h)
        iw, ih = w * s, h * s
        img = QRectF(avail.x() + (avail.width() - iw) / 2, avail.y() + (avail.height() - ih) / 2, iw, ih)
        barr = QRectF(img.right() + 10 * scale, img.y() + 8 * scale, 14 * scale, ih - 16 * scale)
        return img, barr

    def _to_screen(self, x: float, y: float) -> QPointF:
        r, s = self._img_rect, self._src
        return QPointF(r.x() + (x + 0.5 - s.x()) * r.width() / s.width(),
                       r.y() + (y + 0.5 - s.y()) * r.height() / s.height())

    def _to_sensor(self, pos: QPointF):
        r, s = self._img_rect, self._src
        if r.isEmpty() or not r.contains(pos):
            return None
        x = s.x() + (pos.x() - r.x()) * s.width() / r.width()
        y = s.y() + (pos.y() - r.y()) * s.height() / r.height()
        w, h = self.sensor_size()
        return min(max(int(x), 0), w - 1), min(max(int(y), 0), h - 1)

    # ------------------------------------------------------------ painting
    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), QColor(theme.BG))
        if self.qimg is None:
            self._paint_placeholder(p)
            return
        area = QRectF(self.rect()).adjusted(16, 16, -16, -16)
        self._paint_scene(p, area, 1.0, live=True)
        a = 1.0 - (time.perf_counter() - self._flash_t) / 0.33
        if a > 0:
            p.fillRect(self._img_rect, QColor(255, 255, 255, int(170 * a)))

    def render_composite(self, sensor_scale: float = 2.0) -> QImage | None:
        """Off-screen render of image + overlays + colour bar for capture."""
        if self.qimg is None:
            return None
        w, h = self.sensor_size()
        k = sensor_scale * w / 384.0     # overlay scale relative to a 384-wide sensor
        bar = BAR_W * k if self.show["bar"] else 0
        out = QImage(int(w * sensor_scale + bar), int(h * sensor_scale), QImage.Format.Format_RGB888)
        out.fill(QColor(theme.BG))
        p = QPainter(out)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        saved = (self._img_rect, self._src)
        self._paint_scene(p, QRectF(0, 0, out.width(), out.height()), k, live=False)
        self._img_rect, self._src = saved
        p.end()
        return out

    def _paint_scene(self, p: QPainter, area: QRectF, k: float, live: bool):
        pk = self.packet
        img, bar = self._layout(area, k)
        self._img_rect, self._src = img, self._src_rect()
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, self.zoom < 4)
        p.drawImage(img, self.qimg, self._src)
        if live:
            p.setPen(QPen(QColor(theme.BORDER), 1))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRect(img.adjusted(-0.5, -0.5, 0.5, 0.5))

        p.save()
        p.setClipRect(img)
        st = pk.stats
        if pk.temps is not None:
            if self.roi:
                self._paint_roi(p, k)
            if self.show["hot"] and st:
                self._paint_extreme(p, st["max_xy"], st["max"], QColor(theme.HOT), True, k)
            if self.show["cold"] and st:
                self._paint_extreme(p, st["min_xy"], st["min"], QColor(theme.COLD), False, k)
            if self.show["center"]:
                w, h = self.sensor_size()
                self._paint_center(p, w // 2, h // 2, k)
            for i, (x, y) in enumerate(self.pins, 1):
                self._paint_pin(p, x, y, f"P{i}", k)
            if live and self._drag_start and self._drag_now:
                self._paint_drag(p)
            if live and self.show["cursor"] and self.hover and not self._drag_start:
                self._paint_cursor(p, *self.hover, k)
        p.restore()

        if self.show["hud"]:
            self._paint_hud(p, img, k, live)
        if self.show["bar"]:
            self._paint_bar(p, bar, k)

    # overlay primitives ---------------------------------------------------
    def _font(self, k, pt=9.0, bold=True):
        f = QFont(theme.FONT)
        f.setPixelSize(max(9, int(pt * 1.45 * k)))
        f.setWeight(QFont.Weight.DemiBold if bold else QFont.Weight.Normal)
        return f

    def _label(self, p: QPainter, anchor: QPointF, text: str, k: float, accent: QColor | None = None,
               dx=10.0, dy=-10.0, bg=QColor(12, 14, 18, 205), below=False):
        """Pill label offset from anchor; flips side to stay inside the image."""
        p.setFont(self._font(k))
        fm = p.fontMetrics()
        pad = 5 * k
        tw = fm.horizontalAdvance(text)
        th = fm.height()
        dot = 8 * k if accent else 0
        w, h = tw + 2 * pad + dot, th + 2 * pad * .6
        x = anchor.x() + dx * k
        y = anchor.y() + dy * k if below else anchor.y() + dy * k - h
        bounds = self._img_rect
        if x + w > bounds.right() - 2:
            x = bounds.right() - 2 - w if dx == 0 else anchor.x() - abs(dx) * k - w
        x = max(x, bounds.left() + 2)
        if y < bounds.top() + 2:
            y = anchor.y() + abs(dy) * k
        if y + h > bounds.bottom() - 2:
            y = anchor.y() - abs(dy) * k - h
        r = QRectF(x, y, w, h)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(bg)
        p.drawRoundedRect(r, 5 * k, 5 * k)
        if accent:
            p.setBrush(accent)
            p.drawEllipse(QPointF(r.x() + pad + 2.5 * k, r.center().y()), 3 * k, 3 * k)
        p.setPen(QColor(theme.TEXT))
        p.drawText(QRectF(r.x() + pad + dot, r.y(), tw + 2, r.height()), Qt.AlignmentFlag.AlignVCenter, text)

    def _outlined_pen(self, color, width):
        return QPen(color, width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)

    def _paint_center(self, p, x, y, k):
        c = self._to_screen(x, y)
        g, L = 4 * k, 12 * k
        for pen in (self._outlined_pen(QColor(0, 0, 0, 160), 3.2 * k),
                    self._outlined_pen(QColor(255, 255, 255, 235), 1.4 * k)):
            p.setPen(pen)
            p.drawLine(QPointF(c.x() - L, c.y()), QPointF(c.x() - g, c.y()))
            p.drawLine(QPointF(c.x() + g, c.y()), QPointF(c.x() + L, c.y()))
            p.drawLine(QPointF(c.x(), c.y() - L), QPointF(c.x(), c.y() - g))
            p.drawLine(QPointF(c.x(), c.y() + g), QPointF(c.x(), c.y() + L))
        self._label(p, c, fmt(self.temp_at(x, y), self.unit), k, dx=12, dy=-6)

    def _paint_extreme(self, p, xy, t, color, hot, k):
        c = self._to_screen(*xy)
        s = 7 * k
        tri = QPolygonF([QPointF(c.x(), c.y() + (s if not hot else -s) * 0.15),
                         QPointF(c.x() - s, c.y() - s * 1.6 if hot else c.y() + s * 1.6),
                         QPointF(c.x() + s, c.y() - s * 1.6 if hot else c.y() + s * 1.6)])
        p.setPen(QPen(QColor(0, 0, 0, 170), 1.2 * k))
        p.setBrush(color)
        p.drawPolygon(tri)
        self._label(p, c, ("Max " if hot else "Min ") + fmt(t, self.unit), k, color,
                    dx=10, dy=-14 if hot else 34)

    def _paint_pin(self, p, x, y, name, k):
        c = self._to_screen(x, y)
        p.setPen(QPen(QColor(0, 0, 0, 170), 3 * k))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(c, 6 * k, 6 * k)
        p.setPen(QPen(QColor(theme.ACCENT_HI), 1.6 * k))
        p.drawEllipse(c, 6 * k, 6 * k)
        p.drawPoint(c)
        self._label(p, c, f"{name}  {fmt(self.temp_at(x, y), self.unit)}", k, QColor(theme.ACCENT))

    def _paint_cursor(self, p, x, y, k):
        c = self._to_screen(x, y)
        p.setPen(QPen(QColor(255, 255, 255, 200), 1 * k))
        p.drawLine(QPointF(c.x() - 6 * k, c.y()), QPointF(c.x() + 6 * k, c.y()))
        p.drawLine(QPointF(c.x(), c.y() - 6 * k), QPointF(c.x(), c.y() + 6 * k))
        self._label(p, c, fmt(self.temp_at(x, y), self.unit), k, dx=10, dy=22,
                    bg=QColor(40, 44, 54, 220))

    def _paint_roi(self, p, k):
        x0, y0, x1, y1 = self.roi
        a, b = self._to_screen(x0 - .5, y0 - .5), self._to_screen(x1 + .5, y1 + .5)
        r = QRectF(a, b)
        p.setBrush(QColor(255, 122, 47, 22))
        p.setPen(QPen(QColor(0, 0, 0, 150), 3 * k))
        p.drawRect(r)
        pen = QPen(QColor(theme.ACCENT_HI), 1.5 * k, Qt.PenStyle.DashLine)
        p.setPen(pen)
        p.drawRect(r)
        st = self.roi_stats()
        if st:
            u = self.unit
            txt = f"Area  max {fmt(st['max'], u)}  min {fmt(st['min'], u)}  avg {fmt(st['mean'], u)}"
            self._label(p, QPointF(r.left(), r.top()), txt, k, QColor(theme.ACCENT), dx=0, dy=-4)

    def _paint_drag(self, p):
        p.setBrush(QColor(255, 122, 47, 30))
        p.setPen(QPen(QColor(theme.ACCENT_HI), 1.2, Qt.PenStyle.DashLine))
        p.drawRect(QRectF(self._drag_start, self._drag_now).normalized())

    def _paint_hud(self, p, img: QRectF, k, live):
        pk = self.packet
        model = self.info.get("model", "")
        w, h = self.sensor_size()
        parts = [model, f"{w}×{h}", f"{pk.fps:.1f} fps"]
        if self.zoom > 1:
            parts.append(f"{self.zoom}× zoom")
        if self.frozen:
            parts.append("PAUSED")
        tl = QPointF(img.left() + 10 * k, img.top() + 10 * k)
        self._label(p, tl, "  ·  ".join(x for x in parts if x), k, dx=0, dy=0,
                    bg=QColor(12, 14, 18, 170), below=True)
        ts = time.strftime("%Y-%m-%d  %H:%M:%S")
        self._label(p, QPointF(img.left() + 10 * k, img.bottom() - 10 * k), ts, k, dx=0, dy=0,
                    bg=QColor(12, 14, 18, 170))
        if self.recording:
            m, s = divmod(int(self.rec_elapsed), 60)
            blink = int(time.time() * 2) % 2 == 0
            p.setFont(self._font(k))
            txt = f"REC  {m:02d}:{s:02d}"
            tw = p.fontMetrics().horizontalAdvance(txt) + 30 * k
            r = QRectF(img.right() - 10 * k - tw, img.top() + 10 * k, tw, p.fontMetrics().height() + 8 * k)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(12, 14, 18, 190))
            p.drawRoundedRect(r, 5 * k, 5 * k)
            p.setBrush(QColor(theme.DANGER) if blink else QColor(120, 30, 45))
            p.drawEllipse(QPointF(r.x() + 12 * k, r.center().y()), 4.5 * k, 4.5 * k)
            p.setPen(QColor(theme.TEXT))
            p.drawText(r.adjusted(22 * k, 0, 0, 0), Qt.AlignmentFlag.AlignVCenter, txt)
        if pk.alarm:
            txt = f"⚠  ALARM  ≥ {fmt(self.alarm_threshold, self.unit)}   (max {fmt(pk.stats.get('max'), self.unit)})"
            p.setFont(self._font(k, 10))
            tw = p.fontMetrics().horizontalAdvance(txt) + 28 * k
            r = QRectF(img.center().x() - tw / 2, img.top() + 42 * k, tw, p.fontMetrics().height() + 10 * k)
            a = 235 if int(time.time() * 2.5) % 2 == 0 else 160
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(220, 30, 70, a))
            p.drawRoundedRect(r, 6 * k, 6 * k)
            p.setPen(QColor("white"))
            p.drawText(r, Qt.AlignmentFlag.AlignCenter, txt)

    def _paint_bar(self, p, r: QRectF, k):
        pk = self.packet
        lut = palettes.luts()[pk.palette]
        g = QLinearGradient(r.bottomLeft(), r.topLeft())
        for i in range(0, 256, 15):
            c = lut[i]
            g.setColorAt(i / 255, QColor(int(c[0]), int(c[1]), int(c[2])))
        c = lut[255]
        g.setColorAt(1.0, QColor(int(c[0]), int(c[1]), int(c[2])))
        p.setPen(QPen(QColor(theme.BORDER), 1))
        p.setBrush(QBrush(g))
        p.drawRoundedRect(r, 3 * k, 3 * k)
        if pk.temps is None:
            return
        p.setFont(self._font(k, 8))
        fm = p.fontMetrics()
        ticks = [0.0, 0.25, 0.5, 0.75, 1.0] if pk.linear else [0.0, 1.0]
        for f in ticks:
            y = r.bottom() - f * r.height()
            t = pk.lo + f * (pk.hi - pk.lo)
            p.setPen(QPen(QColor(theme.MUTED), 1))
            p.drawLine(QPointF(r.right() + 2 * k, y), QPointF(r.right() + 6 * k, y))
            p.setPen(QColor(theme.TEXT) if f in (0.0, 1.0) else QColor(theme.MUTED))
            p.drawText(QPointF(r.right() + 9 * k, y + fm.ascent() / 2 - 1), fmt(t, self.unit, deg=False))
        p.setPen(QColor(theme.MUTED))
        lab = f"°{self.unit}" + ("" if pk.linear else " AGC")
        p.drawText(QPointF(r.left() - 2 * k, r.bottom() + fm.height() + 2 * k), lab)

    def _paint_placeholder(self, p):
        r = QRectF(self.rect())
        c = r.center()
        p.setPen(QPen(QColor(theme.BORDER), 2))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QPointF(c.x(), c.y() - 40), 30, 30)
        p.drawEllipse(QPointF(c.x(), c.y() - 40), 12, 12)
        p.setPen(QColor(theme.TEXT))
        f = QFont(theme.FONT)
        f.setPixelSize(18)
        f.setWeight(QFont.Weight.DemiBold)
        p.setFont(f)
        p.drawText(QRectF(r.x(), c.y() + 2, r.width(), 28), Qt.AlignmentFlag.AlignCenter, self.placeholder[0])
        f.setPixelSize(13)
        f.setWeight(QFont.Weight.Normal)
        p.setFont(f)
        p.setPen(QColor(theme.MUTED))
        p.drawText(QRectF(r.x() + 40, c.y() + 32, r.width() - 80, 60),
                   Qt.AlignmentFlag.AlignHCenter | Qt.TextFlag.TextWordWrap, self.placeholder[1])

    # --------------------------------------------------------------- mouse
    def mouseMoveEvent(self, e):
        if self.packet is None:
            return
        pos = e.position()
        if self._drag_start is not None:
            self._drag_now = pos
        self.hover = self._to_sensor(pos)
        self.update()

    def leaveEvent(self, _):
        self.hover = None
        self.update()

    def mousePressEvent(self, e):
        if self.packet is None or e.button() != Qt.MouseButton.LeftButton:
            return
        if self._to_sensor(e.position()) is not None:
            self._drag_start = e.position()
            self._drag_now = e.position()

    def mouseReleaseEvent(self, e):
        if self._drag_start is None or e.button() != Qt.MouseButton.LeftButton:
            return
        start, end = self._drag_start, e.position()
        self._drag_start = self._drag_now = None
        a = self._to_sensor(start)
        b = self._to_sensor(QPointF(min(max(end.x(), self._img_rect.left()), self._img_rect.right() - 1),
                                    min(max(end.y(), self._img_rect.top()), self._img_rect.bottom() - 1)))
        if a is None:
            return
        if (end - start).manhattanLength() < 6 or b is None:
            if len(self.pins) >= MAX_PINS:
                self.pins.pop(0)
            self.pins.append(a)
        else:
            x0, x1 = sorted((a[0], b[0]))
            y0, y1 = sorted((a[1], b[1]))
            if x1 - x0 >= 2 and y1 - y0 >= 2:
                self.roi = (x0, y0, x1, y1)
                self.roi_changed.emit()
        self.update()

    def contextMenuEvent(self, e):
        if self.packet is None:
            return
        m = QMenu(self)
        a_pins = m.addAction("Clear spot markers")
        a_roi = m.addAction("Clear measurement area")
        m.addSeparator()
        a_all = m.addAction("Clear all")
        a_pins.setEnabled(bool(self.pins))
        a_roi.setEnabled(self.roi is not None)
        act = m.exec(e.globalPos())
        if act is a_pins:
            self.pins.clear()
        elif act is a_roi:
            self.roi = None
            self.roi_changed.emit()
        elif act is a_all:
            self.clear_marks()
        self.update()
