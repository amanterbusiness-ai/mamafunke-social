"""Schreibt docs/pins/feed.xml aus state/pins.json: nur Pins, deren Termin erreicht ist.

Läuft täglich in .github/workflows/pins.yml (nur Standardbibliothek). Pinterest liest den
Feed regelmäßig und veröffentlicht neue Einträge automatisch auf dem verknüpften Board.
"""

from __future__ import annotations

import datetime as dt
import json
from email.utils import format_datetime
from pathlib import Path
from xml.sax.saxutils import escape
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
QUEUE = ROOT / "state" / "pins.json"
FEED = ROOT / "docs" / "pins" / "feed.xml"
BERLIN = ZoneInfo("Europe/Berlin")


def faellig(pins: list[dict], jetzt: dt.datetime) -> list[tuple[dt.datetime, dict]]:
    out = []
    for p in pins:
        zeit = dt.datetime.fromisoformat(f"{p['datum']}T{p['uhr']}").replace(tzinfo=BERLIN)
        if zeit <= jetzt:
            out.append((zeit, p))
    return sorted(out, key=lambda z: z[0], reverse=True)[:30]


def feed(eintraege: list[tuple[dt.datetime, dict]]) -> str:
    items = []
    for zeit, p in eintraege:
        items.append(
            "<item>"
            f"<title>{escape(p['titel'])}</title>"
            f"<link>{escape(p['link'])}</link>"
            f"<guid isPermaLink=\"false\">mamafunke-pin-{escape(p['id'])}</guid>"
            f"<pubDate>{format_datetime(zeit)}</pubDate>"
            f"<description>{escape(p['beschreibung'])}</description>"
            f"<enclosure url=\"{escape(p['bild'])}\" type=\"image/jpeg\" length=\"0\"/>"
            f"<media:content url=\"{escape(p['bild'])}\" medium=\"image\" type=\"image/jpeg\"/>"
            "</item>"
        )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0" xmlns:media="http://search.yahoo.com/mrss/">'
        "<channel><title>MamaFunke: Sprüche für Mütter</title><link>https://mamafunke.de/</link>"
        "<description>Ehrliche Sprüche für Mütter aus der App MamaFunke</description><language>de-DE</language>"
        + "".join(items)
        + "</channel></rss>\n"
    )


if __name__ == "__main__":
    pins = json.loads(QUEUE.read_text(encoding="utf-8"))
    eintraege = faellig(pins, dt.datetime.now(BERLIN))
    FEED.parent.mkdir(parents=True, exist_ok=True)
    FEED.write_text(feed(eintraege), encoding="utf-8", newline="\n")
    print(f"{len(eintraege)} Pins im Feed")
