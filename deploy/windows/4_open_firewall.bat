@echo off
chcp 65001 >nul
REM ============================================================
REM  [서버 PC에서 '관리자 권한'으로 실행]
REM  마우스 우클릭 → '관리자 권한으로 실행'
REM  8080 포트 인바운드를 방화벽에서 허용합니다.
REM ============================================================
netsh advfirewall firewall add rule name="DutySchedule 8080" dir=in action=allow protocol=TCP localport=8080
if errorlevel 1 (
  echo 실패: '관리자 권한으로 실행' 했는지 확인하세요.
) else (
  echo 방화벽 허용 완료 (TCP 8080 인바운드).
)
pause
