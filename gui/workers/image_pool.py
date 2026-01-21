"""
이미지 로더 스레드 풀

다수의 썸네일 이미지를 병렬로 로드합니다.
캐시를 활용하여 반복 요청을 최소화합니다.
"""

from typing import Optional, Dict, Set
from concurrent.futures import ThreadPoolExecutor, Future
import urllib.request
import urllib.error
from functools import partial

from PyQt6.QtCore import QObject, pyqtSignal, QMutex, QMutexLocker
from PyQt6.QtGui import QPixmap, QImage

from cache.image_cache import ImageCache
from config.settings import Settings
from config.constants import DEFAULT_HEADERS
from utils.logging import get_logger

logger = get_logger(__name__)


class ImageLoaderPool(QObject):
    """
    이미지 로더 스레드 풀

    특징:
    - ThreadPoolExecutor 기반 병렬 다운로드
    - ImageCache와 통합 (메모리 + 디스크 캐시)
    - 중복 요청 방지
    - 우선순위 기반 취소 (viewport에 있는 이미지 우선)

    시그널:
        image_loaded: 이미지 로드 완료 (url, QPixmap)
        image_error: 이미지 로드 실패 (url, error_message)

    사용법:
        pool = ImageLoaderPool(settings)
        pool.image_loaded.connect(on_image_loaded)

        # 이미지 요청
        pool.request_image(url)

        # 요청 취소
        pool.cancel_request(url)

        # 모든 요청 취소
        pool.cancel_all()
    """

    # 시그널 정의
    image_loaded = pyqtSignal(str, QPixmap)  # url, pixmap
    image_error = pyqtSignal(str, str)  # url, error_message

    def __init__(
        self,
        settings: Optional[Settings] = None,
        image_cache: Optional[ImageCache] = None,
        max_workers: int = 4,
        parent=None,
    ):
        super().__init__(parent)

        self.settings = settings or Settings()
        self.max_workers = max_workers

        # 이미지 캐시 (외부 주입 또는 생성)
        self._own_cache = image_cache is None
        self.image_cache = image_cache or ImageCache(self.settings)

        # 스레드 풀
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="ImageLoader",
        )

        # 진행 중인 요청 관리
        self._pending_urls: Set[str] = set()  # 요청 대기 중
        self._futures: Dict[str, Future] = {}  # url -> Future
        self._mutex = QMutex()

        # 통계
        self._total_requests = 0
        self._cache_hits = 0
        self._downloads = 0
        self._errors = 0

        logger.info(f"ImageLoaderPool 초기화: max_workers={max_workers}")

    def request_image(self, url: str, priority: bool = False) -> bool:
        """
        이미지 로드 요청

        Args:
            url: 이미지 URL
            priority: 우선 처리 여부 (현재 미구현)

        Returns:
            True면 새 요청, False면 이미 진행 중
        """
        if not url:
            return False

        with QMutexLocker(self._mutex):
            self._total_requests += 1

            # 이미 요청 중이면 무시
            if url in self._pending_urls:
                return False

            # 캐시 확인 (동기)
            cached_data = self.image_cache.get(url)
            if cached_data is not None:
                self._cache_hits += 1
                # 캐시 히트 - 즉시 시그널 발송
                pixmap = self._bytes_to_pixmap(cached_data)
                if pixmap and not pixmap.isNull():
                    self.image_loaded.emit(url, pixmap)
                    return True

            # 새 요청 등록
            self._pending_urls.add(url)

        # 비동기 다운로드 요청
        future = self._executor.submit(self._download_image, url)
        future.add_done_callback(partial(self._on_download_complete, url))

        with QMutexLocker(self._mutex):
            self._futures[url] = future

        return True

    def request_images(self, urls: list) -> int:
        """
        여러 이미지 일괄 요청

        Args:
            urls: 이미지 URL 목록

        Returns:
            새로 요청된 이미지 수
        """
        count = 0
        for url in urls:
            if self.request_image(url):
                count += 1
        return count

    def cancel_request(self, url: str) -> bool:
        """
        특정 요청 취소

        Args:
            url: 취소할 이미지 URL

        Returns:
            취소 성공 여부
        """
        with QMutexLocker(self._mutex):
            if url in self._futures:
                future = self._futures[url]
                cancelled = future.cancel()
                if cancelled:
                    self._pending_urls.discard(url)
                    del self._futures[url]
                    logger.debug(f"이미지 요청 취소: {url[:50]}...")
                return cancelled
        return False

    def cancel_all(self) -> int:
        """
        모든 요청 취소

        Returns:
            취소된 요청 수
        """
        count = 0
        with QMutexLocker(self._mutex):
            for url, future in list(self._futures.items()):
                if future.cancel():
                    count += 1
            self._pending_urls.clear()
            self._futures.clear()

        logger.info(f"모든 이미지 요청 취소: {count}개")
        return count

    def is_pending(self, url: str) -> bool:
        """요청이 진행 중인지 확인"""
        with QMutexLocker(self._mutex):
            return url in self._pending_urls

    def _download_image(self, url: str) -> Optional[bytes]:
        """
        이미지 다운로드 (워커 스레드에서 실행)

        Args:
            url: 이미지 URL

        Returns:
            이미지 바이트 데이터 또는 None
        """
        try:
            request = urllib.request.Request(url, headers=DEFAULT_HEADERS)

            with urllib.request.urlopen(request, timeout=10) as response:
                return response.read()

        except urllib.error.URLError as e:
            logger.debug(f"이미지 다운로드 실패: {url[:50]}... - {e}")
            return None
        except Exception as e:
            logger.debug(f"이미지 다운로드 에러: {url[:50]}... - {e}")
            return None

    def _on_download_complete(self, url: str, future: Future) -> None:
        """
        다운로드 완료 콜백 (워커 스레드에서 호출)

        Args:
            url: 이미지 URL
            future: 완료된 Future
        """
        # 요청 제거
        with QMutexLocker(self._mutex):
            self._pending_urls.discard(url)
            self._futures.pop(url, None)

        # 취소된 경우
        if future.cancelled():
            return

        try:
            data = future.result()

            if data is None:
                with QMutexLocker(self._mutex):
                    self._errors += 1
                self.image_error.emit(url, "다운로드 실패")
                return

            # 캐시에 저장
            self.image_cache.put(url, data)

            # QPixmap 변환
            pixmap = self._bytes_to_pixmap(data)

            if pixmap and not pixmap.isNull():
                with QMutexLocker(self._mutex):
                    self._downloads += 1
                self.image_loaded.emit(url, pixmap)
            else:
                with QMutexLocker(self._mutex):
                    self._errors += 1
                self.image_error.emit(url, "이미지 변환 실패")

        except Exception as e:
            with QMutexLocker(self._mutex):
                self._errors += 1
            self.image_error.emit(url, str(e))

    def _bytes_to_pixmap(self, data: bytes) -> Optional[QPixmap]:
        """바이트 데이터를 QPixmap으로 변환"""
        try:
            image = QImage()
            if image.loadFromData(data):
                return QPixmap.fromImage(image)
        except Exception as e:
            logger.debug(f"이미지 변환 실패: {e}")
        return None

    def get_stats(self) -> dict:
        """통계 반환"""
        with QMutexLocker(self._mutex):
            total = self._total_requests
            hit_rate = (self._cache_hits / total * 100) if total > 0 else 0

            return {
                "total_requests": self._total_requests,
                "cache_hits": self._cache_hits,
                "downloads": self._downloads,
                "errors": self._errors,
                "pending": len(self._pending_urls),
                "hit_rate": round(hit_rate, 1),
                "image_cache": self.image_cache.get_stats(),
            }

    def clear_cache(self) -> None:
        """캐시 초기화"""
        self.image_cache.clear()

    def close(self) -> None:
        """리소스 정리"""
        # 모든 요청 취소
        self.cancel_all()

        # 스레드 풀 종료
        self._executor.shutdown(wait=False)

        # 자체 생성한 캐시면 정리
        if self._own_cache:
            self.image_cache.close()

        logger.debug("ImageLoaderPool 종료")

    def __del__(self):
        self.close()

    def __repr__(self) -> str:
        stats = self.get_stats()
        return (
            f"ImageLoaderPool(pending={stats['pending']}, "
            f"hit_rate={stats['hit_rate']}%)"
        )
