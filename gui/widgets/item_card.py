"""
아이템 카드 위젯

Booth 상품을 카드 형태로 표시합니다.
"""

import webbrowser
import html
import re
from typing import Optional, Callable
from PyQt6.QtWidgets import (
    QFrame,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QPixmap, QFont, QMouseEvent

from models.booth_item import BoothItem, PriceType
from utils.logging import get_logger

logger = get_logger(__name__)


class ItemCard(QFrame):
    """
    Booth 상품 카드

    특징:
    - 썸네일, 상품명, 샵명, 가격 표시
    - 가격 타입별 스타일링 (무료, 유료, 범위, 가격미정)
    - 클릭 시 브라우저에서 상품 페이지 열기
    - 외부 이미지 로더와 통합 가능

    시그널:
        clicked: 카드 클릭 (BoothItem)

    사용법:
        card = ItemCard(booth_item)
        card.clicked.connect(on_card_clicked)

        # 이미지 설정 (ImageLoaderPool에서 호출)
        card.set_thumbnail(pixmap)
    """

    # 시그널
    clicked = pyqtSignal(BoothItem)

    # 크기 상수
    CARD_WIDTH = 200
    CARD_HEIGHT = 280
    THUMBNAIL_SIZE = 180

    def __init__(self, item: BoothItem, parent=None):
        super().__init__(parent)

        self.item = item
        self._thumbnail_loaded = False

        self._setup_ui()
        self._apply_style()

    def _setup_ui(self) -> None:
        """UI 초기화"""
        self.setFixedSize(self.CARD_WIDTH, self.CARD_HEIGHT)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        # 메인 레이아웃
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # 썸네일
        self._thumbnail_label = QLabel()
        self._thumbnail_label.setFixedSize(self.THUMBNAIL_SIZE, self.THUMBNAIL_SIZE)
        self._thumbnail_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._thumbnail_label.setStyleSheet("""
            QLabel {
                background-color: #f5f5f5;
                border-radius: 8px;
            }
        """)
        self._thumbnail_label.setText("로딩중...")
        layout.addWidget(self._thumbnail_label, alignment=Qt.AlignmentFlag.AlignCenter)

        # 상품명
        self._name_label = QLabel()
        self._name_label.setText(self._format_title_html(self.item.name))
        self._name_label.setTextFormat(Qt.TextFormat.RichText)
        self._name_label.setWordWrap(True)
        self._name_label.setMaximumHeight(40)
        self._name_label.setStyleSheet("""
            QLabel {
                font-size: 12px;
                font-weight: bold;
                color: #333;
            }
        """)
        self._name_label.setToolTip(self.item.name)
        layout.addWidget(self._name_label)

        # 매칭 배지
        self._match_label = QLabel(self._format_match_badge())
        self._match_label.setStyleSheet("""
            QLabel {
                font-size: 10px;
                color: #555;
                background-color: #f2f2f2;
                padding: 2px 6px;
                border-radius: 8px;
            }
        """)
        if self._match_label.text():
            layout.addWidget(self._match_label)

        # 샵 이름
        if self.item.shop_name:
            shop_label = QLabel(self._truncate_text(self.item.shop_name, 25))
            shop_label.setStyleSheet("""
                QLabel {
                    font-size: 10px;
                    color: #888;
                }
            """)
            shop_label.setToolTip(self.item.shop_name)
            layout.addWidget(shop_label)

        # 가격
        self._price_label = QLabel(self._format_price())
        self._price_label.setStyleSheet(self._get_price_style())
        layout.addWidget(self._price_label)

        # 스트레치
        layout.addStretch()

    def _apply_style(self) -> None:
        """카드 스타일 적용"""
        self.setStyleSheet("""
            ItemCard {
                background-color: white;
                border: 1px solid #e0e0e0;
                border-radius: 12px;
            }
            ItemCard:hover {
                border-color: #ff6b6b;
                background-color: #fff8f8;
            }
        """)

    def _truncate_text(self, text: str, max_length: int) -> str:
        """텍스트 자르기"""
        if len(text) > max_length:
            return text[:max_length - 1] + "…"
        return text

    def _format_title_html(self, title: str) -> str:
        """타이틀에 매칭 토큰 강조 표시"""
        if not title:
            return ""

        truncated = self._truncate_text(title, 60)
        safe_title = html.escape(truncated)
        tokens = list(self.item.matched_tokens or [])
        if not tokens:
            return safe_title

        highlighted = safe_title
        for token in tokens:
            if not token:
                continue
            pattern = re.compile(re.escape(html.escape(token)), re.IGNORECASE)
            highlighted = pattern.sub(r"<u><b>\\g<0></b></u>", highlighted)

        return highlighted

    def _format_match_badge(self) -> str:
        """매칭 배지 텍스트 구성"""
        label = self.item.relevance_label
        if not label:
            return ""
        if self.item.verified_in_description:
            return f"{label} · 설명에서 확인됨"
        return label

    def _format_price(self) -> str:
        """가격 포맷팅"""
        if self.item.price_type == PriceType.FREE:
            return "무료"
        elif self.item.price_type == PriceType.PAID:
            if self.item.price_value is not None:
                return f"¥{self.item.price_value:,}"
            return self.item.price_text or "가격 미정"
        else:
            return self.item.price_text or "가격 미정"

    def _get_price_style(self) -> str:
        """가격 타입별 스타일"""
        base_style = "font-size: 13px; font-weight: bold;"

        if self.item.price_type == PriceType.FREE:
            return f"{base_style} color: #4caf50;"  # 녹색
        elif self.item.price_type == PriceType.UNKNOWN:
            return f"{base_style} color: #999;"  # 회색
        else:
            return f"{base_style} color: #ff6b6b;"  # 빨간색

    def set_thumbnail(self, pixmap: QPixmap) -> None:
        """
        썸네일 이미지 설정

        Args:
            pixmap: 이미지 QPixmap
        """
        if pixmap.isNull():
            self._thumbnail_label.setText("이미지 없음")
            return

        # 크기 조정
        scaled = pixmap.scaled(
            self.THUMBNAIL_SIZE,
            self.THUMBNAIL_SIZE,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._thumbnail_label.setPixmap(scaled)
        self._thumbnail_loaded = True

    def set_thumbnail_error(self, message: str = "이미지 없음") -> None:
        """
        썸네일 로드 실패 표시

        Args:
            message: 표시할 메시지
        """
        self._thumbnail_label.setText(message)
        self._thumbnail_label.setStyleSheet("""
            QLabel {
                background-color: #f0f0f0;
                border-radius: 8px;
                color: #aaa;
                font-size: 11px;
            }
        """)

    @property
    def thumbnail_url(self) -> Optional[str]:
        """썸네일 URL"""
        return self.item.thumbnail_url

    @property
    def is_thumbnail_loaded(self) -> bool:
        """썸네일 로드 여부"""
        return self._thumbnail_loaded

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """클릭 이벤트"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.item)

            # 브라우저에서 열기
            if self.item.url:
                webbrowser.open(self.item.url)

        super().mousePressEvent(event)


class ItemCardFactory:
    """
    ItemCard 팩토리

    ImageLoaderPool과 통합하여 카드 생성 및 이미지 로딩을 처리합니다.

    사용법:
        factory = ItemCardFactory(image_pool)
        card = factory.create(item)
    """

    def __init__(self, image_pool=None):
        """
        Args:
            image_pool: ImageLoaderPool 인스턴스
        """
        self._image_pool = image_pool
        self._cards: dict[str, ItemCard] = {}  # url -> card
        self._first_thumbnail_callback: Optional[Callable[[], None]] = None
        self._first_thumbnail_emitted = False

        # 이미지 풀 시그널 연결
        if image_pool:
            image_pool.image_loaded.connect(self._on_image_loaded)
            image_pool.image_error.connect(self._on_image_error)

    def set_first_thumbnail_callback(self, callback: Optional[Callable[[], None]]) -> None:
        """? ??? ?? ?? ??"""
        self._first_thumbnail_callback = callback

    def reset_timing(self) -> None:
        """??? ?? ?? ???"""
        self._first_thumbnail_emitted = False

    def create(self, item: BoothItem) -> ItemCard:
        """
        아이템 카드 생성

        Args:
            item: BoothItem

        Returns:
            ItemCard 인스턴스
        """
        card = ItemCard(item)

        # 썸네일 URL이 있으면 이미지 로드 요청
        if item.thumbnail_url and self._image_pool:
            self._cards[item.thumbnail_url] = card
            self._image_pool.request_image(item.thumbnail_url)

        return card

    def _on_image_loaded(self, url: str, pixmap: QPixmap) -> None:
        """??? ?? ?? ??"""
        if url in self._cards:
            self._cards[url].set_thumbnail(pixmap)
            del self._cards[url]

            if not self._first_thumbnail_emitted and self._first_thumbnail_callback:
                self._first_thumbnail_emitted = True
                self._first_thumbnail_callback()

    def _on_image_error(self, url: str, error: str) -> None:
        """이미지 로드 실패 콜백"""
        if url in self._cards:
            self._cards[url].set_thumbnail_error()
            del self._cards[url]

    def clear(self) -> None:
        """등록된 카드 초기화"""
        self._cards.clear()
        self._first_thumbnail_emitted = False
