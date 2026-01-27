"""
에러 다이얼로그

사용자 친화적인 에러 메시지를 표시합니다.
"""

from typing import Optional
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QWidget,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from utils.logging import get_logger

logger = get_logger(__name__)


class ErrorDialog(QDialog):
    """
    에러 다이얼로그

    사용법:
        dialog = ErrorDialog(
            title="연결 오류",
            message="Booth에 연결할 수 없습니다.",
            details="TimeoutError: Connection timed out",
            parent=self,
        )
        dialog.exec()

        # 또는 간단하게
        show_error("연결할 수 없습니다", parent=self)
    """

    def __init__(
        self,
        title: str = "오류",
        message: str = "오류가 발생했습니다.",
        details: Optional[str] = None,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)

        self.setWindowTitle(title)
        self.setMinimumWidth(400)
        self.setModal(True)

        self._setup_ui(message, details)

    def _setup_ui(self, message: str, details: Optional[str]) -> None:
        """UI 초기화"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # 아이콘 + 메시지
        msg_layout = QHBoxLayout()

        # 에러 아이콘
        icon_label = QLabel("!")
        icon_label.setStyleSheet("""
            QLabel {
                background-color: #ff6b6b;
                color: white;
                font-size: 18px;
                font-weight: bold;
                border-radius: 15px;
                min-width: 30px;
                min-height: 30px;
                max-width: 30px;
                max-height: 30px;
            }
        """)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        msg_layout.addWidget(icon_label)

        # 메시지
        msg_label = QLabel(message)
        msg_label.setWordWrap(True)
        msg_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                color: #333;
                padding-left: 10px;
            }
        """)
        msg_layout.addWidget(msg_label, 1)

        layout.addLayout(msg_layout)

        # 상세 정보 (접을 수 있음)
        if details:
            self._details_text = QTextEdit()
            self._details_text.setPlainText(details)
            self._details_text.setReadOnly(True)
            self._details_text.setMaximumHeight(100)
            self._details_text.setStyleSheet("""
                QTextEdit {
                    background-color: #f5f5f5;
                    border: 1px solid #ddd;
                    border-radius: 4px;
                    font-family: Consolas, monospace;
                    font-size: 11px;
                    color: #666;
                }
            """)
            self._details_text.hide()
            layout.addWidget(self._details_text)

            # 상세 보기 버튼
            self._toggle_btn = QPushButton("상세 정보 보기")
            self._toggle_btn.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    border: none;
                    color: #666;
                    font-size: 12px;
                }
                QPushButton:hover {
                    color: #333;
                }
            """)
            self._toggle_btn.clicked.connect(self._toggle_details)
            layout.addWidget(self._toggle_btn, alignment=Qt.AlignmentFlag.AlignLeft)

        # 버튼
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        ok_btn = QPushButton("확인")
        ok_btn.setDefault(True)
        ok_btn.setMinimumWidth(80)
        ok_btn.setStyleSheet("""
            QPushButton {
                background-color: #ff6b6b;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #ff5252;
            }
        """)
        ok_btn.clicked.connect(self.accept)
        btn_layout.addWidget(ok_btn)

        layout.addLayout(btn_layout)

    def _toggle_details(self) -> None:
        """상세 정보 토글"""
        if self._details_text.isVisible():
            self._details_text.hide()
            self._toggle_btn.setText("상세 정보 보기")
        else:
            self._details_text.show()
            self._toggle_btn.setText("상세 정보 숨기기")

        self.adjustSize()


def show_error(
    message: str,
    title: str = "오류",
    details: Optional[str] = None,
    parent: Optional[QWidget] = None,
) -> None:
    """
    에러 다이얼로그 표시 (편의 함수)

    Args:
        message: 에러 메시지
        title: 다이얼로그 제목
        details: 상세 정보
        parent: 부모 위젯
    """
    dialog = ErrorDialog(title, message, details, parent)
    dialog.exec()
