"""Einmalig: YouTube-Zugang für den Posting-Automaten holen und als GitHub Secrets hinterlegen.

    python scripts/youtube_auth.py <pfad-zur-client_secret.json>

Öffnet den Browser. Dort mit dem Google-Konto anmelden, dem der YouTube-Kanal
MamaFunke gehört, und den Zugriff erlauben (Hinweis „nicht überprüfte App“:
Erweitert > Weiter zu MamaFunke Social). Danach setzt das Skript
YT_CLIENT_ID, YT_CLIENT_SECRET und YT_REFRESH_TOKEN in beiden Repositories
(Posten und Kennzahlen) und löscht die heruntergeladene JSON-Datei. Werte werden
nie ausgegeben. Der Zugang darf hochladen, Statistiken lesen und Kommentare beantworten.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow

REPOS = ["amanterbusiness-ai/mamafunke-social", "amanterbusiness-ai/mamafunke-metrics"]
SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
    # Kommentare beantworten (Kommentar-Assistent in mamafunke-metrics)
    "https://www.googleapis.com/auth/youtube.force-ssl",
]


def set_secret(name: str, value: str) -> None:
    for repo in REPOS:
        subprocess.run(["gh", "secret", "set", name, "-R", repo], input=value, text=True, check=True,
                       stdout=subprocess.DEVNULL)


def main() -> int:
    path = Path(sys.argv[1])
    client = json.loads(path.read_text(encoding="utf-8"))["installed"]
    flow = InstalledAppFlow.from_client_secrets_file(str(path), SCOPES)
    creds = flow.run_local_server(port=0, access_type="offline", prompt="consent",
                                  success_message="Fertig. Du kannst dieses Fenster schließen.")
    if not creds.refresh_token:
        print("Kein Refresh-Token erhalten. Bitte erneut ausführen.")
        return 1
    set_secret("YT_CLIENT_ID", client["client_id"])
    set_secret("YT_CLIENT_SECRET", client["client_secret"])
    set_secret("YT_REFRESH_TOKEN", creds.refresh_token)
    path.unlink()
    print(f"YouTube-Zugang hinterlegt (3 Secrets in {len(REPOS)} Repos), JSON-Datei gelöscht.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
