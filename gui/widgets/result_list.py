"""
무한 스크롤 결과 리스트

검색 결과를 그리드 레이아웃으로 표시하고,
스크롤이 하단에 도달하면 다음 페이지를 로드합니다.
"""

from typing import Optional, List, Callable
from PyQt6.QtWidgets import (
    QWidget,
    QScrollArea,
    QVBoxLayout,
    QGridLayout,
    QLabel,
    QSizePolicy,
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QResizeEvent

from models.search_result import SearchResult
from models.booth_item import BoothItem
from utils.logging import get_logger

logger = get_logger(__name__)


class ResultList(QScrollArea):
    """
    무한 스크롤 검색 결과 리스트

    특징:
    - 그리드 레이아웃으로 ItemCard 배치
    - 스크롤 하단 도달 시 load_more 시그널 발생
    - 반응형 컬럼 수 조정 (창 크기에 따라)
    - 가상 스크롤 (대량 아이템 처리)

    시그널:
        load_more: 다음 페이지 로드 요청
        item_clicked: 아이템 클릭 (BoothItem)

    사용법:
        result_list = ResultList()
        result_list.load_more.connect(on_load_more)
        result_list.item_clicked.connect(on_item_click)

        # 결과 설정
        result_list.set_result(search_result)

        # 결과 추가 (무한 스크롤)
        result_list.append_result(next_result)
    """

    # 시그널
    load_more = pyqtSignal()  # 다음 페이지 요청
    item_clicked = pyqtSignal(BoothItem)

    # 상수
    CARD_WIDTH = 200
    CARD_HEIGHT = 280
    CARD_SPACING = 10
    LOAD_MORE_THRESHOLD = 100  # 하단 100px 도달 시 로드

    def __init__(
        self,
        card_factory: Optional[Callable[[BoothItem], QWidget]] = None,
        parent=None,
    ):
        super().__init__(parent)

        # 카드 팩토리 (ItemCard 생성 함수)
        self._card_factory = card_factory

        # 상태
        self._result: Optional[SearchResult] = None
        self._cards: List[QWidget] = []
        self._columns = 4
        self._loading_more = False
        self._has_more = False

        # UI 구성
        self._setup_ui()

        # 스크롤 이벤트 연결
        self.verticalScrollBar().valueChanged.connect(self._on_scroll)

        logger.debug("ResultList 초기화")

    def _setup_ui(self) -> None:
        """UI 초기화"""
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        # 컨테이너 위젯
        self._container = QWidget()
        self._container.setSizePolicy(
            QSizePolicy.Policy.Preferred,
            QSizePolicy.Policy.Minimum,
        )

        # 메인 레이아웃
        self._layout = QVBoxLayout(self._container)
        self._layout.setContentsMargins(self.CARD_SPACING, self.CARD_SPACING,
                                        self.CARD_SPACING, self.CARD_SPACING)
        self._layout.setSpacing(0)

        # 그리드 레이아웃
        self._grid_widget = QWidget()
        self._grid_widget.setSizePolicy(
            QSizePolicy.Policy.Preferred,
            QSizePolicy.Policy.Minimum,
        )
        self._grid_layout = QGridLayout(self._grid_widget)
        self._grid_layout.setSpacing(self.CARD_SPACING)
        self._grid_layout.setContentsMargins(0, 0, 0, 0)
        self._layout.addWidget(self._grid_widget)

        # 상태 라벨 (로딩 중, 결과 없음 등)
        self._status_label = QLabel()
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status_label.setStyleSheet("""
            QLabel {
                color: #888;
                font-size: 14px;
                padding: 20px;
            }
        """)
        self._status_label.hide()
        self._layout.addWidget(self._status_label)

        # 로딩 인디케이터
        self._loading_label = QLabel("더 불러오는 중...")
        self._loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._loading_label.setStyleSheet("""
            QLabel {
                color: #666;
                font-size: 13px;
                padding: 10px;
            }
        """)
        self._loading_label.hide()
        self._layout.addWidget(self._loading_label)

        self.setWidget(self._container)

    def set_card_factory(self, factory: Callable[[BoothItem], QWidget]) -> None:
        """카드 팩토리 설정"""
        self._card_factory = factory

    def set_result(self, result: SearchResult) -> None:
        """
        검색 결과 설정 (기존 결과 대체)

        Args:
            result: 검색 결과
        """
        self._clear_cards()
        self._result = result
        self._has_more = result.has_next

        if result.is_empty:
            self._show_status("검색 결과가 없습니다")
            return

        self._hide_status()
        self._add_items(result.items)

        # 스크롤 맨 위로
        self.verticalScrollBar().setValue(0)

        logger.debug(f"결과 설정: {len(result.items)}개 아이템")

    def append_result(self, result: SearchResult) -> None:
        """
        검색 결과 추가 (무한 스크롤)

        Args:
            result: 추가할 검색 결과
        """
        self._loading_more = False
        self._loading_label.hide()

        if result.is_empty:
            self._has_more = False
            return

        # 기존 결과와 병합
        if self._result is not None:
            self._result = self._result.merge(result)
        else:
            self._result = result

        self._has_more = result.has_next
        self._add_items(result.items)

        logger.debug(f"결과 추가: {len(result.items)}개 아이템")

    def clear(self) -> None:
        """결과 초기화"""
        self._clear_cards()
        self._result = None
        self._has_more = False
        self._show_status("")

    def _update_grid_size(self) -> None:
        """그리드 위젯 크기 업데이트"""
        if not self._cards:
            self._grid_widget.setMinimumHeight(0)
            self._container.updateGeometry()
            return

        # 행 수 계산
        rows = (len(self._cards) + self._columns - 1) // self._columns

        # 필요한 높이 계산 (카드 높이 + 간격)
        total_height = rows * (self.CARD_HEIGHT + self.CARD_SPACING)

        # 그리드 위젯 최소 높이 설정
        self._grid_widget.setMinimumHeight(total_height)
        self._grid_widget.setFixedHeight(total_height)

        # 컨테이너 크기 업데이트 강제
        self._container.updateGeometry()
        self._container.adjustSize()

        # 스크롤 영역 업데이트
        self.updateGeometry()

        logger.debug(f"Grid size updated: {len(self._cards)} cards, {rows} rows, {total_height}px height")

    def _clear_cards(self) -> None:
        """카드 제거"""
        for card in self._cards:
            self._grid_layout.removeWidget(card)
            card.deleteLater()
        self._cards.clear()
        self._update_grid_size()

    def _add_items(self, items: List[BoothItem]) -> None:
        """아이템 추가"""
        if not self._card_factory:
            logger.warning("카드 팩토리가 설정되지 않음")
            return

        start_index = len(self._cards)

        for i, item in enumerate(items):
            card = self._card_factory(item)

            # 클릭 이벤트 연결
            if hasattr(card, "clicked"):
                card.clicked.connect(lambda it=item: self.item_clicked.emit(it))

            self._cards.append(card)

            # 그리드에 추가
            idx = start_index + i
            row = idx // self._columns
            col = idx % self._columns
            self._grid_layout.addWidget(card, row, col)

        # 그리드 위젯 크기 업데이트
        self._update_grid_size()

    def _on_scroll(self, value: int) -> None:
        """스크롤 이벤트 처리"""
        if self._loading_more or not self._has_more:
            return

        scrollbar = self.verticalScrollBar()
        max_value = scrollbar.maximum()

        # 하단 근처에 도달하면 더 로드
        if max_value - value < self.LOAD_MORE_THRESHOLD:
            self._request_load_more()

    def _request_load_more(self) -> None:
        """다음 페이지 로드 요청"""
        if self._loading_more:
            return

        self._loading_more = True
        self._loading_label.show()
        self.load_more.emit()

        logger.debug("다음 페이지 로드 요청")

    def _show_status(self, message: str) -> None:
        """상태 메시지 표시"""
        self._status_label.setText(message)
        self._status_label.show()
        self._grid_widget.hide()

    def _hide_status(self) -> None:
        """상태 메시지 숨김"""
        self._status_label.hide()
        self._grid_widget.show()

    def show_loading(self) -> None:
        """로딩 상태 표시"""
        self._show_status("검색 중...")

    def show_error(self, message: str) -> None:
        """에러 메시지 표시"""
        self._show_status(f"오류: {message}")

    def resizeEvent(self, event: QResizeEvent) -> None:
        """창 크기 변경 시 컬럼 수 조정"""
        super().resizeEvent(event)

        # 새 컬럼 수 계산
        width = self.viewport().width() - self.CARD_SPACING * 2
        new_columns = max(1, width // (self.CARD_WIDTH + self.CARD_SPACING))

        # 컬럼 수가 변경되면 레이아웃 재구성
        if new_columns != self._columns and self._cards:
            self._columns = new_columns
            self._relayout_cards()

    def _relayout_cards(self) -> None:
        """카드 레이아웃 재구성"""
        # 기존 위젯 제거 (삭제하지 않음)
        for card in self._cards:
            self._grid_layout.removeWidget(card)

        # 새 위치에 추가
        for i, card in enumerate(self._cards):
            row = i // self._columns
            col = i % self._columns
            self._grid_layout.addWidget(card, row, col)

        # 그리드 위젯 크기 업데이트
        self._update_grid_size()

    @property
    def result(self) -> Optional[SearchResult]:
        """현재 결과"""
        return self._result

    @property
    def item_count(self) -> int:
        """표시된 아이템 수"""
        return len(self._cards)

    @property
    def has_more(self) -> bool:
        """더 로드할 결과가 있는지"""
        return self._has_more

    @property
    def is_loading(self) -> bool:
        """로딩 중인지"""
        return self._loading_more
