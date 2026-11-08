#!/bin/zsh
# Viewer frames for the video: the replay viewer in its dark theme at 1920x1080, one PNG per moment.
# Needs Playwright's chrome-headless-shell (npx playwright install chromium-headless-shell) or set HEADLESS_SHELL.
set -e
cd "$(dirname "$0")"
HS="${HEADLESS_SHELL:-$(ls ~/Library/Caches/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-*/chrome-headless-shell 2>/dev/null | tail -1)}"
V="$(cd .. && pwd)/viewer/index.html"
mkdir -p public/frames
for spec in "e0:event=0" "e1:event=1" "e2:event=2" "e3:event=3" "last:event=last&panel=verdicts"; do
  n=${spec%%:*}; h=${spec#*:}
  "$HS" --disable-gpu --hide-scrollbars --force-device-scale-factor=1.3333333 --window-size=1440,810 --virtual-time-budget=5000 \
    --screenshot="$PWD/public/frames/cover205-$n.png" "file://$V#example=attack-relabel_cover-seed205&$h&theme=dark" >/dev/null 2>&1
done
echo "frames written to public/frames"
