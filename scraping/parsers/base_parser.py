"""
파서 베이스 클래스

HTML 파싱을 위한 공통 인터페이스 및 유틸리티
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Tuple, Any
from bs4 import BeautifulSoup, Tag

from utils.logging import get_logger

logger = get_logger(__name__)


class BaseParser(ABC):
    """
    HTML 파서 베이스 클래스

    다중 셀렉터 폴백 및 공통 유틸리티를 제공합니다.
    """

    def find_with_fallback(
        self,
        soup: BeautifulSoup,
        selectors: List[str],
    ) -> List[Tag]:
        """
        셀렉터 폴백 체인으로 요소 목록 찾기

        첫 번째로 매칭되는 셀렉터의 결과를 반환합니다.

        Args:
            soup: BeautifulSoup 객체
            selectors: CSS 셀렉터 목록 (우선순위 순)

        Returns:
            매칭된 요소 목록
        """
        for selector in selectors:
            try:
                elements = soup.select(selector)
                if elements:
                    logger.debug(f"Selector matched: {selector} ({len(elements)} elements)")
                    return elements
            except Exception as e:
                logger.warning(f"Selector failed: {selector}: {e}")
                continue

        logger.debug(f"No selector matched from {len(selectors)} selectors")
        return []

    def find_one_with_fallback(
        self,
        element: Tag,
        selectors: List[str],
    ) -> Optional[Tag]:
        """
        셀렉터 폴백 체인으로 단일 요소 찾기

        Args:
            element: 검색할 부모 요소
            selectors: CSS 셀렉터 목록

        Returns:
            매칭된 요소 또는 None
        """
        for selector in selectors:
            try:
                found = element.select_one(selector)
                if found:
                    return found
            except Exception:
                continue

        return None

    def get_text_safe(
        self,
        element: Optional[Tag],
        default: str = "",
        strip: bool = True,
    ) -> str:
        """
        안전하게 텍스트 추출

        Args:
            element: 요소 (None 가능)
            default: 기본값
            strip: 공백 제거 여부

        Returns:
            추출된 텍스트
        """
        if element is None:
            return default

        text = element.get_text(strip=strip)
        return text if text else default

    def get_attr_safe(
        self,
        element: Optional[Tag],
        attr: str,
        default: str = "",
    ) -> str:
        """
        안전하게 속성 값 추출

        Args:
            element: 요소 (None 가능)
            attr: 속성 이름
            default: 기본값

        Returns:
            속성 값
        """
        if element is None:
            return default

        value = element.get(attr, default)

        # 리스트인 경우 첫 번째 값 사용 (class 속성 등)
        if isinstance(value, list):
            return value[0] if value else default

        return str(value) if value else default

    def get_attr_with_fallback(
        self,
        element: Optional[Tag],
        attrs: List[str],
        default: str = "",
    ) -> str:
        """
        속성 폴백 체인으로 값 추출

        Args:
            element: 요소
            attrs: 속성 이름 목록 (우선순위 순)
            default: 기본값

        Returns:
            속성 값
        """
        if element is None:
            return default

        for attr in attrs:
            value = element.get(attr)
            if value:
                if isinstance(value, list):
                    value = value[0]
                return str(value)

        return default

    @abstractmethod
    def parse(self, html: str) -> Any:
        """
        HTML 파싱 (하위 클래스에서 구현)

        Args:
            html: HTML 문자열

        Returns:
            파싱 결과
        """
        pass
