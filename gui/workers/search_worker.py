"""
취소 가능한 검색 워커

백그라운드 스레드에서 검색을 수행하고,
취소 요청 시 즉시 중단합니다.
"""

from typing import Optional
from PyQt6.QtCore import QThread, pyqtSignal, QMutex, QMutexLocker

from models.search_params import SearchParams
from models.search_result import SearchResult
from core.search_service import SearchService
from config.settings import Settings
from utils.logging import get_logger
from utils.exceptions import BoothSearcherError

logger = get_logger(__name__)


class SearchWorker(QThread):
    """
    취소 가능한 검색 워커

    시그널:
        started_signal: 검색 시작 (params)
        progress: 진행 상황 (current_page, total_pages, message)
        result_ready: 검색 결과 (SearchResult)
        error: 에러 발생 (error_message)
        cancelled: 검색 취소됨

    사용법:
        worker = SearchWorker(settings)
        worker.result_ready.connect(on_result)
        worker.error.connect(on_error)

        # 검색 시작
        worker.search(params)

        # 취소
        worker.cancel()
    """

    # 시그널 정의
    started_signal = pyqtSignal(SearchParams)
    progress = pyqtSignal(int, int, str)  # current, total, message
    result_ready = pyqtSignal(SearchResult)
    error = pyqtSignal(str)
    cancelled = pyqtSignal()

    def __init__(
        self,
        settings: Optional[Settings] = None,
        search_service: Optional[SearchService] = None,
        parent=None,
    ):
        super().__init__(parent)

        self.settings = settings or Settings()

        # 검색 서비스 (외부 주입 또는 생성)
        self._own_service = search_service is None
        self._search_service = search_service

        # 검색 파라미터 (run에서 사용)
        self._params: Optional[SearchParams] = None
        self._use_cache = True
        self._load_all_pages = False
        self._max_pages = 5

        # 취소 플래그
        self._cancel_requested = False
        self._mutex = QMutex()

        logger.debug("SearchWorker 초기화")

    @property
    def search_service(self) -> SearchService:
        """검색 서비스 (lazy initialization)"""
        if self._search_service is None:
            self._search_service = SearchService(self.settings)
        return self._search_service

    def search(
        self,
        params: SearchParams,
        use_cache: bool = True,
        load_all_pages: bool = False,
        max_pages: int = 5,
    ) -> None:
        """
        검색 시작

        Args:
            params: 검색 파라미터
            use_cache: 캐시 사용 여부
            load_all_pages: 모든 페이지 로드 여부
            max_pages: 최대 페이지 수 (load_all_pages=True일 때)
        """
        # 이미 실행 중이면 취소 후 재시작
        if self.isRunning():
            logger.debug("이전 검색 취소 후 새 검색 시작")
            self.cancel()
            self.wait()

        # 파라미터 설정
        self._params = params
        self._use_cache = use_cache
        self._load_all_pages = load_all_pages
        self._max_pages = max_pages

        # 취소 플래그 리셋
        with QMutexLocker(self._mutex):
            self._cancel_requested = False

        # 스레드 시작
        self.start()

    def cancel(self) -> None:
        """검색 취소 요청"""
        with QMutexLocker(self._mutex):
            if not self._cancel_requested:
                self._cancel_requested = True
                logger.debug("검색 취소 요청됨")

    def is_cancelled(self) -> bool:
        """취소 요청 확인"""
        with QMutexLocker(self._mutex):
            return self._cancel_requested

    def run(self) -> None:
        """검색 실행 (스레드에서 호출)"""
        if self._params is None:
            logger.error("검색 파라미터가 설정되지 않음")
            self.error.emit("검색 파라미터가 설정되지 않았습니다")
            return

        params = self._params

        try:
            # 시작 알림
            self.started_signal.emit(params)
            self.progress.emit(0, 0, f"'{params.avatar_name}' 검색 중...")

            logger.info(f"검색 시작: '{params.avatar_name}' (page={params.page})")

            # 취소 확인
            if self.is_cancelled():
                logger.info("검색 취소됨 (시작 전)")
                self.cancelled.emit()
                return

            # 검색 실행
            if self._load_all_pages:
                result = self._search_all_pages(params)
            else:
                result = self._search_single_page(params)

            # 취소 확인
            if self.is_cancelled():
                logger.info("검색 취소됨 (완료 후)")
                self.cancelled.emit()
                return

            # 결과 전송
            self.progress.emit(100, 100, "검색 완료")
            self.result_ready.emit(result)

            logger.info(
                f"검색 완료: '{params.avatar_name}' - "
                f"{len(result.items)}개 결과"
            )

        except BoothSearcherError as e:
            if not self.is_cancelled():
                logger.error(f"검색 에러: {e}")
                self.error.emit(str(e))
            else:
                self.cancelled.emit()

        except Exception as e:
            if not self.is_cancelled():
                logger.exception(f"검색 중 예외 발생: {e}")
                self.error.emit(f"검색 중 오류가 발생했습니다: {e}")
            else:
                self.cancelled.emit()

    def _search_single_page(self, params: SearchParams) -> SearchResult:
        """단일 페이지 검색"""
        self.progress.emit(params.page, params.page, f"페이지 {params.page} 로딩...")

        return self.search_service.search(
            params,
            use_cache=self._use_cache,
        )

    def _search_all_pages(self, params: SearchParams) -> SearchResult:
        """
        여러 페이지 검색 (무한 스크롤용)

        취소 가능하도록 페이지별로 취소 상태 확인
        """
        # 첫 페이지
        self.progress.emit(1, self._max_pages, f"페이지 1 로딩...")

        result = self.search_service.search(
            params,
            use_cache=self._use_cache,
        )

        if result.is_empty or not result.has_next:
            return result

        # 총 페이지 수 계산
        total_pages = min(self._max_pages, result.total_pages)

        # 추가 페이지
        current_page = params.page + 1
        while current_page <= total_pages:
            # 취소 확인
            if self.is_cancelled():
                logger.info(f"검색 취소됨 (페이지 {current_page})")
                break

            # 진행 상황 알림
            self.progress.emit(
                current_page,
                total_pages,
                f"페이지 {current_page}/{total_pages} 로딩...",
            )

            # 다음 페이지 검색
            next_params = params.with_page(current_page)
            next_result = self.search_service.search(
                next_params,
                use_cache=self._use_cache,
            )

            if next_result.is_empty:
                break

            # 결과 병합
            result = result.merge(next_result)
            current_page += 1

        return result

    def get_service_stats(self) -> dict:
        """검색 서비스 통계"""
        if self._search_service is not None:
            return self._search_service.get_stats()
        return {}

    def clear_cache(self) -> None:
        """캐시 초기화"""
        if self._search_service is not None:
            self._search_service.clear_cache()

    def close(self) -> None:
        """리소스 정리"""
        # 실행 중이면 취소
        if self.isRunning():
            self.cancel()
            self.wait(5000)  # 최대 5초 대기

        # 자체 생성한 서비스면 정리
        if self._own_service and self._search_service is not None:
            self._search_service.close()
            self._search_service = None

        logger.debug("SearchWorker 종료")

    def __del__(self):
        self.close()
