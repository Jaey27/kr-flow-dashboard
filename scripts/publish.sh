#!/bin/bash
# ---------------------------------------------------------------------------
#  kr-flow-dashboard : docs/index.html + 원장을 GitHub 로 push (Pages 갱신)
#  run.sh 가 렌더 성공 직후에만 부른다. 자사주 대시보드 publish.sh 와 같은 규칙:
#   - 명시한 경로만 스테이징 · .env 추적되면 즉시 중단
#   - 타임스탬프(generated_at/fetched_at)만 바뀐 경우 커밋하지 않음
#   - 커밋 신원이 없으면 중단(개인 메일이 public 커밋에 박히는 것 방지)
#   - '로컬이 origin 보다 앞서 있으면' push (지난번 push 실패분도 다음 실행이 밀어 올린다)
# ---------------------------------------------------------------------------
set -euo pipefail
cd "$(dirname "$0")/.."

log() { printf '[publish] %s\n' "$*"; }
die() { printf '[publish][ERROR] %s\n' "$*" >&2; exit 1; }

git rev-parse --is-inside-work-tree >/dev/null 2>&1 || die "git 리포가 아니다"
git remote get-url origin >/dev/null 2>&1 || die "origin 리모트가 없다"
BRANCH="$(git rev-parse --abbrev-ref HEAD)"
[ "$BRANCH" = "HEAD" ] && die "detached HEAD"
git ls-files --error-unmatch .env >/dev/null 2>&1 && die ".env 가 git 에 추적되고 있다 — git rm --cached .env"
[ -f docs/index.html ] || die "docs/index.html 이 없다 — render.py --docs 먼저"

if git ls-remote --exit-code --heads origin "$BRANCH" >/dev/null 2>&1; then
  git pull -q --rebase --autostash origin "$BRANCH" || die "pull --rebase 실패 — 수동 해결 필요"
fi

PATHS=(docs/index.html docs/sector.html docs/rates.html docs/cpi.html docs/.nojekyll data/flows.json data/macro.json data/fedwatch_ledger.json data/holidays_kr.json data/ledger data/manual data/pce_nowcast_log.json)
for f in "${PATHS[@]}"; do [ -e "$f" ] && git add -- "$f"; done

TS_RE='s/"(generated_at|fetched_at)"([[:space:]]*:[[:space:]]*)"[^"]*"/"\1"\2"~TS~"/g'
substantive() {
  local f
  for f in $(git diff --cached --name-only); do
    if ! diff -q <(git show ":$f" 2>/dev/null | sed -E "$TS_RE") \
                 <(git show "HEAD:$f" 2>/dev/null | sed -E "$TS_RE") >/dev/null 2>&1; then
      return 0
    fi
  done
  return 1
}

if git diff --cached --quiet; then
  log "커밋할 변경 없음"
elif ! substantive; then
  log "타임스탬프만 바뀜 — 커밋하지 않는다"; git reset -q
else
  git config user.name >/dev/null && git config user.email >/dev/null \
    || die "커밋 신원 없음: git config user.name Jaey27 / user.email Jaey27@users.noreply.github.com"
  git commit -q -m "data: update $(date '+%Y-%m-%d %H:%M %Z')"
  log "커밋: $(git log -1 --format=%h) ($(git diff --name-only HEAD~1 2>/dev/null | wc -l | tr -d ' ')개 파일)"
fi

AHEAD=0
if git rev-parse --verify -q "origin/$BRANCH" >/dev/null; then
  AHEAD="$(git rev-list --count "origin/$BRANCH..HEAD")"
else
  AHEAD=1
fi
if [ "$AHEAD" -gt 0 ]; then
  git push -q origin "$BRANCH" && log "push 완료 (${AHEAD}커밋)"
else
  log "push 할 것 없음"
fi
