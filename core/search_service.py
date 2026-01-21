"""
검색 서비스 오케스트레이션

스크래핑, 파싱, 캐싱을 통합하는 고수준 검색 서비스
"""

from typing import Optional, List
from models.search_params import SearchParams, SortOrder
from models.search_result import SearchResult
from models.booth_item import BoothItem
from scraping.booth_client import BoothClient
from scraping.parsers.item_parser import ItemParser
from cache.result_cache import ResultCache
from config.settings import Settings
from config.constants import BOOTH_CATEGORIES
from data.avatar_data import get_popular_avatar_names
from utils.logging import get_logger, LogContext
from utils.exceptions import BoothSearcherError

logger = get_logger(__name__)


class SearchService:
    """
    검색 서비스

    스크래핑, 파싱, 캐싱을 통합하여 고수준 검색 API를 제공합니다.

    사용법:
        service = SearchService(settings)

        # 검색 실행
        result = service.search(params)

        # 다음 페이지 로드
        result = service.search(params.with_page(2))

        # 검색 후 정렬/필터
        result = result.sort_by_price()
        result = result.filter_free_only()
    """

    def __init__(
        self,
        settings: Optional[Settings] = None,
        client: Optional[BoothClient] = None,
        result_cache: Optional[ResultCache] = None,
    ):
        if settings is None:
            settings = Settings()

        self.settings = settings

        # 클라이언트 (외부 주입 또는 생성)
        self._own_client = client is None
        self.client = client or BoothClient(settings)

        # 파서
        self.parser = ItemParser()

        # 캐시 (외부 주입 또는 생성)
        self._own_cache = result_cache is None
        self.result_cache = result_cache or ResultCache(settings)

        logger.info("SearchService 초기화")

    def search(
        self,
        params: SearchParams,
        use_cache: bool = True,
    ) -> SearchResult:
        """
        검색 실행

        Args:
            params: 검색 파라미터
            use_cache: 캐시 사용 여부

        Returns:
            검색 결과

        Raises:
            BoothSearcherError: 검색 실패
        """
        with LogContext("검색", logger, avatar=params.avatar_name, page=params.page):
            # 1. 캐시 확인
            if use_cache:
                cached = self.result_cache.get(params)
                if cached is not None:
                    logger.info(
                        f"캐시 히트: '{params.avatar_name}' "
                        f"(age={cached.cache_age_seconds}s)"
                    )
                    return self._apply_client_side_filters(cached, params)

            # 2. 스크래핑
            html = self._fetch_search_page(params)

            # 3. 파싱
            result = self.parser.parse_search_result(
                html,
                params,
                items_per_page=params.per_page,
            )

            # 4. 캐시 저장
            if use_cache and not result.is_empty:
                self.result_cache.put(params, result)

            # 5. 클라이언트 사이드 필터 적용
            result = self._apply_client_side_filters(result, params)

            logger.info(
                f"검색 완료: '{params.avatar_name}' - "
                f"{len(result.items)}개 결과 (전체 {result.total_count}개)"
            )

            return result

    def _fetch_search_page(self, params: SearchParams) -> str:
        """검색 페이지 HTML 가져오기"""
        keyword = params.get_search_keyword()

        # 카테고리 ID
        category_id = BOOTH_CATEGORIES.get(params.category, "")

        # 정렬 파라미터
        sort = params.sort.booth_param

        logger.debug(f"Fetching: keyword={keyword}, category={params.category}, category_id={category_id}, sort={sort}")

        return self.client.get_search_page(
            keyword=keyword,
            page=params.page,
            category_id=category_id if category_id else None,
            sort=sort,
        )

    def _apply_client_side_filters(
        self,
        result: SearchResult,
        params: SearchParams,
    ) -> SearchResult:
        """
        클라이언트 사이드 필터 적용

        Booth API가 지원하지 않는 필터를 클라이언트에서 처리
        """
        # 가격 필터
        if params.price_range:
            if params.price_range.free_only:
                result = result.filter_free_only()
            else:
                result = result.filter_by_price(
                    min_price=params.price_range.min_price,
                    max_price=params.price_range.max_price,
                )

        # 클라이언트 사이드 정렬 (Booth 정렬이 아닌 경우)
        if params.sort == SortOrder.PRICE_ASC:
            result = result.sort_by_price(ascending=True)
        elif params.sort == SortOrder.PRICE_DESC:
            result = result.sort_by_price(ascending=False)

        return result

    def search_all_pages(
        self,
        params: SearchParams,
        max_pages: int = 5,
        use_cache: bool = True,
    ) -> SearchResult:
        """
        여러 페이지 검색 (무한 스크롤용)

        Args:
            params: 검색 파라미터 (page=1부터 시작)
            max_pages: 최대 페이지 수
            use_cache: 캐시 사용 여부

        Returns:
            병합된 검색 결과
        """
        # 첫 페이지
        result = self.search(params, use_cache=use_cache)

        if result.is_empty or not result.has_next:
            return result

        # 추가 페이지
        current_page = params.page + 1
        while current_page <= min(params.page + max_pages - 1, result.total_pages):
            next_params = params.with_page(current_page)
            next_result = self.search(next_params, use_cache=use_cache)

            if next_result.is_empty:
                break

            result = result.merge(next_result)
            current_page += 1

        return result

    def get_popular_avatars(self) -> List[str]:
        """
        인기 아바타 목록 반환

        외부 JSON 파일에서 로드합니다.
        """
        return get_popular_avatar_names()

    def get_categories(self) -> dict:
        """카테고리 목록 반환"""
        return BOOTH_CATEGORIES.copy()

    def invalidate_cache(self, params: SearchParams) -> bool:
        """특정 검색 결과 캐시 무효화"""
        return self.result_cache.invalidate(params)

    def clear_cache(self) -> None:
        """검색 결과 캐시 전체 삭제"""
        self.result_cache.clear()

    def get_stats(self) -> dict:
        """서비스 통계"""
        return {
            "client": self.client.get_stats(),
            "cache": self.result_cache.get_stats(),
        }

    def close(self) -> None:
        """리소스 정리"""
        if self._own_client:
            self.client.close()
        logger.debug("SearchService 종료")

    def __enter__(self) -> "SearchService":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def __repr__(self) -> str:
        return f"SearchService({self.client}, {self.result_cache})"
