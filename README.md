# 국내 증시 수급 대시보드 (kr-flow-dashboard)

신용거래융자 잔고 · 투자자예탁금 · 미수금/반대매매 · 외국인 코스피200 선물 · 코스피/코스닥 투자자별 순매수(기관 세부 포함) · 지수를
`dashboard.html` 한 장(자기완결, 외부 요청 0건)으로 굽는다. 기본 화면은 최근 1년이고 상단 기간 바(슬라이더 + 1M/3M/6M/1Y/전체)로 조정한다.
구조는 자사주 대시보드(`~/buyback-dashboard`)를 따랐다: 수집 → 원장 → 렌더, Chart.js 인라인, 같은 틸 다크 테마.

## 데이터 출처 (전부 인증 불필요)

| 항목 | 출처 | 공표 시점 |
|---|---|---|
| 신용거래융자(코스피·코스닥·합계), 예탁증권담보융자 | 금융투자협회 FreeSIS `STATSCU0100000070BO` | 기준일 T → **T+1 영업일** |
| 투자자예탁금, 파생 예수금, RP, 미수금, 반대매매(금액·비중) | 금융투자협회 FreeSIS `STATSCU0100000060BO` | T+1 영업일 |
| 코스피/코스닥 투자자별 순매수(개인·외국인·기관 + 금융투자·연기금·투신·사모·보험·은행·기타) | 다음 금융 `api/investor/{KOSPI,KOSDAQ}/days` (원천 KRX) | 장중 잠정 → 마감 후 → **18시경 KRX 확정** |
| 코스피200 선물 투자자별 순매수·미결제약정·가격 | 다음 금융 `api/future/{ISIN}/days` | 위와 같음 |
| 코스피·코스닥 지수 | 다음 금융 `api/market_index/days` | 위와 같음 |

| 삼성전자·SK하이닉스 시총·종가·상장주식수 (코스피·코스닥 전 종목) | **KRX Open API** `sto/stk_bydd_trd`·`ksq_bydd_trd` (`.env` KRX_API_KEY) | 기준일 D → D+1 08시 전후 |
| 삼성전자(보통주)·SK하이닉스 외국인 보유주식 수·지분율, 평균 체결가 | 다음 금융 `api/investor/days?symbolCode=A{code}` | 장 마감 후 |
| 같은 종목 개인·외국인·기관 순매수 수량 | 네이버 모바일 `api/stock/{code}/trend` (pageSize≤60, bizdate 로 과거) | 장 마감 후 |
| 코스피·코스닥 시가총액·외국인 보유 시가총액·외국인 비중(일별) | 금융투자협회 FreeSIS `STATSCU0100000020BO`·`…30BO` | 측정 중(T+1 오전에는 확인) |
| 외국인 상장주식 보유액·시총 비중(월말, 참고) | 금감원 '외국인 증권투자 동향' → `data/manual/fss_foreign_holdings.json` (수동, 출처 URL 포함) | 매월 초~중순 |

- **FreeSIS 는 세션 쿠키가 있어야 JSON 을 준다.** 화면 URL 을 먼저 GET 한 뒤 POST 한다(`scripts/sources/freesis.py`).
- **다음 선물 API 의 외국인/기관/개인 값은 월물별이 아니라 코스피200 선물 전 월물 합계다.** 같은 날짜면 어느 월물을 조회해도 값이
  같다(2024-10~2026-10 전 15개 월물 교차대조 불일치 0일, 롤오버 주간 포함). 미결제약정·거래량만 월물별이라 상장 월물 전부를 더한다.
  매 실행마다 이 전제를 다시 검사해 `daum_futures.json` 의 `investor_mismatch_days` 로 남긴다.
- 선물 ISIN: ~2025년 만기 `KR4101{V=2024,W=2025}{3,6,9,C}000x`, 2026년~ `KR4A01{연도끝자리}{3,6,9,C}000x` (x=ISIN 검증숫자).
- KRX 정보데이터시스템(data.krx.co.kr)은 2025년부터 로그인이 필요해 쓰지 않는다. KRX Open API(`.env` 의 `KRX_API_KEY`)는 시세류만 있고
  D+1 08시 공개라 수급 항목을 빠르게 해 주지는 않지만, 시장 전체 시총 계산에 쓴다(현재 키 승인: `stk_bydd_trd`·`ksq_bydd_trd`, `idx`·`drv` 는 401).

## 갱신 방식 — "나오자마자"

launchd `com.pjy.kr-flow-dashboard` 가 **5분마다** `scripts/run.sh` 를 부른다. `build_data.py --auto` 가 출처별로
"지금 새 값이 나올 차례인가"를 판정해 그 출처만 조회하고, 값이 바뀌었을 때만 렌더한다. 할 일이 없으면 네트워크 0회·로그 0줄.

| 출처 | 조회 조건 |
|---|---|
| 다음(수급·선물·지수) | 영업일 **장 마감 + 10분**(15:40, 수능일은 16:40) 이후 당일 행이 없으면 → **잠정**으로 받음 / **18:30** 이후 다시 받아 **확정** 처리 |
| FreeSIS(신용·예탁금) | 원장 최신일 < 직전 영업일이면 07:00부터 **10분 간격**으로 공표 여부 확인 → 올라오는 즉시 반영 |
| KRX Open API(시총) | 기준일 다음 날 08:10 이후 원장에 없는 영업일을 조회(20분 간격 재시도, 7일 넘게 비면 포기) |
| 종목별(다음·네이버) | 다음 수급과 같은 시점(15:40 잠정 → 18:30 확정) |
| 전 출처 | 매일 첫 실행(07시 이후)에 최근 15일 재수집 — 출처의 사후 정정 반영 |
| 누락 보충 | 맥미니가 꺼져 있던 날 등은 다음 실행에서 자동 보충(30분 간격 재시도) |

잠정치는 페이지에 '잠정' 표시가 붙고, 확정 수집 후 사라진다.
공표 시각 실측(2026-10-13~) 결과가 나오면 `build_data.py` 의 `FREESIS_FROM`·`FINAL_AT` 을 좁힌다.

## 외국인 보유 탭 (삼성전자·SK하이닉스)

- **시장 전체 외국인 보유액 = 금투협 FreeSIS '증시동향'**(`STATSCU0100000020BO` 코스피, `…30BO` 코스닥)의 외국인 보유 시가총액·비중 — KRX 원천 일별 실측.
  금감원 월말(결제 기준, `data/manual/fss_foreign_holdings.json`)은 분모·기준이 달라 참고점으로만 표시.
- **종목(삼성전자 보통주·SK하이닉스, 우선주 제외)**: 외국인 보유액 = 보유주식 수(다음) × KRX 종가.
  투자자별 순매수 금액 = 네이버 순매수 수량 × 다음 평균가(추정).
- **보유액 변화 분해**(`scripts/holdings.py`): 종목은 `ΔH = Δ주식수×P_t + 주식수_{t-1}×ΔP` 항등식(매매/주가).
  시장 전체는 매매 = 외국인 순매수(코스피+코스닥), 주가 = ΔH − 순매수(잔차). 차트는 기간 시작일 종가를 0 으로 누적.
- **보유주식 수에는 장외 이동·DR 예탁이 포함**된다(예: SK하이닉스 2026-07-16 +1,823만주 = 7월 미국 ADR 상장 예탁분).
  그래서 하이닉스는 '보유주식 수 변화'와 '장내 순매수 누적'이 다르다.
- **주장 검증 카드**(고정 기준일 24.10.31 / 24.12.30 / 25.12.30 / 2026 보유액 고점 / 최신)는 매일 자동 재계산된다.
- 금감원 월말 수치는 수동 갱신: 보도자료가 나오면 rows 에
  `{"month":"YYYY-MM","holding_jo":…,"share_pct":…,"net_buy_jo":…,"url":…}` 한 줄 추가(15일 이후 전월분이 없으면 로그 경고).

## 섹터 수급 탭 (네이버 업종 78개 × KRX 주체별)

- 업종: 네이버 `m.stock.naver.com/api/stocks/industry` 79개 중 '기타' 제외 78개(2,868종목, 중복 소속 없음) → `data/sectors_naver.json`
  (`scripts/sources/naver_sector.py` 로 갱신). 현재 소속으로 과거까지 묶는다.
- 수급: KRX 정보데이터시스템 종목별 투자자(개인·외국인·기관합계) 매수·매도 거래대금, pykrx `get_market_net_purchases_of_equities(D,D,"ALL",주체)`.
  **로그인 필요** — `.env` 의 `KRX_ID`/`KRX_PW`(사용자가 직접 입력). 종목 원자료는 `data/krx_inv/YYYY-MM.json.gz`(git 제외),
  업종 집계는 `data/ledger/krx_sector_flow.json`. 매일 18:40 이후 수집, 백필은 `scripts/backfill_krx_inv.py`.
- 검증(2026-10-06, BLITZ '섹션별 수급' 포스트 대조): 업종 순매수는 ±1% 안에서 일치(개인 전자장비와기기 −3,952억 동일 등).
  주체별 '거래액'은 포스트보다 5~10% 크게 나온다(집계 범위 정의 차이로 추정).

## 실행

```bash
bash scripts/run.sh                          # launchd 가 하는 것과 같다(--auto)
KRFLOW_MODE=full bash scripts/run.sh         # 최근 15일 강제 재수집 + 렌더
.venv/bin/python scripts/build_data.py --backfill && .venv/bin/python scripts/render.py   # 원장 처음부터
bash scripts/install_launchd.sh              # 등록/재등록
bash scripts/uninstall_launchd.sh            # 해제
open dashboard.html
```

로그: `logs/run_YYYYMMDD.log`(실제로 조회한 실행만), `logs/heartbeat`(5분마다 갱신 — 멈췄는지 확인용).
페이지 상단 칩이 출처별 기준일을 보여 주고, 기대보다 2영업일 이상 늦으면 노란 경고가 뜬다.

## 파일

```
scripts/
  run.sh               launchd 엔트리 (락·로그·build→render)
  build_data.py        --auto/--full/--backfill · 공표 시점 판정 · 원장 병합 · flows.json 조립
  render.py            flows.json → dashboard.html (패널 정의 PANELS 는 JS 안)
  common.py            KST·HTTP 재시도·KRX 영업일(data/holidays_kr.json)·원장 입출력
  sources/freesis.py   금투협
  sources/daum.py      다음 금융 + 선물 ISIN 생성·월물 집계
data/
  ledger/*.json        출처별 누적 원장(날짜 키, 잠정 목록 포함) — 출처가 과거를 지워도 남는다
  flows.json           렌더 입력(공통 날짜축에 정렬)
  holidays_kr.json     KRX 휴장일(자사주 대시보드와 같은 원본, 2027-12-31 까지) — 만료 45일 전부터 로그 경고
  state.json           마지막 일일 재수집·재시도 시각
vendor/chart.umd.min.js  Chart.js 4.4.0 (인라인)
```

## 항목 추가하는 법

1. `scripts/sources/` 에 수집 함수 추가(또는 기존 FreeSIS `TABLES` 에 OBJ_NM 한 줄) → `build_data.py` 의 fetch 에서 원장으로 병합
2. `build_data.py assemble()` 에 `S["새키"] = col(...)` 한 줄
3. `render.py` JS 의 `PANELS` 에 패널/뷰 한 줄 (`type: line|bar|stack`, `cum: true` 면 기간 시작일 기준 누적, `sign: true` 면 매수 빨강/매도 파랑)

후보: 프로그램 매매(차익/비차익), 대차잔고(FreeSIS 대차거래추이), 공매도 잔고(KRX 로그인 필요), 코스닥150 선물, 고객 RP/CMA.

## GitHub Pages

- 공개 페이지: https://jaey27.github.io/kr-flow-dashboard/ (리포 `Jaey27/kr-flow-dashboard`, main 브랜치 `/docs`)
- `run.sh` 가 렌더한 실행에서만 `render.py --docs` → `scripts/publish.sh` 로 `docs/index.html`·`data/flows.json`·`data/ledger/` 를 커밋·push 한다.
  타임스탬프만 바뀐 경우는 커밋하지 않고, push 실패분은 다음 실행이 다시 민다. `KRFLOW_PUBLISH=0` 이면 끈다.
- push 인증은 SSH 키 `~/.ssh/id_ed25519_gh`(~/.ssh/config 의 github.com), 커밋 신원은 리포 로컬 `Jaey27 <Jaey27@users.noreply.github.com>` — 개인 메일 금지.
- `.env`(KRX 키)는 .gitignore 대상이고 publish.sh 가 추적 여부를 매번 검사한다.
