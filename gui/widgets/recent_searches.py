"""
최근 검색어 위젯

최근 검색한 아바타 이름을 클릭 가능한 태그로 표시합니다.
"""

from typing import List, Optional
from PyQt6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QFrame,
)
from PyQt6.QtCore import pyqtSignal, Qt

from config.user_prefs import get_prefs, save_prefs
from utils.logging import get_logger

logger = get_logger(__name__)


class SearchTag(QPushButton):
    """검색어 태그 버튼"""

    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setStyleSheet("""
            QPushButton {
                background-color: #f0f0f0;
                border: 1px solid #ddd;
                border-radius: 12px;
                padding: 4px 12px;
                font-size: 12px;
                color: #555;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
                border-color: #ccc;
            }
            QPushButton:pressed {
                background-color: #d0d0d0;
            }
        """)
        self.setCursor(Qt.CursorShape.PointingHandCursor)


class RecentSearchesWidget(QWidget):
    """
    최근 검색어 위젯

    시그널:
        search_selected: 검색어 선택됨 (query)
        cleared: 검색어 전체 삭제됨

    사용법:
        widget = RecentSearchesWidget()
        widget.search_selected.connect(on_search)

        # 검색어 추가
        widget.add_search("桔梗")

        # 갱신
        widget.refresh()
    """

    search_selected = pyqtSignal(str)
    cleared = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self.refresh()

    def _setup_ui(self) -> None:
        """UI 초기화"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        # 헤더
        header_layout = QHBoxLayout()

        self._title_label = QLabel("최근 검색")
        self._title_label.setStyleSheet("""
            QLabel {
                font-size: 12px;
                color: #666;
                font-weight: bold;
            }
        """)
        header_layout.addWidget(self._title_label)

        header_layout.addStretch()

        self._clear_btn = QPushButton("지우기")
        self._clear_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: #999;
                font-size: 11px;
            }
            QPushButton:hover {
                color: #666;
            }
        """)
        self._clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._clear_btn.clicked.connect(self._on_clear)
        header_layout.addWidget(self._clear_btn)

        layout.addLayout(header_layout)

        # 태그 컨테이너
        self._tags_container = QWidget()
        self._tags_layout = QHBoxLayout(self._tags_container)
        self._tags_layout.setContentsMargins(0, 0, 0, 0)
        self._tags_layout.setSpacing(8)
        self._tags_layout.addStretch()

        layout.addWidget(self._tags_container)

    def refresh(self) -> None:
        """최근 검색어 갱신"""
        # 기존 태그 제거
        while self._tags_layout.count() > 1:
            item = self._tags_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # 설정에서 로드
        prefs = get_prefs()
        searches = prefs.search.recent_searches

        if not searches:
            self.hide()
            return

        self.show()

        # 태그 추가
        for query in searches:
            tag = SearchTag(query)
            tag.clicked.connect(lambda checked, q=query: self._on_tag_clicked(q))
            self._tags_layout.insertWidget(self._tags_layout.count() - 1, tag)

    def add_search(self, query: str) -> None:
        """
        검색어 추가

        Args:
            query: 검색어
        """
        if not query:
            return

        prefs = get_prefs()
        prefs.add_recent_search(query)
        save_prefs(prefs)

        self.refresh()

    def _on_tag_clicked(self, query: str) -> None:
        """태그 클릭"""
        self.search_selected.emit(query)

    def _on_clear(self) -> None:
        """검색어 삭제"""
        prefs = get_prefs()
        prefs.clear_recent_searches()
        save_prefs(prefs)

        self.refresh()
        self.cleared.emit()

    def get_searches(self) -> List[str]:
        """최근 검색어 목록"""
        prefs = get_prefs()
        return prefs.search.recent_searches.copy()
