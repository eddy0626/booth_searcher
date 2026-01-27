"""
애플리케이션 설정 관리

dataclass 기반 설정 시스템
- JSON 파일 저장/로드
- 환경변수 오버라이드
- 기본값 제공
"""

from dataclasses import dataclass, field, asdict
from typing import Optional
from pathlib import Path
import json
import os
import threading

from .constants import (
    DEFAULT_TIMEOUT,
    DEFAULT_MAX_RETRIES,
    DEFAULT_BACKOFF_FACTOR,
    DEFAULT_REQUESTS_PER_MINUTE,
    DEFAULT_BURST_LIMIT,
    DEFAULT_IMAGE_CACHE_MEMORY_MB,
    DEFAULT_IMAGE_CACHE_DISK_MB,
    DEFAULT_RESULT_CACHE_TTL_MINUTES,
    DEFAULT_ITEMS_PER_PAGE,
    DEFAULT_IMAGE_LOAD_WORKERS,
    DEFAULT_WINDOW_WIDTH,
    DEFAULT_WINDOW_HEIGHT,
    DEFAULT_LOG_LEVEL,
    DEFAULT_LOG_FILE_SIZE_MB,
    DEFAULT_LOG_BACKUP_COUNT,
)


@dataclass
class ScrapingSettings:
    """스크래핑 관련 설정"""

    timeout: int = DEFAULT_TIMEOUT
    max_retries: int = DEFAULT_MAX_RETRIES
    backoff_factor: float = DEFAULT_BACKOFF_FACTOR
    requests_per_minute: int = DEFAULT_REQUESTS_PER_MINUTE
    burst_limit: int = DEFAULT_BURST_LIMIT

    def __post_init__(self):
        """유효성 검사 및 값 보정"""
        # timeout: 최소 1초, 최대 120초
        if self.timeout < 1:
            self.timeout = DEFAULT_TIMEOUT
        elif self.timeout > 120:
            self.timeout = 120

        # max_retries: 최소 0, 최대 10
        if self.max_retries < 0:
            self.max_retries = 0
        elif self.max_retries > 10:
            self.max_retries = 10

        # backoff_factor: 최소 0.1, 최대 10.0
        if self.backoff_factor < 0.1:
            self.backoff_factor = DEFAULT_BACKOFF_FACTOR
        elif self.backoff_factor > 10.0:
            self.backoff_factor = 10.0

        # requests_per_minute: 최소 1, 최대 120
        if self.requests_per_minute < 1:
            self.requests_per_minute = DEFAULT_REQUESTS_PER_MINUTE
        elif self.requests_per_minute > 120:
            self.requests_per_minute = 120

        # burst_limit: 최소 1, 최대 requests_per_minute
        if self.burst_limit < 1:
            self.burst_limit = 1
        elif self.burst_limit > self.requests_per_minute:
            self.burst_limit = self.requests_per_minute

    @classmethod
    def from_dict(cls, data: dict) -> "ScrapingSettings":
        return cls(
            timeout=data.get("timeout", DEFAULT_TIMEOUT),
            max_retries=data.get("max_retries", DEFAULT_MAX_RETRIES),
            backoff_factor=data.get("backoff_factor", DEFAULT_BACKOFF_FACTOR),
            requests_per_minute=data.get("requests_per_minute", DEFAULT_REQUESTS_PER_MINUTE),
            burst_limit=data.get("burst_limit", DEFAULT_BURST_LIMIT),
        )


@dataclass
class CacheSettings:
    """캐시 관련 설정"""

    image_memory_mb: int = DEFAULT_IMAGE_CACHE_MEMORY_MB
    image_disk_mb: int = DEFAULT_IMAGE_CACHE_DISK_MB
    result_ttl_minutes: int = DEFAULT_RESULT_CACHE_TTL_MINUTES

    def __post_init__(self):
        """유효성 검사 및 값 보정"""
        # image_memory_mb: 최소 10MB, 최대 500MB
        if self.image_memory_mb < 10:
            self.image_memory_mb = 10
        elif self.image_memory_mb > 500:
            self.image_memory_mb = 500

        # image_disk_mb: 최소 50MB, 최대 5000MB
        if self.image_disk_mb < 50:
            self.image_disk_mb = 50
        elif self.image_disk_mb > 5000:
            self.image_disk_mb = 5000

        # result_ttl_minutes: 최소 1분, 최대 1440분 (1일)
        if self.result_ttl_minutes < 1:
            self.result_ttl_minutes = 1
        elif self.result_ttl_minutes > 1440:
            self.result_ttl_minutes = 1440

    @classmethod
    def from_dict(cls, data: dict) -> "CacheSettings":
        return cls(
            image_memory_mb=data.get("image_memory_mb", DEFAULT_IMAGE_CACHE_MEMORY_MB),
            image_disk_mb=data.get("image_disk_mb", DEFAULT_IMAGE_CACHE_DISK_MB),
            result_ttl_minutes=data.get("result_ttl_minutes", DEFAULT_RESULT_CACHE_TTL_MINUTES),
        )


@dataclass
class UISettings:
    """UI 관련 설정"""

    items_per_page: int = DEFAULT_ITEMS_PER_PAGE
    image_load_workers: int = DEFAULT_IMAGE_LOAD_WORKERS
    window_width: int = DEFAULT_WINDOW_WIDTH
    window_height: int = DEFAULT_WINDOW_HEIGHT

    def __post_init__(self):
        """유효성 검사 및 값 보정"""
        # items_per_page: 최소 6, 최대 100
        if self.items_per_page < 6:
            self.items_per_page = 6
        elif self.items_per_page > 100:
            self.items_per_page = 100

        # image_load_workers: 최소 1, 최대 16
        if self.image_load_workers < 1:
            self.image_load_workers = 1
        elif self.image_load_workers > 16:
            self.image_load_workers = 16

        # window_width: 최소 400, 최대 4000
        if self.window_width < 400:
            self.window_width = 400
        elif self.window_width > 4000:
            self.window_width = 4000

        # window_height: 최소 300, 최대 3000
        if self.window_height < 300:
            self.window_height = 300
        elif self.window_height > 3000:
            self.window_height = 3000

    @classmethod
    def from_dict(cls, data: dict) -> "UISettings":
        return cls(
            items_per_page=data.get("items_per_page", DEFAULT_ITEMS_PER_PAGE),
            image_load_workers=data.get("image_load_workers", DEFAULT_IMAGE_LOAD_WORKERS),
            window_width=data.get("window_width", DEFAULT_WINDOW_WIDTH),
            window_height=data.get("window_height", DEFAULT_WINDOW_HEIGHT),
        )


@dataclass
class LoggingSettings:
    """로깅 관련 설정"""

    level: str = DEFAULT_LOG_LEVEL
    file_enabled: bool = True
    max_file_size_mb: int = DEFAULT_LOG_FILE_SIZE_MB
    backup_count: int = DEFAULT_LOG_BACKUP_COUNT

    @classmethod
    def from_dict(cls, data: dict) -> "LoggingSettings":
        return cls(
            level=data.get("level", DEFAULT_LOG_LEVEL),
            file_enabled=data.get("file_enabled", True),
            max_file_size_mb=data.get("max_file_size_mb", DEFAULT_LOG_FILE_SIZE_MB),
            backup_count=data.get("backup_count", DEFAULT_LOG_BACKUP_COUNT),
        )


@dataclass
class Settings:
    """
    애플리케이션 전체 설정

    사용법:
        # 기본 설정 로드
        settings = Settings.load()

        # 설정 접근
        timeout = settings.scraping.timeout

        # 설정 저장
        settings.save()
    """

    scraping: ScrapingSettings = field(default_factory=ScrapingSettings)
    cache: CacheSettings = field(default_factory=CacheSettings)
    ui: UISettings = field(default_factory=UISettings)
    logging: LoggingSettings = field(default_factory=LoggingSettings)

    def to_dict(self) -> dict:
        """설정을 딕셔너리로 변환"""
        return {
            "scraping": asdict(self.scraping),
            "cache": asdict(self.cache),
            "ui": asdict(self.ui),
            "logging": asdict(self.logging),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Settings":
        """딕셔너리에서 설정 생성"""
        return cls(
            scraping=ScrapingSettings.from_dict(data.get("scraping", {})),
            cache=CacheSettings.from_dict(data.get("cache", {})),
            ui=UISettings.from_dict(data.get("ui", {})),
            logging=LoggingSettings.from_dict(data.get("logging", {})),
        )

    @classmethod
    def load(cls, config_path: Optional[Path] = None) -> "Settings":
        """
        설정 파일에서 로드

        Args:
            config_path: 설정 파일 경로 (None이면 기본 경로 사용)

        Returns:
            Settings 인스턴스
        """
        # 지연 import로 순환 참조 방지
        from utils.paths import get_settings_path

        if config_path is None:
            config_path = get_settings_path()

        settings = cls()

        # 파일에서 로드
        if config_path.exists():
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    settings = cls.from_dict(data)
            except (json.JSONDecodeError, IOError) as e:
                # 로드 실패 시 기본 설정 사용
                print(f"설정 파일 로드 실패, 기본 설정 사용: {e}")

        # 환경변수 오버라이드
        settings = cls._apply_env_overrides(settings)

        return settings

    @classmethod
    def _apply_env_overrides(cls, settings: "Settings") -> "Settings":
        """환경변수로 설정 오버라이드"""
        # BOOTH_ 접두사 환경변수 처리
        env_mappings = {
            "BOOTH_TIMEOUT": ("scraping", "timeout", int),
            "BOOTH_MAX_RETRIES": ("scraping", "max_retries", int),
            "BOOTH_REQUESTS_PER_MINUTE": ("scraping", "requests_per_minute", int),
            "BOOTH_LOG_LEVEL": ("logging", "level", str),
            "BOOTH_CACHE_TTL": ("cache", "result_ttl_minutes", int),
        }

        for env_var, (section, key, type_fn) in env_mappings.items():
            value = os.environ.get(env_var)
            if value is not None:
                try:
                    section_obj = getattr(settings, section)
                    setattr(section_obj, key, type_fn(value))
                except (ValueError, AttributeError):
                    pass

        return settings

    def save(self, config_path: Optional[Path] = None) -> None:
        """
        설정을 파일에 저장

        Args:
            config_path: 저장할 경로 (None이면 기본 경로 사용)
        """
        from utils.paths import get_settings_path

        if config_path is None:
            config_path = get_settings_path()

        config_path.parent.mkdir(parents=True, exist_ok=True)

        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

    def __repr__(self) -> str:
        return f"Settings(scraping={self.scraping}, cache={self.cache}, ui={self.ui}, logging={self.logging})"


# 전역 설정 인스턴스 (싱글톤 패턴)
_settings_instance: Optional[Settings] = None
_settings_lock = threading.Lock()


def get_settings() -> Settings:
    """
    전역 설정 인스턴스 반환 (싱글톤, thread-safe)

    Returns:
        Settings 인스턴스
    """
    global _settings_instance
    if _settings_instance is None:
        with _settings_lock:
            # Double-checked locking
            if _settings_instance is None:
                _settings_instance = Settings.load()
    return _settings_instance


def reload_settings() -> Settings:
    """
    설정 다시 로드 (thread-safe)

    Returns:
        새로 로드된 Settings 인스턴스
    """
    global _settings_instance
    with _settings_lock:
        _settings_instance = Settings.load()
    return _settings_instance
