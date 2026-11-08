"""Abstract word count and page count for the event's format rules (issue #12).

  python tools/report_stats.py report/report.md [--pdf report/report.pdf]

The abstract is the text under the heading "Abstract" up to the next heading; the event requires 150 to
250 words. The PDF page count reads the page objects of a PDF file. The event allows at most 8 pages
before the references and appendices: the body ends on the page where the References heading starts, and that
page counts when any body text sits above the heading. Finding the heading needs pdftotext (poppler);
--references-page overrides it.
Exit 1 when a rule is broken.
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path


def abstract_words(markdown: str) -> int:
    m = re.search(r"^#+\s*Abstract\s*$(.*?)(?=^#+\s)", markdown, re.S | re.M | re.I)
    if not m:
        return 0
    text = re.sub(r"[*_`>]", " ", m.group(1))
    return len(re.findall(r"[A-Za-z0-9][A-Za-z0-9'./%-]*", text))


def pdf_pages(data: bytes) -> int:
    return len(re.findall(rb"/Type\s*/Page(?![s\w])", data))


def body_pages(pdf: str) -> tuple[int, int] | None:
    """(page where the References heading starts, body pages) from the PDF's text, or None without pdftotext."""
    if not shutil.which("pdftotext"):
        return None
    text = subprocess.run(["pdftotext", "-layout", pdf, "-"], capture_output=True, text=True, check=True).stdout
    for i, page in enumerate(text.split("\f"), 1):
        lines = [ln.strip() for ln in page.splitlines() if ln.strip()]
        if "References" in lines:
            above = lines[:lines.index("References")]
            return i, (i if above else i - 1)
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("report")
    ap.add_argument("--pdf")
    ap.add_argument("--references-page", type=int)
    a = ap.parse_args()
    bad = 0
    words = abstract_words(Path(a.report).read_text())
    ok = 150 <= words <= 250
    bad += not ok
    print(f"abstract: {words} words ({'ok' if ok else 'must be 150 to 250'})")
    if a.pdf:
        pages = pdf_pages(Path(a.pdf).read_bytes())
        found = body_pages(a.pdf)
        if a.references_page:
            body = a.references_page - 1
        elif found:
            body = found[1]
        else:
            body = pages
        ok = body <= 8
        bad += not ok
        print(f"pdf: {pages} pages; {body} before the references ({'ok' if ok else 'must be 8 or fewer'})")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
