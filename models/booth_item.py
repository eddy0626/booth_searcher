"""
Booth 상품 데이터 모델
"""

from dataclasses import dataclass, field, asdict
from typing import Optional, Tuple, Dict, Any
from datetime import datetime
from enum import Enum
import re


class PriceType(Enum):
    """가격 유형"""

    FREE = "free"
    PAID = "paid"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class BoothItem:
    """
    Booth 상품 정보 데이터 클래스 (불변)

    Attributes:
        id: Booth 상품 ID (URL에서 추출)
        name: 상품명
        price_text: 원본 가격 문자열 (예: "¥1,500")
        price_value: 파싱된 가격 값 (정렬용)
        price_type: 가격 유형 (무료/유료/미정)
        url: 상품 페이지 URL
        thumbnail_url: 썸네일 이미지 URL
        shop_name: 판매자 이름
        shop_url: 판매자 페이지 URL
        likes: 좋아요 수 (인기순 정렬용)
        created_at: 등록일 (최신순 정렬용)
        tags: 태그 목록
    """

    id: str
    name: str
    price_text: str
    url: str
    thumbnail_url: str
    price_value: Optional[int] = None
    price_type: PriceType = PriceType.UNKNOWN
    shop_name: str = ""
    shop_url: str = ""
    likes: int = 0
    created_at: Optional[datetime] = None
    tags: Tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> Dict[str, Any]:
        """
        딕셔너리로 변환 (캐시 저장용)
        """
        return {
            "id": self.id,
            "name": self.name,
            "price_text": self.price_text,
            "price_value": self.price_value,
            "price_type": self.price_type.value,
            "url": self.url,
            "thumbnail_url": self.thumbnail_url,
            "shop_name": self.shop_name,
            "shop_url": self.shop_url,
            "likes": self.likes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "tags": list(self.tags),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BoothItem":
        """
        딕셔너리에서 생성 (캐시 복원용)
        """
        created_at = None
        if data.get("created_at"):
            try:
                created_at = datetime.fromisoformat(data["created_at"])
            except (ValueError, TypeError):
                pass

        price_type = PriceType.UNKNOWN
        if data.get("price_type"):
            try:
                price_type = PriceType(data["price_type"])
            except ValueError:
                pass

        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            price_text=data.get("price_text", ""),
            price_value=data.get("price_value"),
            price_type=price_type,
            url=data.get("url", ""),
            thumbnail_url=data.get("thumbnail_url", ""),
            shop_name=data.get("shop_name", ""),
            shop_url=data.get("shop_url", ""),
            likes=data.get("likes", 0),
            created_at=created_at,
            tags=tuple(data.get("tags", [])),
        )

    @property
    def is_free(self) -> bool:
        """무료 상품 여부"""
        return self.price_type == PriceType.FREE or self.price_value == 0

    @property
    def display_price(self) -> str:
        """표시용 가격 문자열"""
        if self.is_free:
            return "무료"
        return self.price_text or "가격 미정"

    def matches_price_range(
        self, min_price: Optional[int] = None, max_price: Optional[int] = None
    ) -> bool:
        """
        가격 범위 필터 매칭

        Args:
            min_price: 최소 가격
            max_price: 최대 가격

        Returns:
            범위 내에 있으면 True
        """
        if self.price_value is None:
            return True  # 가격 미정은 항상 포함

        if min_price is not None and self.price_value < min_price:
            return False

        if max_price is not None and self.price_value > max_price:
            return False

        return True

    def __str__(self) -> str:
        return f"{self.name} ({self.display_price})"

    def __repr__(self) -> str:
        return f"BoothItem(id={self.id!r}, name={self.name!r}, price={self.display_price})"


def parse_price(price_text: str) -> Tuple[Optional[int], PriceType]:
    """
    가격 문자열 파싱

    Args:
        price_text: 원본 가격 문자열 (예: "¥1,500", "無料", "Free")

    Returns:
        (파싱된 가격, 가격 유형) 튜플
    """
    if not price_text:
        return None, PriceType.UNKNOWN

    text = price_text.strip().lower()

    # 무료 체크
    if "無料" in price_text or "free" in text or "0円" in price_text:
        return 0, PriceType.FREE

    # 숫자 추출
    numbers = re.findall(r"[\d,]+", price_text)
    if numbers:
        try:
            value = int(numbers[0].replace(",", ""))
            if value == 0:
                return 0, PriceType.FREE
            return value, PriceType.PAID
        except ValueError:
            pass

    return None, PriceType.UNKNOWN


def extract_item_id_from_url(url: str) -> Optional[str]:
    """
    URL에서 상품 ID 추출

    Args:
        url: Booth 상품 URL

    Returns:
        상품 ID 또는 None
    """
    match = re.search(r"/items/(\d+)", url)
    if match:
        return match.group(1)
    return None
