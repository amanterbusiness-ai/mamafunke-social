"""Baut Pinterest-Pins (1000 x 1500) aus den freigegebenen MamaFunke-Sprüchen.

Lokal ausführen (braucht Pillow und das App-Repo):
    python scripts/pins_bauen.py
Erzeugt docs/pins/img/<id>.jpg und state/pins.json (Warteschlange, 2 Pins pro Tag).
Den Feed baut danach täglich scripts/pins_feed.py (GitHub Action), damit Pinterest
nicht alles auf einmal veröffentlicht.
"""

from __future__ import annotations

import datetime as dt
import json
import random
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
APP = Path(r"C:\dev\mama-app\app")
FONTS = APP / "assets" / "google_fonts"
IMPULSE = APP / "assets" / "content" / "mamafunke_impulses.json"
BILDER = ROOT / "docs" / "pins" / "img"
QUEUE = ROOT / "state" / "pins.json"
START = dt.date(2026, 10, 8)
UHRZEITEN = ("09:00", "20:00")
W, H = 1000, 1500

# Suchbegriffe laut Keyword-Analyse 07.10.2026 (Google DACH): sprüche für mütter 11.260,
# mama sprüche 4.290, mental load 11.780, spruch des tages 44.700.
THEMA = {
    "mental-load": ("Mental Load Sprüche für Mütter", "Mental Load"),
    "selbstmitgefuehl": ("Sprüche für Mütter, die sich selbst zu streng sind", "Selbstmitgefühl"),
    "ueberreizung": ("Mama Sprüche für Tage, an denen alles zu laut ist", "Überreizung"),
    "schuldgefuehle": ("Sprüche gegen das schlechte Gewissen als Mama", "Schlechtes Gewissen"),
    "grenzen": ("Sprüche für Mütter über Grenzen und Bedürfnisse", "Grenzen"),
    "erschoepfung": ("Sprüche für müde Mamas", "Müde Mama"),
    "babyzeit": ("Mama Sprüche für die Babyzeit", "Babyzeit"),
    "kleinkind": ("Mama Sprüche für die Kleinkindzeit", "Kleinkind"),
    "schulkind": ("Sprüche für Mütter von Schulkindern", "Schulkind"),
    "partnerschaft": ("Sprüche für Mütter über Partnerschaft und Elternsein", "Partnerschaft"),
    "alleinerziehend": ("Sprüche für alleinerziehende Mütter", "Alleinerziehend"),
    "beruf": ("Sprüche für berufstätige Mütter", "Job und Familie"),
    "identitaet": ("Sprüche für Mütter, die sich selbst wiederfinden wollen", "Wieder ich"),
}

CREME, TINTE, GOLD, GRAU = (251, 246, 238), (36, 31, 28), (180, 125, 34), (110, 103, 96)


def font(name: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONTS / name), size)


def umbrechen(d: ImageDraw.ImageDraw, text: str, f: ImageFont.FreeTypeFont, breite: int) -> list[str]:
    zeilen, aktuell = [], ""
    for wort in text.split():
        probe = f"{aktuell} {wort}".strip()
        if d.textlength(probe, font=f) <= breite:
            aktuell = probe
        else:
            zeilen.append(aktuell)
            aktuell = wort
    zeilen.append(aktuell)
    return zeilen


def hintergrund() -> Image.Image:
    im = Image.new("RGB", (W, H), CREME)
    glanz = Image.new("L", (W, H), 0)
    ImageDraw.Draw(glanz).ellipse((-200, -300, W + 200, 700), fill=90)
    glanz = glanz.filter(ImageFilter.GaussianBlur(160))
    im.paste(Image.new("RGB", (W, H), (255, 236, 205)), (0, 0), glanz)
    return im


def pin_bild(text: str, etikett: str, ziel: Path) -> None:
    im = hintergrund()
    d = ImageDraw.Draw(im)
    cx = W // 2
    d.text((cx, 150), "SPRÜCHE FÜR MÜTTER", font=font("NunitoSans-Bold.ttf", 34), fill=GOLD, anchor="mm")
    d.text((cx, 205), etikett, font=font("NunitoSans-Bold.ttf", 30), fill=GRAU, anchor="mm")
    groesse = 70
    while True:
        f = font("Fraunces-SemiBold.ttf", groesse)
        zeilen = umbrechen(d, text, f, 800)
        hoehe = len(zeilen) * round(groesse * 1.28)
        if hoehe <= 760 or groesse <= 46:
            break
        groesse -= 4
    zh = round(groesse * 1.28)
    y = 760 - hoehe // 2 + zh // 2
    for i, z in enumerate(zeilen):
        d.text((cx, y + i * zh), z, font=f, fill=TINTE, anchor="mm")
    d.rounded_rectangle((cx - 30, 1240, cx + 30, 1246), 3, fill=GOLD)
    d.text((cx, 1310), "MamaFunke", font=font("Fraunces-SemiBold.ttf", 46), fill=TINTE, anchor="mm")
    d.text((cx, 1370), "Mehr Sprüche für Mütter in der App · mamafunke.de", font=font("NunitoSans-Bold.ttf", 28),
           fill=GRAU, anchor="mm")
    ziel.parent.mkdir(parents=True, exist_ok=True)
    im.save(ziel, "JPEG", quality=88, optimize=True)


def titel(t: str) -> str:
    """Pinterest erlaubt 100 Zeichen; nie mitten im Wort abschneiden."""
    if len(t) <= 100:
        return t
    return t[:98].rsplit(" ", 1)[0] + " …"


def main() -> None:
    impulse = [x for x in json.loads(IMPULSE.read_text(encoding="utf-8"))
               if x.get("status") == "approved" and not x.get("authorName")]
    random.Random(7).shuffle(impulse)
    # Themen abwechseln, damit nicht zwei gleiche Pins hintereinander kommen
    nach_thema: dict[str, list[dict]] = {}
    for x in impulse:
        nach_thema.setdefault(re.sub(r"^mf-|-\d+$", "", x["id"]), []).append(x)
    reihe = []
    while any(nach_thema.values()):
        for t in list(nach_thema):
            if nach_thema[t]:
                reihe.append((t, nach_thema[t].pop()))
    queue = []
    for n, (thema, x) in enumerate(reihe[:120]):
        titel_basis, etikett = THEMA[thema]
        tag = START + dt.timedelta(days=n // 2)
        bild = BILDER / f"{x['id']}.jpg"
        pin_bild(x["textDe"], etikett, bild)
        kurz = x["textDe"] if len(x["textDe"]) <= 70 else x["textDe"][:67].rsplit(" ", 1)[0] + " …"
        queue.append({
            "id": x["id"],
            "datum": tag.isoformat(),
            "uhr": UHRZEITEN[n % 2],
            "titel": titel(f"{titel_basis}: {kurz}"),
            "beschreibung": (
                f"„{x['textDe']}“ Ehrliche Sprüche für Mütter, ohne Kitsch und ohne Leistungsdruck. "
                f"Thema: {etikett}. "
                "Mehr Mama Sprüche in der kostenlosen App MamaFunke, mit Spruch des Tages als Widget. "
                "#sprüchefürmütter #mamasprüche #mentalload #mamaalltag #mamaleben"
            )[:500],
            "bild": f"https://mamafunke.de/pins/img/{x['id']}.jpg",
            "link": "https://mamafunke.de/pin",
        })
    QUEUE.parent.mkdir(exist_ok=True)
    QUEUE.write_text(json.dumps(queue, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(queue)} Pins, {queue[0]['datum']} bis {queue[-1]['datum']}")


if __name__ == "__main__":
    main()
