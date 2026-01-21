#!/usr/bin/env python3
"""
PyInstaller 빌드 스크립트

사용법:
    python build.py          # 기본 빌드
    python build.py --onefile  # 단일 실행 파일
    python build.py --clean    # 빌드 캐시 삭제 후 빌드
"""

import os
import sys
import shutil
import subprocess
import argparse
from pathlib import Path

# 프로젝트 루트
PROJECT_ROOT = Path(__file__).parent
BUILD_DIR = PROJECT_ROOT / "build"
DIST_DIR = PROJECT_ROOT / "dist"


def get_version() -> str:
    """버전 정보 로드"""
    sys.path.insert(0, str(PROJECT_ROOT))
    from __version__ import __version__
    return __version__


def clean_build():
    """빌드 캐시 삭제"""
    print("빌드 캐시 삭제 중...")

    for path in [BUILD_DIR, DIST_DIR]:
        if path.exists():
            shutil.rmtree(path)
            print(f"  삭제: {path}")

    # __pycache__ 삭제
    for pycache in PROJECT_ROOT.rglob("__pycache__"):
        shutil.rmtree(pycache)

    print("완료")


def build(onefile: bool = False, console: bool = False):
    """PyInstaller 빌드 실행"""
    version = get_version()
    print(f"Booth VRChat 의상 검색기 v{version} 빌드 시작")
    print()

    # PyInstaller 명령 구성
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name", "BoothSearcher",
        "--windowed" if not console else "--console",
    ]

    if onefile:
        cmd.append("--onefile")
    else:
        cmd.append("--onedir")

    # 데이터 파일 추가
    data_files = [
        ("data/popular_avatars.json", "data"),
    ]

    for src, dst in data_files:
        src_path = PROJECT_ROOT / src
        if src_path.exists():
            cmd.extend(["--add-data", f"{src_path}{os.pathsep}{dst}"])

    # 숨겨진 임포트
    hidden_imports = [
        "PyQt6.QtWidgets",
        "PyQt6.QtCore",
        "PyQt6.QtGui",
        "bs4",
        "urllib3",
    ]

    for imp in hidden_imports:
        cmd.extend(["--hidden-import", imp])

    # 제외 모듈 (용량 줄이기)
    excludes = [
        "tkinter",
        "unittest",
        "email",
        "xml",
        "pydoc",
    ]

    for exc in excludes:
        cmd.extend(["--exclude-module", exc])

    # 아이콘 (있으면)
    icon_path = PROJECT_ROOT / "assets" / "icon.ico"
    if icon_path.exists():
        cmd.extend(["--icon", str(icon_path)])

    # 메인 스크립트
    cmd.append(str(PROJECT_ROOT / "main.py"))

    # 실행
    print("PyInstaller 실행 중...")
    print(f"  명령: {' '.join(cmd)}")
    print()

    result = subprocess.run(cmd, cwd=PROJECT_ROOT)

    if result.returncode == 0:
        print()
        print("빌드 성공!")
        print(f"  출력 위치: {DIST_DIR}")
    else:
        print()
        print("빌드 실패!")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Booth Searcher 빌드 스크립트")
    parser.add_argument("--onefile", action="store_true", help="단일 실행 파일로 빌드")
    parser.add_argument("--console", action="store_true", help="콘솔 창 표시")
    parser.add_argument("--clean", action="store_true", help="빌드 전 캐시 삭제")

    args = parser.parse_args()

    if args.clean:
        clean_build()
        print()

    build(onefile=args.onefile, console=args.console)


if __name__ == "__main__":
    main()
