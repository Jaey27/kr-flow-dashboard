# 맥미니 이관 가이드 (kr-flow-dashboard)

이 zip은 이 PC에서 만든 CPI 대시보드 프로토타입 전체다. 데이터(2026년 9월분까지)와 가중치 캐시가 들어 있어 바로 렌더할 수 있다.
Claude Code를 맥미니에서 열고 이 문서를 그대로 보여 주면 이어서 작업할 수 있다.

## 1. 배치

```
cd ~/kr-flow-dashboard
unzip ~/Downloads/cpi_dashboard_macmini.zip -d /tmp/cpi
mkdir -p scripts/cpi data/cpi
cp /tmp/cpi/cpi_dashboard/scripts/*.py /tmp/cpi/cpi_dashboard/scripts/template.html scripts/cpi/
cp -R /tmp/cpi/cpi_dashboard/data/* data/cpi/
```

경로 맞추기: 프로토타입은 `cpi_dashboard/{scripts,data,vendor}` 구조를 가정한다(`ROOT = scripts의 상위`).
kr-flow 구조(`scripts/cpi/`, `data/cpi/`, `vendor/`)로 옮기면 아래 네 군데의 경로만 바꾸면 된다.
- `fetch.py`: `RAW = ROOT / "data" / "raw"` → `ROOT / "data" / "cpi" / "raw"`, `ROOT = parents[2]`
- `build_cpi.py`: `DATA = ROOT / "data"` → `ROOT / "data" / "cpi"`
- `render_cpi.py`: 입력 `data/cpi/cpi.json`, Chart.js는 kr-flow의 `vendor/chart.umd.min.js`(같은 4.4.0), 출력 `docs/cpi.html`
- `run_cpi.py`, `telegram_report.py`: `STATE`, `cpi.json` 경로

간단히 가려면 kr-flow 안에 `cpi_dashboard/` 폴더를 통째로 두고 경로를 그대로 써도 된다.

## 2. 환경

```
.venv/bin/pip install -r cpi_dashboard/requirements.txt   # openpyxl
cp cpi_dashboard/.env.example cpi_dashboard/.env           # 봇 토큰 입력
```

- API 키 불필요. BLS는 User-Agent에 연락처가 있어야 받아 준다(`fetch.BLS_UA`).
- FRED는 쓰지 않는다(연은 원본 CSV/xlsx 직접 수집).

## 3. 첫 실행 확인

```
.venv/bin/python cpi_dashboard/scripts/build_cpi.py          # 전체 재수집 (BLS 파일 약 50MB)
.venv/bin/python cpi_dashboard/scripts/render_cpi.py
open cpi_dashboard/cpi.html
.venv/bin/python cpi_dashboard/scripts/telegram_report.py --dry-run
.venv/bin/python cpi_dashboard/scripts/telegram_report.py    # ← 발송 테스트 (보류해 둔 것)
```

## 4. 자동화 (launchd 5분 주기에 얹기)

`scripts/run.sh` 끝부분, 수급 렌더 다음에 추가:

```
.venv/bin/python cpi_dashboard/scripts/run_cpi.py
if [ $? -eq 10 ]; then
  cp cpi_dashboard/cpi.html docs/cpi.html
  CPI_CHANGED=1      # publish.sh 커밋 대상에 docs/cpi.html, cpi_dashboard/data/cpi.json 추가
fi
```

`run_cpi.py` 동작:
- 발표일(미 동부) 08:30 이후부터 다음 날 12:00 ET까지만 BLS 파일의 Last-Modified를 확인한다. 그 외 시간에는 네트워크 호출 없이 끝난다(일정 페이지 조회는 7일 캐시).
- 갱신이 감지되면 빌드·렌더·텔레그램 발송. 같은 지표월에는 한 번만 보낸다(`data/state.json`의 `sent_for`).
- 연은 보조지표가 CPI보다 늦으면 11:00 ET 이후 30분 간격으로 다시 빌드한다(KST 자정~새벽 1시 반영).
- 종료 코드 10 = 새로 렌더함 → publish 하라는 뜻.
- 첫 실행 때 동봉된 `cpi.json`의 Last-Modified로 상태를 채워 9월분 보고서를 다시 보내지 않는다.

KST 기준 시각: 서머타임(3~11월 초) 21:30 / 그 외 22:30에 BLS 공개 → 5분 주기면 21:35~21:40(22:35~22:40)에 반영된다.

## 5. 연 1회 수작업

매년 3월 CPI 발표(1월 지수) 뒤 `fetch.py`의 `WEIGHT_RELEASES`에 그해 항목을 추가한다.
예: `2027: "cpi_03xx2027.htm"` (BLS 보도자료 아카이브 파일명 = 3월 발표일). 표1·2의 '1월 상대중요도'가 그해 가중치 기준점이다.
추가하지 않으면 직전 해 기준점을 지수 비율로 이어 써서 오차가 조금 커질 뿐 멈추지는 않는다.

## 6. 페이지 연결

`render.py`의 상단 헤더(sector.html 링크 옆)에 `cpi.html` 링크를 추가한다. cpi.html 헤더에도 메인 대시보드로 돌아가는 링크를 넣으면 좋다.

## 파일 목록

| 파일 | 역할 |
|---|---|
| `scripts/items.py` | 항목 정의 31개 + 집계·파생·하위 항목, 한글 설명 |
| `scripts/fetch.py` | BLS 플랫파일·가중치·연은·트레이딩뷰 캘린더·발표 일정 수집 |
| `scripts/build_cpi.py` | 계산 → `data/cpi.json`, `data/cpi_data.xlsx` |
| `scripts/excel.py` | 엑셀 시트 생성 |
| `scripts/template.html`, `render_cpi.py` | 대시보드 HTML |
| `scripts/telegram_report.py` | 월간 보고서 |
| `scripts/run_cpi.py` | 자동 판정 러너 |
| `data/raw/` | 캐시 (가중치 보도자료 6개는 재다운로드 불필요) |
| `vendor/chart.umd.min.js` | Chart.js 4.4.0 |
