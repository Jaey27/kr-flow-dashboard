# 금리 발언 tracker (매크로 탭 첫 화면)

2026년 1월 이후 Fed 의장·대통령·재무장관·Fed 위원·셀사이드·투자자의 금리 발언을 0~10 매파 점수로 모아, 금리 기대(연방기금 선물)·2년물·S&P 500·나스닥과 같이 본다. 화면은 `docs/fedspeak.html`(흰 배경 단독 페이지)이고, 매크로 탭의 하위 탭 「금리 발언 tracker」가 이 페이지를 iframe으로 띄운다.

## 파일

| 경로 | 뭐 | 누가 바꾸나 |
|---|---|---|
| `scripts/fedspeak/pipeline.py` | `merge` raw → 원장 후보, `verify` 출처 페이지를 받아 인용이 글자 그대로 있는지 대조, `report` 인물별 표 | 코드 |
| `scripts/fedspeak/analyze.py` | `--fetch` 시장 데이터(EFFR·ZQF27·S&P·나스닥) 받기 + 톤 지수·백테스트 → `data/fedspeak/analysis.json`(커밋 안 함) | 코드 |
| `scripts/fedspeak/build.py` | `--docs` → `docs/fedspeak.html` | 코드 |
| `scripts/fedspeak/BRIEF.md`, `BRIEF_H1.md` | 수집 에이전트에 주는 기준(증거 규칙·채점 기준·JSON 형식) | 사람 |
| `data/fedspeak/raw/*.json` | 수집 묶음(에이전트 출력 그대로) | 주간 수집 |
| `data/fedspeak/ledger.json` | 대조까지 끝난 원장 | `pipeline.py verify` |
| `data/fedspeak/overrides.json` | 사람이 다시 본 점수·AI 맥락 분류·제외(id 기준) | 검토자 |
| `data/fedspeak/kr.json` | 한국어 요약(id → 1~2문장, ~함체, 긴 줄표 금지) | 주간 수집 |
| `data/fedspeak/verify_manual.json` | 스크립트로 못 받는 페이지를 브라우저로 열어 확인한 id | 검토자 |
| `data/fedspeak/roster_extra.json` | 명단 보강(재임 기간 since/until) | 사람 |

드러켄밀러 원장은 Jae 노션 아카이브라서(비공개 노트) 사본을 리포에 두지 않는다. 원장의 `verify: notion` 판정은 처음 대조한 결과를 유지한다.

## 매일(자동, run_daily.sh)

`analyze.py --fetch` → `build.py --docs`. 시장선과 기간 막대, 인물 수준(새 발언이 없으면 마지막 값 유지)만 갱신된다. LLM 안 씀.

## 주 1회 전수조사(발언 추가) — Claude 세션이 한다

발언 수집은 웹 검색·원문 확인·채점이 필요해서 스크립트만으로는 안 된다. Claude Code 세션 하나가 아래 순서로 한다.

1. 기간: 원장 마지막 날짜 − 2일 ~ 오늘(겹치게 잡고 중복은 merge가 거름).
2. `BRIEF.md`를 기준으로 수집 에이전트 4개 정도를 나눠 띄운다(한 번에 10개를 띄우면 사용 한도에 걸린다, 2026-11-23 경험).
   - 이사회·의장 / 지역 총재(투표·비투표) / 트럼프·베센트 / 투자자·셀사이드
   - 출력은 `data/fedspeak/raw/W<YYYYMMDD>_<묶음>.json`
3. `python scripts/fedspeak/pipeline.py merge && python scripts/fedspeak/pipeline.py verify`
   - 이 PC에서 curl이 막히는 곳: kansascityfed.org, stlouisfed.org(타임아웃) → 브라우저로 열어 인용을 확인하고 id를 `verify_manual.json`에 넣는다.
4. 새 id에 한국어 요약을 붙여 `kr.json`에 합친다.
5. 채점 통일: +2(화면 10)는 "곧·이번 회의·필요하다·소수의견" 같은 무조건형만, 조건부·확률 표현은 +1(7.5). AI 투자·조달을 언급한 건은 `overrides.json`에 `ai_side`(demand / loose / crowding / watch / calm)를 붙인다.
6. `analyze.py && build.py --docs`로 확인한 뒤 `data/fedspeak/`만 커밋한다(docs는 맥미니 run_daily가 다시 굽는다).

FOMC 주간(블랙아웃 직후 ~ 회의 다음 주)에는 발언이 몰리므로 수요일에 한 번 더 돌려도 된다.

## 주의

- `analyze.py`의 `ZQF27`(27년 1월물 = 12/9 회의 뒤 금리 기대)은 2027년 1월 회의가 지나면 다음 월물로 바꿔야 한다.
- 점수는 모델이 매겼다. 인물별 상관은 표본이 작아 참고용이다.
