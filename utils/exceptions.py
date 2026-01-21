"""
애플리케이션 예외 계층 정의

예외 계층 구조:
    BoothSearcherError (기본 예외)
    ├── BoothClientError (HTTP 클라이언트)
    │   └── RateLimitError (요청 제한)
    ├── ParsingError (HTML 파싱)
    ├── CacheError (캐시 관련)
    └── ConfigError (설정 관련)
"""

from typing import Optional


class BoothSearcherError(Exception):
    """
    애플리케이션 기본 예외

    모든 커스텀 예외의 부모 클래스
    """

    def __init__(self, message: str = "알 수 없는 오류가 발생했습니다"):
        self.message = message
        super().__init__(self.message)


class BoothClientError(BoothSearcherError):
    """
    HTTP 클라이언트 에러

    네트워크 요청 실패, 타임아웃, 서버 오류 등
    """

    def __init__(
        self,
        message: str = "HTTP 요청 중 오류가 발생했습니다",
        status_code: Optional[int] = None,
        url: Optional[str] = None,
    ):
        self.status_code = status_code
        self.url = url
        if status_code:
            message = f"{message} (상태 코드: {status_code})"
        if url:
            message = f"{message} - URL: {url}"
        super().__init__(message)


class RateLimitError(BoothClientError):
    """
    Rate Limit 초과 에러

    Booth.pm 요청 제한에 도달했을 때 발생
    """

    def __init__(
        self,
        retry_after: int = 60,
        message: str = "요청 제한에 도달했습니다",
    ):
        self.retry_after = retry_after
        message = f"{message}. {retry_after}초 후에 다시 시도하세요."
        super().__init__(message, status_code=429)


class ParsingError(BoothSearcherError):
    """
    HTML 파싱 에러

    Booth.pm 페이지 구조 변경, 예상치 못한 HTML 형식 등
    """

    def __init__(
        self,
        message: str = "HTML 파싱 중 오류가 발생했습니다",
        selector: Optional[str] = None,
        html_snippet: Optional[str] = None,
    ):
        self.selector = selector
        self.html_snippet = html_snippet
        if selector:
            message = f"{message} (셀렉터: {selector})"
        super().__init__(message)


class CacheError(BoothSearcherError):
    """
    캐시 관련 에러

    캐시 읽기/쓰기 실패, 손상된 캐시 데이터 등
    """

    def __init__(
        self,
        message: str = "캐시 작업 중 오류가 발생했습니다",
        cache_key: Optional[str] = None,
    ):
        self.cache_key = cache_key
        if cache_key:
            message = f"{message} (캐시 키: {cache_key})"
        super().__init__(message)


class ConfigError(BoothSearcherError):
    """
    설정 관련 에러

    설정 파일 로드 실패, 잘못된 설정 값 등
    """

    def __init__(
        self,
        message: str = "설정 오류가 발생했습니다",
        config_key: Optional[str] = None,
        config_value: Optional[str] = None,
    ):
        self.config_key = config_key
        self.config_value = config_value
        if config_key:
            message = f"{message} (설정 키: {config_key})"
        if config_value:
            message = f"{message} (값: {config_value})"
        super().__init__(message)


class SearchCancelledError(BoothSearcherError):
    """
    검색 취소 에러

    사용자가 검색을 취소했을 때 발생 (정상적인 흐름)
    """

    def __init__(self, message: str = "검색이 취소되었습니다"):
        super().__init__(message)


class ValidationError(BoothSearcherError):
    """
    입력값 검증 에러

    잘못된 검색어, 유효하지 않은 파라미터 등
    """

    def __init__(
        self,
        message: str = "입력값 검증에 실패했습니다",
        field: Optional[str] = None,
        value: Optional[str] = None,
    ):
        self.field = field
        self.value = value
        if field:
            message = f"{message} (필드: {field})"
        super().__init__(message)


# Alias for backward compatibility
BoothScraperError = BoothSearcherError
