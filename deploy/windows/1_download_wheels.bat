@echo off
REM ============================================================
REM  [인터넷 되는 Windows PC에서 실행]
REM  서버에 옮길 Python 패키지(wheel)를 wheels 폴더에 모읍니다.
REM  ※ 이 PC의 Python 버전을 '서버 PC에 설치할 버전'과 동일하게 맞추세요.
REM ============================================================
setlocal
cd /d "%~dp0"

echo [1/2] Python 확인...
python --version || (echo Python이 없습니다. 먼저 설치하세요. & pause & exit /b 1)

echo [2/2] wheel 다운로드 중...  (wheels 폴더에 저장)
python -m pip download -r requirements-offline.txt -d wheels
if errorlevel 1 (echo 다운로드 실패 & pause & exit /b 1)

echo.
echo 완료! 아래 두 가지를 USB에 함께 담아 서버 PC로 옮기세요:
echo   1) 이 프로젝트 폴더 전체 (work_schedule)
echo   2) Python 설치 파일 python-3.x.x-amd64.exe  (python.org에서 다운로드)
echo.
pause
