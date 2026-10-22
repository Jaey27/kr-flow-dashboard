#!/bin/bash
# ---------------------------------------------------------------------------
#  BLITZ AI 플레이북 「매크로/시황 대시보드」 탭에 올릴 dash.html 을 굽는다.
#  맥미니 Claude 데스크톱 앱의 예약 작업(매일 07:50)이 이 스크립트를 실행한 뒤 Artifact 도구로 게시한다.
#  (CLI 헤드리스 claude -p 에는 Artifact 도구가 없어서 게시는 앱 세션이 맡는다 — 10/19 맥미니 시험)
#
#  하는 일: 아침 run_daily 가 끝났는지 확인 → 오늘 data 로 render.py 를 따로 돌려 logs/playbook/dash.html 생성
#  출력: (px.json 성공 시) PX <파일> 한 줄 → 마지막 줄 READY <파일> <bytes> <generated_at>  또는  SKIP <이유>
#  --if-new (10:30 재게시 회차, 10/23 Jae): 오늘 리스크 재수집(logs/risk_done_YYYYMMDD)이 마지막 게시 성공
#           (logs/playbook/last_publish_ok, 게시 작업이 OK 때 touch) 보다 새로울 때만 굽는다. 아니면 SKIP.
#           → 09:50 게시가 실패했거나 10:00 재수집이 새로 돌았을 때만 10:30 에 다시 올린다.
# ---------------------------------------------------------------------------
set -uo pipefail
cd "$(dirname "$0")/.."
ROOT="$(pwd -P)"
export TZ=Asia/Seoul PYTHONIOENCODING=utf-8 PYTHONUTF8=1
PY="${KRFLOW_PYTHON:-$ROOT/.venv/bin/python}"
OUT_DIR="$ROOT/logs/playbook"; mkdir -p "$OUT_DIR"
OUT="$OUT_DIR/dash.html"

# run_daily / run.sh 가 돌고 있으면 최대 20분 기다린다(같은 락)
for i in $(seq 1 120); do [ -d "$ROOT/.run.lock" ] || break; sleep 10; done
[ -d "$ROOT/.run.lock" ] && { echo "SKIP 갱신 작업이 20분 넘게 실행 중(.run.lock)"; exit 1; }

if [ "${1:-}" = "--if-new" ]; then
  DONE="$ROOT/logs/risk_done_$(date +%Y%m%d)"; OKF="$OUT_DIR/last_publish_ok"
  [ -e "$DONE" ] || { echo "SKIP 오늘 리스크 재수집(09:30/10:00) 기록 없음"; exit 1; }
  [ -e "$OKF" ] && [ "$OKF" -nt "$DONE" ] && { echo "SKIP 마지막 게시($(date -r "$OKF" '+%H:%M')) 뒤로 새 리스크 수집 없음 — 재게시 불필요"; exit 1; }
fi

# 오늘 아침 run_daily 가 끝났는지(오늘 날짜 daily 로그 + docs/index.html 오늘 수정)
LOG="$ROOT/logs/daily_$(date +%Y%m%d).log"
[ -s "$LOG" ] || { echo "SKIP 오늘 run_daily 로그 없음($LOG)"; exit 1; }
[ "$(date -r "$ROOT/docs/index.html" +%Y%m%d 2>/dev/null)" = "$(date +%Y%m%d)" ] || { echo "SKIP docs/index.html 이 오늘 것이 아님"; exit 1; }

"$PY" scripts/render.py --out "$OUT" >/dev/null 2>&1 || { echo "SKIP render.py 실패"; exit 1; }
[ -s "$OUT" ] || { echo "SKIP 출력 파일 없음"; exit 1; }
# 이벤트 리스트 수익률용 주가(px.json, 10/20 추가). 실패해도 dash.html 게시는 그대로 진행(페이지는 내장/직전 주가로 표시)
if "$PY" scripts/playbook_px.py --out "$OUT_DIR/px.json" >/dev/null 2>&1 && [ -s "$OUT_DIR/px.json" ]; then
  echo "PX $OUT_DIR/px.json"
else
  echo "PX-FAIL playbook_px.py 실패(px.json 은 이번엔 넘기지 않음)"
fi
SIZE=$(wc -c <"$OUT" | tr -d ' ')
GEN=$(grep -o '"generated_at": *"[^"]*"' "$OUT" | head -1 | cut -d'"' -f4)
WARN=$(grep -c '^\[WARN\]' "$LOG" 2>/dev/null || true)
echo "READY $OUT $SIZE ${GEN:-?} (오늘 run_daily WARN ${WARN:-0}건)"
