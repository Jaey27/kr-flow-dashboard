#!/bin/bash
# 리스크 아침 재수집(run_risk.sh)을 launchd 에 등록 — 평일 KST 09:30. 해제: launchctl unload ~/Library/LaunchAgents/com.pjy.kr-flow-risk.plist
set -euo pipefail
PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
PLIST="$HOME/Library/LaunchAgents/com.pjy.kr-flow-risk.plist"
chmod +x "$PROJECT_DIR/scripts/run_risk.sh"
DAYS=""; for d in 1 2 3 4 5; do DAYS="$DAYS<dict><key>Weekday</key><integer>$d</integer><key>Hour</key><integer>9</integer><key>Minute</key><integer>30</integer></dict>"; done
cat >"$PLIST" <<PL
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>com.pjy.kr-flow-risk</string>
  <key>ProgramArguments</key><array><string>/bin/bash</string><string>$PROJECT_DIR/scripts/run_risk.sh</string></array>
  <key>StartCalendarInterval</key><array>$DAYS</array>
  <key>StandardOutPath</key><string>$PROJECT_DIR/logs/launchd.risk.out.log</string>
  <key>StandardErrorPath</key><string>$PROJECT_DIR/logs/launchd.risk.err.log</string>
</dict></plist>
PL
launchctl unload "$PLIST" 2>/dev/null || true
launchctl load "$PLIST"
echo "등록됨: $PLIST (평일 09:30 KST)"
