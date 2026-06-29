@echo off
chcp 65001 >nul
REM ============================================================
REM  [서버 PC에서 실행] 당직표 서버를 켭니다.
REM  이 창을 닫으면 서버가 꺼집니다. 테스트 동안 켜 두세요.
REM ============================================================
setlocal
REM 프로젝트 루트로 이동 - deploy\windows 에서 두 단계 위
cd /d "%~dp0..\.."

set "PY="
python --version >nul 2>&1 && set "PY=python"
if not defined PY ( py --version >nul 2>&1 && set "PY=py" )
if not defined PY ( echo [오류] Python을 찾을 수 없습니다. & pause & exit /b 1 )

set PORT=8080
set HOST=0.0.0.0
echo ============================================================
echo  NEXTRADE IT전략본부 당직표 서버 시작 - 포트 %PORT%
echo.
echo  직원 접속: http://[이 PC의 IP]:%PORT%   IP는 ipconfig 로 확인
echo  서버 본인: http://localhost:%PORT%
echo ============================================================
echo.
%PY% -m uvicorn app.main:app --host %HOST% --port %PORT%
pause
