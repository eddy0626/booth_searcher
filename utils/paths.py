"""
플랫폼별 경로 관리 유틸리티

OS별 표준 위치:
- Windows: %APPDATA%/BoothSearcher
- macOS: ~/Library/Application Support/BoothSearcher
- Linux: ~/.local/share/BoothSearcher
"""

from pathlib import Path
import sys
import os
from typing import Optional

# 앱 디렉토리 이름
APP_DIR_NAME = "BoothSearcher"


def get_app_dir() -> Path:
    """
    애플리케이션 루트 디렉토리 (소스코드 또는 실행파일 위치)

    Returns:
        PyInstaller 빌드: 실행 파일 디렉토리
        스크립트 실행: 프로젝트 루트 디렉토리
    """
    if getattr(sys, 'frozen', False):
        # PyInstaller로 빌드된 실행 파일
        return Path(sys.executable).parent
    else:
        # 스크립트로 실행
        return Path(__file__).parent.parent


def get_data_dir() -> Path:
    """
    사용자 데이터 디렉토리 (OS별 표준 위치)

    설정, 캐시, 로그 등 사용자 데이터 저장용

    Returns:
        Windows: %APPDATA%/BoothSearcher
        macOS: ~/Library/Application Support/BoothSearcher
        Linux: ~/.local/share/BoothSearcher
    """
    if sys.platform == "win32":
        # Windows: %APPDATA%
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif sys.platform == "darwin":
        # macOS: ~/Library/Application Support
        base = Path.home() / "Library" / "Application Support"
    else:
        # Linux 및 기타: XDG_DATA_HOME 또는 ~/.local/share
        xdg_data = os.environ.get("XDG_DATA_HOME")
        if xdg_data:
            base = Path(xdg_data)
        else:
            base = Path.home() / ".local" / "share"

    data_dir = base / APP_DIR_NAME
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def get_config_dir() -> Path:
    """
    설정 파일 디렉토리

    Returns:
        {data_dir}/config
    """
    config_dir = get_data_dir() / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def get_cache_dir() -> Path:
    """
    캐시 디렉토리

    Returns:
        {data_dir}/cache
    """
    cache_dir = get_data_dir() / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def get_log_dir() -> Path:
    """
    로그 파일 디렉토리

    Returns:
        {data_dir}/logs
    """
    log_dir = get_data_dir() / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def get_bundled_data_dir() -> Path:
    """
    번들된 데이터 디렉토리 (avatars.json 등 읽기 전용 데이터)

    Returns:
        PyInstaller 빌드: _MEIPASS/data
        스크립트 실행: {app_dir}/data
    """
    if getattr(sys, 'frozen', False):
        # PyInstaller 빌드 시 _MEIPASS에서 데이터 로드
        return Path(sys._MEIPASS) / "data"
    else:
        return get_app_dir() / "data"


def get_user_data_dir() -> Path:
    """
    사용자 커스텀 데이터 디렉토리 (사용자 추가 아바타 목록 등)

    Returns:
        {data_dir}/user_data
    """
    user_data_dir = get_data_dir() / "user_data"
    user_data_dir.mkdir(parents=True, exist_ok=True)
    return user_data_dir


def ensure_dir(path: Path) -> Path:
    """
    디렉토리가 존재하는지 확인하고 없으면 생성

    Args:
        path: 확인할 디렉토리 경로

    Returns:
        생성된/확인된 디렉토리 경로
    """
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_settings_path() -> Path:
    """설정 파일 경로"""
    return get_config_dir() / "settings.json"


def get_log_file_path() -> Path:
    """기본 로그 파일 경로"""
    return get_log_dir() / "app.log"


def get_image_cache_dir() -> Path:
    """이미지 캐시 디렉토리"""
    return ensure_dir(get_cache_dir() / "images")


def get_result_cache_path() -> Path:
    """검색 결과 캐시 DB 경로"""
    return get_cache_dir() / "search_cache.db"
