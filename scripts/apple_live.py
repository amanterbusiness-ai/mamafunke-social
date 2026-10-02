"""Schaltet die iPhone-Weiterleitung der Link-Seite ein, sobald MamaFunke im App Store ist.

Läuft täglich im Workflow apple-live.yml. Ist die App öffentlich (iTunes-Lookup liefert
ein Ergebnis), wird in docs/index.html APPLE_LIVE auf true gesetzt und die Kurzlinks
werden neu erzeugt. Der Tag der Freigabe landet in state/apple_live.json; danach
erscheinen die Posts mit "nach_apple" in plan/posts.json. Sonst passiert nichts.
"""

import json
import subprocess
import sys
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
SEITE = ROOT / "docs" / "index.html"
STAND = ROOT / "state" / "apple_live.json"
LOOKUP = "https://itunes.apple.com/lookup?id=6817131358&country=de"

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
    SEITE.write_text(text.replace("var APPLE_LIVE = false;", "var APPLE_LIVE = true;"), encoding="utf-8")
    subprocess.run([sys.executable, str(ROOT / "scripts" / "kurzlinks.py")], check=True)
    if not STAND.exists():
        heute = datetime.now(ZoneInfo("Europe/Berlin")).date().isoformat()
        STAND.write_text(json.dumps({"datum": heute}) + "
", encoding="utf-8")
    print("App ist im App Store, iPhone-Weiterleitung eingeschaltet")
