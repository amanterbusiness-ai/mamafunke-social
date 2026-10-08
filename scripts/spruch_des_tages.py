"""Schreibt docs/spruch-des-tages/index.html: der Spruch für Mütter von heute plus die letzten Tage.

Läuft täglich kurz nach Mitternacht in .github/workflows/spruch.yml (nur Standardbibliothek).
Die Reihenfolge ist fest und gemischt: Jeder der 260 Sätze aus data/saetze.json kommt
einmal dran, bevor sich etwas wiederholt. Gleiches Datum ergibt immer denselben Satz.
"""

from __future__ import annotations

import datetime as dt
import html
import json
import random
import sys
from pathlib import Path
from urllib.parse import quote
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
SAETZE = ROOT / "data" / "saetze.json"
ZIEL = ROOT / "docs" / "spruch-des-tages" / "index.html"
BILDER = ROOT / "docs" / "pins" / "img"
BERLIN = ZoneInfo("Europe/Berlin")
START = dt.date(2026, 10, 8)
URL = "https://mamafunke.de/spruch-des-tages/"

THEMEN = {
    "mentalLoad": "Mental Load", "selbstmitgefuehl": "Selbstmitgefühl",
    "ueberreizungUndRuhe": "Ruhe", "schuldgefuehle": "Schlechtes Gewissen",
    "grenzenUndBeduerfnisse": "Grenzen", "schlafmangelUndErschoepfung": "Müde Tage",
    "babyzeit": "Babyzeit", "kleinkindUndStarkeGefuehle": "Kleinkind",
    "schulkindUndLoslassen": "Loslassen", "partnerschaftUndTeam": "Partnerschaft",
    "alleinerziehend": "Alleinerziehend", "berufUndWiedereinstieg": "Beruf",
    "identitaetUndFreude": "Ich selbst",
}
MONATE = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August",
          "September", "Oktober", "November", "Dezember"]


def reihenfolge(saetze: list[dict]) -> list[dict]:
    liste = sorted(saetze, key=lambda s: s["id"])
    random.Random(20261008).shuffle(liste)
    return liste


def satz_fuer(tag: dt.date, liste: list[dict]) -> dict:
    return liste[(tag - START).days % len(liste)]


def datum_text(tag: dt.date) -> str:
    return f"{tag.day}. {MONATE[tag.month - 1]} {tag.year}"


def seite(heute: dt.date, liste: list[dict]) -> str:
    e = html.escape
    s = satz_fuer(heute, liste)
    thema = THEMEN.get(s["thema"], "")
    bild = f"https://mamafunke.de/pins/img/{s['id']}.jpg" if (BILDER / f"{s['id']}.jpg").exists() else "https://mamafunke.de/icon.png"
    wa = "https://wa.me/?text=" + quote(f"„{s['text']}“ Der Spruch des Tages für Mamas: {URL}")
    frueher = []
    for n in range(1, 8):
        tag = heute - dt.timedelta(days=n)
        if tag < START:
            break
        alt = satz_fuer(tag, liste)
        frueher.append(f'  <li><span class="tag">{e(datum_text(tag))}</span> {e(alt["text"])}</li>\n')
    liste_frueher = "".join(frueher) or "  <li>Ab morgen findest du hier die Sprüche der letzten Tage.</li>\n"
    titel = "Spruch des Tages für Mamas: heute neu"
    desc = f"Der Spruch des Tages für Mütter vom {datum_text(heute)}: „{s['text']}“ Jeden Tag ein neuer, ehrlicher Satz für Mamas."
    if len(desc) > 300:
        desc = desc[:297] + "…"
    ld = {
        "@context": "https://schema.org", "@type": "WebPage", "name": titel, "description": desc,
        "inLanguage": "de-DE", "url": URL, "dateModified": heute.isoformat(),
        "mainEntity": {"@type": "Quotation", "text": s["text"],
                       "creator": {"@type": "Organization", "name": "MamaFunke"}},
    }
    return f"""<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{e(titel)}</title>
<meta name="description" content="{e(desc)}">
<link rel="canonical" href="{URL}">
<link rel="icon" href="/icon.png">
<link rel="stylesheet" href="/ratgeber/ratgeber.css">
<meta property="og:type" content="website">
<meta property="og:locale" content="de_DE">
<meta property="og:site_name" content="MamaFunke">
<meta property="og:title" content="Spruch des Tages für Mamas">
<meta property="og:description" content="{e(s['text'])}">
<meta property="og:url" content="{URL}">
<meta property="og:image" content="{bild}">
<meta name="twitter:card" content="summary_large_image">
<script type="application/ld+json">
{json.dumps(ld, ensure_ascii=False, indent=1)}
</script>
<style>
.heute {{ background: #fff; border-radius: 18px; padding: 28px 22px; margin: 18px 0 22px; box-shadow: 0 6px 24px rgba(41,37,31,.08); text-align: center; }}
.heute .label {{ text-transform: uppercase; letter-spacing: .08em; font-size: .8rem; color: #788b78; margin: 0 0 10px; }}
.heute blockquote {{ font-family: Georgia, "Times New Roman", serif; font-size: 1.6rem; line-height: 1.35; margin: 0 0 12px; }}
.heute .thema {{ color: #788b78; font-size: .9rem; margin: 0 0 18px; }}
.frueher li {{ margin-bottom: 10px; }}
.frueher .tag {{ display: block; font-size: .8rem; color: #788b78; }}
</style>
</head>
<body>
<div class="wrap">
<header class="top">
  <a href="/"><img src="/icon.png" alt="" width="36" height="36"></a>
  <a href="/">MamaFunke</a>
  <nav><a href="/ratgeber/">Ratgeber</a></nav>
</header>

<main>
<h1>Spruch des Tages für Mamas</h1>
<p class="lead">Jeden Tag ein neuer, ehrlicher Satz für Mütter. Ohne Kalenderkitsch, ohne Optimierungsdruck. Für den Moment, in dem du kurz durchatmen willst.</p>

<section class="heute" aria-labelledby="heute-titel">
  <p class="label" id="heute-titel">{e(datum_text(heute))}</p>
  <blockquote>{e(s["text"])}</blockquote>
  <p class="thema">Thema: {e(thema)}</p>
  <p><a class="cta" href="{e(wa)}" target="_blank" rel="noopener">Einer Mama per WhatsApp schicken</a></p>
</section>

<h2>Die Sprüche der letzten Tage</h2>
<ul class="frueher">
{liste_frueher}</ul>

<p>Noch mehr Sätze nach Thema sortiert findest du in der Sammlung <a href="/ratgeber/sprueche-fuer-muetter/">Sprüche für Mütter</a>.</p>

<div class="box">
  <h2>Den Spruch des Tages direkt auf dem Startbildschirm</h2>
  <p>In der App MamaFunke liegt dein Satz als Widget auf dem Startbildschirm, und wenn er heute nicht passt, wischst du einfach weiter: 260 Sätze zu 13 Themen, Favoriten zum Speichern, sanfte Erinnerungen. Kostenlos, ohne Konto und ohne Werbung. Für Android gibt es MamaFunke bei Google Play.</p>
  <p><a class="cta" href="https://mamafunke.de/teilen">MamaFunke kostenlos holen</a></p>
</div>
</main>

<footer>
  <a href="/ratgeber/">Ratgeber</a> · <a href="/">MamaFunke</a>
</footer>
</div>
</body>
</html>
"""


if __name__ == "__main__":
    liste = reihenfolge(json.loads(SAETZE.read_text(encoding="utf-8")))
    heute = dt.date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else dt.datetime.now(BERLIN).date()
    text = seite(heute, liste)
    assert "–" not in text and "—" not in text, "Gedankenstrich"
    ZIEL.parent.mkdir(parents=True, exist_ok=True)
    ZIEL.write_text(text, encoding="utf-8", newline="\n")
    print(heute, satz_fuer(heute, liste)["text"])
