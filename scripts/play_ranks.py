"""Misst wöchentlich die Google-Play-Plätze von MamaFunke (DE) für die wichtigsten Suchbegriffe.

Aufruf: python scripts/play_ranks.py  -> hängt eine Zeile pro Begriff an state/play_ranks.csv an.
Platz 0 heißt: nicht unter den ersten Treffern.
"""

import csv
import datetime
import re
import urllib.parse
import urllib.request
from pathlib import Path

BEGRIFFE = [
    "spruch des tages", "sprüche für mütter", "mama sprüche", "mental load", "sprüche zum nachdenken",
    "muttertag sprüche", "aufmunternde sprüche", "positive sprüche", "tagesspruch", "zitat des tages",
    "mutter sprüche", "affirmationen", "positive affirmationen", "mama affirmationen", "mamafunke",
]
PAKET = "de.mamafunke.app"
ZIEL = Path(__file__).resolve().parent.parent / "state" / "play_ranks.csv"


def platz(begriff: str) -> tuple[int, int]:
    url = "https://play.google.com/store/search?" + urllib.parse.urlencode(
        {"q": begriff, "c": "apps", "hl": "de", "gl": "DE"})
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept-Language": "de-DE"})
    html = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "ignore")
    ids: list[str] = []
    for m in re.findall(r"/store/apps/details\?id=([\w\.]+)", html):
        if m not in ids:
            ids.append(m)
    return (ids.index(PAKET) + 1 if PAKET in ids else 0), len(ids)


if __name__ == "__main__":
    heute = datetime.date.today().isoformat()
    neu = not ZIEL.exists()
    with ZIEL.open("a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if neu:
            w.writerow(["datum", "begriff", "platz", "treffer"])
        for b in BEGRIFFE:
            p, n = platz(b)
            w.writerow([heute, b, p, n])
            print(f"{b:26} Platz {p or '-'} von {n}")
