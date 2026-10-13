#!/bin/bash
# launchd 등록: 5분마다 scripts/run.sh (할 일이 없으면 네트워크·로그 0)
set -euo pipefail
PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
LABEL=com.pjy.kr-flow-dashboard
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
cat >"$PLIST" <<PL
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key><string>$LABEL</string>
    <key>ProgramArguments</key>
    <array><string>/bin/bash</string><string>$PROJECT_DIR/scripts/run.sh</string></array>
    <key>WorkingDirectory</key><string>$PROJECT_DIR</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key><string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
        <key>TZ</key><string>Asia/Seoul</string>
    </dict>
    <key>StartInterval</key><integer>300</integer>
    <key>RunAtLoad</key><true/>
    <key>ProcessType</key><string>Background</string>
    <key>StandardOutPath</key><string>$PROJECT_DIR/logs/launchd.out.log</string>
    <key>StandardErrorPath</key><string>$PROJECT_DIR/logs/launchd.err.log</string>
</dict>
</plist>
PL
launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"
echo "등록 완료: $PLIST"
launchctl print "gui/$(id -u)/$LABEL" | grep -E "state|run interval|last exit" || true
