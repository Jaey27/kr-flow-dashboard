#!/bin/bash
LABEL=com.pjy.kr-flow-dashboard
launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null && echo "해제: $LABEL" || echo "등록돼 있지 않음"
echo "(plist 는 ~/Library/LaunchAgents/$LABEL.plist 에 남겨 둔다)"
