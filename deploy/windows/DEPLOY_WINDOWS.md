# 폐쇄망 Windows 서버 배포 가이드 (처음 하는 분용)

> 목표: 내부망 Windows PC 한 대에 당직표 서버를 올려, 같은 망의 직원들이 브라우저로 접속해 테스트.
> 환경: **서버 = Windows / 폐쇄망(인터넷 안 됨) → 인터넷 되는 PC에서 부품을 받아 USB로 반입**.

전체 흐름 한눈에:
```
[인터넷 되는 Windows PC]                    [USB]        [폐쇄망 Windows 서버 PC]
 ① Python 설치파일 받기        ─────────────┐
 ② wheel(패키지) 받기  (1_download_wheels)  ├──USB──▶  ③ Python 설치
 + 프로젝트 폴더 복사                        ┘           ④ 오프라인 설치 (2_install_offline)
                                                         ⑤ 방화벽 열기 (4_open_firewall, 관리자)
                                                         ⑥ 서버 실행 (3_run_server)
                                                         ⑦ 직원에게 http://서버IP:8080 안내
```

---

## 사전 결정: Python 버전 통일 (중요)
"부품 받는 PC"와 "서버 PC"의 **Python 버전을 똑같이** 맞춰야 합니다(예: 둘 다 3.12.x).
권장: **Python 3.12.x (64-bit)**. python.org → Downloads → Windows → "Windows installer (64-bit)".

---

## A. 인터넷 되는 Windows PC에서 (부품 모으기)

1. **Python 설치파일 다운로드**
   - python.org에서 `python-3.12.x-amd64.exe` 다운로드 → USB에 보관(서버에서 설치할 것).
   - 이 PC에도 같은 버전 Python이 설치돼 있어야 합니다(설치 시 **"Add python.exe to PATH" 체크**).

2. **프로젝트 폴더 준비**
   - 개발에 쓴 `work_schedule` 폴더 전체를 이 PC로 복사(또는 USB에).

3. **wheel(패키지) 다운로드**
   - `work_schedule\deploy\windows\` 폴더에서 **`1_download_wheels.bat` 더블클릭**.
   - 끝나면 `deploy\windows\wheels\` 폴더에 `.whl` 파일들이 생깁니다.

4. **USB에 담기** (아래 3개를 함께)
   - `work_schedule` 폴더 전체 (방금 만든 `wheels` 폴더 포함)
   - `python-3.12.x-amd64.exe`

> 💡 인터넷 되는 PC가 **Mac밖에 없다면**: Mac에서 받은 패키지는 Windows에서 안 돕니다.
> 가능하면 인터넷 되는 윈도우 PC를 쓰세요. 정 안 되면 알려주시면 Mac에서 Windows용 wheel을
> 받는 명령(`pip download --platform ... --only-binary=:all:`)을 따로 안내하겠습니다.

---

## B. 폐쇄망 Windows 서버 PC에서

5. **Python 설치**
   - USB의 `python-3.12.x-amd64.exe` 실행 → 설치 첫 화면에서 **"Add python.exe to PATH" 체크** → Install.
   - 확인: 명령 프롬프트(cmd)에서 `python --version` → 버전이 보이면 OK.
   - (회사 PC에 이미 같은 버전 Python이 있으면 이 단계 생략)

6. **프로젝트 폴더 복사**
   - USB의 `work_schedule` 폴더를 서버 PC의 적당한 위치(예: `C:\duty\work_schedule`)에 복사.

7. **오프라인 설치**
   - `work_schedule\deploy\windows\` 에서 **`2_install_offline.bat` 더블클릭** → "설치 완료" 뜨면 OK.

8. **방화벽 열기 (한 번만)**
   - `4_open_firewall.bat` **마우스 우클릭 → "관리자 권한으로 실행"** → "방화벽 허용 완료" 확인.

9. **관리자 비밀번호 설정 (권장)**
   - `work_schedule\.env` 파일을 메모장으로 열어:
     - `ADMIN_PASSWORD=` 뒤를 원하는 비밀번호로 변경 (기본 `nextrade`).
     - `ADMIN_SECRET=` 뒤를 길고 임의의 문자열로 변경.
     - (선택) `ADMIN_IPS=` 에 관리자 PC IP를 적으면 그 PC에서만 관리 가능.
   - `.env` 파일이 없으면 `.env.example`을 복사해 `.env`로 만든 뒤 수정.

10. **서버 실행**
    - **`3_run_server.bat` 더블클릭**. 검은 창이 뜨고 로그가 흐르면 실행 중입니다.
    - **이 창을 닫으면 서버가 꺼집니다.** 테스트하는 동안 켜 두세요.

11. **서버 PC의 IP 확인**
    - 새 cmd 창에서 `ipconfig` → **"IPv4 주소"**(예: `172.24.10.50`) 확인.

12. **직원에게 안내**
    - 같은 내부망의 직원은 브라우저에서: **`http://172.24.10.50:8080`** (위에서 확인한 IP).
    - 서버 PC 본인은 `http://localhost:8080` 으로도 확인 가능.

---

## C. 동작 확인 체크리스트
- [ ] 서버 PC 브라우저에서 `http://localhost:8080` → '당직 달력' 화면이 뜬다.
- [ ] 다른 직원 PC에서 `http://서버IP:8080` → 같은 화면이 뜬다.
- [ ] '관리' 탭 → 비밀번호 입력 → 명단 업로드(`data\sample_members.xlsx`) → 시작/종료일 지정 → 자동 생성.
- [ ] '당직 달력'에서 셀 드래그(교환)·우클릭(수정/삭제) 동작.

---

## D. 자주 막히는 곳 (해결)
| 증상 | 원인 / 해결 |
|------|-------------|
| 다른 PC에서 접속 안 됨 | ① 방화벽(8단계) 안 열림 → `4_open_firewall.bat` 관리자 실행. ② IP가 바뀜 → `ipconfig`로 다시 확인. |
| `2_install_offline` 설치 실패 | 부품 받은 PC와 서버의 **Python 버전 불일치**. 같은 버전으로 맞춰 wheel 다시 받기. |
| `python` 명령 없음 | 설치 때 'Add to PATH' 누락. Python 재설치(체크) 또는 PATH 등록. |
| 포트 8080이 이미 쓰임 | `3_run_server.bat`의 `set PORT=8080`을 8090 등으로 변경(방화벽도 해당 포트로). |
| 서버 창을 닫으면 꺼짐 | 테스트 단계 정상. 항상 켜두려면 아래 E(자동 시작). |
| 한글/엑셀 깨짐 | 파일을 .xlsx로 저장했는지 확인(.xls/.csv 아님). |

---

## E. (선택) 자동 시작 — 테스트가 끝나고 상시 운영할 때
PC를 켜면 서버가 자동으로 뜨게 하려면 **작업 스케줄러**:
1. 시작 → "작업 스케줄러" → **작업 만들기**.
2. 일반: "사용자가 로그온할 때만" 또는 "사용자의 로그온 여부와 관계없이", "가장 높은 권한으로 실행" 체크.
3. 트리거: **시작할 때**(또는 로그온할 때).
4. 동작: 프로그램 시작 → `3_run_server.bat` 경로 지정.
> 테스트 단계에서는 굳이 안 해도 됩니다. `3_run_server.bat`만 켜 두면 충분합니다.

---

## F. 백업 / 종료
- 데이터는 `work_schedule\data\duty.sqlite` 한 파일에 모두 들어있습니다.
- **백업/복사는 반드시 서버를 끈 뒤**(검은 창 닫기) 그 파일을 복사하세요. (실행 중 삭제·복사 금지)
- 종료: 서버 실행 창을 닫으면 끝.
