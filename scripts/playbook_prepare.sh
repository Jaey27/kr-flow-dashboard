#!/bin/bash
# ---------------------------------------------------------------------------
#  BLITZ AI 플레이북 「매크로/시황 대시보드」 탭에 올릴 dash.html 을 굽는다.
#  맥미니 Claude 데스크톱 앱의 예약 작업(매일 07:50)이 이 스크립트를 실행한 뒤 Artifact 도구로 게시한다.
#  (CLI 헤드리스 claude -p 에는 Artifact 도구가 없어서 게시는 앱 세션이 맡는다 — 10/19 맥미니 시험)
#
#  하는 일: 아침 run_daily 가 끝났는지 확인 → 오늘 data 로 render.py 를 따로 돌려 logs/playbook/dash.html 생성
#  출력 마지막 줄: READY <파일> <bytes> <generated_at>  또는  SKIP <이유>
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

# 오늘 아침 run_daily 가 끝났는지(오늘 날짜 daily 로그 + docs/index.html 오늘 수정)
LOG="$ROOT/logs/daily_$(date +%Y%m%d).log"
[ -s "$LOG" ] || { echo "SKIP 오늘 run_daily 로그 없음($LOG)"; exit 1; }
[ "$(date -r "$ROOT/docs/index.html" +%Y%m%d 2>/dev/null)" = "$(date +%Y%m%d)" ] || { echo "SKIP docs/index.html 이 오늘 것이 아님"; exit 1; }

"$PY" scripts/render.py --out "$OUT" >/dev/null 2>&1 || { echo "SKIP render.py 실패"; exit 1; }
[ -s "$OUT" ] || { echo "SKIP 출력 파일 없음"; exit 1; }
SIZE=$(wc -c <"$OUT" | tr -d ' ')
GEN=$(grep -o '"generated_at": *"[^"]*"' "$OUT" | head -1 | cut -d'"' -f4)
WARN=$(grep -c '^\[WARN\]' "$LOG" 2>/dev/null || true)
echo "READY $OUT $SIZE ${GEN:-?} (오늘 run_daily WARN ${WARN:-0}건)"
