@echo off
chcp 65001 >nul
REM ============================================================
REM  [서버 PC(폐쇄망)에서 실행]
REM  USB로 옮긴 wheels 폴더에서 패키지를 오프라인 설치합니다.
REM  ※ 먼저 Python 설치 - 설치 시 'Add Python to PATH' 체크
REM ============================================================
setlocal
cd /d "%~dp0"

set "PY="
python --version >nul 2>&1 && set "PY=python"
if not defined PY ( py --version >nul 2>&1 && set "PY=py" )
if not defined PY (
  echo [오류] Python을 찾을 수 없습니다. python-3.12.x-amd64.exe 를 먼저 설치하세요 - Add to PATH 체크
  pause
  exit /b 1
)
echo 사용할 Python:
%PY% --version

echo 오프라인 설치 중...
%PY% -m pip install --no-index --find-links=wheels -r requirements-offline.txt
if errorlevel 1 ( echo 설치 실패. wheels 폴더와 Python 버전이 맞는지 확인하세요. & pause & exit /b 1 )

echo.
echo 설치 완료! 다음으로 3_run_server.bat 를 실행하세요.
pause
