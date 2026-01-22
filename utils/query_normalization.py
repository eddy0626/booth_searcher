"""
검색어 정규화 유틸리티
"""

from __future__ import annotations

import re
import unicodedata
from typing import List

# 공백/구분자 정규화용 정규식
_WHITESPACE_RE = re.compile(r"\s+")
_MULTI_SEPARATOR_RE = re.compile(r"[,;/|\n]+")

# 일본어/전각 구두점 정규화
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


def normalize_query(text: str) -> str:
    """
    검색어 정규화

    - 전각/반각, 호환 문자 정규화 (NFKC)
    - 공백 정리
    - 일본어 구두점 변환
    """
    if text is None:
        return ""

    normalized = unicodedata.normalize("NFKC", text)
    if not normalized:
        return ""

    normalized = "".join(_PUNCTUATION_MAP.get(ch, ch) for ch in normalized)
    normalized = _WHITESPACE_RE.sub(" ", normalized).strip()
    return normalized


def split_multi_query(text: str) -> List[str]:
    """
    여러 검색어 입력 분리

    구분자: 줄바꿈, 콤마, 세미콜론, 슬래시, 파이프
    """
    if text is None:
        return []

    parts = _MULTI_SEPARATOR_RE.split(text)
    return [part.strip() for part in parts if part and part.strip()]


def remove_spaces(text: str) -> str:
    """공백 제거"""
    if text is None:
        return ""
    return _WHITESPACE_RE.sub("", text)
