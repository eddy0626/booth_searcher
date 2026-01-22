"""
검색 서비스 오케스트레이션

스크래핑, 파싱, 캐싱을 통합하는 고수준 검색 서비스
"""

from dataclasses import dataclass, replace
from typing import Optional, List, Callable, Tuple, Dict
import time
from models.search_params import SearchParams, SortOrder
from models.search_result import SearchResult
from models.booth_item import BoothItem
from scraping.booth_client import BoothClient
from scraping.parsers.item_parser import ItemParser
from cache.result_cache import ResultCache
from config.settings import Settings
from config.constants import BOOTH_CATEGORIES
from data.avatar_data import get_popular_avatar_names
from data.avatar_aliases import build_alias_map
from data.relevance_config import load_relevance_config
from utils.query_normalization import normalize_query, split_multi_query, remove_spaces
from utils.relevance_scoring import compute_relevance_score, score_to_label, tokenize_query
from utils.logging import get_logger, LogContext
from utils.exceptions import BoothSearcherError
from config.user_prefs import get_prefs

try:
    from bs4 import BeautifulSoup
except ImportError:  # pragma: no cover
    BeautifulSoup = None

logger = get_logger(__name__)


@dataclass
class SearchAttempt:
    """검색 시도 정보"""

    label: str
    query: str
    description: str = ""


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

        # 별칭 매핑
        self._alias_map = build_alias_map(normalize_query)
        self._relevance_config = load_relevance_config()
        self._detail_verify_cache: Dict[str, Tuple[bool, float]] = {}
        self._detail_cache_ttl = settings.cache.result_ttl_minutes * 60

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

            # 3-1. 관련성 점수 계산 및 정렬
            result = self._apply_relevance_scoring(result, params)

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

    def search_with_fallback(
        self,
        params: SearchParams,
        use_cache: bool = True,
        cancel_check: Optional[Callable[[], bool]] = None,
        progress_callback: Optional[Callable[[str], None]] = None,
        min_results: int = 3,
        max_attempts: int = 3,
    ) -> SearchResult:
        """
        검색어 정규화 + 폴백 시도 포함 검색

        Args:
            params: 검색 파라미터
            use_cache: 캐시 사용 여부
            cancel_check: 취소 여부 확인 콜백
            progress_callback: 진행 메시지 콜백
            min_results: 결과가 충분하다고 판단하는 최소 개수
            max_attempts: 최대 시도 횟수 (기본 3)
        """
        if params.page != 1 or not params.normalization_enabled:
            return self.search(params, use_cache=use_cache)

        raw_query = params.raw_query or params.avatar_name
        attempts = self._build_attempts(
            raw_query=raw_query,
            normalize_enabled=params.normalization_enabled,
            allow_multi=params.allow_multi,
            max_attempts=max_attempts,
        )

        if not attempts:
            return self.search(params, use_cache=use_cache)

        best_result: Optional[SearchResult] = None

        for attempt in attempts:
            if cancel_check and cancel_check():
                logger.info("검색 취소됨 (폴백 전)")
                break

            attempt_params = params.with_avatar_name(attempt.query)

            if attempt.label != "A" and progress_callback:
                progress_callback(f"검색어 보정 시도 ({attempt.label}: {attempt.description})")

            result = self.search(attempt_params, use_cache=use_cache)
            self._apply_attempt_metadata(result, raw_query, attempt)

            if best_result is None or self._result_score(result) > self._result_score(best_result):
                best_result = result

            if not self._should_retry(result, min_results=min_results):
                break

        if best_result is None:
            best_result = SearchResult.empty(query=params.avatar_name)
            self._apply_attempt_metadata(
                best_result,
                raw_query,
                SearchAttempt(label="A", query=params.avatar_name, description=""),
            )

        if params.verify_mode and params.verify_top_n > 0:
            best_result = self._verify_top_items(
                best_result,
                params,
                cancel_check=cancel_check,
                progress_callback=progress_callback,
            )

        return best_result

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

    def _build_attempts(
        self,
        raw_query: str,
        normalize_enabled: bool,
        allow_multi: bool,
        max_attempts: int,
    ) -> List[SearchAttempt]:
        raw_query = raw_query or ""
        raw_trimmed = raw_query.strip()
        parts = split_multi_query(raw_query) if allow_multi else [raw_query]
        if not parts:
            parts = [raw_query]

        candidates: List[Tuple[str, str, bool]] = []
        for part in parts:
            original = part.strip()
            if not original:
                continue
            normalized = normalize_query(original) if normalize_enabled else original
            if not normalized:
                continue
            normalization_applied = normalize_enabled and normalized != original
            candidates.append((original, normalized, normalization_applied))

        if not candidates and raw_trimmed:
            normalized = normalize_query(raw_trimmed) if normalize_enabled else raw_trimmed
            normalization_applied = normalize_enabled and normalized != raw_trimmed
            candidates = [(raw_trimmed, normalized, normalization_applied)]

        # 중복 제거 (정규화 기준)
        deduped: List[Tuple[str, str, bool]] = []
        seen = set()
        for original, normalized, normalization_applied in candidates:
            if normalized in seen:
                continue
            seen.add(normalized)
            deduped.append((original, normalized, normalization_applied))

        if not deduped:
            return []

        attempts: List[SearchAttempt] = []

        _, primary_query, primary_normalized = deduped[0]
        desc_parts = []
        if len(deduped) > 1:
            desc_parts.append(f"다중 입력 1/{len(deduped)} 선택")
        if primary_normalized:
            desc_parts.append("정규화")
        primary_desc = ", ".join(desc_parts)
        attempts.append(SearchAttempt(label="A", query=primary_query, description=primary_desc))

        # Attempt B: 공백 제거 또는 따옴표 검색
        attempt_b = self._build_attempt_b(primary_query)
        if attempt_b:
            attempts.append(attempt_b)

        # Attempt C: 별칭 매핑
        attempt_c = self._build_attempt_c(primary_query, normalize_enabled)
        if attempt_c:
            attempts.append(attempt_c)

        # 남은 시도 횟수에 한해 다른 후보를 순차 시도
        if allow_multi and len(deduped) > 1 and len(attempts) < max_attempts:
            for idx, (_, alt_query, alt_normalized) in enumerate(deduped[1:], start=2):
                if len(attempts) >= max_attempts:
                    break
                desc_parts = [f"다중 입력 {idx}/{len(deduped)} 선택"]
                if alt_normalized:
                    desc_parts.append("정규화")
                attempts.append(
                    SearchAttempt(label="A", query=alt_query, description=", ".join(desc_parts))
                )

        # 중복 시도 제거 (동일 쿼리)
        deduped_attempts: List[SearchAttempt] = []
        seen_queries = set()
        for attempt in attempts:
            if attempt.query in seen_queries:
                continue
            seen_queries.add(attempt.query)
            deduped_attempts.append(attempt)

        return deduped_attempts[:max_attempts]

    def _build_attempt_b(self, query: str) -> Optional[SearchAttempt]:
        if not query:
            return None

        if " " in query:
            no_space = remove_spaces(query)
            if no_space and no_space != query:
                return SearchAttempt(label="B", query=no_space, description="공백 제거")

        quoted = query
        if not (query.startswith("\"") and query.endswith("\"")):
            quoted = f"\"{query}\""

        if quoted != query:
            return SearchAttempt(label="B", query=quoted, description="따옴표 검색")

        return None

    def _build_attempt_c(self, query: str, normalize_enabled: bool) -> Optional[SearchAttempt]:
        if not query or not normalize_enabled:
            return None

        key = normalize_query(query)
        canonical = self._alias_map.get(key)
        if canonical and canonical != query:
            return SearchAttempt(label="C", query=canonical, description="별칭 매핑")

        return None

    @staticmethod
    def _result_score(result: SearchResult) -> int:
        if result.total_count > 0:
            return result.total_count
        return len(result.items)

    @staticmethod
    def _should_retry(result: SearchResult, min_results: int) -> bool:
        count = SearchService._result_score(result)
        return result.is_empty or count < min_results

    @staticmethod
    def _apply_attempt_metadata(
        result: SearchResult,
        raw_query: str,
        attempt: SearchAttempt,
    ) -> None:
        raw_trimmed = raw_query.strip()
        result.raw_query = raw_query
        result.resolved_query = attempt.query
        result.query = attempt.query
        result.attempt_label = attempt.label
        result.attempt_description = attempt.description
        result.correction_applied = (
            attempt.label != "A"
            or attempt.query != raw_trimmed
            or bool(attempt.description)
        )

    def _apply_relevance_scoring(
        self,
        result: SearchResult,
        params: SearchParams,
    ) -> SearchResult:
        if result.is_empty:
            return result

        if params.sort != SortOrder.RELEVANCE:
            return result

        prefs = get_prefs()
        recent_titles = prefs.search.recent_clicked_titles
        recent_shops = prefs.search.recent_clicked_shops

        score_weights = self._relevance_config.score
        buckets = self._relevance_config.buckets

        scored_items = []
        for index, item in enumerate(result.items):
            score, matched_tokens = compute_relevance_score(
                title=item.name,
                shop_name=item.shop_name,
                avatar_name=params.avatar_name,
                positive_keywords=self._relevance_config.positive_keywords,
                negative_keywords=self._relevance_config.negative_keywords,
                unrelated_keywords=self._relevance_config.unrelated_keywords,
                score_weights=score_weights,
                recent_clicked_titles=recent_titles,
                recent_clicked_shops=recent_shops,
            )
            label = score_to_label(score, buckets)
            scored_item = replace(
                item,
                relevance_score=score,
                relevance_label=label,
                matched_tokens=matched_tokens,
            )
            scored_items.append((score, index, scored_item))

        scored_items.sort(key=lambda entry: (-entry[0], entry[1]))
        result.items = [item for _, __, item in scored_items]
        return result

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

    def _verify_top_items(
        self,
        result: SearchResult,
        params: SearchParams,
        cancel_check: Optional[Callable[[], bool]] = None,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> SearchResult:
        if result.is_empty:
            return result

        if BeautifulSoup is None:
            logger.warning("BeautifulSoup 미설치: 정확도 검증 모드 비활성")
            return result

        top_n = min(params.verify_top_n, len(result.items))
        if top_n <= 0:
            return result

        verified_map: Dict[str, bool] = {}
        for idx, item in enumerate(result.items[:top_n], start=1):
            if cancel_check and cancel_check():
                logger.info("검색 취소됨 (검증 중)")
                break

            if progress_callback:
                progress_callback(f"정확도 검증 중... ({idx}/{top_n})")

            cached = self._get_cached_verification(item.id)
            if cached is None:
                html = self.client.get_item_page(item.id)
                verified = self._check_avatar_in_description(html, params.avatar_name)
                self._set_cached_verification(item.id, verified)
            else:
                verified = cached

            verified_map[item.id] = verified

        if not verified_map:
            return result

        updated_items = []
        for item in result.items:
            verified = verified_map.get(item.id, item.verified_in_description)
            updated_items.append(replace(item, verified_in_description=verified))

        result.items = updated_items
        return result

    def _check_avatar_in_description(self, html: str, avatar_name: str) -> bool:
        soup = BeautifulSoup(html, "html.parser")
        selectors = [
            ".item-description",
            ".item-description__text",
            ".js-item-description",
            ".item-detail__description",
            ".description",
        ]
        description_text = ""
        for selector in selectors:
            elem = soup.select_one(selector)
            if elem:
                description_text = elem.get_text(separator=" ", strip=True)
                if description_text:
                    break

        if not description_text:
            description_text = soup.get_text(separator=" ", strip=True)

        avatar_tokens = tokenize_query(avatar_name)
        description_norm = normalize_query(description_text).lower()

        for token in avatar_tokens:
            token_norm = normalize_query(token).lower()
            if token_norm and token_norm in description_norm:
                return True

        return False

    def _get_cached_verification(self, item_id: str) -> Optional[bool]:
        if not item_id:
            return None

        cached = self._detail_verify_cache.get(item_id)
        if not cached:
            return None

        verified, timestamp = cached
        if time.time() - timestamp > self._detail_cache_ttl:
            self._detail_verify_cache.pop(item_id, None)
            return None

        return verified

    def _set_cached_verification(self, item_id: str, verified: bool) -> None:
        if not item_id:
            return
        self._detail_verify_cache[item_id] = (verified, time.time())

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
        result = self.search_with_fallback(params, use_cache=use_cache)

        if result.is_empty or not result.has_next:
            return result

        # 추가 페이지
        current_page = params.page + 1
        while current_page <= min(params.page + max_pages - 1, result.total_pages):
            next_params = params.with_avatar_name(result.resolved_query or params.avatar_name).with_page(current_page)
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
