"""
Booth 의상 검색기 GUI 모듈
PyQt6 기반 사용자 인터페이스
"""

import sys
import webbrowser
from typing import List
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QComboBox, QScrollArea,
    QFrame, QGridLayout, QMessageBox, QProgressBar, QSizePolicy
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize, QUrl
from PyQt6.QtGui import QPixmap, QFont, QDesktopServices
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply

from scraper import BoothScraper, BoothItem


class SearchWorker(QThread):
    """백그라운드 검색 스레드"""
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, scraper: BoothScraper, avatar_name: str, category: str):
        super().__init__()
        self.scraper = scraper
        self.avatar_name = avatar_name
        self.category = category

    def run(self):
        try:
            results = self.scraper.search(self.avatar_name, self.category)
            self.finished.emit(results)
        except Exception as e:
            self.error.emit(str(e))


class ImageLoader(QThread):
    """이미지 비동기 로더"""
    loaded = pyqtSignal(str, bytes)

    def __init__(self, url: str):
        super().__init__()
        self.url = url

    def run(self):
        try:
            import requests
            response = requests.get(self.url, timeout=10)
            if response.status_code == 200:
                self.loaded.emit(self.url, response.content)
        except Exception:
            pass


class ItemCard(QFrame):
    """상품 카드 위젯"""

    def __init__(self, item: BoothItem, parent=None):
        super().__init__(parent)
        self.item = item
        self.setup_ui()

    def setup_ui(self):
        self.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Raised)
        self.setStyleSheet("""
            ItemCard {
                background-color: white;
                border: 1px solid #ddd;
                border-radius: 8px;
                padding: 10px;
            }
            ItemCard:hover {
                border-color: #ff6b6b;
                background-color: #fff5f5;
            }
        """)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(120)
        self.setMaximumHeight(150)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        # 썸네일 이미지
        self.thumbnail_label = QLabel()
        self.thumbnail_label.setFixedSize(100, 100)
        self.thumbnail_label.setStyleSheet("background-color: #f0f0f0; border-radius: 4px;")
        self.thumbnail_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumbnail_label.setText("로딩중...")
        layout.addWidget(self.thumbnail_label)

        # 상품 정보
        info_layout = QVBoxLayout()
        info_layout.setSpacing(5)

        # 상품명
        name_label = QLabel(self.item.name)
        name_label.setFont(QFont("맑은 고딕", 10, QFont.Weight.Bold))
        name_label.setWordWrap(True)
        name_label.setMaximumHeight(50)
        info_layout.addWidget(name_label)

        # 샵 이름
        if self.item.shop_name:
            shop_label = QLabel(f"판매자: {self.item.shop_name}")
            shop_label.setStyleSheet("color: #666;")
            shop_label.setFont(QFont("맑은 고딕", 8))
            info_layout.addWidget(shop_label)

        # 가격
        price_label = QLabel(self.item.price)
        price_label.setFont(QFont("맑은 고딕", 11, QFont.Weight.Bold))
        price_label.setStyleSheet("color: #ff6b6b;")
        info_layout.addWidget(price_label)

        info_layout.addStretch()
        layout.addLayout(info_layout, 1)

        # 이미지 로드
        if self.item.thumbnail_url:
            self.load_image()

    def load_image(self):
        """이미지를 비동기로 로드합니다."""
        self.image_loader = ImageLoader(self.item.thumbnail_url)
        self.image_loader.loaded.connect(self.on_image_loaded)
        self.image_loader.start()

    def on_image_loaded(self, url: str, data: bytes):
        """이미지 로드 완료 콜백"""
        pixmap = QPixmap()
        if pixmap.loadFromData(data):
            scaled = pixmap.scaled(
                100, 100,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.thumbnail_label.setPixmap(scaled)
        else:
            self.thumbnail_label.setText("이미지 없음")

    def mousePressEvent(self, event):
        """클릭 시 브라우저에서 상품 페이지 열기"""
        if self.item.url:
            webbrowser.open(self.item.url)
        super().mousePressEvent(event)


class MainWindow(QMainWindow):
    """메인 윈도우"""

    def __init__(self):
        super().__init__()
        self.scraper = BoothScraper()
        self.search_worker = None
        self.item_cards: List[ItemCard] = []
        self.setup_ui()

    def setup_ui(self):
        self.setWindowTitle("Booth VRChat 의상 검색기")
        self.setMinimumSize(800, 600)
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }
            QLineEdit {
                padding: 8px;
                border: 2px solid #ddd;
                border-radius: 4px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border-color: #ff6b6b;
            }
            QPushButton {
                padding: 8px 16px;
                background-color: #ff6b6b;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #ff5252;
            }
            QPushButton:pressed {
                background-color: #e04545;
            }
            QPushButton:disabled {
                background-color: #ccc;
            }
            QComboBox {
                padding: 8px;
                border: 2px solid #ddd;
                border-radius: 4px;
                font-size: 14px;
            }
            QComboBox:focus {
                border-color: #ff6b6b;
            }
        """)

        # 중앙 위젯
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # 제목
        title_label = QLabel("🎮 Booth VRChat 의상 검색기")
        title_label.setFont(QFont("맑은 고딕", 18, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title_label)

        # 검색 영역
        search_frame = QFrame()
        search_frame.setStyleSheet("background-color: white; border-radius: 8px; padding: 10px;")
        search_layout = QVBoxLayout(search_frame)

        # 검색어 입력 행
        input_layout = QHBoxLayout()

        # 아바타 이름 입력
        avatar_label = QLabel("아바타 이름:")
        avatar_label.setFont(QFont("맑은 고딕", 10))
        input_layout.addWidget(avatar_label)

        self.avatar_input = QLineEdit()
        self.avatar_input.setPlaceholderText("예: 桔梗, セレスティア, マヌカ")
        self.avatar_input.returnPressed.connect(self.on_search)
        input_layout.addWidget(self.avatar_input, 2)

        # 인기 아바타 콤보박스
        popular_label = QLabel("인기 아바타:")
        popular_label.setFont(QFont("맑은 고딕", 10))
        input_layout.addWidget(popular_label)

        self.popular_combo = QComboBox()
        self.popular_combo.addItem("직접 입력")
        for avatar in self.scraper.get_popular_avatars():
            self.popular_combo.addItem(avatar)
        self.popular_combo.currentTextChanged.connect(self.on_popular_selected)
        input_layout.addWidget(self.popular_combo, 1)

        search_layout.addLayout(input_layout)

        # 필터 및 검색 버튼 행
        filter_layout = QHBoxLayout()

        # 카테고리 필터
        category_label = QLabel("카테고리:")
        category_label.setFont(QFont("맑은 고딕", 10))
        filter_layout.addWidget(category_label)

        self.category_combo = QComboBox()
        for category in self.scraper.CATEGORIES.keys():
            self.category_combo.addItem(category)
        filter_layout.addWidget(self.category_combo)

        filter_layout.addStretch()

        # 검색 버튼
        self.search_button = QPushButton("🔍 검색")
        self.search_button.setMinimumWidth(100)
        self.search_button.clicked.connect(self.on_search)
        filter_layout.addWidget(self.search_button)

        search_layout.addLayout(filter_layout)
        main_layout.addWidget(search_frame)

        # 진행 상태 바
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # 무한 로딩 애니메이션
        self.progress_bar.setVisible(False)
        self.progress_bar.setMaximumHeight(5)
        main_layout.addWidget(self.progress_bar)

        # 결과 상태 레이블
        self.status_label = QLabel("아바타 이름을 입력하고 검색 버튼을 클릭하세요.")
        self.status_label.setFont(QFont("맑은 고딕", 10))
        self.status_label.setStyleSheet("color: #666;")
        main_layout.addWidget(self.status_label)

        # 검색 결과 스크롤 영역
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("QScrollArea { border: none; }")

        self.results_widget = QWidget()
        self.results_layout = QVBoxLayout(self.results_widget)
        self.results_layout.setSpacing(10)
        self.results_layout.addStretch()

        scroll_area.setWidget(self.results_widget)
        main_layout.addWidget(scroll_area, 1)

        # 도움말
        help_label = QLabel("💡 팁: 상품 카드를 클릭하면 Booth.pm 페이지로 이동합니다.")
        help_label.setFont(QFont("맑은 고딕", 9))
        help_label.setStyleSheet("color: #999;")
        help_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(help_label)

    def on_popular_selected(self, text: str):
        """인기 아바타 선택 시"""
        if text != "직접 입력":
            # 괄호 안의 한글 이름 제거하고 일본어 이름만 추출
            avatar_name = text.split(" (")[0]
            self.avatar_input.setText(avatar_name)

    def on_search(self):
        """검색 실행"""
        avatar_name = self.avatar_input.text().strip()
        if not avatar_name:
            QMessageBox.warning(self, "알림", "아바타 이름을 입력해주세요.")
            return

        # UI 상태 변경
        self.search_button.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.status_label.setText(f"'{avatar_name}' 대응 의상 검색 중...")

        # 기존 결과 제거
        self.clear_results()

        # 백그라운드 검색 시작
        category = self.category_combo.currentText()
        self.search_worker = SearchWorker(self.scraper, avatar_name, category)
        self.search_worker.finished.connect(self.on_search_finished)
        self.search_worker.error.connect(self.on_search_error)
        self.search_worker.start()

    def on_search_finished(self, items: List[BoothItem]):
        """검색 완료 콜백"""
        self.search_button.setEnabled(True)
        self.progress_bar.setVisible(False)

        if not items:
            self.status_label.setText("검색 결과가 없습니다. 다른 검색어를 시도해보세요.")
            return

        self.status_label.setText(f"검색 결과: {len(items)}개의 상품을 찾았습니다.")

        # 결과 표시
        for item in items:
            card = ItemCard(item)
            self.item_cards.append(card)
            # stretch 위에 삽입
            self.results_layout.insertWidget(self.results_layout.count() - 1, card)

    def on_search_error(self, error_msg: str):
        """검색 오류 콜백"""
        self.search_button.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.status_label.setText(f"검색 오류: {error_msg}")
        QMessageBox.critical(self, "오류", f"검색 중 오류가 발생했습니다:\n{error_msg}")

    def clear_results(self):
        """검색 결과 초기화"""
        for card in self.item_cards:
            card.deleteLater()
        self.item_cards.clear()


def run_app():
    """애플리케이션 실행"""
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # 폰트 설정
    font = QFont("맑은 고딕", 10)
    app.setFont(font)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    run_app()
