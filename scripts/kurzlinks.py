"""Kurzlinks mamafunke.de/ig, /tt, ... erzeugen: je Kanal eine Kopie von docs/index.html.

Die Seite liest den Kanal aus dem ersten Pfadteil. Nach jeder Änderung an docs/index.html
einmal ausführen: python scripts/kurzlinks.py
"""

from pathlib import Path

KANAELE = ["ig", "tt", "yt", "fb", "forum", "pin", "creator"]
DOCS = Path(__file__).resolve().parent.parent / "docs"

if __name__ == "__main__":
    seite = (DOCS / "index.html").read_text(encoding="utf-8")
    for k in KANAELE:
        (DOCS / k).mkdir(exist_ok=True)
        (DOCS / k / "index.html").write_text(seite, encoding="utf-8")
    print(f"{len(KANAELE)} Kurzlinks geschrieben")
