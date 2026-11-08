#!/bin/zsh
# Build report/report.pdf from report/report.md (pandoc 3 and a Chromium binary).
set -e
cd "$(dirname "$0")"
pandoc report.md --standalone --embed-resources --css style.css --metadata pagetitle="report" -o report.html
CH="${CHROMIUM:-$(ls ~/Library/Caches/ms-playwright/chromium-*/chrome-mac*/Chromium.app/Contents/MacOS/Chromium 2>/dev/null | tail -1)}"
"$CH" --headless=new --disable-gpu --no-first-run --no-pdf-header-footer --virtual-time-budget=5000 --print-to-pdf=report.pdf "file://$PWD/report.html" 2>/dev/null
echo "wrote $(pwd)/report.pdf"
