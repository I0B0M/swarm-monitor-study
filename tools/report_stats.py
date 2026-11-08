"""Abstract word count and page count for the event's format rules (issue #12).

  python tools/report_stats.py report/report.md [--pdf report/report.pdf --references-page 9]

The abstract is the text under the heading "Abstract" up to the next heading; the event requires 150 to
250 words. The PDF page count reads the page objects of a PDF file. The event allows at most 8 pages
before the references and appendices; pass --references-page with the page where References begins.
Exit 1 when a rule is broken.
"""

from __future__ import annotations

import argparse
import re
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
        body = (a.references_page - 1) if a.references_page else pages
        ok = body <= 8
        bad += not ok
        print(f"pdf: {pages} pages; {body} before the references ({'ok' if ok else 'must be 8 or fewer'})")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
