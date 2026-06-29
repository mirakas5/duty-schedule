@echo off
chcp 65001 >nul
REM ============================================================
REM  [인터넷 되는 Windows PC에서 실행]
REM  서버에 옮길 Python 패키지(wheel)를 wheels 폴더에 모읍니다.
REM  ※ 이 PC의 Python 버전을 '서버 PC에 설치할 버전'과 동일하게 맞추세요.
REM ============================================================
setlocal
cd /d "%~dp0"

REM Python 탐지 (python 또는 py 런처)
set "PY="
python --version >nul 2>&1 && set "PY=python"
if not defined PY ( py --version >nul 2>&1 && set "PY=py" )
if not defined PY (
  echo [오류] Python을 찾을 수 없습니다.
  echo   1] python.org 에서 Python 3.12 설치 - 첫 화면 'Add python.exe to PATH' 체크
  echo   2] 설치 후 이 창을 닫고 '새' 명령창에서 다시 실행
  pause
  exit /b 1
)
echo 사용할 Python:
%PY% --version

echo wheel 다운로드 중... wheels 폴더에 저장
%PY% -m pip download -r requirements-offline.txt -d wheels
if errorlevel 1 ( echo 다운로드 실패 & pause & exit /b 1 )

echo.
echo 완료! 아래를 USB에 함께 담아 서버 PC로 옮기세요:
echo   1] 이 프로젝트 폴더 전체 - wheels 폴더 포함
echo   2] Python 설치 파일 python-3.12.x-amd64.exe
echo.
pause
