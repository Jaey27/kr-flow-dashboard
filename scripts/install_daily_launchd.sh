#!/bin/bash
# 매일 갱신(run_daily.sh)을 launchd 에 등록 — KST 06:50, 19:00. 해제: launchctl unload ~/Library/LaunchAgents/com.pjy.kr-flow-daily.plist
set -euo pipefail
PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
PLIST="$HOME/Library/LaunchAgents/com.pjy.kr-flow-daily.plist"
chmod +x "$PROJECT_DIR/scripts/run_daily.sh"
cat >"$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>com.pjy.kr-flow-daily</string>
  <key>ProgramArguments</key><array><string>/bin/bash</string><string>$PROJECT_DIR/scripts/run_daily.sh</string></array>
  <key>StartCalendarInterval</key><array>
    <dict><key>Hour</key><integer>6</integer><key>Minute</key><integer>50</integer></dict>
    <dict><key>Hour</key><integer>19</integer><key>Minute</key><integer>0</integer></dict>
  </array>
  <key>StandardOutPath</key><string>$PROJECT_DIR/logs/launchd.daily.out.log</string>
  <key>StandardErrorPath</key><string>$PROJECT_DIR/logs/launchd.daily.err.log</string>
</dict></plist>
EOF
launchctl unload "$PLIST" 2>/dev/null || true
launchctl load "$PLIST"
echo "등록됨: $PLIST (06:50, 19:00 KST — 맥미니 시간대가 Asia/Seoul 이어야 함)"
