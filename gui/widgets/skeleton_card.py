"""
스켈레톤 로딩 카드

이미지 로딩 중 애니메이션 표시
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QFrame, QGraphicsOpacityEffect
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QSequentialAnimationGroup
from PyQt6.QtGui import QPainter, QColor, QLinearGradient, QPaintEvent


class SkeletonWidget(QWidget):
    """스켈레톤 애니메이션 위젯"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._shimmer_pos = 0.0
        self._setup_animation()

    def _setup_animation(self) -> None:
        """애니메이션 설정"""
        self._animation = QPropertyAnimation(self, b"shimmer_pos")
        self._animation.setDuration(1500)
        self._animation.setStartValue(0.0)
        self._animation.setEndValue(1.0)
        self._animation.setEasingCurve(QEasingCurve.Type.InOutSine)
        self._animation.setLoopCount(-1)  # 무한 반복
        self._animation.start()

    @property
    def shimmer_pos(self) -> float:
        return self._shimmer_pos

    @shimmer_pos.setter
    def shimmer_pos(self, value: float) -> None:
        self._shimmer_pos = value
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        """그라데이션 애니메이션 그리기"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect()

        # 기본 배경
        base_color = QColor("#e0e0e0")
        painter.fillRect(rect, base_color)

        # Shimmer 효과
        gradient = QLinearGradient(0, 0, rect.width(), 0)
        shimmer_width = 0.3

        pos = self._shimmer_pos

        # 그라데이션 위치 계산
        start = pos - shimmer_width
        end = pos + shimmer_width

        gradient.setColorAt(max(0, start), QColor("#e0e0e0"))
        gradient.setColorAt(max(0, min(1, pos - shimmer_width / 2)), QColor("#f0f0f0"))
        gradient.setColorAt(min(1, pos), QColor("#f8f8f8"))
        gradient.setColorAt(min(1, pos + shimmer_width / 2), QColor("#f0f0f0"))
        gradient.setColorAt(min(1, end), QColor("#e0e0e0"))

        painter.fillRect(rect, gradient)

    def stop(self) -> None:
        """애니메이션 중지"""
        self._animation.stop()

    def start(self) -> None:
        """애니메이션 시작"""
        self._animation.start()


class SkeletonCard(QFrame):
    """
    스켈레톤 로딩 카드

    아이템 카드와 동일한 크기의 로딩 플레이스홀더
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("skeletonCard")
        self._setup_ui()

    def _setup_ui(self) -> None:
        """UI 설정"""
        self.setFixedSize(200, 280)
        self.setStyleSheet("""
            #skeletonCard {
                background-color: #ffffff;
                border: 1px solid #e8e8e8;
                border-radius: 8px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # 이미지 스켈레톤
        self._image_skeleton = SkeletonWidget()
        self._image_skeleton.setFixedSize(184, 184)
        self._image_skeleton.setStyleSheet("border-radius: 6px;")
        layout.addWidget(self._image_skeleton)

        # 제목 스켈레톤 (2줄)
        title_skeleton1 = SkeletonWidget()
        title_skeleton1.setFixedHeight(16)
        title_skeleton1.setStyleSheet("border-radius: 4px;")
        layout.addWidget(title_skeleton1)

        title_skeleton2 = SkeletonWidget()
        title_skeleton2.setFixedSize(120, 16)
        title_skeleton2.setStyleSheet("border-radius: 4px;")
        layout.addWidget(title_skeleton2)

        # 가격 스켈레톤
        price_skeleton = SkeletonWidget()
        price_skeleton.setFixedSize(80, 20)
        price_skeleton.setStyleSheet("border-radius: 4px;")
        layout.addWidget(price_skeleton)

        layout.addStretch()

        # 스켈레톤 위젯들 저장
        self._skeletons = [
            self._image_skeleton,
            title_skeleton1,
            title_skeleton2,
            price_skeleton,
        ]

    def stop_animation(self) -> None:
        """모든 애니메이션 중지"""
        for skeleton in self._skeletons:
            skeleton.stop()

    def start_animation(self) -> None:
        """모든 애니메이션 시작"""
        for skeleton in self._skeletons:
            skeleton.start()


class SkeletonGrid(QWidget):
    """
    스켈레톤 카드 그리드

    여러 개의 스켈레톤 카드를 그리드로 표시
    """

    def __init__(self, count: int = 6, parent=None):
        super().__init__(parent)
        self._cards: list[SkeletonCard] = []
        self._setup_ui(count)

    def _setup_ui(self, count: int) -> None:
        """UI 설정"""
        from PyQt6.QtWidgets import QGridLayout

        layout = QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(15)

        columns = 4  # 4열 그리드

        for i in range(count):
            card = SkeletonCard()
            self._cards.append(card)
            row = i // columns
            col = i % columns
            layout.addWidget(card, row, col)

    def stop_all(self) -> None:
        """모든 애니메이션 중지"""
        for card in self._cards:
            card.stop_animation()

    def start_all(self) -> None:
        """모든 애니메이션 시작"""
        for card in self._cards:
            card.start_animation()


# PyQt6의 QPropertyAnimation이 사용자 정의 프로퍼티를 지원하도록 등록
from PyQt6.QtCore import pyqtProperty

# shimmer_pos를 pyqtProperty로 다시 정의
SkeletonWidget.shimmer_pos = pyqtProperty(
    float,
    fget=lambda self: self._shimmer_pos,
    fset=lambda self, value: setattr(self, '_shimmer_pos', value) or self.update()
)
