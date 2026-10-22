#!/bin/bash
# ---------------------------------------------------------------------------
#  kr-flow-dashboard : 리스크 탭 아침 재수집 (launchd com.pjy.kr-flow-risk, 평일 KST 09:30)
#  06:50 run_daily 때는 전날 미국분이 아직 없다(10/20 실측: FINRA 08~09시, DTCC CDS 09:15 KST 게시).
#  그래서 FINRA(하루 1번, Jae 10/19 조회 횟수 줄이기)와 DTCC·주가를 여기서 다시 받아 리스크만 다시 굽고 Pages 게시.
#  run.sh·run_daily.sh 와 같은 락. 각 단계는 실패해도 다음 단계로 넘어간다.
# ---------------------------------------------------------------------------
set -uo pipefail
PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
cd "$PROJECT_DIR"
export TZ=Asia/Seoul PYTHONIOENCODING=utf-8 PYTHONUTF8=1
PY="${KRFLOW_PYTHON:-$PROJECT_DIR/.venv/bin/python}"
LOG_DIR="$PROJECT_DIR/logs"; mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/risk_$(date +%Y%m%d).log"
LOCK_DIR="$PROJECT_DIR/.run.lock"
for i in $(seq 1 90); do mkdir "$LOCK_DIR" 2>/dev/null && break; sleep 10; done
[ -d "$LOCK_DIR" ] || { echo "$(date) 락 획득 실패" >>"$LOG"; exit 1; }
printf '%s\n%s\n' "$$" "$(sysctl -n kern.boottime 2>/dev/null)" >"$LOCK_DIR/pid"
trap 'rm -rf "$LOCK_DIR"' EXIT HUP INT TERM
step(){ echo "=== $(date '+%H:%M:%S') $*" >>"$LOG"; "$@" >>"$LOG" 2>&1 || echo "[WARN] 실패: $*" >>"$LOG"; }

step git pull -q --rebase --autostash origin "$(git rev-parse --abbrev-ref HEAD)"
step "$PY" scripts/risk_history.py finra         # FINRA 웹 채권 일별(하루 1번). 막히면 data/risk/FINRA_BLOCKED 남기고 자동 중단
step "$PY" scripts/hy_split.py --backfill-ai     # AI 채권 스프레드 복원(위 FINRA 결과 사용)
step "$PY" scripts/risk_breadth.py               # FINRA 공식 API 시장 등락
step "$PY" scripts/risk_history.py cds           # DTCC CDS (09:15 게시분)
step "$PY" scripts/risk_history.py cdsvol        # CDS 거래 건수 + 북미 IG CDX
step "$PY" scripts/risk_history.py stocks        # 관련 회사 주가 (Yahoo)
step "$PY" scripts/hy_split.py --fred            # ICE BofA OAS
step "$PY" scripts/risk_data.py
step "$PY" scripts/render.py --docs
if [ "${KRFLOW_PUBLISH:-auto}" != "0" ]; then step bash scripts/publish.sh; fi
find "$LOG_DIR" -name 'risk_*.log' -type f -mtime +60 -delete 2>/dev/null || true
exit 0
