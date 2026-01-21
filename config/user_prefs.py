"""
사용자 환경설정 관리

JSON 파일로 사용자 설정을 저장/로드합니다.
"""

import json
from dataclasses import dataclass, field, asdict
from typing import Optional, List
from pathlib import Path

from utils.paths import get_config_dir
from utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class WindowState:
    """창 상태"""

    width: int = 900
    height: int = 700
    x: Optional[int] = None
    y: Optional[int] = None
    maximized: bool = False


@dataclass
class SearchPrefs:
    """검색 설정"""

    last_avatar: str = ""
    last_category: str = "전체"
    recent_searches: List[str] = field(default_factory=list)
    max_recent: int = 10


@dataclass
class DisplayPrefs:
    """표시 설정"""

    sort_order: str = "new"  # new, popular, price_asc, price_desc
    show_free_only: bool = False
    grid_columns: int = 4


@dataclass
class UserPrefs:
    """사용자 환경설정"""

    window: WindowState = field(default_factory=WindowState)
    search: SearchPrefs = field(default_factory=SearchPrefs)
    display: DisplayPrefs = field(default_factory=DisplayPrefs)

    # 메타 정보
    version: str = "1.0.0"

    def to_dict(self) -> dict:
        """딕셔너리로 변환"""
        return {
            "version": self.version,
            "window": asdict(self.window),
            "search": asdict(self.search),
            "display": asdict(self.display),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "UserPrefs":
        """딕셔너리에서 생성"""
        prefs = cls()

        if "window" in data:
            prefs.window = WindowState(**data["window"])

        if "search" in data:
            prefs.search = SearchPrefs(**data["search"])

        if "display" in data:
            prefs.display = DisplayPrefs(**data["display"])

        if "version" in data:
            prefs.version = data["version"]

        return prefs

    def add_recent_search(self, query: str) -> None:
        """최근 검색어 추가"""
        if not query:
            return

        # 기존 항목 제거
        if query in self.search.recent_searches:
            self.search.recent_searches.remove(query)

        # 맨 앞에 추가
        self.search.recent_searches.insert(0, query)

        # 최대 개수 유지
        if len(self.search.recent_searches) > self.search.max_recent:
            self.search.recent_searches = self.search.recent_searches[
                : self.search.max_recent
            ]

    def clear_recent_searches(self) -> None:
        """최근 검색어 삭제"""
        self.search.recent_searches.clear()


class UserPrefsManager:
    """
    사용자 환경설정 관리자

    JSON 파일로 설정을 저장하고 로드합니다.

    사용법:
        manager = UserPrefsManager()
        prefs = manager.load()
        prefs.search.last_avatar = "桔梗"
        manager.save(prefs)
    """

    FILENAME = "user_prefs.json"

    def __init__(self, config_dir: Optional[Path] = None):
        self._config_dir = config_dir or get_config_dir()
        self._prefs_path = self._config_dir / self.FILENAME
        self._prefs: Optional[UserPrefs] = None

    @property
    def prefs_path(self) -> Path:
        """설정 파일 경로"""
        return self._prefs_path

    def load(self) -> UserPrefs:
        """
        설정 로드

        파일이 없거나 오류 시 기본값 반환

        Returns:
            UserPrefs 인스턴스
        """
        if self._prefs is not None:
            return self._prefs

        if not self._prefs_path.exists():
            logger.info("설정 파일 없음, 기본값 사용")
            self._prefs = UserPrefs()
            return self._prefs

        try:
            with open(self._prefs_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._prefs = UserPrefs.from_dict(data)
            logger.info(f"설정 로드: {self._prefs_path}")

        except json.JSONDecodeError as e:
            logger.warning(f"설정 파일 파싱 오류: {e}")
            self._prefs = UserPrefs()

        except Exception as e:
            logger.warning(f"설정 로드 실패: {e}")
            self._prefs = UserPrefs()

        return self._prefs

    def save(self, prefs: Optional[UserPrefs] = None) -> bool:
        """
        설정 저장

        Args:
            prefs: 저장할 설정 (None이면 현재 설정)

        Returns:
            저장 성공 여부
        """
        if prefs is not None:
            self._prefs = prefs
        elif self._prefs is None:
            logger.warning("저장할 설정이 없음")
            return False

        try:
            # 디렉토리 생성
            self._config_dir.mkdir(parents=True, exist_ok=True)

            # JSON 저장
            with open(self._prefs_path, "w", encoding="utf-8") as f:
                json.dump(self._prefs.to_dict(), f, ensure_ascii=False, indent=2)

            logger.debug(f"설정 저장: {self._prefs_path}")
            return True

        except Exception as e:
            logger.error(f"설정 저장 실패: {e}")
            return False

    def reset(self) -> UserPrefs:
        """설정 초기화"""
        self._prefs = UserPrefs()

        # 파일 삭제
        if self._prefs_path.exists():
            try:
                self._prefs_path.unlink()
                logger.info("설정 파일 삭제")
            except Exception as e:
                logger.warning(f"설정 파일 삭제 실패: {e}")

        return self._prefs

    def get(self) -> UserPrefs:
        """현재 설정 반환 (로드 안됐으면 로드)"""
        if self._prefs is None:
            return self.load()
        return self._prefs


# 싱글톤 인스턴스
_manager: Optional[UserPrefsManager] = None


def get_prefs_manager() -> UserPrefsManager:
    """전역 설정 관리자 반환"""
    global _manager
    if _manager is None:
        _manager = UserPrefsManager()
    return _manager


def get_prefs() -> UserPrefs:
    """현재 사용자 설정 반환"""
    return get_prefs_manager().get()


def save_prefs(prefs: Optional[UserPrefs] = None) -> bool:
    """사용자 설정 저장"""
    return get_prefs_manager().save(prefs)


# Aliases for convenience
def load_user_prefs() -> UserPrefs:
    """사용자 설정 로드 (alias)"""
    return get_prefs()


def save_user_prefs(prefs: Optional[UserPrefs] = None) -> bool:
    """사용자 설정 저장 (alias)"""
    return save_prefs(prefs)
