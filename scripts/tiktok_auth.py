"""Einmalig: TikTok-Zugang für den Posting-Automaten holen und als GitHub Secrets hinterlegen.

    python scripts/tiktok_auth.py            Upload-Modus (Entwurf in der TikTok-App)
    python scripts/tiktok_auth.py --direct   zusätzlich Direct Post (video.publish)

Fragt Client Key und Client Secret der TikTok-App ab (Eingabe bleibt unsichtbar),
öffnet den Browser für die Zustimmung mit dem MamaFunke-Konto und setzt danach
TIKTOK_CLIENT_KEY, TIKTOK_CLIENT_SECRET und TIKTOK_REFRESH_TOKEN im Repository.
Jeder Wert geht über eine kurzlebige Datei an `gh secret set NAME < datei`, die
Datei wird sofort gelöscht. Werte werden nie ausgegeben.

Voraussetzung in der TikTok-App: Plattform "Desktop" mit der Redirect URI
http://localhost:3455/callback/ (TikTok verlangt für Desktop PKCE und localhost).
Das Refresh-Token gilt 365 Tage; danach dieses Skript erneut ausführen.
"""

from __future__ import annotations

import getpass
import hashlib
import http.server
import os
import secrets
import subprocess
import sys
import tempfile
import urllib.parse
import webbrowser

import requests

REPO = "amanterbusiness-ai/mamafunke-social"
PORT = 3455
REDIRECT = f"http://localhost:{PORT}/callback/"
AUTH = "https://www.tiktok.com/v2/auth/authorize/"
TOKEN = "https://open.tiktokapis.com/v2/oauth/token/"


def pkce() -> tuple[str, str]:
    """TikTok Desktop: code_challenge ist der Hex-SHA256 des Verifiers."""
    verifier = secrets.token_urlsafe(64)[:96]
    return verifier, hashlib.sha256(verifier.encode()).hexdigest()


def set_secret(name: str, value: str) -> None:
    fd, pfad = tempfile.mkstemp(prefix="tt_")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(value)
        with open(pfad, encoding="utf-8") as f:
            subprocess.run(["gh", "secret", "set", name, "-R", REPO], stdin=f, check=True,
                           stdout=subprocess.DEVNULL)
    finally:
        os.remove(pfad)


def warte_auf_code(state: str) -> str:
    ergebnis: dict[str, str] = {}

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            if q.get("state", [""])[0] == state and "code" in q:
                ergebnis["code"] = q["code"][0]
                antwort = "Fertig. Du kannst dieses Fenster schließen."
            else:
                ergebnis["fehler"] = q.get("error_description", q.get("error", ["unbekannt"]))[0]
                antwort = "Das hat nicht geklappt. Details stehen im Terminal."
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(antwort.encode())

        def log_message(self, *args):
            pass

    with http.server.HTTPServer(("localhost", PORT), Handler) as server:
        while not ergebnis:
            server.handle_request()
    if "code" not in ergebnis:
        raise SystemExit(f"Zustimmung fehlgeschlagen: {ergebnis.get('fehler')}")
    return ergebnis["code"]


def main() -> int:
    scopes = ["user.info.basic", "video.upload"] + (["video.publish"] if "--direct" in sys.argv else [])
    client_key = input("TikTok Client Key: ").strip()
    client_secret = getpass.getpass("TikTok Client Secret (unsichtbar): ").strip()
    verifier, challenge = pkce()
    state = secrets.token_urlsafe(16)
    url = AUTH + "?" + urllib.parse.urlencode({
        "client_key": client_key, "scope": ",".join(scopes), "response_type": "code",
        "redirect_uri": REDIRECT, "state": state,
        "code_challenge": challenge, "code_challenge_method": "S256"})
    print("Browser öffnet sich. Mit dem MamaFunke-TikTok-Konto anmelden und auf Autorisieren tippen.")
    webbrowser.open(url)
    code = warte_auf_code(state)
    r = requests.post(TOKEN, timeout=60, data={
        "client_key": client_key, "client_secret": client_secret, "code": code,
        "grant_type": "authorization_code", "redirect_uri": REDIRECT, "code_verifier": verifier})
    data = r.json()
    if "refresh_token" not in data:
        print(f"Kein Refresh-Token erhalten: {data.get('error_description') or data.get('error')}")
        return 1
    fehlend = set(scopes) - set(data.get("scope", "").split(","))
    if fehlend:
        print(f"Achtung, nicht freigegeben: {', '.join(sorted(fehlend))}")
    set_secret("TIKTOK_CLIENT_KEY", client_key)
    set_secret("TIKTOK_CLIENT_SECRET", client_secret)
    set_secret("TIKTOK_REFRESH_TOKEN", data["refresh_token"])
    print(f"TikTok-Zugang hinterlegt (3 Secrets in {REPO}). Gültig 365 Tage.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
