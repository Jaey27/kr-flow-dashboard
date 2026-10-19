# CPI 대시보드 (프로토타입)

미국 CPI 헤드라인·근원과 주요 31개 항목의 상승률·기여도·일회성 신호를 보는 단일 HTML 대시보드.
맥미니 `kr-flow-dashboard`에 `cpi.html` 페이지로 이식할 예정이다.

## 실행

```
python scripts/build_cpi.py      # 수집 + 계산 → data/cpi.json, data/cpi_data.xlsx
python scripts/render_cpi.py     # → cpi.html (Chart.js 인라인, 외부 요청 없음)
python scripts/build_cpi.py --offline   # data/raw 캐시만 사용
```

필요 패키지: `openpyxl` (나머지는 표준 라이브러리). API 키 불필요.

## 출처와 공개 시각

| 출처 | 내용 | 공개 |
|---|---|---|
| BLS `cu.data.0.Current` (download.bls.gov) | 전 항목 SA·NSA 지수 | 발표일 08:30 ET (Last-Modified로 갱신 확인) |
| BLS 3월 보도자료 표1·2 | 매년 1월 상대중요도 (가중치 기준점) | 연 1회. 새해 3월 발표 후 `fetch.WEIGHT_RELEASES`에 파일명 추가 |
| 클리블랜드 연은 CSV | 중위·절사평균 CPI | 발표일 11:00 ET 전후 |
| 애틀랜타 연은 xlsx | sticky CPI | 발표일 11:00 ET 전후 |
| 트레이딩뷰 경제 캘린더 | CPI 컨센서스·실제, FOMC 결정 | 상시 |
| BLS 발표 일정 페이지 | 다음 발표일 | 상시 |

FRED는 이 PC에서 접속이 막혀 연은 원본 파일을 직접 쓴다.

## 계산 규칙

- 전월비 = SA, 전년비 = NSA. SA가 없는 항목(세입자보험·통신·기타개인서비스)은 NSA.
- 가중치: 1월 상대중요도 × (항목 지수 변화 / 전체 지수 변화). 2026년 8월 값이 BLS 표와 일치함을 확인.
- 기여도(전월비) = 전월 가중치 × 전월비. 근원 기준은 근원 가중치로 나눔. 잔여 = 발표치 − 항목 합 (전월비 기준 ±0.06%p 이내).
- 파생: 슈퍼코어 = 근원 서비스 − 주거비, 차량 제외 근원 상품, 숙박 제외 주거비, 기타 교통서비스 (가중치 차감, 결측월은 건너뛰어 체인 연결).
- 일회성: 직전 12개월 대비 z ≥ 2 → 급등/급락, 다음 달 |z| < 1 → 되돌림, 같은 방향 z ≥ 1 → 지속.
- 2025-10 (셧다운 결측): 전월비·전년비 빈칸, 연율 계산에서만 앞뒤 기하평균 보간.
- 가사 서비스(SEHP)는 2024-10에 BLS가 시리즈를 중단해 제외 (잔여에 흡수).

## 맥미니 이식 메모

- `scripts/cpi/`로 옮기고 `run.sh`에서 발표일에만 호출: 21:25 KST(서머타임) / 22:25 KST부터 5분마다 `fetch.bls_last_modified()` 확인 → 바뀌면 빌드·렌더·publish.
- 연은 지표는 같은 날 00:00~01:00 KST 이후 한 번 더 빌드.
- 테마·기간 바는 kr-flow `render.py`와 맞추고, sector.html처럼 상단에서 링크.

## 텔레그램 보고서

`python scripts/telegram_report.py` — 빌드 후 실행. `.env`에 `TELEGRAM_BOT_TOKEN`, `CHAT_ID`, `CPI_DASHBOARD_URL`.
`--dry-run`이면 발송 없이 출력만 한다. 내용: 헤드라인·근원 vs 컨센서스, 근원 3·6개월 연율, 슈퍼코어, 근원 기여 상위 3·하위 2, 헤드라인 최대 기여, 일회성 신호 상위 5.
