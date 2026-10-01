"""Einmalig: YouTube-Zugang für den Posting-Automaten holen und als GitHub Secrets hinterlegen.

    python scripts/youtube_auth.py <pfad-zur-client_secret.json>

Öffnet den Browser. Dort mit dem Google-Konto anmelden, dem der YouTube-Kanal
MamaFunke gehört, und den Zugriff erlauben (Hinweis „nicht überprüfte App“:
Erweitert > Weiter zu MamaFunke Social). Danach setzt das Skript
YT_CLIENT_ID, YT_CLIENT_SECRET und YT_REFRESH_TOKEN im Repository und löscht
die heruntergeladene JSON-Datei. Werte werden nie ausgegeben.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow

REPO = "amanterbusiness-ai/mamafunke-social"
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def set_secret(name: str, value: str) -> None:
    subprocess.run(["gh", "secret", "set", name, "-R", REPO], input=value, text=True, check=True,
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
    print("YouTube-Zugang hinterlegt (3 Secrets), JSON-Datei gelöscht.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
