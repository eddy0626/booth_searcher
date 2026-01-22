"""
검색 관련성 설정 로더
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

from utils.paths import get_bundled_data_dir, get_user_data_dir
from utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class RelevanceConfig:
    positive_keywords: List[str]
    negative_keywords: List[str]
    unrelated_keywords: List[str]
    score: Dict[str, float]
    buckets: Dict[str, float]


_DEFAULT_CONFIG = RelevanceConfig(
    positive_keywords=["対応", "専用", "for", "対応品", "対応衣装"],
    negative_keywords=["汎用", "素体", "アバター不問", "generic"],
    unrelated_keywords=["unity", "blender", "shader", "texture"],
    score={
        "exact_title_match": 50,
        "token_match": 10,
        "positive_keyword": 5,
        "negative_keyword": -15,
        "unrelated_keyword": -8,
        "recent_click_title": 6,
        "recent_click_shop": 4,
    },
    buckets={
        "strong": 60,
        "medium": 30,
    },
)


def _get_bundled_config_path() -> Path:
    return get_bundled_data_dir() / "relevance_config.json"


def _get_user_config_path() -> Path:
    return get_user_data_dir() / "relevance_config.json"


def _load_from_file(path: Path) -> RelevanceConfig:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return RelevanceConfig(
        positive_keywords=list(data.get("positive_keywords", [])),
        negative_keywords=list(data.get("negative_keywords", [])),
        unrelated_keywords=list(data.get("unrelated_keywords", [])),
        score=dict(data.get("score", {})),
        buckets=dict(data.get("buckets", {})),
    )


def load_relevance_config() -> RelevanceConfig:
    user_path = _get_user_config_path()
    if user_path.exists():
        try:
            config = _load_from_file(user_path)
            logger.info("사용자 관련성 설정 로드")
            return _merge_with_default(config)
        except Exception as e:
            logger.warning(f"사용자 관련성 설정 로드 실패: {e}")

    bundled_path = _get_bundled_config_path()
    if bundled_path.exists():
        try:
            config = _load_from_file(bundled_path)
            logger.info("번들 관련성 설정 로드")
            return _merge_with_default(config)
        except Exception as e:
            logger.warning(f"번들 관련성 설정 로드 실패: {e}")

    return _DEFAULT_CONFIG


def _merge_with_default(config: RelevanceConfig) -> RelevanceConfig:
    return RelevanceConfig(
        positive_keywords=config.positive_keywords or _DEFAULT_CONFIG.positive_keywords,
        negative_keywords=config.negative_keywords or _DEFAULT_CONFIG.negative_keywords,
        unrelated_keywords=config.unrelated_keywords or _DEFAULT_CONFIG.unrelated_keywords,
        score={**_DEFAULT_CONFIG.score, **(config.score or {})},
        buckets={**_DEFAULT_CONFIG.buckets, **(config.buckets or {})},
    )
