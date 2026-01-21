"""
검색 결과 캐시 시스템

SQLite 기반 검색 결과 캐시:
- TTL 기반 만료
- 자동 정리
- 검색 파라미터별 캐싱
"""

import sqlite3
import json
import time
import threading
from typing import Optional
from pathlib import Path
from contextlib import contextmanager

from models.search_params import SearchParams
from models.search_result import SearchResult
from models.booth_item import BoothItem
from config.settings import Settings
from utils.paths import get_result_cache_path
from utils.logging import get_logger
from utils.exceptions import CacheError

logger = get_logger(__name__)


class ResultCache:
    """
    SQLite 기반 검색 결과 캐시

    - TTL 기반 만료 (기본 30분)
    - 자동 정리
    - 스레드 안전

    사용법:
        cache = ResultCache(settings)

        # 캐시에서 가져오기
        result = cache.get(params)

        # 캐시에 저장
        cache.put(params, result)

        # 만료된 캐시 정리
        cache.cleanup()
    """

    def __init__(self, settings: Optional[Settings] = None):
        if settings is None:
            settings = Settings()

        self.settings = settings
        self.ttl_seconds = settings.cache.result_ttl_minutes * 60

        self._db_path = get_result_cache_path()
        self._lock = threading.Lock()

        # 통계
        self._hits = 0
        self._misses = 0

        # DB 초기화
        self._init_db()

        logger.info(f"ResultCache 초기화: TTL={settings.cache.result_ttl_minutes}min")

    def _init_db(self) -> None:
        """데이터베이스 초기화"""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS search_cache (
                    cache_key TEXT PRIMARY KEY,
                    result_json TEXT NOT NULL,
                    query TEXT,
                    total_count INTEGER,
                    created_at REAL NOT NULL,
                    accessed_at REAL NOT NULL
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_created_at
                ON search_cache(created_at)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_query
                ON search_cache(query)
            """)

    @contextmanager
    def _get_connection(self):
        """SQLite 연결 컨텍스트 매니저"""
        conn = sqlite3.connect(str(self._db_path), timeout=5.0)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except sqlite3.Error as e:
            conn.rollback()
            raise CacheError(f"Database error: {e}")
        finally:
            conn.close()

    def get(self, params: SearchParams) -> Optional[SearchResult]:
        """
        캐시에서 검색 결과 조회

        Args:
            params: 검색 파라미터

        Returns:
            SearchResult 또는 None (캐시 미스/만료)
        """
        key = params.cache_key()
        now = time.time()

        with self._lock:
            try:
                with self._get_connection() as conn:
                    row = conn.execute(
                        "SELECT result_json, created_at FROM search_cache WHERE cache_key = ?",
                        (key,)
                    ).fetchone()

                    if not row:
                        self._misses += 1
                        return None

                    result_json, created_at = row["result_json"], row["created_at"]
                    age = now - created_at

                    # TTL 확인
                    if age > self.ttl_seconds:
                        conn.execute(
                            "DELETE FROM search_cache WHERE cache_key = ?",
                            (key,)
                        )
                        self._misses += 1
                        logger.debug(f"Cache expired: {key[:8]}... (age={age:.0f}s)")
                        return None

                    # 접근 시간 업데이트
                    conn.execute(
                        "UPDATE search_cache SET accessed_at = ? WHERE cache_key = ?",
                        (now, key)
                    )

                    # JSON 파싱
                    try:
                        data = json.loads(result_json)
                        result = SearchResult.from_dict(
                            data,
                            cached=True,
                            cache_age=int(age)
                        )
                        self._hits += 1
                        logger.debug(f"Cache hit: {key[:8]}... (age={age:.0f}s)")
                        return result

                    except (json.JSONDecodeError, KeyError) as e:
                        logger.warning(f"Cache parse error: {e}")
                        conn.execute(
                            "DELETE FROM search_cache WHERE cache_key = ?",
                            (key,)
                        )
                        self._misses += 1
                        return None

            except CacheError:
                self._misses += 1
                return None

    def put(self, params: SearchParams, result: SearchResult) -> None:
        """
        검색 결과 캐시에 저장

        Args:
            params: 검색 파라미터
            result: 검색 결과
        """
        key = params.cache_key()
        now = time.time()

        # 결과를 JSON으로 변환
        data = result.to_dict()
        result_json = json.dumps(data, ensure_ascii=False)

        with self._lock:
            try:
                with self._get_connection() as conn:
                    conn.execute(
                        """INSERT OR REPLACE INTO search_cache
                           (cache_key, result_json, query, total_count, created_at, accessed_at)
                           VALUES (?, ?, ?, ?, ?, ?)""",
                        (key, result_json, result.query, result.total_count, now, now)
                    )
                    logger.debug(
                        f"Cache put: {key[:8]}... ({len(result.items)} items)"
                    )

            except CacheError as e:
                logger.warning(f"Cache put failed: {e}")

    def invalidate(self, params: SearchParams) -> bool:
        """
        특정 검색 결과 캐시 무효화

        Args:
            params: 검색 파라미터

        Returns:
            삭제 성공 여부
        """
        key = params.cache_key()

        with self._lock:
            try:
                with self._get_connection() as conn:
                    result = conn.execute(
                        "DELETE FROM search_cache WHERE cache_key = ?",
                        (key,)
                    )
                    return result.rowcount > 0

            except CacheError:
                return False

    def invalidate_query(self, query: str) -> int:
        """
        특정 검색어의 모든 캐시 무효화

        Args:
            query: 검색어

        Returns:
            삭제된 캐시 수
        """
        with self._lock:
            try:
                with self._get_connection() as conn:
                    result = conn.execute(
                        "DELETE FROM search_cache WHERE query = ?",
                        (query,)
                    )
                    return result.rowcount

            except CacheError:
                return 0

    def cleanup(self) -> int:
        """
        만료된 캐시 정리

        Returns:
            삭제된 캐시 수
        """
        cutoff = time.time() - self.ttl_seconds

        with self._lock:
            try:
                with self._get_connection() as conn:
                    result = conn.execute(
                        "DELETE FROM search_cache WHERE created_at < ?",
                        (cutoff,)
                    )
                    count = result.rowcount

                    if count > 0:
                        logger.info(f"Cache cleanup: {count} expired entries removed")
                        # VACUUM으로 공간 회수
                        conn.execute("VACUUM")

                    return count

            except CacheError:
                return 0

    def clear(self) -> None:
        """캐시 전체 삭제"""
        with self._lock:
            try:
                with self._get_connection() as conn:
                    conn.execute("DELETE FROM search_cache")
                    conn.execute("VACUUM")
                    self._hits = 0
                    self._misses = 0
                    logger.info("Result cache cleared")

            except CacheError as e:
                logger.warning(f"Cache clear failed: {e}")

    def get_stats(self) -> dict:
        """캐시 통계 반환"""
        with self._lock:
            total = self._hits + self._misses
            hit_rate = (self._hits / total * 100) if total > 0 else 0

            try:
                with self._get_connection() as conn:
                    # 캐시 항목 수
                    count = conn.execute(
                        "SELECT COUNT(*) FROM search_cache"
                    ).fetchone()[0]

                    # 유효한 캐시 항목 수
                    cutoff = time.time() - self.ttl_seconds
                    valid_count = conn.execute(
                        "SELECT COUNT(*) FROM search_cache WHERE created_at >= ?",
                        (cutoff,)
                    ).fetchone()[0]

                    # DB 파일 크기
                    db_size = self._db_path.stat().st_size if self._db_path.exists() else 0

                    return {
                        "total_entries": count,
                        "valid_entries": valid_count,
                        "expired_entries": count - valid_count,
                        "db_size_kb": round(db_size / 1024, 2),
                        "ttl_minutes": self.settings.cache.result_ttl_minutes,
                        "hits": self._hits,
                        "misses": self._misses,
                        "hit_rate": round(hit_rate, 1),
                    }

            except (CacheError, OSError):
                return {
                    "total_entries": 0,
                    "valid_entries": 0,
                    "hits": self._hits,
                    "misses": self._misses,
                    "hit_rate": round(hit_rate, 1),
                }

    def get_recent_queries(self, limit: int = 10) -> list:
        """
        최근 검색어 목록 반환

        Args:
            limit: 최대 개수

        Returns:
            최근 검색어 목록
        """
        with self._lock:
            try:
                with self._get_connection() as conn:
                    rows = conn.execute(
                        """SELECT DISTINCT query FROM search_cache
                           ORDER BY accessed_at DESC LIMIT ?""",
                        (limit,)
                    ).fetchall()
                    return [row["query"] for row in rows]

            except CacheError:
                return []

    def __repr__(self) -> str:
        stats = self.get_stats()
        return (
            f"ResultCache(entries={stats['valid_entries']}, "
            f"hit_rate={stats['hit_rate']}%)"
        )
