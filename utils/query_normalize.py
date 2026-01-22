"""
검색어 정규화 유틸리티
"""

from __future__ import annotations

import re
import unicodedata
from typing import List

_WHITESPACE_RE = re.compile(r"\s+")
_MULTI_SEPARATOR_RE = re.compile(r"[,;/|\n]+")

_PUNCTUATION_MAP = {
    "・": " ",
    "･": " ",
    "·": " ",
    "•": " ",
    "、": ",",
    "，": ",",
    "｡": ".",
    "。": ".",
    "（": "(",
    "）": ")",
    "［": "[",
    "］": "]",
    "｛": "{",
    "｝": "}",
    "「": '"',
    "」": '"',
    "『": '"',
    "』": '"',
}


def normalize_query(raw: str) -> str:
    """
    검색어 정규화

    - 전각/반각, 호환 문자 정규화 (NFKC)
    - 공백 정리
    - 일본어 구두점 변환
    """
    if raw is None:
        return ""

    normalized = unicodedata.normalize("NFKC", raw)
    if not normalized:
        return ""

    normalized = "".join(_PUNCTUATION_MAP.get(ch, ch) for ch in normalized)
    normalized = _WHITESPACE_RE.sub(" ", normalized).strip()
    return normalized


def parse_multi_query(raw: str) -> List[str]:
    """
    여러 검색어 입력 분리

    구분자: 줄바꿈, 콤마, 세미콜론, 슬래시, 파이프
    """
    if raw is None:
        return []

    parts = _MULTI_SEPARATOR_RE.split(raw)
    cleaned = [part.strip() for part in parts if part and part.strip()]

    seen = set()
    unique: List[str] = []
    for part in cleaned:
        if part and part not in seen:
            seen.add(part)
            unique.append(part)

    return unique


def remove_spaces(text: str) -> str:
    if text is None:
        return ""
    return _WHITESPACE_RE.sub("", text)
