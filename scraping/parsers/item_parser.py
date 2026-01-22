"""
Booth 상품 파서

레이아웃 변경에 강한 다중 셀렉터 기반 파서
"""

from typing import List, Optional, Tuple
from bs4 import BeautifulSoup, Tag
import re

from models.booth_item import BoothItem, PriceType, parse_price, extract_item_id_from_url
from models.search_result import SearchResult
from models.search_params import SearchParams
from utils.logging import get_logger
from utils.exceptions import ParsingError
from .base_parser import BaseParser

logger = get_logger(__name__)


class ItemParser(BaseParser):
    """
    Booth 상품 목록 파서

    레이아웃 변경에 강한 다중 CSS 셀렉터를 사용합니다.
    각 요소에 대해 폴백 체인을 통해 다양한 셀렉터를 시도합니다.
    """

    # 상품 카드 컨테이너 셀렉터 (우선순위 순)
    ITEM_CARD_SELECTORS = [
        "li.item-card",
        "[data-product-id]",
        "li[data-tracking-name='search-item']",
        ".l-row-card-list > li",
        ".shop-item-list > li",
    ]

    # 상품명 셀렉터
    TITLE_SELECTORS = [
        ".item-card__title",
        "[data-product-name]",
        ".item-card__title-anchor",
        ".item-card__title a",
        "h3 a",
        "h2 a",
    ]

    # 가격 셀렉터
    PRICE_SELECTORS = [
        ".price",
        "[data-price]",
        ".item-card__price",
        ".u-text-price",
        ".shop-item-price",
    ]

    # 썸네일 셀렉터 (a 태그의 data-original 또는 img 태그)
    THUMBNAIL_SELECTORS = [
        "a.js-thumbnail-image",
        "a.item-card__thumbnail-image",
        ".item-card__thumbnail-images a[data-original]",
        "img.item-card__thumbnail-image",
        "img[data-src]",
        "img.lazy",
        ".item-card__thumbnail img",
        ".shop-item-thumbnail img",
    ]

    # 링크 셀렉터
    LINK_SELECTORS = [
        "a.item-card__title-anchor",
        "a[href*='/items/']",
        ".item-card__thumbnail a",
        "a.item-card__anchor",
    ]

    # 샵 이름 셀렉터
    SHOP_SELECTORS = [
        ".item-card__shop-name",
        "[data-shop-name]",
        ".item-card__shop-name a",
        ".shop-name",
    ]

    # 좋아요 수 셀렉터
    LIKES_SELECTORS = [
        ".item-card__wish-count",
        "[data-wish-count]",
        ".wish-count",
        ".like-count",
    ]

    # 전체 결과 수 셀렉터
    TOTAL_COUNT_SELECTORS = [
        ".search-result__count",
        "[data-result-count]",
        ".result-count",
        ".pager-result",
    ]

    def parse(self, html: str) -> Tuple[List[BoothItem], int]:
        """
        HTML에서 상품 목록과 전체 결과 수 파싱

        Args:
            html: 검색 결과 HTML

        Returns:
            (상품 목록, 전체 결과 수) 튜플
        """
        return self.parse_items(html)

    def parse_items(self, html: str) -> Tuple[List[BoothItem], int]:
        """
        HTML에서 상품 목록 파싱

        Args:
            html: 검색 결과 HTML

        Returns:
            (상품 목록, 전체 결과 수) 튜플
        """
        soup = BeautifulSoup(html, "html.parser")
        items: List[BoothItem] = []

        # 상품 카드 요소 찾기
        cards = self.find_with_fallback(soup, self.ITEM_CARD_SELECTORS)

        if not cards:
            logger.warning("No item cards found with any selector")
            total_count = self._parse_total_count(soup)
            return [], total_count

        logger.debug(f"Found {len(cards)} item cards")

        # 각 카드 파싱
        for i, card in enumerate(cards):
            try:
                item = self._parse_single_card(card)
                if item:
                    items.append(item)
            except Exception as e:
                logger.warning(f"Failed to parse card {i}: {e}")
                continue

        # 전체 결과 수 파싱
        total_count = self._parse_total_count(soup)

        logger.info(f"Parsed {len(items)} items, total count: {total_count}")

        return items, total_count

    def _parse_single_card(self, card: Tag) -> Optional[BoothItem]:
        """
        단일 상품 카드 파싱

        Args:
            card: 상품 카드 요소

        Returns:
            BoothItem 또는 None
        """
        # 상품 ID 추출
        item_id = self._extract_item_id(card)
        if not item_id:
            logger.debug("Could not extract item ID, skipping card")
            return None

        # 상품명
        title_elem = self.find_one_with_fallback(card, self.TITLE_SELECTORS)
        name = self.get_text_safe(title_elem, default="제목 없음")

        # 가격
        price_elem = self.find_one_with_fallback(card, self.PRICE_SELECTORS)
        price_text = self.get_text_safe(price_elem, default="가격 미정")
        price_value, price_type = parse_price(price_text)

        # URL
        link_elem = self.find_one_with_fallback(card, self.LINK_SELECTORS)
        url = self._normalize_url(self.get_attr_safe(link_elem, "href"))

        # 썸네일
        img_elem = self.find_one_with_fallback(card, self.THUMBNAIL_SELECTORS)
        thumbnail_url = self._extract_image_url(img_elem)

        # 샵 이름
        shop_elem = self.find_one_with_fallback(card, self.SHOP_SELECTORS)
        shop_name = self.get_text_safe(shop_elem)

        # 좋아요 수
        likes = self._extract_likes(card)

        return BoothItem(
            id=item_id,
            name=name,
            price_text=price_text,
            price_value=price_value,
            price_type=price_type,
            url=url,
            thumbnail_url=thumbnail_url,
            shop_name=shop_name,
            likes=likes,
        )

    def _extract_item_id(self, card: Tag) -> Optional[str]:
        """상품 ID 추출 (여러 방법 시도)"""
        # 1. data-product-id 속성
        product_id = card.get("data-product-id")
        if product_id:
            return str(product_id)

        # 2. data-item-id 속성
        item_id = card.get("data-item-id")
        if item_id:
            return str(item_id)

        # 3. URL에서 추출
        link = card.select_one("a[href*='/items/']")
        if link:
            href = link.get("href", "")
            extracted = extract_item_id_from_url(str(href))
            if extracted:
                return extracted

        # 4. id 속성에서 추출
        card_id = card.get("id", "")
        if card_id:
            match = re.search(r"item[_-]?(\d+)", str(card_id), re.IGNORECASE)
            if match:
                return match.group(1)

        return None

    def _extract_image_url(self, elem: Optional[Tag]) -> str:
        """
        이미지 URL 추출 (lazy loading 대응)

        여러 속성을 순서대로 시도합니다.
        a 태그의 data-original, style 속성도 지원합니다.
        """
        if not elem:
            return ""

        # 속성 우선순위: data-original > data-src > data-lazy > src
        attrs = ["data-original", "data-src", "data-lazy", "src"]

        for attr in attrs:
            url = elem.get(attr, "")
            if url and isinstance(url, str):
                # data: URL 스킵
                if url.startswith("data:"):
                    continue
                # placeholder 스킵
                if "placeholder" in url.lower() or "loading" in url.lower():
                    continue
                return url

        # style 속성에서 background-image URL 추출
        style = elem.get("style", "")
        if style:
            match = re.search(r'background-image:\s*url\(["\']?([^"\')\s]+)["\']?\)', style)
            if match:
                return match.group(1)

        return ""

    def _extract_likes(self, card: Tag) -> int:
        """좋아요 수 추출"""
        likes_elem = self.find_one_with_fallback(card, self.LIKES_SELECTORS)

        if likes_elem:
            # data 속성 확인
            data_count = likes_elem.get("data-wish-count") or likes_elem.get("data-count")
            if data_count:
                try:
                    return int(data_count)
                except ValueError:
                    pass

            # 텍스트에서 숫자 추출
            text = likes_elem.get_text(strip=True)
            numbers = re.findall(r"\d+", text)
            if numbers:
                try:
                    return int(numbers[0])
                except ValueError:
                    pass

        return 0

    def _parse_total_count(self, soup: BeautifulSoup) -> int:
        """전체 결과 수 파싱"""
        # 1. 기존 셀렉터로 시도
        count_elem = self.find_one_with_fallback(soup, self.TOTAL_COUNT_SELECTORS)

        if count_elem:
            # data 속성 확인
            data_count = count_elem.get("data-result-count") or count_elem.get("data-total")
            if data_count:
                try:
                    return int(data_count)
                except ValueError:
                    pass

            # 텍스트에서 숫자 추출
            text = count_elem.get_text()
            numbers = re.findall(r"[\d,]+", text)
            if numbers:
                try:
                    return int(numbers[0].replace(",", ""))
                except ValueError:
                    pass

        # 2. "件" 포함 텍스트에서 추출 (Booth 한국어 페이지)
        for elem in soup.find_all(string=lambda t: t and "件" in t):
            text = elem.strip()
            numbers = re.findall(r"[\d,]+", text)
            if numbers:
                try:
                    return int(numbers[0].replace(",", ""))
                except ValueError:
                    pass

        # 3. "개" 또는 "results" 포함 텍스트에서 추출
        for pattern in ["개", "results", "items"]:
            for elem in soup.find_all(string=lambda t, p=pattern: t and p in t.lower()):
                text = elem.strip()
                numbers = re.findall(r"[\d,]+", text)
                if numbers:
                    try:
                        return int(numbers[0].replace(",", ""))
                    except ValueError:
                        pass

        return 0

    def _normalize_url(self, url: str) -> str:
        """URL 정규화"""
        if not url:
            return ""

        url = url.strip()

        if url.startswith("//"):
            return f"https:{url}"

        if url.startswith("/"):
            return f"https://booth.pm{url}"

        if not url.startswith("http"):
            return f"https://booth.pm/{url}"

        return url

    def parse_search_result(
        self,
        html: str,
        params: SearchParams,
        items_per_page: int = 24,
    ) -> SearchResult:
        """
        검색 결과 전체 파싱

        Args:
            html: 검색 결과 HTML
            params: 검색 파라미터
            items_per_page: 페이지당 아이템 수

        Returns:
            SearchResult 객체
        """
        items, total_count = self.parse_items(html)

        # 페이지 계산
        total_pages = max(1, (total_count + items_per_page - 1) // items_per_page)
        has_next = params.page < total_pages

        return SearchResult(
            items=items,
            total_count=total_count,
            current_page=params.page,
            total_pages=total_pages,
            has_next=has_next,
            query=params.avatar_name,
        )
