"""
이미지 캐시 시스템

2단계 캐시:
- 메모리: LRU 캐시 (빠른 접근)
- 디스크: 파일 캐시 (영속성)
"""

from typing import Optional
from collections import OrderedDict
from pathlib import Path
import hashlib
import threading
import time

from config.settings import Settings
from utils.paths import get_image_cache_dir
from utils.logging import get_logger

logger = get_logger(__name__)


class ImageCache:
    """
    2단계 이미지 캐시 (메모리 + 디스크)

    - 메모리: OrderedDict 기반 LRU (기본 50MB)
    - 디스크: 파일 기반 캐시 (기본 500MB)

    사용법:
        cache = ImageCache(settings)

        # 캐시에서 가져오기
        data = cache.get(url)

        # 캐시에 저장
        cache.put(url, image_data)

        # 캐시 정리
        cache.clear()
    """

    def __init__(self, settings: Optional[Settings] = None):
        if settings is None:
            settings = Settings()

        self.settings = settings

        # 메모리 캐시 설정
        self.memory_max_size = settings.cache.image_memory_mb * 1024 * 1024
        self._memory_cache: OrderedDict[str, bytes] = OrderedDict()
        self._memory_size = 0

        # 디스크 캐시 설정
        self.disk_max_size = settings.cache.image_disk_mb * 1024 * 1024
        self._disk_dir = get_image_cache_dir()
        self._disk_dir.mkdir(parents=True, exist_ok=True)

        # 스레드 안전성
        self._lock = threading.RLock()

        # 통계
        self._hits = 0
        self._misses = 0

        logger.info(
            f"ImageCache 초기화: memory={settings.cache.image_memory_mb}MB, "
            f"disk={settings.cache.image_disk_mb}MB"
        )

    def get(self, url: str) -> Optional[bytes]:
        """
        캐시에서 이미지 조회

        Args:
            url: 이미지 URL

        Returns:
            이미지 데이터 또는 None
        """
        if not url:
            return None

        key = self._url_to_key(url)

        with self._lock:
            # 1. 메모리 캐시 확인
            if key in self._memory_cache:
                # LRU: 최근 사용으로 이동
                self._memory_cache.move_to_end(key)
                self._hits += 1
                logger.debug(f"Memory cache hit: {key[:8]}...")
                return self._memory_cache[key]

        # 2. 디스크 캐시 확인 (락 외부에서 I/O)
        disk_path = self._disk_dir / key
        if disk_path.exists():
            try:
                data = disk_path.read_bytes()

                # 메모리 캐시에 추가
                with self._lock:
                    self._add_to_memory(key, data)
                    self._hits += 1

                logger.debug(f"Disk cache hit: {key[:8]}...")
                return data

            except IOError as e:
                logger.warning(f"Disk cache read failed: {e}")

        with self._lock:
            self._misses += 1

        return None

    def put(self, url: str, data: bytes) -> None:
        """
        캐시에 이미지 저장

        Args:
            url: 이미지 URL
            data: 이미지 데이터
        """
        if not url or not data:
            return

        key = self._url_to_key(url)

        # 메모리 캐시에 추가
        with self._lock:
            self._add_to_memory(key, data)

        # 디스크 캐시에 저장 (백그라운드에서 해도 됨)
        try:
            disk_path = self._disk_dir / key
            disk_path.write_bytes(data)
            logger.debug(f"Disk cache write: {key[:8]}... ({len(data)} bytes)")
        except IOError as e:
            logger.warning(f"Disk cache write failed: {e}")

    def _add_to_memory(self, key: str, data: bytes) -> None:
        """메모리 캐시에 추가 (LRU 정책)"""
        size = len(data)

        # 이미 존재하면 크기 업데이트
        if key in self._memory_cache:
            old_size = len(self._memory_cache[key])
            self._memory_size -= old_size
            del self._memory_cache[key]

        # 용량 확보 (LRU eviction)
        while self._memory_size + size > self.memory_max_size and self._memory_cache:
            oldest_key, oldest_data = self._memory_cache.popitem(last=False)
            self._memory_size -= len(oldest_data)
            logger.debug(f"Memory cache evict: {oldest_key[:8]}...")

        # 추가
        self._memory_cache[key] = data
        self._memory_size += size

    def _url_to_key(self, url: str) -> str:
        """URL을 캐시 키로 변환 (SHA256 해시)"""
        return hashlib.sha256(url.encode()).hexdigest()[:32]

    def contains(self, url: str) -> bool:
        """캐시에 URL이 존재하는지 확인"""
        if not url:
            return False

        key = self._url_to_key(url)

        with self._lock:
            if key in self._memory_cache:
                return True

        return (self._disk_dir / key).exists()

    def remove(self, url: str) -> bool:
        """캐시에서 URL 제거"""
        if not url:
            return False

        key = self._url_to_key(url)
        removed = False

        with self._lock:
            if key in self._memory_cache:
                data = self._memory_cache.pop(key)
                self._memory_size -= len(data)
                removed = True

        disk_path = self._disk_dir / key
        if disk_path.exists():
            try:
                disk_path.unlink()
                removed = True
            except IOError:
                pass

        return removed

    def clear(self) -> None:
        """캐시 전체 삭제"""
        # 메모리 캐시 삭제
        with self._lock:
            self._memory_cache.clear()
            self._memory_size = 0
            self._hits = 0
            self._misses = 0

        # 디스크 캐시 삭제
        try:
            for f in self._disk_dir.glob("*"):
                if f.is_file():
                    f.unlink()
            logger.info("Image cache cleared")
        except IOError as e:
            logger.warning(f"Disk cache clear failed: {e}")

    def clear_memory(self) -> None:
        """메모리 캐시만 삭제"""
        with self._lock:
            self._memory_cache.clear()
            self._memory_size = 0
            logger.info("Memory cache cleared")

    def get_stats(self) -> dict:
        """캐시 통계 반환"""
        with self._lock:
            total = self._hits + self._misses
            hit_rate = (self._hits / total * 100) if total > 0 else 0

            # 디스크 캐시 크기 계산
            disk_size = sum(
                f.stat().st_size for f in self._disk_dir.glob("*") if f.is_file()
            )

            return {
                "memory_size_mb": round(self._memory_size / 1024 / 1024, 2),
                "memory_max_mb": self.settings.cache.image_memory_mb,
                "memory_items": len(self._memory_cache),
                "disk_size_mb": round(disk_size / 1024 / 1024, 2),
                "disk_max_mb": self.settings.cache.image_disk_mb,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": round(hit_rate, 1),
            }

    def cleanup_disk(self, max_age_days: int = 7) -> int:
        """
        오래된 디스크 캐시 정리

        Args:
            max_age_days: 최대 보관 일수

        Returns:
            삭제된 파일 수
        """
        cutoff = time.time() - (max_age_days * 24 * 60 * 60)
        removed = 0

        try:
            for f in self._disk_dir.glob("*"):
                if f.is_file() and f.stat().st_mtime < cutoff:
                    f.unlink()
                    removed += 1

            if removed > 0:
                logger.info(f"Disk cache cleanup: {removed} old files removed")

        except IOError as e:
            logger.warning(f"Disk cache cleanup failed: {e}")

        return removed

    def close(self) -> None:
        """리소스 정리 (필요 시)"""
        # 메모리 캐시만 정리 (디스크 캐시는 유지)
        self.clear_memory()
        logger.debug("ImageCache 종료")

    def __repr__(self) -> str:
        stats = self.get_stats()
        return (
            f"ImageCache(memory={stats['memory_size_mb']}/{stats['memory_max_mb']}MB, "
            f"disk={stats['disk_size_mb']}/{stats['disk_max_mb']}MB, "
            f"hit_rate={stats['hit_rate']}%)"
        )
