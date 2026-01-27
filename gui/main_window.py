"""
메인 윈도우

모든 GUI 컴포넌트를 통합한 애플리케이션 메인 윈도우
"""

from typing import Optional
from pathlib import Path
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
    QFileDialog,
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QCloseEvent

from models.search_params import SearchParams, SortOrder, PriceRange
from models.search_result import SearchResult
from models.booth_item import BoothItem
from core.search_service import SearchService
from core.exporter import ResultExporter, get_default_export_filename
from config.settings import Settings
from config.constants import BOOTH_CATEGORIES
from utils.logging import get_logger

from .workers.search_worker import SearchWorker
from .workers.image_pool import ImageLoaderPool
from .widgets.result_list import ResultList
from .widgets.filter_panel import FilterPanel
from .widgets.item_card import ItemCard, ItemCardFactory
from .themes import ThemeMode, get_theme, generate_stylesheet, is_system_dark_mode

logger = get_logger(__name__)


class ThemeToggleButton(QPushButton):
    """테마 토글 버튼"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(36, 36)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._is_dark = False
        self._update_icon()

    def set_dark_mode(self, is_dark: bool) -> None:
        """다크 모드 설정"""
        self._is_dark = is_dark
        self._update_icon()

    def _update_icon(self) -> None:
        """아이콘 업데이트"""
        if self._is_dark:
            self.setText("\u2600")  # ☀ (라이트 모드로 전환)
            self.setToolTip("라이트 모드로 전환")
        else:
            self.setText("\u263D")  # ☽ (다크 모드로 전환)
            self.setToolTip("다크 모드로 전환")


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

        # 현재 검색 상태
        self._current_params: Optional[SearchParams] = None
        self._current_result: Optional[SearchResult] = None

        # 테마 상태
        self._theme_mode = ThemeMode.DARK if is_system_dark_mode() else ThemeMode.LIGHT

        # UI 구성
        self._setup_ui()
        self._connect_signals()
        self._apply_theme()

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

        # === 제목 영역 ===
        title_layout = QHBoxLayout()
        title_layout.setContentsMargins(0, 0, 0, 0)

        # 왼쪽 여백
        title_layout.addStretch()

        # 제목
        title_label = QLabel("Booth VRChat 의상 검색기")
        title_label.setObjectName("titleLabel")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_layout.addWidget(title_label)

        # 오른쪽 버튼들
        title_layout.addStretch()

        # 내보내기 버튼
        self._export_btn = QPushButton("내보내기")
        self._export_btn.setObjectName("exportButton")
        self._export_btn.setFixedWidth(80)
        self._export_btn.setEnabled(False)
        title_layout.addWidget(self._export_btn)

        # 테마 토글 버튼
        self._theme_btn = ThemeToggleButton()
        self._theme_btn.setObjectName("themeButton")
        self._theme_btn.set_dark_mode(self._theme_mode == ThemeMode.DARK)
        title_layout.addWidget(self._theme_btn)

        main_layout.addLayout(title_layout)

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

        # 테마 토글
        self._theme_btn.clicked.connect(self._on_toggle_theme)

        # 내보내기
        self._export_btn.clicked.connect(self._on_export)

    def _apply_theme(self) -> None:
        """테마 적용"""
        theme = get_theme(self._theme_mode)
        stylesheet = generate_stylesheet(theme)
        self.setStyleSheet(stylesheet)

        # 테마 버튼 상태 업데이트
        if hasattr(self, '_theme_btn'):
            self._theme_btn.set_dark_mode(self._theme_mode == ThemeMode.DARK)

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
        self._current_params = SearchParams(
            avatar_name=avatar_name,
            category=self._category_combo.currentText(),
            sort=self._filter_panel.sort_order,
            price_range=self._filter_panel.price_range,
            page=1,
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
        self._result_list.show_loading()

        logger.debug(f"검색 시작: {params.avatar_name}")

    def _on_search_progress(self, current: int, total: int, message: str) -> None:
        """검색 진행 상황"""
        self._status_label.setText(message)

        if total > 0:
            self._progress_bar.setRange(0, total)
            self._progress_bar.setValue(current)
        else:
            self._progress_bar.setRange(0, 0)

    def _on_search_result(self, result: SearchResult) -> None:
        """검색 결과 수신"""
        self._search_complete()
        self._current_result = result

        if result.is_empty:
            self._status_label.setText("검색 결과가 없습니다.")
            self._result_list.clear()
            self._export_btn.setEnabled(False)
        else:
            self._status_label.setText(
                f"'{result.query}' 검색 결과: "
                f"{len(result.items)}개 (전체 {result.total_count}개)"
            )
            self._result_list.set_result(result)
            self._export_btn.setEnabled(True)

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

    def _on_toggle_theme(self) -> None:
        """테마 토글"""
        if self._theme_mode == ThemeMode.LIGHT:
            self._theme_mode = ThemeMode.DARK
        else:
            self._theme_mode = ThemeMode.LIGHT

        self._apply_theme()
        logger.debug(f"테마 변경: {self._theme_mode.value}")

    def _on_export(self) -> None:
        """검색 결과 내보내기"""
        if self._current_result is None or self._current_result.is_empty:
            QMessageBox.warning(self, "내보내기 오류", "내보낼 검색 결과가 없습니다.")
            return

        # 파일 형식 선택
        file_filter = "CSV 파일 (*.csv);;JSON 파일 (*.json)"
        default_name = get_default_export_filename(
            self._current_result.query, "csv"
        )

        file_path, selected_filter = QFileDialog.getSaveFileName(
            self,
            "검색 결과 내보내기",
            default_name,
            file_filter,
        )

        if not file_path:
            return

        path = Path(file_path)
        exporter = ResultExporter()

        if "csv" in selected_filter.lower():
            success = exporter.export_csv(self._current_result, path)
        else:
            success = exporter.export_json(self._current_result, path)

        if success:
            QMessageBox.information(
                self,
                "내보내기 완료",
                f"검색 결과가 저장되었습니다.\n{path}",
            )
        else:
            QMessageBox.warning(
                self,
                "내보내기 실패",
                "파일 저장 중 오류가 발생했습니다.",
            )

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
