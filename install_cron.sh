#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="$(which python3)"
PLIST="$HOME/Library/LaunchAgents/ncu.checkin.plist"

# ── 1. Prevent sleep when plugged in ─────────────────────────────────────────
echo "Disabling sleep on AC power..."
sudo pmset -c sleep 0
sudo pmset -c disksleep 0

# ── 2. Write launchd plist ────────────────────────────────────────────────────
echo "Installing launchd job → $PLIST"
cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>ncu.checkin</string>

  <key>ProgramArguments</key>
  <array>
    <string>$PYTHON</string>
    <string>$SCRIPT_DIR/checkin.py</string>
  </array>

  <key>WorkingDirectory</key>
  <string>$SCRIPT_DIR</string>

  <key>StartInterval</key>
  <integer>300</integer>

  <key>RunAtLoad</key>
  <false/>

  <key>StandardOutPath</key>
  <string>$SCRIPT_DIR/launchd.log</string>

  <key>StandardErrorPath</key>
  <string>$SCRIPT_DIR/launchd.log</string>

  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key>
    <string>/usr/local/bin:/usr/bin:/bin</string>
    <key>HOME</key>
    <string>$HOME</string>
  </dict>
</dict>
</plist>
EOF

# ── 3. Load the job ───────────────────────────────────────────────────────────
# Unload first in case it was already loaded
launchctl unload "$PLIST" 2>/dev/null || true
launchctl load "$PLIST"

echo ""
echo "Done."
echo "  Checkin runs every 5 minutes via launchd."
echo "  Sleep disabled on AC power (plugged in)."
echo ""
echo "To uninstall:"
echo "  launchctl unload $PLIST && rm $PLIST"
echo "  sudo pmset -c sleep 1"
