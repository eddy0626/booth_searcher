@echo off
chcp 65001 > nul
echo Booth VRChat 의상 검색기 빌드 스크립트
echo ========================================
echo.

echo [1/3] 의존성 설치 중...
pip install -r requirements.txt
if errorlevel 1 (
    echo 오류: 의존성 설치에 실패했습니다.
    pause
    exit /b 1
)
echo.

echo [2/3] EXE 빌드 중...
pyinstaller build.spec --noconfirm
if errorlevel 1 (
    echo 오류: 빌드에 실패했습니다.
    pause
    exit /b 1
)
echo.

echo [3/3] 빌드 완료!
echo 실행 파일 위치: dist\BoothSearcher.exe
echo.
pause
