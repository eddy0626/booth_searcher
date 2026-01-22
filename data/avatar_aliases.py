"""
아바타 별칭 데이터 로더

사용자 편집 가능한 별칭 파일을 로드합니다.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List

from utils.paths import get_bundled_data_dir, get_user_data_dir
from utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class AvatarAliasEntry:
    """아바타 별칭 엔트리"""

    canonical: str
    variants: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> "AvatarAliasEntry":
        return cls(
            canonical=data.get("canonical", ""),
            variants=data.get("variants", []) or [],
        )


def _get_bundled_alias_path() -> Path:
    return get_bundled_data_dir() / "avatar_aliases.json"


def _get_user_alias_path() -> Path:
    return get_user_data_dir() / "avatar_aliases.json"


def _load_from_file(path: Path) -> List[AvatarAliasEntry]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    entries: List[AvatarAliasEntry] = []
    for item in data.get("aliases", []):
        try:
            entry = AvatarAliasEntry.from_dict(item)
            if entry.canonical:
                entries.append(entry)
        except Exception as e:
            logger.warning(f"별칭 파싱 실패: {e}")

    return entries


def load_avatar_aliases() -> List[AvatarAliasEntry]:
    """
    아바타 별칭 목록 로드

    우선순위:
    1. 사용자 데이터 디렉토리
    2. 번들된 데이터 파일
    """
    user_path = _get_user_alias_path()
    if user_path.exists():
        try:
            entries = _load_from_file(user_path)
            logger.info(f"사용자 별칭 데이터 로드: {len(entries)}개")
            return entries
        except Exception as e:
            logger.warning(f"사용자 별칭 데이터 로드 실패: {e}")

    bundled_path = _get_bundled_alias_path()
    if bundled_path.exists():
        try:
            entries = _load_from_file(bundled_path)
            logger.info(f"번들 별칭 데이터 로드: {len(entries)}개")
            return entries
        except Exception as e:
            logger.warning(f"번들 별칭 데이터 로드 실패: {e}")

    logger.info("별칭 데이터를 찾을 수 없음")
    return []


def build_alias_map(normalize_fn) -> Dict[str, str]:
    """
    별칭 -> canonical 매핑 생성

    Args:
        normalize_fn: 정규화 함수
    """
    entries = load_avatar_aliases()
    alias_map: Dict[str, str] = {}

    for entry in entries:
        canonical = entry.canonical.strip()
        if not canonical:
            continue

        all_variants = [canonical] + list(entry.variants)
        for variant in all_variants:
            key = normalize_fn(variant)
            if not key:
                continue
            if key not in alias_map:
                alias_map[key] = canonical

    return alias_map
