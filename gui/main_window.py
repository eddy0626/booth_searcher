"""
메인 윈도우

모든 GUI 컴포넌트를 통합한 애플리케이션 메인 윈도우
"""

from typing import Optional
import time
from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QComboBox,
    QPushButton,
    QFrame,
    QProgressBar,
    QStatusBar,
    QMessageBox,
    QCheckBox,
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QCloseEvent

from models.search_params import SearchParams, SortOrder, PriceRange
from models.search_result import SearchResult
from models.booth_item import BoothItem
from core.search_service import SearchService
from config.settings import Settings
from config.constants import BOOTH_CATEGORIES
from config.user_prefs import get_prefs, save_prefs
from utils.logging import get_logger, log_timing

from .workers.search_worker import SearchWorker
from .workers.image_pool import ImageLoaderPool
from .widgets.result_list import ResultList
from .widgets.filter_panel import FilterPanel
from .widgets.item_card import ItemCard, ItemCardFactory

logger = get_logger(__name__)


class MainWindow(QMainWindow):
    """
    Booth VRChat 의상 검색기 메인 윈도우

    특징:
    - 아바타 이름 검색
    - 인기 아바타 목록
    - 카테고리 필터
    - 정렬/가격 필터
    - 무한 스크롤 결과 리스트
    - 썸네일 비동기 로딩
    """

    def __init__(self, settings: Optional[Settings] = None):
        super().__init__()

        self.settings = settings or Settings()

        # 서비스 초기화
        self._search_service = SearchService(self.settings)
        self._search_worker = SearchWorker(
            settings=self.settings,
            search_service=self._search_service,
        )
        self._image_pool = ImageLoaderPool(settings=self.settings)
        self._card_factory = ItemCardFactory(self._image_pool)
        self._card_factory.set_first_thumbnail_callback(
            self._on_first_thumbnail_rendered
        )

        # 현재 검색 상태
        self._current_params: Optional[SearchParams] = None
        self._current_result: Optional[SearchResult] = None
        self._search_start_time: Optional[float] = None
        self._first_result_logged = False
        self._first_thumbnail_logged = False

        # UI 구성
        self._setup_ui()
        self._connect_signals()
        self._apply_styles()

        logger.info("MainWindow 초기화")

    def _setup_ui(self) -> None:
        """UI 초기화"""
        self.setWindowTitle("Booth VRChat 의상 검색기")
        self.setMinimumSize(900, 700)

        # 중앙 위젯
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # === 제목 ===
        title_label = QLabel("Booth VRChat 의상 검색기")
        title_label.setObjectName("titleLabel")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title_label)

        # === 검색 영역 ===
        search_frame = self._create_search_frame()
        main_layout.addWidget(search_frame)

        # === 필터 패널 ===
        self._filter_panel = FilterPanel()
        main_layout.addWidget(self._filter_panel)

        # === 프로그레스 바 ===
        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 0)
        self._progress_bar.setMaximumHeight(5)
        self._progress_bar.hide()
        main_layout.addWidget(self._progress_bar)

        # === 결과 상태 라벨 ===
        self._status_label = QLabel("아바타 이름을 입력하고 검색 버튼을 클릭하세요.")
        self._status_label.setObjectName("statusLabel")
        main_layout.addWidget(self._status_label)

        # === 검색어 보정 힌트 ===
        self._correction_hint = QLabel("")
        self._correction_hint.setObjectName("correctionHint")
        self._correction_hint.hide()
        main_layout.addWidget(self._correction_hint)

        # === 결과 리스트 ===
        self._result_list = ResultList()
        self._result_list.set_card_factory(self._card_factory.create)
        main_layout.addWidget(self._result_list, 1)

        # === 상태 바 ===
        self._statusbar = QStatusBar()
        self.setStatusBar(self._statusbar)

    def _create_search_frame(self) -> QFrame:
        """검색 영역 생성"""
        frame = QFrame()
        frame.setObjectName("searchFrame")

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        # 검색어 입력 행
        input_layout = QHBoxLayout()
        input_layout.setSpacing(10)

        # 아바타 이름 입력
        avatar_label = QLabel("아바타 이름:")
        input_layout.addWidget(avatar_label)

        self._avatar_input = QLineEdit()
        self._avatar_input.setPlaceholderText("예: 桔梗, セレスティア, マヌカ")
        input_layout.addWidget(self._avatar_input, 2)

        # 인기 아바타 콤보박스
        popular_label = QLabel("인기 아바타:")
        input_layout.addWidget(popular_label)

        self._popular_combo = QComboBox()
        self._popular_combo.addItem("직접 입력")
        for avatar in self._search_service.get_popular_avatars():
            self._popular_combo.addItem(avatar)
        input_layout.addWidget(self._popular_combo, 1)

        layout.addLayout(input_layout)

        # 카테고리 및 검색 버튼 행
        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(10)

        # 카테고리 필터
        category_label = QLabel("카테고리:")
        filter_layout.addWidget(category_label)

        self._category_combo = QComboBox()
        for category in BOOTH_CATEGORIES.keys():
            self._category_combo.addItem(category)
        filter_layout.addWidget(self._category_combo)

        filter_layout.addStretch()

        # 검색 버튼
        self._search_btn = QPushButton("검색")
        self._search_btn.setObjectName("searchButton")
        self._search_btn.setMinimumWidth(100)
        filter_layout.addWidget(self._search_btn)

        # 취소 버튼
        self._cancel_btn = QPushButton("취소")
        self._cancel_btn.setObjectName("cancelButton")
        self._cancel_btn.setMinimumWidth(80)
        self._cancel_btn.hide()
        filter_layout.addWidget(self._cancel_btn)

        layout.addLayout(filter_layout)

        # 검색어 보정 토글
        correction_layout = QHBoxLayout()
        correction_layout.setSpacing(8)
        correction_layout.addStretch()
        self._correction_toggle = QCheckBox("검색어 보정")
        prefs = get_prefs()
        self._correction_toggle.setChecked(prefs.search.normalize_enabled)
        self._correction_toggle.setToolTip("검색어 정규화/폴백 검색을 사용합니다.")
        correction_layout.addWidget(self._correction_toggle)
        layout.addLayout(correction_layout)

        return frame

    def _connect_signals(self) -> None:
        """시그널 연결"""
        # 검색 입력
        self._avatar_input.returnPressed.connect(self._on_search)
        self._popular_combo.currentTextChanged.connect(self._on_popular_selected)
        self._search_btn.clicked.connect(self._on_search)
        self._cancel_btn.clicked.connect(self._on_cancel)

        # 필터
        self._filter_panel.filters_changed.connect(self._on_filters_changed)

        # 검색 워커
        self._search_worker.started_signal.connect(self._on_search_started)
        self._search_worker.progress.connect(self._on_search_progress)
        self._search_worker.result_ready.connect(self._on_search_result)
        self._search_worker.error.connect(self._on_search_error)
        self._search_worker.cancelled.connect(self._on_search_cancelled)

        # 결과 리스트
        self._result_list.load_more.connect(self._on_load_more)
        self._result_list.item_clicked.connect(self._on_item_clicked)
        self._result_list.first_item_rendered.connect(self._on_first_result_rendered)

        # 검색어 보정 토글
        self._correction_toggle.toggled.connect(self._on_correction_toggle)

    def _apply_styles(self) -> None:
        """스타일 적용"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }

            #titleLabel {
                font-size: 20px;
                font-weight: bold;
                color: #333;
                padding: 10px;
            }

            #searchFrame {
                background-color: white;
                border-radius: 10px;
                border: 1px solid #e0e0e0;
            }

            QLineEdit {
                padding: 10px;
                border: 2px solid #ddd;
                border-radius: 6px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border-color: #ff6b6b;
            }

            QComboBox {
                padding: 8px;
                border: 2px solid #ddd;
                border-radius: 6px;
                font-size: 14px;
                background: white;
            }
            QComboBox:focus {
                border-color: #ff6b6b;
            }

            #searchButton {
                padding: 10px 20px;
                background-color: #ff6b6b;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 14px;
                font-weight: bold;
            }
            #searchButton:hover {
                background-color: #ff5252;
            }
            #searchButton:pressed {
                background-color: #e04545;
            }
            #searchButton:disabled {
                background-color: #ccc;
            }

            #cancelButton {
                padding: 10px 15px;
                background-color: #888;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 14px;
            }
            #cancelButton:hover {
                background-color: #666;
            }

            #statusLabel {
                color: #666;
                font-size: 13px;
                padding: 5px;
            }
            #correctionHint {
                color: #888;
                font-size: 12px;
                padding: 2px 5px;
            }

            QProgressBar {
                border: none;
                background-color: #e0e0e0;
            }
            QProgressBar::chunk {
                background-color: #ff6b6b;
            }
        """)

    def _on_popular_selected(self, text: str) -> None:
        """인기 아바타 선택"""
        if text != "직접 입력":
            # 일본어 이름만 추출 (한글 이름 제거)
            name = text.split(" (")[0] if " (" in text else text
            self._avatar_input.setText(name)

    def _on_search(self) -> None:
        """검색 시작"""
        avatar_name = self._avatar_input.text().strip()
        if not avatar_name:
            QMessageBox.warning(self, "입력 오류", "아바타 이름을 입력해주세요.")
            return

        # 검색 파라미터 생성
        prefs = get_prefs()
        correction_enabled = self._correction_toggle.isChecked()
        self._current_params = SearchParams(
            avatar_name=avatar_name,
            category=self._category_combo.currentText(),
            sort=self._filter_panel.sort_order,
            price_range=self._filter_panel.price_range,
            page=1,
            raw_query=avatar_name,
            normalize_enabled=correction_enabled,
            alias_enabled=correction_enabled,
            fallback_enabled=correction_enabled,
            fallback_min_results=prefs.search.fallback_min_results,
        )

        # 카드 팩토리 초기화
        self._card_factory.clear()

        # 검색 실행
        self._search_worker.search(
            self._current_params,
            use_cache=True,
        )

    def _on_cancel(self) -> None:
        """검색 취소"""
        self._search_worker.cancel()

    def _on_search_started(self, params: SearchParams) -> None:
        """검색 시작됨"""
        self._search_btn.setEnabled(False)
        self._cancel_btn.show()
        self._progress_bar.show()
        self._status_label.setText(f"'{params.avatar_name}' 검색 중...")
        self._correction_hint.hide()
        self._result_list.show_loading()
        if params.page == 1:
            self._search_start_time = time.perf_counter()
            self._first_result_logged = False
            self._first_thumbnail_logged = False
            self._card_factory.reset_timing()

        logger.debug(f"검색 시작: {params.avatar_name}")

    def _on_search_progress(self, current: int, total: int, message: str) -> None:
        """검색 진행 상황"""
        self._status_label.setText(message)

        if total > 0:
            self._progress_bar.setRange(0, total)
            self._progress_bar.setValue(current)
        else:
            self._progress_bar.setRange(0, 0)

    def _on_first_result_rendered(self) -> None:
        """? ?? ??? ??? ??"""
        if self._search_start_time is None or self._first_result_logged:
            return
        self._first_result_logged = True
        log_timing(logger, "time_to_first_result", self._search_start_time)

    def _on_first_thumbnail_rendered(self) -> None:
        """? ??? ??? ??? ??"""
        if self._search_start_time is None or self._first_thumbnail_logged:
            return
        self._first_thumbnail_logged = True
        log_timing(logger, "time_to_first_thumbnail", self._search_start_time)

    def _on_search_result(self, result: SearchResult) -> None:
        """검색 결과 수신"""
        self._search_complete()
        self._current_result = result
        if self._current_params is not None and result.resolved_query:
            self._current_params = self._current_params.with_avatar_name(result.resolved_query)

        if result.is_empty:
            self._status_label.setText("검색 결과가 없습니다.")
            self._result_list.clear()
        else:
            self._status_label.setText(
                f"'{result.query}' 검색 결과: "
                f"{len(result.items)}개 (전체 {result.total_count}개)"
            )
            self._result_list.set_result(result)

        if result.current_page == 1:
            if result.used_strategy and result.used_strategy != "original":
                raw = result.raw_query or self._avatar_input.text().strip()
                resolved = result.resolved_query or result.query
                self._correction_hint.setText(
                    f"검색어 보정 적용됨: {resolved} (원문: {raw})"
                )
                self._correction_hint.show()
            else:
                self._correction_hint.hide()

        # 상태 바 업데이트
        stats = self._search_service.get_stats()
        cache_stats = stats.get("cache", {})
        self._statusbar.showMessage(
            f"캐시 히트율: {cache_stats.get('hit_rate', 0)}%"
        )

    def _on_search_error(self, error: str) -> None:
        """검색 에러"""
        self._search_complete()
        self._status_label.setText(f"검색 실패: {error}")
        self._result_list.show_error(error)

        logger.error(f"검색 에러: {error}")

    def _on_search_cancelled(self) -> None:
        """검색 취소됨"""
        self._search_complete()
        self._status_label.setText("검색이 취소되었습니다.")

        logger.info("검색 취소됨")

    def _search_complete(self) -> None:
        """검색 완료 처리"""
        self._search_btn.setEnabled(True)
        self._cancel_btn.hide()
        self._progress_bar.hide()

    def _on_filters_changed(
        self,
        sort: SortOrder,
        price_range: Optional[PriceRange],
    ) -> None:
        """필터 변경"""
        if self._current_params is None:
            return

        # 새 파라미터로 재검색
        self._current_params = SearchParams(
            avatar_name=self._current_params.avatar_name,
            category=self._current_params.category,
            sort=sort,
            price_range=price_range,
            page=1,
            raw_query=self._current_params.raw_query,
            normalize_enabled=self._current_params.normalize_enabled,
            alias_enabled=self._current_params.alias_enabled,
            fallback_enabled=self._current_params.fallback_enabled,
            fallback_min_results=self._current_params.fallback_min_results,
            normalization_enabled=self._current_params.normalization_enabled,
            allow_multi=self._current_params.allow_multi,
        )

        # 카드 팩토리 초기화
        self._card_factory.clear()

        # 재검색
        self._search_worker.search(
            self._current_params,
            use_cache=True,
        )

    def _on_load_more(self) -> None:
        """다음 페이지 로드"""
        if self._current_params is None or self._current_result is None:
            return

        if not self._current_result.has_next:
            return

        # 다음 페이지
        next_params = self._current_params.with_page(
            self._current_result.current_page + 1
        )
        self._current_params = next_params

        # 검색 (append 모드)
        self._search_worker.search(
            next_params,
            use_cache=True,
        )

    def _on_item_clicked(self, item: BoothItem) -> None:
        """아이템 클릭"""
        logger.debug(f"아이템 클릭: {item.name}")
        prefs = get_prefs()
        prefs.add_recent_click(item.name, item.shop_name)
        save_prefs(prefs)

    def _on_correction_toggle(self, checked: bool) -> None:
        """검색어 보정 토글 변경"""
        prefs = get_prefs()
        prefs.search.normalize_enabled = checked
        prefs.search.alias_enabled = checked
        prefs.search.fallback_enabled = checked
        save_prefs(prefs)

    def closeEvent(self, event: QCloseEvent) -> None:
        """창 닫기 이벤트"""
        # 검색 취소
        self._search_worker.cancel()
        self._search_worker.wait(3000)

        # 리소스 정리
        self._search_worker.close()
        self._image_pool.close()
        self._search_service.close()

        logger.info("MainWindow 종료")
        event.accept()
