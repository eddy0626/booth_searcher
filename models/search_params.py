"""
검색 파라미터 데이터 모델
"""

from dataclasses import dataclass, field
from typing import Optional
from enum import Enum
import hashlib


class SortOrder(Enum):
    """정렬 순서"""

    RELEVANCE = "relevance"  # 관련성 (기본)
    NEWEST = "new"  # 최신순
    POPULAR = "wish_count"  # 인기순 (좋아요 수)
    PRICE_ASC = "price_asc"  # 가격 낮은순
    PRICE_DESC = "price_desc"  # 가격 높은순

    @property
    def display_name(self) -> str:
        """표시용 이름"""
        names = {
            SortOrder.RELEVANCE: "관련성",
            SortOrder.NEWEST: "최신순",
            SortOrder.POPULAR: "인기순",
            SortOrder.PRICE_ASC: "가격 낮은순",
            SortOrder.PRICE_DESC: "가격 높은순",
        }
        return names.get(self, "관련성")

    @property
    def booth_param(self) -> Optional[str]:
        """Booth API 파라미터 값"""
        params = {
            SortOrder.RELEVANCE: None,  # 기본값
            SortOrder.NEWEST: "new",
            SortOrder.POPULAR: "wish_count",
            SortOrder.PRICE_ASC: "price",
            SortOrder.PRICE_DESC: "price",
        }
        return params.get(self)


@dataclass
class PriceRange:
    """가격 범위 필터"""

    min_price: Optional[int] = None
    max_price: Optional[int] = None
    free_only: bool = False

    def is_empty(self) -> bool:
        """필터가 비어있는지 확인"""
        return self.min_price is None and self.max_price is None and not self.free_only

    def to_dict(self) -> dict:
        """딕셔너리로 변환"""
        return {
            "min_price": self.min_price,
            "max_price": self.max_price,
            "free_only": self.free_only,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PriceRange":
        """딕셔너리에서 생성"""
        return cls(
            min_price=data.get("min_price"),
            max_price=data.get("max_price"),
            free_only=data.get("free_only", False),
        )

    def __str__(self) -> str:
        if self.free_only:
            return "무료만"
        parts = []
        if self.min_price is not None:
            parts.append(f"¥{self.min_price:,}~")
        if self.max_price is not None:
            parts.append(f"~¥{self.max_price:,}")
        return " ".join(parts) if parts else "전체"


@dataclass
class SearchParams:
    """
    검색 파라미터

    검색 조건을 담는 데이터 클래스
    캐시 키 생성을 위해 해시 가능하도록 설계
    """

    avatar_name: str
    category: str = "전체"
    sort: SortOrder = SortOrder.RELEVANCE
    price_range: Optional[PriceRange] = None
    page: int = 1
    per_page: int = 24
    raw_query: str = ""
    normalize_enabled: Optional[bool] = None
    alias_enabled: bool = True
    fallback_enabled: bool = True
    fallback_min_results: int = 5
    resolved_query: Optional[str] = None
    used_strategy: Optional[str] = None
    normalization_enabled: bool = True  # backward compat
    allow_multi: bool = False
    verify_mode: bool = False
    verify_top_n: int = 10

    def __post_init__(self):
        """초기화 후 유효성 검사"""
        self.avatar_name = self.avatar_name.strip()
        if not self.raw_query:
            self.raw_query = self.avatar_name
        if self.normalize_enabled is None:
            self.normalize_enabled = self.normalization_enabled
        self.normalization_enabled = bool(self.normalize_enabled)
        if self.page < 1:
            self.page = 1
        if self.per_page < 1:
            self.per_page = 24
        if self.fallback_min_results < 1:
            self.fallback_min_results = 1

    def cache_key(self) -> str:
        """
        캐시 키 생성

        Returns:
            고유한 캐시 키 문자열
        """
        price_str = ""
        if self.price_range:
            price_str = f"{self.price_range.min_price}:{self.price_range.max_price}:{self.price_range.free_only}"

        key_parts = [
            self.avatar_name,
            self.category,
            self.sort.value,
            price_str,
            str(self.page),
        ]
        key_string = ":".join(key_parts)

        # 해시로 변환 (긴 키 방지)
        return hashlib.sha256(key_string.encode()).hexdigest()[:16]

    def to_dict(self) -> dict:
        """딕셔너리로 변환"""
        return {
            "avatar_name": self.avatar_name,
            "category": self.category,
            "sort": self.sort.value,
            "price_range": self.price_range.to_dict() if self.price_range else None,
            "page": self.page,
            "per_page": self.per_page,
            "raw_query": self.raw_query,
            "normalize_enabled": self.normalize_enabled,
            "alias_enabled": self.alias_enabled,
            "fallback_enabled": self.fallback_enabled,
            "fallback_min_results": self.fallback_min_results,
            "resolved_query": self.resolved_query,
            "used_strategy": self.used_strategy,
            "normalization_enabled": self.normalization_enabled,
            "allow_multi": self.allow_multi,
            "verify_mode": self.verify_mode,
            "verify_top_n": self.verify_top_n,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SearchParams":
        """딕셔너리에서 생성"""
        sort = SortOrder.RELEVANCE
        if data.get("sort"):
            try:
                sort = SortOrder(data["sort"])
            except ValueError:
                pass

        price_range = None
        if data.get("price_range"):
            price_range = PriceRange.from_dict(data["price_range"])

        normalize_enabled = data.get(
            "normalize_enabled",
            data.get("normalization_enabled", True),
        )

        return cls(
            avatar_name=data.get("avatar_name", ""),
            category=data.get("category", "전체"),
            sort=sort,
            price_range=price_range,
            page=data.get("page", 1),
            per_page=data.get("per_page", 24),
            raw_query=data.get("raw_query", ""),
            normalize_enabled=normalize_enabled,
            alias_enabled=data.get("alias_enabled", True),
            fallback_enabled=data.get("fallback_enabled", True),
            fallback_min_results=data.get("fallback_min_results", 5),
            resolved_query=data.get("resolved_query"),
            used_strategy=data.get("used_strategy"),
            normalization_enabled=data.get("normalization_enabled", normalize_enabled),
            allow_multi=data.get("allow_multi", False),
            verify_mode=data.get("verify_mode", False),
            verify_top_n=data.get("verify_top_n", 10),
        )

    def with_page(self, page: int) -> "SearchParams":
        """새 페이지 번호로 복사본 생성"""
        return SearchParams(
            avatar_name=self.avatar_name,
            category=self.category,
            sort=self.sort,
            price_range=self.price_range,
            page=page,
            per_page=self.per_page,
            raw_query=self.raw_query,
            normalize_enabled=self.normalize_enabled,
            alias_enabled=self.alias_enabled,
            fallback_enabled=self.fallback_enabled,
            fallback_min_results=self.fallback_min_results,
            resolved_query=self.resolved_query,
            used_strategy=self.used_strategy,
            normalization_enabled=self.normalization_enabled,
            allow_multi=self.allow_multi,
            verify_mode=self.verify_mode,
            verify_top_n=self.verify_top_n,
        )

    def with_avatar_name(self, avatar_name: str) -> "SearchParams":
        """새 아바타 이름으로 복사본 생성"""
        return SearchParams(
            avatar_name=avatar_name,
            category=self.category,
            sort=self.sort,
            price_range=self.price_range,
            page=self.page,
            per_page=self.per_page,
            raw_query=self.raw_query,
            normalize_enabled=self.normalize_enabled,
            alias_enabled=self.alias_enabled,
            fallback_enabled=self.fallback_enabled,
            fallback_min_results=self.fallback_min_results,
            resolved_query=self.resolved_query,
            used_strategy=self.used_strategy,
            normalization_enabled=self.normalization_enabled,
            allow_multi=self.allow_multi,
            verify_mode=self.verify_mode,
            verify_top_n=self.verify_top_n,
        )

    def get_search_keyword(self) -> str:
        """Booth 검색용 키워드 생성"""
        return f"{self.avatar_name} 対応"

    def __str__(self) -> str:
        return f"SearchParams(avatar={self.avatar_name!r}, category={self.category}, page={self.page})"

    def __repr__(self) -> str:
        return str(self)
