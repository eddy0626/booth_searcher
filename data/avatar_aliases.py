"""
아바타 별칭 데이터 로더

사용자 편집 가능한 별칭 파일을 로드합니다.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

from utils.paths import get_bundled_data_dir, get_user_data_dir
from utils.logging import get_logger

logger = get_logger(__name__)


def _get_bundled_alias_path() -> Path:
    return get_bundled_data_dir() / "avatar_aliases.json"


def _get_user_alias_path() -> Path:
    return get_user_data_dir() / "avatar_aliases.json"


def _load_from_file(path: Path) -> Dict[str, List[str]]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 레거시 포맷 지원: {"aliases": [{"canonical": "...", "variants": []}]}
    if isinstance(data, dict) and "aliases" in data:
        legacy_map: Dict[str, List[str]] = {}
        for item in data.get("aliases", []):
            canonical = str(item.get("canonical", "")).strip()
            variants = item.get("variants", []) or []
            if canonical:
                legacy_map[canonical] = [str(v) for v in variants]
        return legacy_map

    if isinstance(data, dict):
        # 기대 포맷: { "canonical": ["alias1", "alias2"] }
        return {
            str(key): [str(value) for value in (values or [])]
            for key, values in data.items()
            if isinstance(values, list)
        }

    return {}


def load_avatar_aliases() -> Dict[str, List[str]]:
    """
    아바타 별칭 목록 로드

    우선순위:
    1. 사용자 데이터 디렉토리
    2. 번들된 데이터 파일
    """
    user_path = _get_user_alias_path()
    if user_path.exists():
        try:
            data = _load_from_file(user_path)
            logger.info(f"사용자 별칭 데이터 로드: {len(data)}개")
            return data
        except Exception as e:
            logger.warning(f"사용자 별칭 데이터 로드 실패: {e}")

    bundled_path = _get_bundled_alias_path()
    if bundled_path.exists():
        try:
            data = _load_from_file(bundled_path)
            logger.info(f"번들 별칭 데이터 로드: {len(data)}개")
            return data
        except Exception as e:
            logger.warning(f"번들 별칭 데이터 로드 실패: {e}")

    logger.warning("별칭 데이터를 찾을 수 없음")
    return {}


def build_alias_map(normalize_fn) -> Dict[str, str]:
    """
    별칭 -> canonical 매핑 생성

    Args:
        normalize_fn: 정규화 함수
    """
    aliases = load_avatar_aliases()
    alias_map: Dict[str, str] = {}

    for canonical, variants in aliases.items():
        canonical = canonical.strip()
        if not canonical:
            continue

        all_variants = [canonical] + list(variants or [])
        for variant in all_variants:
            key = normalize_fn(variant)
            if not key:
                continue
            if key not in alias_map:
                alias_map[key] = canonical

    return alias_map
