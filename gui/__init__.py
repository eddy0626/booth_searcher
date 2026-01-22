"""GUI 모듈"""
import sys
from PyQt6.QtWidgets import QApplication

from .main_window import MainWindow

__all__ = ["MainWindow", "run_app"]


def run_app():
    """애플리케이션 실행"""
    # 콘솔 인코딩 설정 (Windows)
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
            sys.stderr.reconfigure(encoding="utf-8")
        except AttributeError:
            pass

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())
