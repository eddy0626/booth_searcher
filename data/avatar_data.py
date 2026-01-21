"""
아바타 데이터 로더

외부 JSON 파일에서 인기 아바타 정보를 로드합니다.
"""

import json
from dataclasses import dataclass, field
from typing import List, Optional, Dict
from pathlib import Path

from utils.paths import get_data_dir
from utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class AvatarData:
    """아바타 정보"""

    name_jp: str  # 일본어 이름 (검색용)
    name_kr: str  # 한국어 이름 (표시용)
    name_en: str = ""  # 영어 이름
    aliases: List[str] = field(default_factory=list)  # 별칭
    creator: str = ""  # 제작자
    booth_id: str = ""  # Booth 샵 ID

    @property
    def display_name(self) -> str:
        """표시용 이름 (일본어 + 한국어)"""
        return f"{self.name_jp} ({self.name_kr})"

    @property
    def search_name(self) -> str:
        """검색용 이름 (일본어)"""
        return self.name_jp

    def matches(self, query: str) -> bool:
        """검색어와 일치하는지 확인"""
        query_lower = query.lower()
        return (
            query_lower in self.name_jp.lower()
            or query_lower in self.name_kr.lower()
            or query_lower in self.name_en.lower()
            or any(query_lower in alias.lower() for alias in self.aliases)
        )

    @classmethod
    def from_dict(cls, data: dict) -> "AvatarData":
        """딕셔너리에서 생성"""
        return cls(
            name_jp=data.get("name_jp", ""),
            name_kr=data.get("name_kr", ""),
            name_en=data.get("name_en", ""),
            aliases=data.get("aliases", []),
            creator=data.get("creator", ""),
            booth_id=data.get("booth_id", ""),
        )


def _get_bundled_data_path() -> Path:
    """번들된 데이터 파일 경로"""
    # 패키지 내 data 디렉토리
    return Path(__file__).parent / "popular_avatars.json"


def _get_user_data_path() -> Path:
    """사용자 데이터 파일 경로"""
    return get_data_dir() / "popular_avatars.json"


def load_avatars() -> List[AvatarData]:
    """
    인기 아바타 목록 로드

    우선순위:
    1. 사용자 데이터 디렉토리
    2. 번들된 데이터 파일

    Returns:
        아바타 목록
    """
    # 사용자 데이터 확인
    user_path = _get_user_data_path()
    if user_path.exists():
        try:
            avatars = _load_from_file(user_path)
            logger.info(f"사용자 아바타 데이터 로드: {len(avatars)}개")
            return avatars
        except Exception as e:
            logger.warning(f"사용자 데이터 로드 실패: {e}")

    # 번들된 데이터
    bundled_path = _get_bundled_data_path()
    if bundled_path.exists():
        try:
            avatars = _load_from_file(bundled_path)
            logger.info(f"번들 아바타 데이터 로드: {len(avatars)}개")
            return avatars
        except Exception as e:
            logger.warning(f"번들 데이터 로드 실패: {e}")

    # 기본값
    logger.warning("아바타 데이터를 찾을 수 없음, 기본값 사용")
    return _get_default_avatars()


def _load_from_file(path: Path) -> List[AvatarData]:
    """파일에서 아바타 데이터 로드"""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    avatars = []
    for item in data.get("avatars", []):
        try:
            avatars.append(AvatarData.from_dict(item))
        except Exception as e:
            logger.warning(f"아바타 파싱 실패: {e}")

    return avatars


def _get_default_avatars() -> List[AvatarData]:
    """기본 아바타 목록 (폴백)"""
    return [
        AvatarData(name_jp="桔梗", name_kr="키쿄"),
        AvatarData(name_jp="セレスティア", name_kr="셀레스티아"),
        AvatarData(name_jp="マヌカ", name_kr="마누카"),
        AvatarData(name_jp="舞夜", name_kr="마이야"),
        AvatarData(name_jp="ルーシュカ", name_kr="루슈카"),
        AvatarData(name_jp="リーファ", name_kr="리파"),
    ]


def get_popular_avatar_names() -> List[str]:
    """
    인기 아바타 표시 이름 목록

    Returns:
        "일본어 (한국어)" 형식의 이름 목록
    """
    avatars = load_avatars()
    return [avatar.display_name for avatar in avatars]


def search_avatars(query: str) -> List[AvatarData]:
    """
    아바타 검색

    Args:
        query: 검색어

    Returns:
        일치하는 아바타 목록
    """
    avatars = load_avatars()
    return [avatar for avatar in avatars if avatar.matches(query)]


def get_avatar_by_name(name: str) -> Optional[AvatarData]:
    """
    이름으로 아바타 찾기

    Args:
        name: 아바타 이름 (일본어/한국어/영어)

    Returns:
        AvatarData 또는 None
    """
    avatars = load_avatars()
    for avatar in avatars:
        if (
            name == avatar.name_jp
            or name == avatar.name_kr
            or name == avatar.name_en
            or name in avatar.aliases
        ):
            return avatar
    return None
