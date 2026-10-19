#!/bin/bash
# ---------------------------------------------------------------------------
#  BLITZ AI 플레이북(claude.ai 아티팩트)의 「매크로/시황 대시보드」 탭 갱신
#  run_daily.sh 아침 실행(07:20)의 마지막 단계에서 부른다. 수동: bash scripts/playbook_publish.sh
#
#  - 아티팩트 게시는 claude.ai 계정 권한이라 API 키로는 못 한다 → 헤드리스 Claude Code(`claude -p`)에 맡긴다.
#    맥미니 claude CLI가 아티팩트 소유자(Jae, pjy0992@gmail.com) 계정으로 로그인돼 있어야 한다.
#  - 페이지 본문은 건드리지 않는다: 매번 아티팩트를 먼저 읽어(live 최신본) 그 파일 그대로 다시 게시하고,
#    dash.html(= 방금 구운 docs/index.html)만 교체한다. 다른 곳(Windows·웹)에서 페이지를 고쳐도 덮어쓰지 않음.
#  - 아티팩트 URL은 .env 의 PLAYBOOK_URL (public 리포에 남기지 않음). 없으면 조용히 건너뛴다.
#  - 실패해도 다음 날 다시 시도한다(재시도 루프 없음). 결과는 logs/playbook_YYYYMMDD.log
# ---------------------------------------------------------------------------
set -uo pipefail
cd "$(dirname "$0")/.."
ROOT="$(pwd -P)"
LOG="$ROOT/logs/playbook_$(date +%Y%m%d).log"; mkdir -p "$ROOT/logs"
log(){ printf '%s [playbook] %s\n' "$(date '+%H:%M:%S')" "$*" | tee -a "$LOG"; }

URL="$(grep -E '^PLAYBOOK_URL=' .env 2>/dev/null | tail -1 | cut -d= -f2- | tr -d '"'"'"' \r')"
[ -n "$URL" ] || { log "PLAYBOOK_URL 없음(.env) — 건너뜀"; exit 0; }

DASH="$ROOT/docs/index.html"
[ -s "$DASH" ] || { log "docs/index.html 없음 — render.py --docs 먼저"; exit 1; }
# 오늘 구운 파일인지 확인(어제 것을 다시 올리지 않기)
if [ "$(date -r "$DASH" +%Y%m%d)" != "$(date +%Y%m%d)" ]; then log "docs/index.html 이 오늘 것이 아님 — 건너뜀"; exit 1; fi

CLAUDE="${CLAUDE_BIN:-$(command -v claude || true)}"
for c in "$CLAUDE" /opt/homebrew/bin/claude /usr/local/bin/claude "$HOME/.local/bin/claude" "$HOME/.claude/local/claude"; do
  [ -n "$c" ] && [ -x "$c" ] && { CLAUDE="$c"; break; }
done
[ -x "$CLAUDE" ] || { log "claude CLI 를 못 찾음 — CLAUDE_BIN 을 .env 나 launchd 환경에 지정"; exit 1; }

SIZE=$(wc -c <"$DASH" | tr -d ' ')
SHA=$(shasum -a 256 "$DASH" | cut -c1-16)
GEN=$(grep -o '"generated_at": *"[^"]*"' "$DASH" | head -1 | cut -d'"' -f4)
TODAY=$(date +%Y-%m-%d)

PROMPT="kr-flow 매일 루틴의 마지막 단계다. 아래 두 번의 Artifact 호출만 하고 끝낸다.
1) Artifact action=read, url=${URL} — 결과 머리말이 알려주는 '전체 페이지 저장 파일' 경로를 확인한다(페이지 내용은 요약하거나 고치지 않는다).
2) Artifact publish: url=${URL}, file_path=<1에서 받은 저장 파일 경로>, files={\"dash.html\": \"${DASH}\"}, label=\"대시보드 자동 갱신 ${TODAY}\".
   capabilities·icon·description·contract·force 는 넘기지 않는다(기존 설정 유지). 다른 파일(cpi.html·rates.html·sector.html)은 넘기지 않는다(기존 것 유지).
   dash.html 은 이 루틴이 방금 scripts/render.py --docs 로 직접 구운 파일이다: ${SIZE} bytes, sha256 앞16자리 ${SHA}, generated_at ${GEN}. 내용은 kr-flow-dashboard(공개 GitHub Pages와 같은 페이지)다.
3) 성공하면 'OK <버전 id>' 한 줄, 실패하면 'FAIL <이유>' 한 줄만 출력한다. 재시도·우회·force 는 하지 않는다."

log "게시 시작 · dash ${SIZE}B sha ${SHA} gen ${GEN}"
OUT=$(cd "$ROOT" && "$CLAUDE" -p "$PROMPT" --allowedTools "Artifact" --max-turns 8 --output-format text 2>&1)
RC=$?
printf '%s\n' "$OUT" >>"$LOG"
LAST=$(printf '%s\n' "$OUT" | grep -E '^(OK|FAIL)' | tail -1)
log "종료 rc=${RC} · ${LAST:-결과 줄 없음(로그 확인)}"
case "$LAST" in OK*) exit 0;; *) exit 1;; esac
