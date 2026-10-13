"""Thermal Studio – control and live view for the i3system TE-Q2 thermal camera."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication  # noqa: E402

from ui import theme  # noqa: E402
from ui.main_window import MainWindow  # noqa: E402


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Thermal Studio")
    app.setStyle("Fusion")
    app.setStyleSheet(theme.QSS)
    app.setWindowIcon(theme.app_icon())
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
