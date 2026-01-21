"""
Booth VRChat 의상 검색기 버전 정보
"""

__version__ = "2.0.0"
__app_name__ = "Booth VRChat 의상 검색기"
__app_name_en__ = "Booth VRChat Outfit Searcher"
__author__ = "Kim"
__description__ = "VRChat 아바타에 대응하는 의상을 Booth.pm에서 검색하는 데스크톱 애플리케이션"
__url__ = "https://github.com/kim/booth_searcher"
__license__ = "MIT"


def get_version() -> str:
    """버전 문자열 반환"""
    return __version__


def get_full_name() -> str:
    """앱 이름 + 버전 반환"""
    return f"{__app_name__} v{__version__}"


def get_user_agent() -> str:
    """HTTP User-Agent 문자열"""
    return f"{__app_name_en__}/{__version__}"
