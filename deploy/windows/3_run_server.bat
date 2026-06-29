@echo off
chcp 65001 >nul
REM ============================================================
REM  [서버 PC에서 실행] 당직표 서버를 켭니다.
REM  이 창을 닫으면 서버가 꺼집니다. 테스트 동안 켜 두세요.
REM ============================================================
setlocal
REM 프로젝트 루트로 이동 (deploy\windows 에서 두 단계 위)
cd /d "%~dp0..\.."

set PORT=8080
set HOST=0.0.0.0

echo ============================================================
echo  NEXTRADE IT전략본부 당직표 서버 시작
echo  포트: %PORT%
echo.
echo  같은 망의 직원은 브라우저에서 접속:
echo     http://(이 PC의 IP):%PORT%
echo  이 PC의 IP는 새 명령창에서  ipconfig  실행 후 'IPv4 주소' 확인.
echo  (서버 본인은 http://localhost:%PORT% 로 확인 가능)
echo ============================================================
echo.

python -m uvicorn app.main:app --host %HOST% --port %PORT%
pause
