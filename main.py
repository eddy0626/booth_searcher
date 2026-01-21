#!/usr/bin/env python3
"""
Booth VRChat 의상 검색기
메인 실행 파일
"""

import sys
import os

# PyInstaller로 빌드된 경우 경로 처리
if getattr(sys, 'frozen', False):
    # 실행 파일 경로
    application_path = os.path.dirname(sys.executable)
else:
    # 스크립트 경로
    application_path = os.path.dirname(os.path.abspath(__file__))

# 모듈 경로 추가
sys.path.insert(0, application_path)

from gui import run_app


def main():
    """메인 함수"""
    print("Booth VRChat 의상 검색기를 시작합니다...")
    run_app()


if __name__ == "__main__":
    main()
