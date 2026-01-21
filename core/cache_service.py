"""
캐시 서비스 추상화

이미지 캐시와 결과 캐시를 통합 관리
"""

from typing import Optional, Callable
from cache.image_cache import ImageCache
from cache.result_cache import ResultCache
from models.search_params import SearchParams
from models.search_result import SearchResult
from config.settings import Settings
from utils.logging import get_logger

logger = get_logger(__name__)


class CacheService:
    """
    캐시 서비스 통합 관리

    이미지 캐시와 검색 결과 캐시를 통합 관리합니다.

    사용법:
        service = CacheService(settings)

        # 검색 결과 캐시 조회 또는 fetch
        result = service.get_or_fetch(params, fetch_fn)

        # 이미지 캐시
        image_data = service.get_image(url)
        service.put_image(url, data)

        # 통계
        stats = service.get_stats()
    """

    def __init__(self, settings: Optional[Settings] = None):
        if settings is None:
            settings = Settings()

        self.settings = settings
        self.image_cache = ImageCache(settings)
        self.result_cache = ResultCache(settings)

        logger.info("CacheService 초기화")

    def get_or_fetch(
        self,
        params: SearchParams,
        fetch_fn: Callable[[SearchParams], SearchResult],
        force_refresh: bool = False,
    ) -> SearchResult:
        """
        캐시에서 결과를 가져오거나, 없으면 fetch 후 캐시에 저장

        Args:
            params: 검색 파라미터
            fetch_fn: 캐시 미스 시 호출할 함수
            force_refresh: True면 캐시 무시하고 새로 fetch

        Returns:
            검색 결과
        """
        # 캐시 확인 (force_refresh가 아닌 경우)
        if not force_refresh:
            cached = self.result_cache.get(params)
            if cached is not None:
                logger.debug(f"Cache hit for '{params.avatar_name}'")
                return cached

        # Fetch
        logger.debug(f"Cache miss for '{params.avatar_name}', fetching...")
        result = fetch_fn(params)

        # 캐시에 저장
        if not result.is_empty:
            self.result_cache.put(params, result)

        return result

    def get_image(self, url: str) -> Optional[bytes]:
        """이미지 캐시에서 조회"""
        return self.image_cache.get(url)

    def put_image(self, url: str, data: bytes) -> None:
        """이미지 캐시에 저장"""
        self.image_cache.put(url, data)

    def has_image(self, url: str) -> bool:
        """이미지가 캐시에 있는지 확인"""
        return self.image_cache.contains(url)

    def invalidate_search(self, params: SearchParams) -> bool:
        """특정 검색 결과 캐시 무효화"""
        return self.result_cache.invalidate(params)

    def invalidate_query(self, query: str) -> int:
        """특정 검색어의 모든 캐시 무효화"""
        return self.result_cache.invalidate_query(query)

    def cleanup(self) -> dict:
        """
        만료된 캐시 정리

        Returns:
            정리 결과 통계
        """
        result_count = self.result_cache.cleanup()
        image_count = self.image_cache.cleanup_disk()

        return {
            "result_cache_cleaned": result_count,
            "image_cache_cleaned": image_count,
        }

    def clear_all(self) -> None:
        """모든 캐시 삭제"""
        self.image_cache.clear()
        self.result_cache.clear()
        logger.info("All caches cleared")

    def clear_images(self) -> None:
        """이미지 캐시만 삭제"""
        self.image_cache.clear()

    def clear_results(self) -> None:
        """결과 캐시만 삭제"""
        self.result_cache.clear()

    def get_stats(self) -> dict:
        """통합 캐시 통계"""
        return {
            "image_cache": self.image_cache.get_stats(),
            "result_cache": self.result_cache.get_stats(),
        }

    def get_recent_queries(self, limit: int = 10) -> list:
        """최근 검색어 목록"""
        return self.result_cache.get_recent_queries(limit)

    def __repr__(self) -> str:
        return f"CacheService({self.image_cache}, {self.result_cache})"
