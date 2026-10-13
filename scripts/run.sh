#!/bin/bash
# ---------------------------------------------------------------------------
#  kr-flow-dashboard : launchd 가 5분마다 부르는 엔트리포인트
#
#   1) build_data.py --auto : '지금 새 값이 나올 차례인 출처'만 조회 -> 원장 병합 -> flows.json
#        exit 0 = 바뀜 · 3 = 할 일 없음/변경 없음(조용히 종료) · 1 = 수집 실패
#   2) render.py            : 바뀐 경우에만 dashboard.html 을 다시 굽는다
#   3) publish.sh           : 렌더된 경우에만 docs/index.html·원장을 GitHub Pages 로 push
#
#  할 일이 없는 실행은 네트워크 0회, 로그 0줄이다(하트비트 파일만 갱신).
#  환경변수: KRFLOW_PYTHON(기본 .venv/bin/python) · KRFLOW_MODE(auto|full|backfill, 기본 auto)
# ---------------------------------------------------------------------------
set -uo pipefail

PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
cd "$PROJECT_DIR"
export TZ=Asia/Seoul PYTHONIOENCODING=utf-8 PYTHONUTF8=1

PY="${KRFLOW_PYTHON:-$PROJECT_DIR/.venv/bin/python}"
MODE="${KRFLOW_MODE:-auto}"
LOG_DIR="$PROJECT_DIR/logs"
LOCK_DIR="$PROJECT_DIR/.run.lock"
mkdir -p "$LOG_DIR"
date "+%Y-%m-%d %H:%M:%S" >"$LOG_DIR/heartbeat"

# launchd stdout/err 파일은 무한 append 되므로 5MB 넘으면 비운다
for f in "$LOG_DIR/launchd.out.log" "$LOG_DIR/launchd.err.log"; do
  [ -f "$f" ] && [ "$(wc -c <"$f")" -gt 5242880 ] && : >"$f"
done

# ---- 중복 실행 락 (mkdir 은 원자적). 죽은 PID·재부팅·30분 초과 락은 회수 ----
if ! mkdir "$LOCK_DIR" 2>/dev/null; then
  OLD_PID="$(sed -n 1p "$LOCK_DIR/pid" 2>/dev/null || true)"
  OLD_BOOT="$(sed -n 2p "$LOCK_DIR/pid" 2>/dev/null || true)"
  NOW_BOOT="$(sysctl -n kern.boottime 2>/dev/null || true)"
  AGE_MIN=$(( ( $(date +%s) - $(stat -f %m "$LOCK_DIR" 2>/dev/null || date +%s) ) / 60 ))
  if [ -n "$OLD_PID" ] && kill -0 "$OLD_PID" 2>/dev/null && [ "$OLD_BOOT" = "$NOW_BOOT" ] && [ "$AGE_MIN" -lt 30 ]; then
    exit 0   # 앞선 실행이 아직 도는 중
  fi
  rm -rf "$LOCK_DIR"; mkdir "$LOCK_DIR" 2>/dev/null || exit 0
fi
printf '%s\n%s\n' "$$" "$(sysctl -n kern.boottime 2>/dev/null)" >"$LOCK_DIR/pid"
trap 'rm -rf "$LOCK_DIR"' EXIT HUP INT TERM

RUN_LOG="$LOG_DIR/run_$(date +%Y%m%d).log"
OUT="$(mktemp -t krflow)"

rc=0
"$PY" scripts/build_data.py "--$MODE" >"$OUT" 2>&1 || rc=$?

if [ "$rc" -eq 3 ] && [ ! -s "$OUT" ]; then
  rm -f "$OUT"; exit 0          # 할 일 없음 — 로그 남기지 않음
fi

{
  echo "=== $(date '+%Y-%m-%d %H:%M:%S') build_data --$MODE (exit $rc)"
  cat "$OUT"
} >>"$RUN_LOG"
rm -f "$OUT"

if [ "$rc" -eq 1 ]; then
  echo "[ERROR] 수집 실패 — dashboard.html 은 직전 값 그대로" >>"$RUN_LOG"
  exit 1
fi

if [ "$rc" -eq 0 ] || [ ! -f "$PROJECT_DIR/dashboard.html" ]; then
  if ! "$PY" scripts/render.py --docs >>"$RUN_LOG" 2>&1; then
    echo "[ERROR] render.py 실패" >>"$RUN_LOG"; exit 2
  fi
  # 렌더 성공 시에만 GitHub Pages 로 push. 실패해도 로컬은 정상이고 다음 실행이 밀린 커밋을 다시 push 한다
  if [ "${KRFLOW_PUBLISH:-auto}" != "0" ] && git -C "$PROJECT_DIR" remote get-url origin >/dev/null 2>&1; then
    bash scripts/publish.sh >>"$RUN_LOG" 2>&1 || echo "[WARN] publish.sh 실패 — 공개 페이지 미갱신" >>"$RUN_LOG"
  fi
fi

find "$LOG_DIR" -name 'run_*.log' -type f -mtime +60 -delete 2>/dev/null || true
exit 0
