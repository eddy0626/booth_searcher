"""
필터 패널

가격 범위, 무료만 보기, 정렬 옵션을 제공합니다.
"""

from typing import Optional
from PyQt6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QComboBox,
    QCheckBox,
    QSpinBox,
    QPushButton,
    QFrame,
)
from PyQt6.QtCore import pyqtSignal, Qt

from models.search_params import SortOrder, PriceRange
from utils.logging import get_logger

logger = get_logger(__name__)


class FilterPanel(QWidget):
    """
    검색 필터 패널

    특징:
    - 정렬 옵션 (최신순, 인기순, 가격순)
    - 가격 범위 필터
    - 무료만 보기 체크박스
    - 필터 초기화 버튼

    시그널:
        filters_changed: 필터 변경 (sort_order, price_range)
        sort_changed: 정렬 변경 (SortOrder)
        price_changed: 가격 범위 변경 (PriceRange)

    사용법:
        panel = FilterPanel()
        panel.filters_changed.connect(on_filters_changed)

        # 현재 필터 가져오기
        sort = panel.sort_order
        price_range = panel.price_range
    """

    # 시그널
    filters_changed = pyqtSignal(SortOrder, object)  # sort, price_range (or None)
    sort_changed = pyqtSignal(SortOrder)
    price_changed = pyqtSignal(object)  # PriceRange or None

    def __init__(self, parent=None):
        super().__init__(parent)

        # 상태
        self._sort_order = SortOrder.NEWEST
        self._price_range: Optional[PriceRange] = None

        # UI 구성
        self._setup_ui()
        self._connect_signals()

        logger.debug("FilterPanel 초기화")

    def _setup_ui(self) -> None:
        """UI 초기화"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(15)

        # === 정렬 섹션 ===
        sort_section = self._create_sort_section()
        layout.addWidget(sort_section)

        # 구분선
        layout.addWidget(self._create_separator())

        # === 가격 섹션 ===
        price_section = self._create_price_section()
        layout.addWidget(price_section)

        # 스트레치
        layout.addStretch()

        # === 리셋 버튼 ===
        self._reset_btn = QPushButton("필터 초기화")
        self._reset_btn.setFixedWidth(80)
        self._reset_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #666;
                border: 1px solid #ccc;
                border-radius: 4px;
                padding: 4px 8px;
            }
            QPushButton:hover {
                background: #f0f0f0;
                color: #333;
            }
        """)
        layout.addWidget(self._reset_btn)

    def _create_sort_section(self) -> QWidget:
        """정렬 섹션 생성"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        label = QLabel("정렬:")
        label.setStyleSheet("color: #666;")
        layout.addWidget(label)

        self._sort_combo = QComboBox()
        self._sort_combo.setFixedWidth(120)
        self._sort_combo.addItems([
            "최신순",
            "인기순",
            "가격 낮은순",
            "가격 높은순",
        ])
        self._sort_combo.setStyleSheet("""
            QComboBox {
                border: 1px solid #ccc;
                border-radius: 4px;
                padding: 4px 8px;
                background: white;
            }
            QComboBox:hover {
                border-color: #999;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
        """)
        layout.addWidget(self._sort_combo)

        return widget

    def _create_price_section(self) -> QWidget:
        """가격 필터 섹션 생성"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # 무료만 체크박스
        self._free_only_cb = QCheckBox("무료만")
        self._free_only_cb.setStyleSheet("color: #666;")
        layout.addWidget(self._free_only_cb)

        # 구분선
        layout.addWidget(self._create_separator())

        # 가격 범위
        price_label = QLabel("가격:")
        price_label.setStyleSheet("color: #666;")
        layout.addWidget(price_label)

        self._min_price = QSpinBox()
        self._min_price.setRange(0, 999999)
        self._min_price.setSingleStep(100)
        self._min_price.setPrefix("¥")
        self._min_price.setFixedWidth(90)
        self._min_price.setSpecialValueText("최소")
        self._min_price.setStyleSheet(self._spinbox_style())
        layout.addWidget(self._min_price)

        dash_label = QLabel("~")
        dash_label.setStyleSheet("color: #666;")
        layout.addWidget(dash_label)

        self._max_price = QSpinBox()
        self._max_price.setRange(0, 999999)
        self._max_price.setSingleStep(100)
        self._max_price.setPrefix("¥")
        self._max_price.setFixedWidth(90)
        self._max_price.setSpecialValueText("최대")
        self._max_price.setStyleSheet(self._spinbox_style())
        layout.addWidget(self._max_price)

        # 적용 버튼
        self._apply_price_btn = QPushButton("적용")
        self._apply_price_btn.setFixedWidth(50)
        self._apply_price_btn.setStyleSheet("""
            QPushButton {
                background: #4a90d9;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 4px 8px;
            }
            QPushButton:hover {
                background: #357abd;
            }
        """)
        layout.addWidget(self._apply_price_btn)

        return widget

    def _create_separator(self) -> QFrame:
        """구분선 생성"""
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.VLine)
        separator.setStyleSheet("color: #ddd;")
        return separator

    def _spinbox_style(self) -> str:
        """스핀박스 스타일"""
        return """
            QSpinBox {
                border: 1px solid #ccc;
                border-radius: 4px;
                padding: 4px;
                background: white;
            }
            QSpinBox:hover {
                border-color: #999;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                width: 16px;
            }
        """

    def _connect_signals(self) -> None:
        """시그널 연결"""
        self._sort_combo.currentIndexChanged.connect(self._on_sort_changed)
        self._free_only_cb.stateChanged.connect(self._on_free_only_changed)
        self._apply_price_btn.clicked.connect(self._on_price_apply)
        self._reset_btn.clicked.connect(self.reset)

    def _on_sort_changed(self, index: int) -> None:
        """정렬 변경 처리"""
        sort_map = {
            0: SortOrder.NEWEST,
            1: SortOrder.POPULAR,
            2: SortOrder.PRICE_ASC,
            3: SortOrder.PRICE_DESC,
        }
        self._sort_order = sort_map.get(index, SortOrder.NEWEST)
        self.sort_changed.emit(self._sort_order)
        self._emit_filters_changed()

        logger.debug(f"정렬 변경: {self._sort_order.name}")

    def _on_free_only_changed(self, state: int) -> None:
        """무료만 체크박스 변경"""
        is_free = state == Qt.CheckState.Checked.value

        if is_free:
            self._price_range = PriceRange(free_only=True)
            # 가격 입력 비활성화
            self._min_price.setEnabled(False)
            self._max_price.setEnabled(False)
            self._apply_price_btn.setEnabled(False)
        else:
            self._price_range = None
            # 가격 입력 활성화
            self._min_price.setEnabled(True)
            self._max_price.setEnabled(True)
            self._apply_price_btn.setEnabled(True)

        self.price_changed.emit(self._price_range)
        self._emit_filters_changed()

        logger.debug(f"무료만: {is_free}")

    def _on_price_apply(self) -> None:
        """가격 범위 적용"""
        min_price = self._min_price.value() if self._min_price.value() > 0 else None
        max_price = self._max_price.value() if self._max_price.value() > 0 else None

        if min_price is None and max_price is None:
            self._price_range = None
        else:
            self._price_range = PriceRange(
                min_price=min_price,
                max_price=max_price,
            )

        self.price_changed.emit(self._price_range)
        self._emit_filters_changed()

        logger.debug(f"가격 범위: {self._price_range}")

    def _emit_filters_changed(self) -> None:
        """필터 변경 시그널 발송"""
        self.filters_changed.emit(self._sort_order, self._price_range)

    def reset(self) -> None:
        """필터 초기화"""
        # 정렬
        self._sort_combo.setCurrentIndex(0)
        self._sort_order = SortOrder.NEWEST

        # 무료만
        self._free_only_cb.setChecked(False)

        # 가격 범위
        self._min_price.setValue(0)
        self._max_price.setValue(0)
        self._min_price.setEnabled(True)
        self._max_price.setEnabled(True)
        self._apply_price_btn.setEnabled(True)

        self._price_range = None

        self._emit_filters_changed()

        logger.debug("필터 초기화")

    @property
    def sort_order(self) -> SortOrder:
        """현재 정렬 순서"""
        return self._sort_order

    @sort_order.setter
    def sort_order(self, value: SortOrder) -> None:
        """정렬 순서 설정"""
        index_map = {
            SortOrder.NEWEST: 0,
            SortOrder.POPULAR: 1,
            SortOrder.PRICE_ASC: 2,
            SortOrder.PRICE_DESC: 3,
        }
        index = index_map.get(value, 0)
        self._sort_combo.setCurrentIndex(index)

    @property
    def price_range(self) -> Optional[PriceRange]:
        """현재 가격 범위"""
        return self._price_range

    @property
    def is_free_only(self) -> bool:
        """무료만 필터 여부"""
        return self._free_only_cb.isChecked()
