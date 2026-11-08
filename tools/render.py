"""Render figures with a headless Chromium (no plotting library, no network).

Pages run in $CHROMIUM, else the newest Playwright Chromium in ~/Library/Caches/ms-playwright. Screenshots use
Playwright's chrome-headless-shell ($HEADLESS_SHELL), whose viewport equals the window size; Chromium's new headless
mode keeps part of the window for itself and would clip the bottom of a figure.
"""

from __future__ import annotations

import html
import os
import re
import subprocess
import tempfile
from pathlib import Path


def chromium() -> str:
    env = os.environ.get("CHROMIUM")
    if env:
        return env
    found = sorted(Path.home().glob("Library/Caches/ms-playwright/chromium-*/chrome-mac*/Chromium.app/Contents/MacOS/Chromium"))
    if not found:
        raise SystemExit("No Chromium found: set CHROMIUM to a Chromium or Chrome binary.")
    return str(found[-1])


def headless_shell() -> str:
    env = os.environ.get("HEADLESS_SHELL")
    if env:
        return env
    found = sorted(Path.home().glob("Library/Caches/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-*/chrome-headless-shell"))
    if not found:
        raise SystemExit("No chrome-headless-shell found: set HEADLESS_SHELL (npx playwright install chromium-headless-shell).")
    return str(found[-1])


def svg_size(svg: str) -> tuple[int, int]:
    m = re.search(r'viewBox="0 0 ([\d.]+) ([\d.]+)"', svg)
    if not m:
        raise ValueError("the SVG has no viewBox")
    return round(float(m.group(1))), round(float(m.group(2)))


def svg_to_png(svg_path: Path, png_path: Path, scale: int = 2) -> None:
    """Screenshot the SVG at its own size, `scale` device pixels per unit."""
    svg = svg_path.read_text(encoding="utf-8")
    w, h = svg_size(svg)
    with tempfile.TemporaryDirectory() as tmp:
        page = Path(tmp) / "page.html"
        page.write_text(f'<!doctype html><meta charset="utf-8"><style>html,body{{margin:0;padding:0}}svg{{display:block;width:{w}px;height:{h}px}}</style>{svg}',
                        encoding="utf-8")
        subprocess.run([headless_shell(), "--disable-gpu", "--no-first-run", "--hide-scrollbars",
                        f"--force-device-scale-factor={scale}", f"--window-size={w},{h}", f"--screenshot={png_path.resolve()}",
                        f"file://{page}"], check=True, capture_output=True, timeout=120)


def dump_dom(url: str, budget_ms: int = 8000) -> str:
    """Load a page, let its scripts and timers run, and return the serialised DOM."""
    out = subprocess.run([chromium(), "--headless=new", "--disable-gpu", "--no-first-run", f"--virtual-time-budget={budget_ms}",
                          "--dump-dom", url], check=True, capture_output=True, timeout=120)
    return out.stdout.decode("utf-8")


def pre_text(dom: str, element_id: str) -> str | None:
    m = re.search(rf'<pre id="{element_id}">(.*?)</pre>', dom, re.S)
    return html.unescape(m.group(1)) if m else None
