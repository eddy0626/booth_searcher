"""
로딩 스피너 위젯

로딩 상태를 애니메이션으로 표시합니다.
"""

from typing import Optional
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt, QTimer, pyqtProperty
from PyQt6.QtGui import QPainter, QColor, QPen

from utils.logging import get_logger

logger = get_logger(__name__)


class LoadingSpinner(QWidget):
    """
    로딩 스피너 위젯

    특징:
    - 회전하는 원형 스피너 애니메이션
    - 로딩 메시지 표시
    - 배경 오버레이 옵션

    사용법:
        spinner = LoadingSpinner(parent=self)
        spinner.start("검색 중...")
        # 작업 완료 후
        spinner.stop()
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        # 설정
        self._angle = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._rotate)

        # 스타일
        self._line_width = 4
        self._color = QColor("#ff6b6b")
        self._bg_color = QColor(255, 255, 255, 200)
        self._spinner_size = 40

        # UI
        self._setup_ui()
        self.hide()

    def _setup_ui(self) -> None:
        """UI 초기화"""
        self.setMinimumSize(100, 80)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(10)

        # 스피너 영역
        self._spinner_widget = QWidget()
        self._spinner_widget.setFixedSize(self._spinner_size + 10, self._spinner_size + 10)
        layout.addWidget(self._spinner_widget, alignment=Qt.AlignmentFlag.AlignCenter)

        # 메시지 라벨
        self._message_label = QLabel()
        self._message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._message_label.setStyleSheet("""
            QLabel {
                color: #666;
                font-size: 13px;
            }
        """)
        layout.addWidget(self._message_label)

    def start(self, message: str = "로딩 중...") -> None:
        """
        스피너 시작

        Args:
            message: 표시할 메시지
        """
        self._message_label.setText(message)
        self.show()
        self._timer.start(30)  # ~33fps

    def stop(self) -> None:
        """스피너 정지"""
        self._timer.stop()
        self.hide()

    def set_message(self, message: str) -> None:
        """메시지 변경"""
        self._message_label.setText(message)

    def _rotate(self) -> None:
        """회전 애니메이션"""
        self._angle = (self._angle + 10) % 360
        self._spinner_widget.update()
        self.update()

    def paintEvent(self, event) -> None:
        """스피너 그리기"""
        super().paintEvent(event)

        # 반투명 배경
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), self._bg_color)

        # 스피너 위치 계산
        spinner_rect = self._spinner_widget.geometry()
        center_x = spinner_rect.center().x()
        center_y = spinner_rect.center().y()
        radius = self._spinner_size // 2 - self._line_width

        # 스피너 그리기
        pen = QPen(self._color)
        pen.setWidth(self._line_width)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)

        # 원호 그리기 (270도)
        painter.translate(center_x, center_y)
        painter.rotate(self._angle)
        painter.drawArc(
            -radius, -radius,
            radius * 2, radius * 2,
            0 * 16,  # 시작 각도
            270 * 16  # 호의 길이 (270도)
        )

    @pyqtProperty(QColor)
    def color(self) -> QColor:
        return self._color

    @color.setter
    def color(self, value: QColor) -> None:
        self._color = value
        self.update()

    @property
    def is_running(self) -> bool:
        """스피너 실행 중 여부"""
        return self._timer.isActive()


class LoadingOverlay(QWidget):
    """
    로딩 오버레이

    부모 위젯 전체를 덮는 로딩 화면

    사용법:
        overlay = LoadingOverlay(parent=content_widget)
        overlay.show_loading("데이터 로딩 중...")
        # 완료 후
        overlay.hide_loading()
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.setStyleSheet("background-color: rgba(255, 255, 255, 180);")

        # 스피너
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._spinner = LoadingSpinner()
        self._spinner.setStyleSheet("background: transparent;")
        layout.addWidget(self._spinner)

        self.hide()

    def show_loading(self, message: str = "로딩 중...") -> None:
        """로딩 표시"""
        if self.parent():
            self.setGeometry(self.parent().rect())
        self.show()
        self.raise_()
        self._spinner.start(message)

    def hide_loading(self) -> None:
        """로딩 숨기기"""
        self._spinner.stop()
        self.hide()

    def set_message(self, message: str) -> None:
        """메시지 변경"""
        self._spinner.set_message(message)

    def resizeEvent(self, event) -> None:
        """부모 크기 변경 시 조정"""
        super().resizeEvent(event)
        if self.parent():
            self.setGeometry(self.parent().rect())
