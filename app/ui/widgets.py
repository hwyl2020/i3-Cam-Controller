"""Small reusable widgets: cards, segmented buttons, stat chips, sliders."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QIcon, QLinearGradient, QPainter, QPixmap
from PySide6.QtWidgets import (QButtonGroup, QFrame, QHBoxLayout, QLabel, QPushButton,
                               QSlider, QVBoxLayout, QWidget)


class Card(QFrame):
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setObjectName("Card")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 12, 14, 14)
        lay.setSpacing(10)
        t = QLabel(title.upper())
        t.setObjectName("CardTitle")
        lay.addWidget(t)
        self.body = lay

    def add(self, w):
        if isinstance(w, QWidget):
            self.body.addWidget(w)
        else:
            self.body.addLayout(w)
        return w


def hint(text: str) -> QLabel:
    lab = QLabel(text)
    lab.setObjectName("Hint")
    lab.setWordWrap(True)
    return lab


def row(*widgets, stretch_last=False, spacing=8) -> QHBoxLayout:
    lay = QHBoxLayout()
    lay.setSpacing(spacing)
    lay.setContentsMargins(0, 0, 0, 0)
    for w in widgets:
        if w is None:
            lay.addStretch(1)
        elif isinstance(w, QWidget):
            lay.addWidget(w)
        else:
            lay.addLayout(w)
    return lay


class Segmented(QWidget):
    """Exclusive row of buttons; emits the selected key."""
    changed = Signal(object)

    def __init__(self, items: list[tuple[object, str]], current=None, parent=None):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        self.group = QButtonGroup(self)
        self.group.setExclusive(True)
        self.buttons = {}
        for i, (key, text) in enumerate(items):
            b = QPushButton(text)
            b.setCheckable(True)
            b.setObjectName("SegL" if i == 0 else "SegR" if i == len(items) - 1 else "Seg")
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            lay.addWidget(b, 1)
            self.group.addButton(b)
            self.buttons[key] = b
            b.clicked.connect(lambda _=False, k=key: self.changed.emit(k))
        self.set(current if current is not None else items[0][0])

    def set(self, key):
        if key in self.buttons:
            self.buttons[key].setChecked(True)


class StatChip(QFrame):
    def __init__(self, label: str, color: str | None = None, parent=None):
        super().__init__(parent)
        self.setObjectName("StatChip")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 6, 12, 7)
        lay.setSpacing(0)
        top = QHBoxLayout()
        top.setSpacing(6)
        if color:
            dot = QLabel()
            dot.setFixedSize(8, 8)
            dot.setStyleSheet(f"background:{color}; border-radius:4px;")
            top.addWidget(dot)
        lab = QLabel(label.upper())
        lab.setObjectName("StatLabel")
        top.addWidget(lab)
        top.addStretch(1)
        lay.addLayout(top)
        self.value = QLabel("—")
        self.value.setObjectName("StatValue")
        lay.addWidget(self.value)

    def set(self, text: str):
        self.value.setText(text)


class LabeledSlider(QWidget):
    """Slider with a caption on the left and live value on the right."""
    valueChanged = Signal(float)

    def __init__(self, caption: str, lo: float, hi: float, step: float, value: float,
                 fmt="{:.2f}", parent=None):
        super().__init__(parent)
        self.lo, self.step, self.fmt = lo, step, fmt
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)
        top = QHBoxLayout()
        cap = QLabel(caption)
        cap.setObjectName("Key")
        self.val = QLabel()
        self.val.setObjectName("Value")
        top.addWidget(cap)
        top.addStretch(1)
        top.addWidget(self.val)
        lay.addLayout(top)
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(0, round((hi - lo) / step))
        self.slider.valueChanged.connect(self._changed)
        lay.addWidget(self.slider)
        self.setValue(value)

    def value(self) -> float:
        return self.lo + self.slider.value() * self.step

    def setValue(self, v: float):
        self.slider.setValue(round((v - self.lo) / self.step))
        self.val.setText(self.fmt.format(self.value()))

    def _changed(self, _):
        v = self.value()
        self.val.setText(self.fmt.format(v))
        self.valueChanged.emit(v)


def palette_icon(lut, w=46, h=14) -> QIcon:
    pm = QPixmap(w, h)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    g = QLinearGradient(0, 0, w, 0)
    for i in range(0, 256, 17):
        c = lut[i]
        g.setColorAt(i / 255, QColor(int(c[0]), int(c[1]), int(c[2])))
    c = lut[255]
    g.setColorAt(1, QColor(int(c[0]), int(c[1]), int(c[2])))
    p.setBrush(g)
    p.setPen(QColor(255, 255, 255, 40))
    p.drawRoundedRect(0, 0, w - 1, h - 1, 3, 3)
    p.end()
    return QIcon(pm)
