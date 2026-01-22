"""
검색 결과 관련성 점수 계산
"""

from __future__ import annotations

import re
from typing import Iterable, List, Tuple, Dict

from utils.query_normalization import normalize_query

_WHITESPACE_RE = re.compile(r"\s+")


def tokenize_query(text: str) -> List[str]:
    normalized = normalize_query(text)
    if not normalized:
        return []
    return [token for token in _WHITESPACE_RE.split(normalized) if token]


def compute_relevance_score(
    title: str,
    shop_name: str,
    avatar_name: str,
    positive_keywords: Iterable[str],
    negative_keywords: Iterable[str],
    unrelated_keywords: Iterable[str],
    score_weights: Dict[str, float],
    recent_clicked_titles: Iterable[str] | None = None,
    recent_clicked_shops: Iterable[str] | None = None,
) -> Tuple[float, Tuple[str, ...]]:
    """
    관련성 점수 계산

    Returns:
        (score, matched_tokens)
    """
    title_norm = normalize_query(title).lower()
    shop_norm = normalize_query(shop_name).lower()
    avatar_norm = normalize_query(avatar_name).lower()

    tokens = tokenize_query(avatar_name)
    matched_tokens: List[str] = []

    score = 0.0

    if avatar_norm and avatar_norm in title_norm:
        score += score_weights.get("exact_title_match", 0)
        matched_tokens.append(avatar_norm)

    for token in tokens:
        token_norm = token.lower()
        if token_norm and token_norm in title_norm:
            score += score_weights.get("token_match", 0)
            matched_tokens.append(token_norm)

    for keyword in positive_keywords:
        key_norm = normalize_query(keyword).lower()
        if key_norm and key_norm in title_norm:
            score += score_weights.get("positive_keyword", 0)

    for keyword in negative_keywords:
        key_norm = normalize_query(keyword).lower()
        if key_norm and key_norm in title_norm:
            score += score_weights.get("negative_keyword", 0)

    for keyword in unrelated_keywords:
        key_norm = normalize_query(keyword).lower()
        if key_norm and (key_norm in title_norm or key_norm in shop_norm):
            score += score_weights.get("unrelated_keyword", 0)

    if recent_clicked_titles:
        for clicked in recent_clicked_titles:
            clicked_norm = normalize_query(clicked).lower()
            if clicked_norm and clicked_norm in title_norm:
                score += score_weights.get("recent_click_title", 0)
                break

    if recent_clicked_shops:
        for clicked in recent_clicked_shops:
            clicked_norm = normalize_query(clicked).lower()
            if clicked_norm and clicked_norm in shop_norm:
                score += score_weights.get("recent_click_shop", 0)
                break

    return score, tuple(dict.fromkeys(matched_tokens))


def score_to_label(score: float, buckets: Dict[str, float]) -> str:
    strong = buckets.get("strong", 60)
    medium = buckets.get("medium", 30)

    if score >= strong:
        return "매칭 강함"
    if score >= medium:
        return "매칭 보통"
    return "매칭 약함"
