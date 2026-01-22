"""
로깅 시스템 설정

특징:
- 콘솔 + 파일 로깅 (RotatingFileHandler)
- 구조화된 포맷 (타임스탬프, 레벨, 모듈명)
- 외부 라이브러리 로깅 레벨 조정
"""

import logging
import logging.handlers
import time
from pathlib import Path
from typing import Optional
import sys

from .paths import get_log_dir

# 초기화 상태 플래그
_initialized = False

# 기본 설정값
DEFAULT_LOG_LEVEL = "INFO"
DEFAULT_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s"
DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
DEFAULT_MAX_BYTES = 10 * 1024 * 1024  # 10MB
DEFAULT_BACKUP_COUNT = 3


def setup_logging(
    level: str = DEFAULT_LOG_LEVEL,
    file_enabled: bool = True,
    max_file_size_mb: int = 10,
    backup_count: int = 3,
    log_file: Optional[Path] = None,
) -> None:
    """
    로깅 시스템 초기화

    Args:
        level: 로그 레벨 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        file_enabled: 파일 로깅 활성화 여부
        max_file_size_mb: 로그 파일 최대 크기 (MB)
        backup_count: 로그 파일 백업 개수
        log_file: 로그 파일 경로 (None이면 기본 경로 사용)
    """
    global _initialized

    if _initialized:
        return

    # 루트 로거 설정
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # 기존 핸들러 제거
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # 포맷터 생성
    formatter = logging.Formatter(
        fmt=DEFAULT_LOG_FORMAT,
        datefmt=DEFAULT_DATE_FORMAT,
    )

    # 콘솔 핸들러
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(getattr(logging, level.upper(), logging.INFO))
    root_logger.addHandler(console_handler)

    # 파일 핸들러 (로테이션)
    if file_enabled:
        if log_file is None:
            log_file = get_log_dir() / "app.log"

        log_file.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_file_size_mb * 1024 * 1024,
            backupCount=backup_count,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.DEBUG)  # 파일에는 모든 레벨 기록
        root_logger.addHandler(file_handler)

    # 외부 라이브러리 로깅 레벨 조정 (노이즈 감소)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("PIL").setLevel(logging.WARNING)
    logging.getLogger("PyQt6").setLevel(logging.WARNING)

    _initialized = True

    # 초기화 완료 로그
    logger = get_logger(__name__)
    logger.info(f"로깅 시스템 초기화 완료 (레벨: {level})")
    if file_enabled:
        logger.info(f"로그 파일: {log_file}")


def get_logger(name: str) -> logging.Logger:
    """
    모듈별 로거 반환

    Args:
        name: 로거 이름 (보통 __name__ 사용)

    Returns:
        Logger 인스턴스

    Example:
        logger = get_logger(__name__)
        logger.info("작업 시작")
        logger.error("오류 발생", exc_info=True)
    """
    return logging.getLogger(name)


def set_level(level: str) -> None:
    """
    로그 레벨 동적 변경

    Args:
        level: 새 로그 레벨
    """
    root_logger = logging.getLogger()
    new_level = getattr(logging, level.upper(), logging.INFO)
    root_logger.setLevel(new_level)

    for handler in root_logger.handlers:
        if isinstance(handler, logging.StreamHandler) and not isinstance(
            handler, logging.handlers.RotatingFileHandler
        ):
            handler.setLevel(new_level)

    get_logger(__name__).info(f"로그 레벨 변경: {level}")


def shutdown() -> None:
    """
    로깅 시스템 종료 (리소스 정리)
    """
    logging.shutdown()


def log_timing(
    logger: logging.Logger,
    label: str,
    start_time: float,
) -> float:
    """
    간단한 타이밍 로그 출력

    Args:
        logger: 사용할 로거
        label: 로그 라벨
        start_time: time.perf_counter() 시작 시각

    Returns:
        경과 시간 (ms)
    """
    elapsed_ms = (time.perf_counter() - start_time) * 1000.0
    logger.info(f"[timing] {label}: {elapsed_ms:.1f}ms")
    return elapsed_ms


class LogContext:
    """
    컨텍스트 매니저를 사용한 작업 로깅

    Example:
        with LogContext("검색 작업", avatar="桔梗"):
            # 작업 수행
            pass
    """

    def __init__(self, operation: str, logger: Optional[logging.Logger] = None, **context):
        self.operation = operation
        self.logger = logger or get_logger(__name__)
        self.context = context

    def __enter__(self):
        context_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
        if context_str:
            self.logger.info(f"[시작] {self.operation} ({context_str})")
        else:
            self.logger.info(f"[시작] {self.operation}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.logger.info(f"[완료] {self.operation}")
        else:
            self.logger.error(
                f"[실패] {self.operation}: {exc_type.__name__}: {exc_val}",
                exc_info=True,
            )
        return False  # 예외 전파
