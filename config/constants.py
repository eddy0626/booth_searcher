"""
애플리케이션 상수 정의
"""

# Booth.pm 관련
BOOTH_BASE_URL = "https://booth.pm"
BOOTH_SEARCH_PATH = "/ko/search"
BOOTH_ITEMS_PATH = "/items"

# 기본 타임아웃 및 재시도
DEFAULT_TIMEOUT = 15  # 초
DEFAULT_MAX_RETRIES = 3
DEFAULT_BACKOFF_FACTOR = 1.0

# Rate Limiting
DEFAULT_REQUESTS_PER_MINUTE = 30
DEFAULT_BURST_LIMIT = 5

# 캐시 설정
DEFAULT_IMAGE_CACHE_MEMORY_MB = 50
DEFAULT_IMAGE_CACHE_DISK_MB = 500
DEFAULT_RESULT_CACHE_TTL_MINUTES = 30

# UI 설정
DEFAULT_ITEMS_PER_PAGE = 24
DEFAULT_IMAGE_LOAD_WORKERS = 4
DEFAULT_WINDOW_WIDTH = 900
DEFAULT_WINDOW_HEIGHT = 700

# 로깅 설정
DEFAULT_LOG_LEVEL = "INFO"
DEFAULT_LOG_FILE_SIZE_MB = 10
DEFAULT_LOG_BACKUP_COUNT = 3

# VRChat 관련 카테고리
BOOTH_CATEGORIES = {
    "전체": "",
    "3D 의상": "208",
    "3D 캐릭터": "217",
    "3D 액세서리": "209",
    "3D 모델": "207",
}

# User-Agent 풀 (로테이션용)
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

# HTTP 헤더
DEFAULT_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "ko-KR,ko;q=0.9,ja;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
    "Cache-Control": "no-cache",
}
