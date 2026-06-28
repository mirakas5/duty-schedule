# Linux 서버 배포 가이드

> NEXTRADE IT전략본부 당직표 — Linux(Ubuntu/Debian/CentOS/RHEL) 서버에 서비스로 올리기.
> 온라인/폐쇄망 둘 다 다루고, **systemd 서비스**로 자동 시작·자동 재시작까지 구성합니다.

---

## 0. 사전 요구
- Python **3.9 이상** (권장 3.11~3.12), `python3`·`pip`·`venv`
- 서버 접속(SSH) 가능, `sudo` 권한
- 같은 내부망의 직원 PC에서 서버 IP로 접근 가능

확인:
```bash
python3 --version          # 3.9+ 이어야
python3 -m venv --help >/dev/null && echo "venv OK"
```
없으면 (예: Ubuntu):
```bash
sudo apt update && sudo apt install -y python3 python3-venv python3-pip
# RHEL/CentOS: sudo dnf install -y python3 python3-pip
```

---

## A. 코드 가져오기

### A-1. 인터넷 되는 서버 (간단)
```bash
sudo mkdir -p /opt/duty-schedule && sudo chown $USER /opt/duty-schedule
git clone https://github.com/mirakas5/duty-schedule.git /opt/duty-schedule
cd /opt/duty-schedule
```

### A-2. 폐쇄망 서버 (인터넷 안 됨)
인터넷 되는 PC에서 코드를 받아 **scp/USB로 반입**:
```bash
# (인터넷 PC) 코드 압축
git clone https://github.com/mirakas5/duty-schedule.git
tar czf duty-schedule.tar.gz duty-schedule

# 서버로 복사 (scp 예시) 또는 USB로 반입
scp duty-schedule.tar.gz user@서버IP:/tmp/

# (서버) 풀기
sudo mkdir -p /opt/duty-schedule && sudo chown $USER /opt/duty-schedule
tar xzf /tmp/duty-schedule.tar.gz -C /opt/ --strip-components=0
cd /opt/duty-schedule
```

---

## B. Python 가상환경 + 의존성 설치

### B-1. 가상환경 생성 (공통)
```bash
cd /opt/duty-schedule
python3 -m venv .venv
```

### B-2-a. 온라인 설치
```bash
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt
```

### B-2-b. 폐쇄망(오프라인) 설치
> ⚠️ wheel을 받는 PC와 서버의 **OS·아키텍처(x86_64/aarch64)·Python 버전**이 같아야 합니다.
```bash
# (인터넷 되는 같은 사양 Linux PC에서) wheel 다운로드
python3 -m pip download -r requirements.txt -d wheels
#   → wheels/ 폴더를 USB/scp로 서버 /opt/duty-schedule/wheels 에 반입

# (서버) 오프라인 설치
.venv/bin/pip install --no-index --find-links=wheels -r requirements.txt
```

---

## C. 설정 (.env)
```bash
cp .env.example .env
nano .env       # 또는 vi
```
최소 설정:
```ini
DB_PATH=/opt/duty-schedule/data/duty.sqlite
HOST=0.0.0.0
PORT=8080
ADMIN_PASSWORD=새비밀번호로_변경       # 기본 nextrade 금지
ADMIN_SECRET=긴_랜덤문자열             # 예: openssl rand -hex 32 결과
# ADMIN_IPS=172.24.10.5,172.24.10.6   # (선택) 관리 허용 IP. 비우면 비번만
```
`ADMIN_SECRET` 랜덤 생성:
```bash
openssl rand -hex 32
```

---

## D. 수동 실행 테스트 (먼저 한 번)
```bash
cd /opt/duty-schedule
.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8080
```
- 다른 터미널/PC에서: `curl http://서버IP:8080/api/health` → `{"status":"ok"}`
- 확인되면 `Ctrl + C`로 멈추고 아래 systemd로 상시 구동.

---

## E. systemd 서비스 등록 (자동 시작·재시작 — 권장)

서비스 파일 생성:
```bash
sudo nano /etc/systemd/system/duty-schedule.service
```
내용 붙여넣기 (경로·User 확인):
```ini
[Unit]
Description=NEXTRADE IT전략본부 당직표
After=network.target

[Service]
Type=simple
User=YOUR_USER
WorkingDirectory=/opt/duty-schedule
EnvironmentFile=/opt/duty-schedule/.env
ExecStart=/opt/duty-schedule/.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8080
Restart=on-failure
RestartSec=3

[Install]
WantedBy=multi-user.target
```
> `YOUR_USER`를 실제 계정명으로 바꾸세요 (`whoami`로 확인).

활성화·시작:
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now duty-schedule
sudo systemctl status duty-schedule          # active (running) 확인
```
로그 보기:
```bash
journalctl -u duty-schedule -f
```

---

## F. 방화벽 열기 (8080)
```bash
# Ubuntu/Debian (ufw)
sudo ufw allow 8080/tcp

# RHEL/CentOS (firewalld)
sudo firewall-cmd --permanent --add-port=8080/tcp
sudo firewall-cmd --reload
```

---

## G. (선택) nginx 리버스 프록시 — 포트 없이 접속
80포트로 접속(`http://서버IP`)하고 싶으면:
```bash
sudo apt install -y nginx     # 또는 dnf install -y nginx
sudo nano /etc/nginx/conf.d/duty.conf
```
```nginx
server {
    listen 80;
    server_name _;
    client_max_body_size 10m;          # 엑셀 업로드 여유
    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $remote_addr;
    }
}
```
```bash
sudo nginx -t && sudo systemctl restart nginx
sudo ufw allow 80/tcp     # 또는 firewalld 80
```
> 이때 systemd의 ExecStart는 `--host 127.0.0.1`로 바꿔 내부에서만 듣게 하면 더 안전합니다.

---

## H. 접속·확인
- 서버 IP 확인: `ip addr` 또는 `hostname -I`
- 직원 브라우저: **`http://서버IP:8080`** (nginx 쓰면 `http://서버IP`)
- 관리 탭 → `.env`에 설정한 비밀번호 → 명단 업로드 → 스케줄 생성

---

## I. 운영 팁
| 작업 | 명령 |
|------|------|
| 재시작 | `sudo systemctl restart duty-schedule` |
| 중지 | `sudo systemctl stop duty-schedule` |
| 로그 | `journalctl -u duty-schedule -f` |
| 코드 업데이트(온라인) | `cd /opt/duty-schedule && git pull && .venv/bin/pip install -r requirements.txt && sudo systemctl restart duty-schedule` |
| **DB 백업** | 서비스 중지 후 `cp data/duty.sqlite data/duty.backup.sqlite` (실행 중 복사 금지) |

---

## 자주 막히는 곳
| 증상 | 해결 |
|------|------|
| 다른 PC에서 접속 안 됨 | 방화벽(F) 미개방 또는 `--host 0.0.0.0` 아님 확인 |
| `systemctl status`가 failed | `journalctl -u duty-schedule -e`로 오류 확인. 보통 경로/권한/.env 문제 |
| 오프라인 설치 실패 | wheel의 OS·아키텍처·Python 버전이 서버와 불일치 → 같은 사양에서 다시 받기 |
| 업로드 413 오류(nginx) | `client_max_body_size` 추가했는지 확인 |
| 관리 로그인 안 됨 | `.env`의 `ADMIN_PASSWORD` 확인, 변경 후 서비스 재시작 |

---

## 보안 메모 (정보보안)
- `.env`의 `ADMIN_PASSWORD`·`ADMIN_SECRET`는 **반드시 변경**, 파일 권한 제한: `chmod 600 .env`
- 조회·일상 편집은 무인증(설계 의도) → **내부망에서만** 노출, 외부 공개 금지
- 개인정보(실명) 포함 명단 엑셀·`duty.sqlite`는 git/외부 반출 금지
