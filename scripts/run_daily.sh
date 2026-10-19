#!/bin/bash
# ---------------------------------------------------------------------------
#  kr-flow-dashboard : 매크로·리스크·경제지표·SEIBro 매일 갱신 (launchd com.pjy.kr-flow-daily)
#  하루 2번(KST 06:50 = 미국 마감 반영 / 19:00 = 국내 장 마감·SEIBro 반영). 수급 5분 루프(run.sh)와 락을 공유한다.
#  각 단계는 실패해도 다음 단계로 넘어간다(앞 단계 실패 = 그 데이터만 직전 값 유지).
# ---------------------------------------------------------------------------
set -uo pipefail
PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
cd "$PROJECT_DIR"
export TZ=Asia/Seoul PYTHONIOENCODING=utf-8 PYTHONUTF8=1
PY="${KRFLOW_PYTHON:-$PROJECT_DIR/.venv/bin/python}"
LOG_DIR="$PROJECT_DIR/logs"; mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/daily_$(date +%Y%m%d).log"
LOCK_DIR="$PROJECT_DIR/.run.lock"

# run.sh 와 같은 락. 최대 15분 기다린다
for i in $(seq 1 90); do mkdir "$LOCK_DIR" 2>/dev/null && break; sleep 10; done
[ -d "$LOCK_DIR" ] || { echo "$(date) 락 획득 실패" >>"$LOG"; exit 1; }
printf '%s\n%s\n' "$$" "$(sysctl -n kern.boottime 2>/dev/null)" >"$LOCK_DIR/pid"
trap 'rm -rf "$LOCK_DIR"' EXIT HUP INT TERM

step(){ echo "=== $(date '+%H:%M:%S') $*" >>"$LOG"; "$@" >>"$LOG" 2>&1 || echo "[WARN] 실패: $*" >>"$LOG"; }

# 편집은 다른 곳(Windows·웹 Claude)에서 GitHub로 push → 맥미니는 실행 전에 받아서 새 코드로 굽는다(코드만 받고, docs/data 는 맥미니가 주인)
step git pull -q --rebase --autostash origin "$(git rev-parse --abbrev-ref HEAD)"

step "$PY" scripts/macro_data.py                 # 미 금리·BEI·TP·원달러·Brent·Kalshi·FedWatch·금리분해·발표일정
step "$PY" scripts/hy_split.py                   # HYG/LQD 보유종목 AI/비AI 원장(하루 1행)
step "$PY" scripts/hy_split.py --fred            # ICE BofA OAS (FRED, UA=curl)
step "$PY" scripts/risk_breadth.py               # FINRA 공식 API 시장 등락 (.env FINRA_CLIENT/SECRET)
step "$PY" scripts/risk_history.py cds           # DTCC CDS (일자 캐시)
step "$PY" scripts/risk_history.py stocks        # 관련 회사 주가 (Yahoo)
# FINRA 웹 채권 일별 — 아침(12시 전) 실행에서만(Jae 10/19: 조회 횟수 줄이기). 막히면 data/risk/FINRA_BLOCKED 남기고 자동 중단
if [ "$(date +%H)" -lt 12 ]; then
  step "$PY" scripts/risk_history.py finra
  step "$PY" scripts/hy_split.py --backfill-ai     # AI 채권 스프레드 복원(위 FINRA 결과 사용)
fi
step "$PY" scripts/fss_fetch.py                  # 금감원 외국인 증권투자 동향(월간, KDI 게재본) — 빠진 달만 추가
step "$PY" scripts/seibro_flow.py                # SEIBro 한국인 미국주식 결제·보관 + 종목 TOP50(일자 캐시)
step "$PY" cpi_dashboard/scripts/run_cpi.py --no-send   # CPI(발표일에만 재빌드)
[ -f cpi_dashboard/cpi.html ] && cp cpi_dashboard/cpi.html docs/cpi.html
step "$PY" scripts/risk_data.py
step "$PY" scripts/render.py --docs
step "$PY" scripts/render_sector.py --docs
if [ "${KRFLOW_PUBLISH:-auto}" != "0" ]; then step bash scripts/publish.sh; fi
find "$LOG_DIR" -name 'daily_*.log' -type f -mtime +60 -delete 2>/dev/null || true
exit 0
