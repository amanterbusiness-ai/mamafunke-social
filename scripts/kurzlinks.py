"""Kurzlinks mamafunke.de/ig, /tt, ... erzeugen: je Kanal eine Kopie von docs/weiter.html.

Die Seite liest den Kanal aus dem ersten Pfadteil. docs/index.html ist die normale
Startseite (für Google, ohne Weiterleitung). Nach jeder Änderung an docs/weiter.html
einmal ausführen: python scripts/kurzlinks.py
"""

from pathlib import Path

KANAELE = ["ig", "tt", "yt", "fb", "forum", "pin", "creator", "teilen", "wa"]
DOCS = Path(__file__).resolve().parent.parent / "docs"

if __name__ == "__main__":
    seite = (DOCS / "weiter.html").read_text(encoding="utf-8")
    for k in KANAELE:
        (DOCS / k).mkdir(exist_ok=True)
        (DOCS / k / "index.html").write_text(seite, encoding="utf-8", newline="\n")
    print(f"{len(KANAELE)} Kurzlinks geschrieben")
