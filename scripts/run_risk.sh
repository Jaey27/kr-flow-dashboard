#!/bin/bash
# ---------------------------------------------------------------------------
#  kr-flow-dashboard : 리스크 탭 아침 재수집 (launchd com.pjy.kr-flow-risk, 평일 KST 09:30 · 10:00 재시도)
#  06:50 run_daily 때는 전날 미국분이 아직 없다(10/20 실측: FINRA 08~09시, DTCC CDS 09:15 KST 게시).
#  그래서 FINRA(하루 1번, Jae 10/19 조회 횟수 줄이기)와 DTCC·주가를 여기서 다시 받아 리스크만 다시 굽고 Pages 게시.
#  run.sh·run_daily.sh 와 같은 락. 각 단계는 실패해도 다음 단계로 넘어간다.
#  10:00 회차(10/23 Jae): 오늘 이미 돌았으면 risk_fresh.py 로 판정 → FRESH 면 아무것도 안 하고 끝,
#  STALE(DTCC 직전 영업일분 없음 등)이면 다시 돈다. FINRA 는 오늘 이미 받았으면 재시도에서도 건너뜀(하루 1번).
#  끝나면 logs/risk_done_YYYYMMDD 를 갱신 → 10:30 PLAYBOOK 재게시(playbook_prepare.sh --if-new)가 이걸 보고 판단.
#  수동으로 무조건 다시 돌리려면: bash scripts/run_risk.sh --force
# ---------------------------------------------------------------------------
set -uo pipefail
PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
cd "$PROJECT_DIR"
export TZ=Asia/Seoul PYTHONIOENCODING=utf-8 PYTHONUTF8=1
PY="${KRFLOW_PYTHON:-$PROJECT_DIR/.venv/bin/python}"
LOG_DIR="$PROJECT_DIR/logs"; mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/risk_$(date +%Y%m%d).log"
LOCK_DIR="$PROJECT_DIR/.run.lock"
DONE="$LOG_DIR/risk_done_$(date +%Y%m%d)"
RETRY=0
if [ -e "$DONE" ] && [ "${1:-}" != "--force" ]; then
  STATE="$("$PY" scripts/risk_fresh.py 2>&1 | tail -1)"
  if [ "${STATE%% *}" = "FRESH" ]; then
    echo "=== $(date '+%H:%M:%S') 재시도 회차: 앞 회차가 다 받음(FRESH) — 생략" >>"$LOG"; exit 0
  fi
  echo "=== $(date '+%H:%M:%S') 재시도 회차: $STATE — 다시 수집" >>"$LOG"; RETRY=1
fi
for i in $(seq 1 90); do mkdir "$LOCK_DIR" 2>/dev/null && break; sleep 10; done
[ -d "$LOCK_DIR" ] || { echo "$(date) 락 획득 실패" >>"$LOG"; exit 1; }
printf '%s\n%s\n' "$$" "$(sysctl -n kern.boottime 2>/dev/null)" >"$LOCK_DIR/pid"
trap 'rm -rf "$LOCK_DIR"' EXIT HUP INT TERM
step(){ echo "=== $(date '+%H:%M:%S') $*" >>"$LOG"; "$@" >>"$LOG" 2>&1 || echo "[WARN] 실패: $*" >>"$LOG"; }

step git pull -q --rebase --autostash origin "$(git rev-parse --abbrev-ref HEAD)"
if [ "$RETRY" = 0 ] || "$PY" scripts/risk_fresh.py --need finra; then
  step "$PY" scripts/risk_history.py finra       # FINRA 웹 채권 일별(하루 1번). 막히면 data/risk/FINRA_BLOCKED 남기고 자동 중단
  step "$PY" scripts/hy_split.py --backfill-ai   # AI 채권 스프레드 복원(위 FINRA 결과 사용)
else
  echo "=== $(date '+%H:%M:%S') FINRA 오늘 이미 수집 — 재시도에서 건너뜀" >>"$LOG"
fi
step "$PY" scripts/risk_breadth.py               # FINRA 공식 API 시장 등락
step "$PY" scripts/risk_history.py cds           # DTCC CDS (09:15 게시분)
step "$PY" scripts/risk_history.py cdsvol        # CDS 거래 건수 + 북미 IG CDX
step "$PY" scripts/risk_history.py stocks        # 관련 회사 주가 (Yahoo)
step "$PY" scripts/hy_split.py --fred            # ICE BofA OAS
step "$PY" scripts/crwv_fwb.py                 # CRWV 9.75% 2031 프랑크푸르트 시세 1회(FINRA 빈 날 메우기, Jae 10/26)
step "$PY" scripts/risk_data.py
step "$PY" scripts/render.py --docs
if [ "${KRFLOW_PUBLISH:-auto}" != "0" ]; then step bash scripts/publish.sh; fi
echo "=== $(date '+%H:%M:%S') 판정: $("$PY" scripts/risk_fresh.py 2>&1 | tail -1)" >>"$LOG"
touch "$DONE"
find "$LOG_DIR" \( -name 'risk_*.log' -o -name 'risk_done_*' \) -type f -mtime +60 -delete 2>/dev/null || true
exit 0
