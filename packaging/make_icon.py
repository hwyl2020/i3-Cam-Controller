"""Writes packaging/ThermalStudio.ico from the app's own icon drawing."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

from PySide6.QtGui import QGuiApplication  # noqa: E402

from ui.theme import app_icon  # noqa: E402

app = QGuiApplication(sys.argv)
out = os.path.join(os.path.dirname(__file__), "ThermalStudio.ico")
if not app_icon().pixmap(256, 256).save(out, "ICO"):
    sys.exit("could not write icon")
print("wrote", out)
