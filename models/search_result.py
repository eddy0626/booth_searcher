"""
검색 결과 데이터 모델
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Iterator

from .booth_item import BoothItem


@dataclass
class SearchResult:
    """
    검색 결과 컨테이너

    검색 결과와 페이지네이션 정보를 담는 데이터 클래스

    Attributes:
        items: 검색된 상품 목록
        total_count: 전체 결과 수
        current_page: 현재 페이지 번호
        total_pages: 전체 페이지 수
        has_next: 다음 페이지 존재 여부
        query: 원본 검색어
        cached: 캐시에서 로드 여부
        cache_age_seconds: 캐시 경과 시간 (초)
    """

    items: List[BoothItem]
    total_count: int
    current_page: int
    total_pages: int
    has_next: bool
    query: str
    cached: bool = False
    cache_age_seconds: Optional[int] = None
    raw_query: str = ""
    resolved_query: str = ""
    attempt_label: str = "A"
    attempt_description: str = ""
    correction_applied: bool = False
    used_strategy: str = "original"
    attempts_count: int = 1

    @property
    def is_empty(self) -> bool:
        """결과가 비어있는지 확인"""
        return len(self.items) == 0

    @property
    def count(self) -> int:
        """현재 페이지 결과 수"""
        return len(self.items)

    @property
    def has_previous(self) -> bool:
        """이전 페이지 존재 여부"""
        return self.current_page > 1

    def __iter__(self) -> Iterator[BoothItem]:
        """아이템 순회"""
        return iter(self.items)

    def __len__(self) -> int:
        """현재 페이지 아이템 수"""
        return len(self.items)

    def __getitem__(self, index: int) -> BoothItem:
        """인덱스로 아이템 접근"""
        return self.items[index]

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환 (캐시 저장용)"""
        return {
            "items": [item.to_dict() for item in self.items],
            "total_count": self.total_count,
            "current_page": self.current_page,
            "total_pages": self.total_pages,
            "has_next": self.has_next,
            "query": self.query,
            "raw_query": self.raw_query,
            "resolved_query": self.resolved_query,
            "attempt_label": self.attempt_label,
            "attempt_description": self.attempt_description,
            "correction_applied": self.correction_applied,
            "used_strategy": self.used_strategy,
            "attempts_count": self.attempts_count,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any], cached: bool = False, cache_age: int = 0) -> "SearchResult":
        """딕셔너리에서 생성 (캐시 복원용)"""
        items = [BoothItem.from_dict(item) for item in data.get("items", [])]

        return cls(
            items=items,
            total_count=data.get("total_count", 0),
            current_page=data.get("current_page", 1),
            total_pages=data.get("total_pages", 1),
            has_next=data.get("has_next", False),
            query=data.get("query", ""),
            cached=cached,
            cache_age_seconds=cache_age if cached else None,
            raw_query=data.get("raw_query", ""),
            resolved_query=data.get("resolved_query", data.get("query", "")),
            attempt_label=data.get("attempt_label", "A"),
            attempt_description=data.get("attempt_description", ""),
            correction_applied=data.get("correction_applied", False),
            used_strategy=data.get("used_strategy", "original"),
            attempts_count=data.get("attempts_count", 1),
        )

    @classmethod
    def empty(cls, query: str = "") -> "SearchResult":
        """빈 결과 생성"""
        return cls(
            items=[],
            total_count=0,
            current_page=1,
            total_pages=0,
            has_next=False,
            query=query,
            raw_query="",
            resolved_query=query,
            attempt_label="A",
            attempt_description="",
            correction_applied=False,
            used_strategy="original",
            attempts_count=1,
        )

    def merge(self, other: "SearchResult") -> "SearchResult":
        """
        다른 결과와 병합 (무한 스크롤용)

        Args:
            other: 병합할 다른 결과

        Returns:
            병합된 새 SearchResult
        """
        return SearchResult(
            items=self.items + other.items,
            total_count=other.total_count,  # 최신 값 사용
            current_page=other.current_page,
            total_pages=other.total_pages,
            has_next=other.has_next,
            query=self.query,
            cached=False,  # 병합 결과는 캐시 아님
            raw_query=self.raw_query,
            resolved_query=self.resolved_query,
            attempt_label=self.attempt_label,
            attempt_description=self.attempt_description,
            correction_applied=self.correction_applied,
            used_strategy=self.used_strategy,
            attempts_count=self.attempts_count,
        )

    def filter_by_price(
        self, min_price: Optional[int] = None, max_price: Optional[int] = None
    ) -> "SearchResult":
        """
        가격 범위로 필터링

        Args:
            min_price: 최소 가격
            max_price: 최대 가격

        Returns:
            필터링된 새 SearchResult
        """
        filtered = [
            item for item in self.items if item.matches_price_range(min_price, max_price)
        ]

        return SearchResult(
            items=filtered,
            total_count=len(filtered),
            current_page=self.current_page,
            total_pages=self.total_pages,
            has_next=self.has_next,
            query=self.query,
            cached=self.cached,
            cache_age_seconds=self.cache_age_seconds,
            raw_query=self.raw_query,
            resolved_query=self.resolved_query,
            attempt_label=self.attempt_label,
            attempt_description=self.attempt_description,
            correction_applied=self.correction_applied,
            used_strategy=self.used_strategy,
            attempts_count=self.attempts_count,
        )

    def filter_free_only(self) -> "SearchResult":
        """무료 상품만 필터링"""
        filtered = [item for item in self.items if item.is_free]

        return SearchResult(
            items=filtered,
            total_count=len(filtered),
            current_page=self.current_page,
            total_pages=self.total_pages,
            has_next=self.has_next,
            query=self.query,
            cached=self.cached,
            cache_age_seconds=self.cache_age_seconds,
            raw_query=self.raw_query,
            resolved_query=self.resolved_query,
            attempt_label=self.attempt_label,
            attempt_description=self.attempt_description,
            correction_applied=self.correction_applied,
            used_strategy=self.used_strategy,
            attempts_count=self.attempts_count,
        )

    def sort_by_price(self, ascending: bool = True) -> "SearchResult":
        """
        가격순 정렬

        Args:
            ascending: True면 가격 낮은순, False면 높은순

        Returns:
            정렬된 새 SearchResult
        """
        # None 가격은 마지막으로
        def price_key(item: BoothItem) -> tuple:
            if item.price_value is None:
                return (1, 0)  # 가격 미정은 마지막
            return (0, item.price_value)

        sorted_items = sorted(self.items, key=price_key, reverse=not ascending)

        return SearchResult(
            items=sorted_items,
            total_count=self.total_count,
            current_page=self.current_page,
            total_pages=self.total_pages,
            has_next=self.has_next,
            query=self.query,
            cached=self.cached,
            cache_age_seconds=self.cache_age_seconds,
            raw_query=self.raw_query,
            resolved_query=self.resolved_query,
            attempt_label=self.attempt_label,
            attempt_description=self.attempt_description,
            correction_applied=self.correction_applied,
            used_strategy=self.used_strategy,
            attempts_count=self.attempts_count,
        )

    def sort_by_likes(self) -> "SearchResult":
        """인기순 (좋아요 수) 정렬"""
        sorted_items = sorted(self.items, key=lambda x: x.likes, reverse=True)

        return SearchResult(
            items=sorted_items,
            total_count=self.total_count,
            current_page=self.current_page,
            total_pages=self.total_pages,
            has_next=self.has_next,
            query=self.query,
            cached=self.cached,
            cache_age_seconds=self.cache_age_seconds,
            raw_query=self.raw_query,
            resolved_query=self.resolved_query,
            attempt_label=self.attempt_label,
            attempt_description=self.attempt_description,
            correction_applied=self.correction_applied,
        )

    def __str__(self) -> str:
        cache_info = " (cached)" if self.cached else ""
        return f"SearchResult({self.count} items, page {self.current_page}/{self.total_pages}{cache_info})"

    def __repr__(self) -> str:
        return str(self)
