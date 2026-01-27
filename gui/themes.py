"""
테마 시스템

다크/라이트 모드 지원
"""

from enum import Enum
from dataclasses import dataclass
from typing import Dict


class ThemeMode(Enum):
    """테마 모드"""
    LIGHT = "light"
    DARK = "dark"
    SYSTEM = "system"


@dataclass
class ThemeColors:
    """테마 색상 정의"""
    background: str
    surface: str
    primary: str
    primary_hover: str
    primary_pressed: str
    text: str
    text_secondary: str
    border: str
    input_bg: str
    input_border: str
    input_focus: str
    error: str
    success: str
    card_bg: str
    card_border: str


# 라이트 테마
LIGHT_THEME = ThemeColors(
    background="#f5f5f5",
    surface="#ffffff",
    primary="#ff6b6b",
    primary_hover="#ff5252",
    primary_pressed="#e04545",
    text="#333333",
    text_secondary="#666666",
    border="#e0e0e0",
    input_bg="#ffffff",
    input_border="#dddddd",
    input_focus="#ff6b6b",
    error="#e53935",
    success="#43a047",
    card_bg="#ffffff",
    card_border="#e8e8e8",
)

# 다크 테마
DARK_THEME = ThemeColors(
    background="#1a1a2e",
    surface="#16213e",
    primary="#ff6b6b",
    primary_hover="#ff8585",
    primary_pressed="#ff5252",
    text="#eaeaea",
    text_secondary="#a0a0a0",
    border="#2a2a4a",
    input_bg="#0f0f23",
    input_border="#3a3a5a",
    input_focus="#ff6b6b",
    error="#ef5350",
    success="#66bb6a",
    card_bg="#16213e",
    card_border="#2a2a4a",
)


def get_theme(mode: ThemeMode) -> ThemeColors:
    """테마 색상 반환"""
    if mode == ThemeMode.DARK:
        return DARK_THEME
    return LIGHT_THEME


def generate_stylesheet(theme: ThemeColors) -> str:
    """테마 기반 스타일시트 생성"""
    return f"""
        QMainWindow {{
            background-color: {theme.background};
        }}

        QWidget {{
            color: {theme.text};
        }}

        #titleLabel {{
            font-size: 20px;
            font-weight: bold;
            color: {theme.text};
            padding: 10px;
        }}

        #searchFrame {{
            background-color: {theme.surface};
            border-radius: 10px;
            border: 1px solid {theme.border};
        }}

        QLineEdit {{
            padding: 10px;
            border: 2px solid {theme.input_border};
            border-radius: 6px;
            font-size: 14px;
            background-color: {theme.input_bg};
            color: {theme.text};
        }}
        QLineEdit:focus {{
            border-color: {theme.input_focus};
        }}

        QComboBox {{
            padding: 8px;
            border: 2px solid {theme.input_border};
            border-radius: 6px;
            font-size: 14px;
            background-color: {theme.input_bg};
            color: {theme.text};
        }}
        QComboBox:focus {{
            border-color: {theme.input_focus};
        }}
        QComboBox QAbstractItemView {{
            background-color: {theme.surface};
            color: {theme.text};
            selection-background-color: {theme.primary};
        }}
        QComboBox::drop-down {{
            border: none;
        }}

        #searchButton {{
            padding: 10px 20px;
            background-color: {theme.primary};
            color: white;
            border: none;
            border-radius: 6px;
            font-size: 14px;
            font-weight: bold;
        }}
        #searchButton:hover {{
            background-color: {theme.primary_hover};
        }}
        #searchButton:pressed {{
            background-color: {theme.primary_pressed};
        }}
        #searchButton:disabled {{
            background-color: {theme.border};
        }}

        #cancelButton {{
            padding: 10px 15px;
            background-color: {theme.text_secondary};
            color: white;
            border: none;
            border-radius: 6px;
            font-size: 14px;
        }}
        #cancelButton:hover {{
            background-color: {theme.text};
        }}

        #statusLabel {{
            color: {theme.text_secondary};
            font-size: 13px;
            padding: 5px;
        }}

        QProgressBar {{
            border: none;
            background-color: {theme.border};
        }}
        QProgressBar::chunk {{
            background-color: {theme.primary};
        }}

        QScrollArea {{
            background-color: {theme.background};
            border: none;
        }}

        QScrollBar:vertical {{
            background-color: {theme.background};
            width: 12px;
            border-radius: 6px;
        }}
        QScrollBar::handle:vertical {{
            background-color: {theme.border};
            border-radius: 6px;
            min-height: 30px;
        }}
        QScrollBar::handle:vertical:hover {{
            background-color: {theme.text_secondary};
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0;
        }}

        QLabel {{
            color: {theme.text};
        }}

        QPushButton {{
            padding: 8px 16px;
            background-color: {theme.surface};
            color: {theme.text};
            border: 1px solid {theme.border};
            border-radius: 6px;
        }}
        QPushButton:hover {{
            background-color: {theme.border};
        }}

        QCheckBox {{
            color: {theme.text};
        }}
        QCheckBox::indicator {{
            width: 18px;
            height: 18px;
            border: 2px solid {theme.input_border};
            border-radius: 4px;
            background-color: {theme.input_bg};
        }}
        QCheckBox::indicator:checked {{
            background-color: {theme.primary};
            border-color: {theme.primary};
        }}

        QStatusBar {{
            background-color: {theme.surface};
            color: {theme.text_secondary};
        }}

        QMessageBox {{
            background-color: {theme.surface};
        }}
        QMessageBox QLabel {{
            color: {theme.text};
        }}

        /* 필터 패널 */
        #filterPanel {{
            background-color: {theme.surface};
            border-radius: 8px;
            border: 1px solid {theme.border};
            padding: 10px;
        }}

        /* 아이템 카드 */
        .ItemCard {{
            background-color: {theme.card_bg};
            border: 1px solid {theme.card_border};
            border-radius: 8px;
        }}
        .ItemCard:hover {{
            border-color: {theme.primary};
        }}

        /* 즐겨찾기 버튼 */
        #favoriteButton {{
            background-color: transparent;
            border: none;
            font-size: 18px;
        }}
        #favoriteButton:hover {{
            background-color: {theme.border};
            border-radius: 4px;
        }}

        /* 내보내기 버튼 */
        #exportButton {{
            padding: 8px 16px;
            background-color: {theme.surface};
            color: {theme.text};
            border: 1px solid {theme.border};
            border-radius: 6px;
        }}
        #exportButton:hover {{
            background-color: {theme.primary};
            color: white;
            border-color: {theme.primary};
        }}

        /* 테마 토글 버튼 */
        #themeButton {{
            padding: 8px 12px;
            background-color: {theme.surface};
            color: {theme.text};
            border: 1px solid {theme.border};
            border-radius: 6px;
            font-size: 16px;
        }}
        #themeButton:hover {{
            background-color: {theme.border};
        }}
        #exportButton:disabled {{
            background-color: {theme.border};
            color: {theme.text_secondary};
        }}
    """


def is_system_dark_mode() -> bool:
    """시스템이 다크 모드인지 확인 (Windows)"""
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
        )
        value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
        winreg.CloseKey(key)
        return value == 0
    except Exception:
        return False
