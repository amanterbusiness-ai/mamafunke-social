"""Schaltet iPhone-Links ein, sobald MamaFunke im App Store ist.

Läuft täglich im Workflow apple-live.yml. Ist die App öffentlich (iTunes-Lookup liefert
ein Ergebnis), wird in docs/weiter.html APPLE_LIVE auf true gesetzt, die Kurzlinks
werden neu erzeugt und auf der Startseite docs/index.html wird der Knopf
"Bald im App Store" zum echten Link. Der Tag der Freigabe landet in
state/apple_live.json; danach erscheinen die Posts mit "nach_apple" in plan/posts.json.
Sonst passiert nichts.
"""

import json
import re
import subprocess
import sys
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
SEITE = ROOT / "docs" / "weiter.html"
START = ROOT / "docs" / "index.html"
STAND = ROOT / "state" / "apple_live.json"
LOOKUP = "https://itunes.apple.com/lookup?id=6817131358&country=de"
APPLE_LINK = "https://apps.apple.com/de/app/id6817131358"


def startseite_umschalten(text: str) -> str:
    """Macht aus jedem "Bald im App Store"-Schild einen echten Link."""
    text = re.sub(
        r'<span class="store-badge soon">(.*?)<span><small>Bald im</small>App Store</span>\s*</span>',
        lambda m: f'<a class="store-badge" href="{APPLE_LINK}" rel="noopener">{m.group(1)}'
        '<span><small>Jetzt im</small>App Store</span>\n      </a>',
        text,
        flags=re.S,
    )
    text = text.replace(
        "Für Android jetzt kostenlos bei Google Play. Für iPhone erscheint MamaFunke in Kürze.",
        "Jetzt kostenlos bei Google Play und im App Store.",
    )
    text = text.replace(
        "Für Android ist MamaFunke bei Google Play verfügbar. Die iPhone-Version ist bei Apple in Prüfung und erscheint in Kürze.",
        "Ja. MamaFunke gibt es für iPhone im App Store und für Android bei Google Play.",
    )
    return text.replace('"operatingSystem": "ANDROID"', '"operatingSystem": "ANDROID, IOS"')


if __name__ == "__main__":
    text = SEITE.read_text(encoding="utf-8")
    if "var APPLE_LIVE = true;" in text:
        print("Schon eingeschaltet")
        sys.exit(0)
    with urllib.request.urlopen(LOOKUP, timeout=30) as antwort:
        treffer = json.load(antwort).get("resultCount", 0)
    if not treffer:
        print("Noch nicht im App Store")
        sys.exit(0)
    SEITE.write_text(
        text.replace("var APPLE_LIVE = false;", "var APPLE_LIVE = true;"), encoding="utf-8", newline="\n"
    )
    START.write_text(startseite_umschalten(START.read_text(encoding="utf-8")), encoding="utf-8", newline="\n")
    subprocess.run([sys.executable, str(ROOT / "scripts" / "kurzlinks.py")], check=True)
    if not STAND.exists():
        heute = datetime.now(ZoneInfo("Europe/Berlin")).date().isoformat()
        STAND.write_text(json.dumps({"datum": heute}) + "\n", encoding="utf-8")
    print("App ist im App Store, iPhone-Links eingeschaltet")
