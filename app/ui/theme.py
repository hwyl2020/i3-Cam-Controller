"""Colours and Qt stylesheet for the dark, presentation-friendly theme."""
import sys
from pathlib import Path

from PySide6.QtGui import QColor, QFont, QIcon, QLinearGradient, QPainter, QPixmap, QPen
from PySide6.QtCore import Qt, QRectF

BG = "#0E1014"
SURFACE = "#14171D"
CARD = "#1A1E26"
CARD_HI = "#222733"
BORDER = "#2A303C"
TEXT = "#E7EAF0"
MUTED = "#8B94A5"
FAINT = "#5D6575"
ACCENT = "#FF7A2F"
ACCENT_HI = "#FF9257"
OK = "#2FCB8A"
WARN = "#F3B23C"
DANGER = "#F0506E"
HOT = "#FF4D4D"
COLD = "#3DA5FF"

FONT = "Segoe UI"

_base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
ASSETS = (_base / "ui" / "assets").as_posix()

QSS = f"""
* {{ font-family: '{FONT}'; font-size: 10pt; color: {TEXT}; }}
QMainWindow, #Root {{ background: {BG}; }}
QToolTip {{ background: {CARD_HI}; color: {TEXT}; border: 1px solid {BORDER}; padding: 4px 6px; }}

#Header {{ background: {SURFACE}; border-bottom: 1px solid {BORDER}; }}
#AppTitle {{ font-size: 13pt; font-weight: 600; }}
#AppSub {{ color: {MUTED}; font-size: 9pt; }}

#Sidebar {{ background: {SURFACE}; border-left: 1px solid {BORDER}; }}
QScrollArea {{ background: transparent; border: none; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}
QScrollBar:vertical {{ background: transparent; width: 8px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {BORDER}; border-radius: 4px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: {FAINT}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}

#Card {{ background: {CARD}; border: 1px solid {BORDER}; border-radius: 10px; }}
#CardTitle {{ color: {MUTED}; font-size: 8.5pt; font-weight: 600; letter-spacing: 1px; }}
#Hint {{ color: {FAINT}; font-size: 8.5pt; }}
#Value {{ color: {TEXT}; font-weight: 600; }}
#Key {{ color: {MUTED}; }}

QPushButton {{
    background: {CARD_HI}; border: 1px solid {BORDER}; border-radius: 7px;
    padding: 6px 12px; color: {TEXT};
}}
QPushButton:hover {{ border-color: {FAINT}; background: #282E3B; }}
QPushButton:pressed {{ background: #1F2430; }}
QPushButton:disabled {{ color: {FAINT}; background: {CARD}; border-color: {CARD_HI}; }}
QPushButton:checked {{ background: rgba(255,122,47,0.16); border-color: {ACCENT}; color: {ACCENT_HI}; }}
QPushButton#Primary {{ background: {ACCENT}; border-color: {ACCENT}; color: #1A0E05; font-weight: 600; }}
QPushButton#Primary:hover {{ background: {ACCENT_HI}; }}
QPushButton#Primary:disabled {{ background: #5A3A28; border-color: #5A3A28; color: #9A8070; }}
QPushButton#Danger {{ background: rgba(240,80,110,0.15); border-color: {DANGER}; color: #FF8AA0; font-weight: 600; }}
QPushButton#Seg {{ border-radius: 0; padding: 5px 8px; }}
QPushButton#SegL {{ border-top-right-radius: 0; border-bottom-right-radius: 0; padding: 5px 8px; }}
QPushButton#SegR {{ border-top-left-radius: 0; border-bottom-left-radius: 0; padding: 5px 8px; }}
QPushButton#Tool {{ background: transparent; border: 1px solid transparent; padding: 6px 10px; }}
QPushButton#Tool:hover {{ background: {CARD_HI}; border-color: {BORDER}; }}
QPushButton#Tool:checked {{ background: rgba(255,122,47,0.16); border-color: {ACCENT}; }}
QPushButton#Palette {{ text-align: left; padding: 4px 6px; border-radius: 7px; font-size: 9pt; }}

QComboBox, QDoubleSpinBox, QSpinBox {{
    background: {BG}; border: 1px solid {BORDER}; border-radius: 7px; padding: 5px 8px;
}}
QComboBox:hover, QDoubleSpinBox:hover {{ border-color: {FAINT}; }}
QComboBox::drop-down {{ border: none; width: 22px; }}
QComboBox QAbstractItemView {{ background: {CARD_HI}; border: 1px solid {BORDER}; selection-background-color: {ACCENT}; selection-color: #1A0E05; outline: 0; }}
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{ width: 0; border: none; }}
QDoubleSpinBox:disabled {{ color: {FAINT}; }}

QCheckBox {{ spacing: 10px; }}
QCheckBox::indicator {{ width: 34px; height: 18px; image: url({ASSETS}/toggle_off.svg); }}
QCheckBox::indicator:checked {{ image: url({ASSETS}/toggle_on.svg); }}
QCheckBox::indicator:disabled {{ image: url({ASSETS}/toggle_disabled.svg); }}
QCheckBox:disabled {{ color: {FAINT}; }}

QSlider::groove:horizontal {{ height: 4px; background: {BORDER}; border-radius: 2px; }}
QSlider::sub-page:horizontal {{ background: {ACCENT}; border-radius: 2px; }}
QSlider::handle:horizontal {{ background: {TEXT}; width: 14px; height: 14px; margin: -5px 0; border-radius: 7px; }}
QSlider::handle:horizontal:hover {{ background: white; }}

QPlainTextEdit {{ background: {BG}; border: 1px solid {BORDER}; border-radius: 7px; font-family: Consolas; font-size: 8.5pt; color: {MUTED}; }}

#StatChip {{ background: {CARD}; border: 1px solid {BORDER}; border-radius: 8px; }}
#StatLabel {{ color: {MUTED}; font-size: 8pt; font-weight: 600; letter-spacing: 1px; }}
#StatValue {{ font-size: 13pt; font-weight: 600; }}
#ToolBar {{ background: {SURFACE}; border-top: 1px solid {BORDER}; }}
QStatusBar {{ background: {SURFACE}; color: {MUTED}; border-top: 1px solid {BORDER}; }}
QStatusBar::item {{ border: none; }}
QMenu {{ background: {CARD_HI}; border: 1px solid {BORDER}; padding: 4px; }}
QMenu::item {{ padding: 6px 18px; border-radius: 5px; }}
QMenu::item:selected {{ background: {ACCENT}; color: #1A0E05; }}
"""


def app_icon() -> QIcon:
    icon = QIcon()
    for size in (16, 32, 48, 64, 128, 256):
        pm = QPixmap(size, size)
        pm.fill(Qt.GlobalColor.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        g = QLinearGradient(0, size, size, 0)
        g.setColorAt(0.0, QColor("#2B0A5E"))
        g.setColorAt(0.45, QColor("#D8314A"))
        g.setColorAt(0.8, QColor("#FF8A2F"))
        g.setColorAt(1.0, QColor("#FFE38A"))
        p.setBrush(g)
        p.setPen(Qt.PenStyle.NoPen)
        r = QRectF(0, 0, size, size).adjusted(size * .06, size * .06, -size * .06, -size * .06)
        p.drawRoundedRect(r, size * .22, size * .22)
        pen = QPen(QColor(255, 255, 255, 230), max(1.0, size * .07))
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        c = size / 2
        p.drawEllipse(QRectF(c - size * .2, c - size * .2, size * .4, size * .4))
        p.drawLine(int(c), int(size * .16), int(c), int(size * .3))
        p.drawLine(int(c), int(size * .7), int(c), int(size * .84))
        p.end()
        icon.addPixmap(pm)
    return icon


def title_font(pt: float = 10, weight=QFont.Weight.DemiBold) -> QFont:
    f = QFont(FONT, -1)
    f.setPointSizeF(pt)
    f.setWeight(weight)
    return f
