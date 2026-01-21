"""
Booth.pm HTTP 클라이언트

특징:
- 자동 재시도 (지수 백오프)
- Rate Limiting
- User-Agent 로테이션
- 타임아웃 관리
"""

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from typing import Optional, Dict, Any
import random

from config.settings import Settings, ScrapingSettings
from config.constants import (
    BOOTH_BASE_URL,
    USER_AGENTS,
    DEFAULT_HEADERS,
)
from utils.logging import get_logger
from utils.exceptions import BoothClientError, RateLimitError
from .rate_limiter import RateLimiter

logger = get_logger(__name__)


class BoothClient:
    """
    Booth.pm HTTP 클라이언트

    재시도, Rate Limiting, User-Agent 로테이션을 포함한 HTTP 클라이언트

    사용법:
        settings = Settings.load()
        client = BoothClient(settings)

        response = client.get("/ko/search/桔梗 対応")
        html = response.text

        client.close()

    Args:
        settings: 애플리케이션 설정
        rate_limiter: 커스텀 Rate Limiter (None이면 자동 생성)
    """

    def __init__(
        self,
        settings: Optional[Settings] = None,
        rate_limiter: Optional[RateLimiter] = None,
    ):
        if settings is None:
            settings = Settings()

        self.settings = settings
        self.scraping = settings.scraping

        # Rate Limiter 설정
        if rate_limiter is None:
            self.rate_limiter = RateLimiter(
                requests_per_minute=self.scraping.requests_per_minute,
                burst_limit=self.scraping.burst_limit,
            )
        else:
            self.rate_limiter = rate_limiter

        # 세션 생성
        self.session = self._create_session()

        logger.info(
            f"BoothClient 초기화: timeout={self.scraping.timeout}s, "
            f"retries={self.scraping.max_retries}, "
            f"rate_limit={self.scraping.requests_per_minute}/min"
        )

    def _create_session(self) -> requests.Session:
        """
        재시도 로직이 포함된 세션 생성
        """
        session = requests.Session()

        # 재시도 전략 설정
        retry_strategy = Retry(
            total=self.scraping.max_retries,
            backoff_factor=self.scraping.backoff_factor,
            status_forcelist=[500, 502, 503, 504],  # 429는 별도 처리
            allowed_methods=["GET", "HEAD"],
            raise_on_status=False,
        )

        # HTTP 어댑터 설정
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=10,
            pool_maxsize=10,
        )

        session.mount("https://", adapter)
        session.mount("http://", adapter)

        return session

    def get(
        self,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None,
    ) -> requests.Response:
        """
        GET 요청 수행

        Rate Limiting과 재시도가 자동으로 적용됩니다.

        Args:
            path: URL 경로 (예: "/ko/search/keyword")
            params: 쿼리 파라미터
            timeout: 요청 타임아웃 (None이면 설정값 사용)

        Returns:
            Response 객체

        Raises:
            RateLimitError: 요청 제한 초과 (429)
            BoothClientError: 요청 실패
        """
        # Rate Limiting
        if not self.rate_limiter.acquire(timeout=30):
            raise RateLimitError(retry_after=30, message="Rate limit 대기 시간 초과")

        # URL 구성
        url = f"{BOOTH_BASE_URL}{path}"

        # 헤더 설정 (User-Agent 로테이션)
        headers = DEFAULT_HEADERS.copy()
        headers["User-Agent"] = random.choice(USER_AGENTS)

        # 타임아웃 설정
        if timeout is None:
            timeout = self.scraping.timeout

        try:
            logger.debug(f"GET {url}", extra={"params": params})

            response = self.session.get(
                url,
                params=params,
                headers=headers,
                timeout=timeout,
            )

            # 429 Too Many Requests 처리
            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 60))
                logger.warning(f"Rate limited by Booth.pm, retry after {retry_after}s")
                raise RateLimitError(retry_after=retry_after)

            # 4xx/5xx 에러 처리
            if response.status_code >= 400:
                logger.error(
                    f"HTTP error: {response.status_code} for {url}",
                    extra={"status_code": response.status_code},
                )
                raise BoothClientError(
                    message=f"HTTP 요청 실패",
                    status_code=response.status_code,
                    url=url,
                )

            logger.debug(
                f"Response: {response.status_code}, "
                f"size={len(response.content)} bytes"
            )

            return response

        except requests.exceptions.Timeout as e:
            logger.error(f"Request timeout: {url}")
            raise BoothClientError(
                message=f"요청 타임아웃 ({timeout}초)",
                url=url,
            ) from e

        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error: {url}")
            raise BoothClientError(
                message="연결 실패 (네트워크 상태를 확인하세요)",
                url=url,
            ) from e

        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {url}: {e}")
            raise BoothClientError(
                message=f"요청 실패: {e}",
                url=url,
            ) from e

    def get_search_page(
        self,
        keyword: str,
        page: int = 1,
        category_id: Optional[str] = None,
        sort: Optional[str] = None,
    ) -> str:
        """
        Booth 검색 페이지 HTML 가져오기

        Args:
            keyword: 검색 키워드
            page: 페이지 번호
            category_id: 카테고리 ID (None이면 전체)
            sort: 정렬 방식 (None이면 기본)

        Returns:
            검색 결과 HTML
        """
        import urllib.parse

        encoded_keyword = urllib.parse.quote(keyword)
        path = f"/ko/search/{encoded_keyword}"

        params: Dict[str, Any] = {"page": page}

        if category_id:
            params["category"] = category_id

        if sort:
            params["sort"] = sort

        response = self.get(path, params=params)
        return response.text

    def get_item_page(self, item_id: str) -> str:
        """
        상품 상세 페이지 HTML 가져오기

        Args:
            item_id: 상품 ID

        Returns:
            상품 페이지 HTML
        """
        path = f"/ko/items/{item_id}"
        response = self.get(path)
        return response.text

    def get_stats(self) -> Dict[str, Any]:
        """
        클라이언트 통계 반환
        """
        return {
            "rate_limiter": self.rate_limiter.get_stats(),
            "settings": {
                "timeout": self.scraping.timeout,
                "max_retries": self.scraping.max_retries,
                "requests_per_minute": self.scraping.requests_per_minute,
            },
        }

    def close(self) -> None:
        """
        클라이언트 리소스 정리
        """
        self.session.close()
        logger.debug("BoothClient 종료")

    def __enter__(self) -> "BoothClient":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def __repr__(self) -> str:
        return (
            f"BoothClient(timeout={self.scraping.timeout}, "
            f"retries={self.scraping.max_retries})"
        )
