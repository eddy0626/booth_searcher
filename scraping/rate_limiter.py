"""
Rate Limiter - 요청 제한기

Token Bucket 알고리즘 기반의 Rate Limiter
Booth.pm 차단 방지를 위한 요청 속도 제어
"""

import time
import threading
from collections import deque
from typing import Optional

from utils.logging import get_logger

logger = get_logger(__name__)


class RateLimiter:
    """
    Token Bucket 기반 Rate Limiter

    분당 요청 수와 버스트 제한을 통해 요청 속도를 제어합니다.

    사용법:
        limiter = RateLimiter(requests_per_minute=30, burst_limit=5)

        # 요청 전 호출 (필요시 자동 대기)
        limiter.acquire()
        response = requests.get(url)

    Args:
        requests_per_minute: 분당 최대 요청 수
        burst_limit: 연속 요청 허용 수 (버스트)
    """

    def __init__(
        self,
        requests_per_minute: int = 30,
        burst_limit: int = 5,
    ):
        self.requests_per_minute = requests_per_minute
        self.burst_limit = burst_limit

        # 요청 간 최소 간격 (초)
        self.min_interval = 60.0 / requests_per_minute

        # 요청 타임스탬프 기록 (슬라이딩 윈도우)
        self.timestamps: deque = deque(maxlen=requests_per_minute)

        # 스레드 안전을 위한 락
        self._lock = threading.Lock()

        # 통계
        self._total_requests = 0
        self._total_wait_time = 0.0

        logger.debug(
            f"RateLimiter 초기화: {requests_per_minute} req/min, burst={burst_limit}"
        )

    def acquire(self, timeout: Optional[float] = None) -> bool:
        """
        요청 슬롯 획득

        필요한 경우 대기 후 True 반환.
        timeout이 설정되고 시간 내에 획득 실패 시 False 반환.

        Args:
            timeout: 최대 대기 시간 (초), None이면 무한 대기

        Returns:
            슬롯 획득 성공 여부
        """
        start_time = time.monotonic()

        with self._lock:
            now = time.monotonic()
            wait_time = self._calculate_wait_time(now)

            # 타임아웃 체크
            if timeout is not None and wait_time > timeout:
                logger.warning(f"Rate limit timeout: 필요 대기시간 {wait_time:.2f}s > timeout {timeout}s")
                return False

            # 대기가 필요하면 대기
            if wait_time > 0:
                logger.debug(f"Rate limiting: {wait_time:.2f}초 대기")
                self._total_wait_time += wait_time

                # 락 해제 후 대기 (다른 스레드 블록 방지)
                self._lock.release()
                try:
                    time.sleep(wait_time)
                finally:
                    self._lock.acquire()

                now = time.monotonic()

            # 타임스탬프 기록
            self.timestamps.append(now)
            self._total_requests += 1

            return True

    def _calculate_wait_time(self, now: float) -> float:
        """
        필요한 대기 시간 계산

        Args:
            now: 현재 시간 (monotonic)

        Returns:
            대기 시간 (초)
        """
        if not self.timestamps:
            return 0.0

        wait_time = 0.0

        # 1. 버스트 제한 체크
        if len(self.timestamps) >= self.burst_limit:
            # 버스트 윈도우 시작 시점
            burst_window_start = self.timestamps[-self.burst_limit]
            burst_window_elapsed = now - burst_window_start
            burst_window_duration = self.min_interval * self.burst_limit

            if burst_window_elapsed < burst_window_duration:
                wait_time = max(wait_time, burst_window_duration - burst_window_elapsed)

        # 2. 분당 제한 체크 (슬라이딩 윈도우)
        if len(self.timestamps) >= self.requests_per_minute:
            oldest = self.timestamps[0]
            window_elapsed = now - oldest

            if window_elapsed < 60.0:
                # 1분 윈도우 내에 이미 최대 요청 수 도달
                wait_time = max(wait_time, 60.0 - window_elapsed)

        # 3. 최소 간격 체크
        if self.timestamps:
            last = self.timestamps[-1]
            elapsed_since_last = now - last

            if elapsed_since_last < self.min_interval:
                wait_time = max(wait_time, self.min_interval - elapsed_since_last)

        return wait_time

    def get_stats(self) -> dict:
        """
        Rate Limiter 통계 반환

        Returns:
            통계 딕셔너리
        """
        with self._lock:
            return {
                "total_requests": self._total_requests,
                "total_wait_time": round(self._total_wait_time, 2),
                "avg_wait_time": (
                    round(self._total_wait_time / self._total_requests, 2)
                    if self._total_requests > 0
                    else 0
                ),
                "requests_per_minute": self.requests_per_minute,
                "burst_limit": self.burst_limit,
                "current_window_size": len(self.timestamps),
            }

    def reset(self) -> None:
        """
        Rate Limiter 상태 리셋
        """
        with self._lock:
            self.timestamps.clear()
            self._total_requests = 0
            self._total_wait_time = 0.0
            logger.debug("RateLimiter 리셋")

    def is_limited(self) -> bool:
        """
        현재 제한 상태인지 확인 (대기 없이)

        Returns:
            True면 다음 요청 시 대기 필요
        """
        with self._lock:
            now = time.monotonic()
            return self._calculate_wait_time(now) > 0

    def remaining_in_window(self) -> int:
        """
        현재 윈도우에서 남은 요청 수

        Returns:
            남은 요청 수
        """
        with self._lock:
            now = time.monotonic()

            # 1분 윈도우 내의 요청 수 계산
            window_start = now - 60.0
            active_count = sum(1 for ts in self.timestamps if ts > window_start)

            return max(0, self.requests_per_minute - active_count)

    def __repr__(self) -> str:
        stats = self.get_stats()
        return (
            f"RateLimiter(rpm={self.requests_per_minute}, "
            f"burst={self.burst_limit}, "
            f"requests={stats['total_requests']})"
        )


class NoOpRateLimiter(RateLimiter):
    """
    테스트용 No-op Rate Limiter

    실제 제한 없이 즉시 통과
    """

    def __init__(self):
        super().__init__(requests_per_minute=9999, burst_limit=9999)

    def acquire(self, timeout: Optional[float] = None) -> bool:
        return True

    def _calculate_wait_time(self, now: float) -> float:
        return 0.0
