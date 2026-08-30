#!/usr/bin/env python3
"""
Regenerate the QNEST print PDFs from the HTML sources.

    pip install playwright
    playwright install chromium
    python make-pdfs.py

Each piece keeps its own page size, so the PDFs come out ready for the printer
with no scaling and no margins.
"""

from pathlib import Path
from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent

JOBS = [
    # source,           output,           page settings
    ("brochure.html", "brochure.pdf", {"format": "A4", "landscape": True}),
    ("handout.html",  "handout.pdf",  {"format": "A4", "landscape": False}),
    ("card.html",     "card.pdf",     {"width": "91mm", "height": "61mm"}),
]

NO_MARGIN = {"top": "0", "right": "0", "bottom": "0", "left": "0"}


def main() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        for src, out, size in JOBS:
            page.goto((HERE / src).as_uri())
            page.wait_for_timeout(1500)

            missing = page.evaluate(
                "Array.from(document.images)"
                ".filter(i => !i.complete || i.naturalWidth === 0)"
                ".map(i => i.src)"
            )
            if missing:
                print(f"  ! {src}: images failed to load: {missing}")

            page.pdf(path=str(HERE / out), print_background=True,
                     margin=NO_MARGIN, **size)
            print(f"  {src}  ->  {out}")
        browser.close()


if __name__ == "__main__":
    main()
