"""
Booth.pm 스크래핑 모듈
VRChat 아바타 대응 의상을 검색합니다.
"""

import requests
from bs4 import BeautifulSoup
from dataclasses import dataclass
from typing import List, Optional
import urllib.parse
import re


@dataclass
class BoothItem:
    """Booth 상품 정보를 담는 데이터 클래스"""
    name: str
    price: str
    url: str
    thumbnail_url: str
    shop_name: str = ""


class BoothScraper:
    """Booth.pm 스크래핑 클래스"""

    BASE_URL = "https://booth.pm"
    SEARCH_URL = "https://booth.pm/ko/search/{keyword}"

    # VRChat 관련 카테고리
    CATEGORIES = {
        "전체": "",
        "3D 의상": "208",
        "3D 캐릭터": "217",
        "3D 액세서리": "209",
        "3D 모델": "207",
    }

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7,ja;q=0.6",
        })

    def search(self, avatar_name: str, category: str = "전체", page: int = 1) -> List[BoothItem]:
        """
        아바타 이름으로 대응 의상을 검색합니다.

        Args:
            avatar_name: 검색할 아바타 이름 (예: 桔梗, セレスティア, マヌカ)
            category: 카테고리 필터
            page: 페이지 번호

        Returns:
            검색된 상품 목록
        """
        items = []

        # 검색어 구성 - 아바타 이름 + 対応 (대응)
        search_keyword = f"{avatar_name} 対応"
        encoded_keyword = urllib.parse.quote(search_keyword)

        # URL 구성
        url = f"{self.BASE_URL}/ko/search/{encoded_keyword}"
        params = {"page": page}

        # 카테고리 필터 추가
        category_id = self.CATEGORIES.get(category, "")
        if category_id:
            params["category"] = category_id

        try:
            response = self.session.get(url, params=params, timeout=15)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            # 상품 목록 파싱
            item_cards = soup.select("li.item-card")

            for card in item_cards:
                item = self._parse_item_card(card)
                if item:
                    items.append(item)

        except requests.RequestException as e:
            print(f"검색 오류: {e}")

        return items

    def _parse_item_card(self, card) -> Optional[BoothItem]:
        """상품 카드 HTML을 파싱합니다."""
        try:
            # 상품명
            name_elem = card.select_one(".item-card__title")
            name = name_elem.get_text(strip=True) if name_elem else "제목 없음"

            # 가격
            price_elem = card.select_one(".price")
            price = price_elem.get_text(strip=True) if price_elem else "가격 미정"

            # 상품 URL
            link_elem = card.select_one("a.item-card__title-anchor")
            if not link_elem:
                link_elem = card.select_one("a[href*='/items/']")
            url = link_elem.get("href", "") if link_elem else ""
            if url and not url.startswith("http"):
                url = self.BASE_URL + url

            # 썸네일 이미지
            img_elem = card.select_one("img.item-card__thumbnail-image")
            if not img_elem:
                img_elem = card.select_one("img[data-src]")
            thumbnail_url = ""
            if img_elem:
                thumbnail_url = img_elem.get("data-src") or img_elem.get("src", "")

            # 샵 이름
            shop_elem = card.select_one(".item-card__shop-name")
            shop_name = shop_elem.get_text(strip=True) if shop_elem else ""

            return BoothItem(
                name=name,
                price=price,
                url=url,
                thumbnail_url=thumbnail_url,
                shop_name=shop_name
            )

        except Exception as e:
            print(f"파싱 오류: {e}")
            return None

    def get_popular_avatars(self) -> List[str]:
        """인기 VRChat 아바타 목록을 반환합니다."""
        return [
            "桔梗 (키쿄)",
            "セレスティア (셀레스티아)",
            "マヌカ (마누카)",
            "舞夜 (마이야)",
            "ルーシュカ (루슈카)",
            "リーファ (리파)",
            "サフィー (사피)",
            "シフォン (시폰)",
            "萌 (모에)",
            "ここあ (코코아)",
            "イメリス (이메리스)",
            "チューベローズ (튜베로즈)",
        ]


# 테스트 코드
if __name__ == "__main__":
    scraper = BoothScraper()
    results = scraper.search("桔梗")
    print(f"검색 결과: {len(results)}개")
    for item in results[:5]:
        print(f"- {item.name}: {item.price}")
        print(f"  URL: {item.url}")
