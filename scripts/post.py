"""Veröffentlicht fällige Posts aus plan/posts.json auf Instagram (Feed und Story), Facebook, YouTube
und (sobald eingerichtet) TikTok.

Läuft in GitHub Actions alle 30 Minuten. Ein Post ist fällig, sobald seine
Uhrzeit (deutsche Zeit) erreicht ist. Erledigtes steht in state/posted.json,
damit nichts doppelt erscheint; der Workflow committet die Datei zurück.

TikTok: Slideshows plant weiterhin die Browser-Aufgabe (TIKTOK.md). Reels gehen über die
Content Posting API (Kanal "tiktok_api", siehe TIKTOK_API.md), aber erst, wenn die
TIKTOK_*-Secrets gesetzt sind. Bis dahin bleibt alles beim Browser.

Kanäle ohne Zugangsdaten werden übersprungen, nicht als Fehler gewertet.
Umgebungsvariablen (GitHub Secrets):
    META_PAGE_TOKEN, FB_PAGE_ID, IG_USER_ID (optional)
    YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN
    TIKTOK_CLIENT_KEY, TIKTOK_CLIENT_SECRET, TIKTOK_REFRESH_TOKEN
    TIKTOK_MODUS  "upload" (Standard, Entwurf in der TikTok-App) oder "direct"
    MEDIA_BASE_URL  öffentlicher Pfad zum Repository-Inhalt (raw.githubusercontent.com/...)
Aufruf lokal zum Testen: python scripts/post.py --dry-run
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "plan" / "posts.json"
STATE = ROOT / "state" / "posted.json"
APPLE = ROOT / "state" / "apple_live.json"
BERLIN = ZoneInfo("Europe/Berlin")
GRAPH = f"https://graph.facebook.com/{os.environ.get('GRAPH_VERSION', 'v25.0')}"
# Verspätete Posts (z. B. nach einem Ausfall) nur bis zu diesem Abstand nachholen,
# damit nicht Tage später ein Schwall alter Posts erscheint.
MAX_DELAY = timedelta(hours=10)
CHANNELS = ("instagram", "facebook", "youtube", "story", "tiktok_api")
TIKTOK = "https://open.tiktokapis.com/v2"
MB = 1024 * 1024


def env(name: str) -> str:
    return os.environ.get(name, "").strip()


def apple_datum() -> str | None:
    """Tag der App-Store-Freigabe, geschrieben von scripts/apple_live.py."""
    if not APPLE.exists():
        return None
    return json.loads(APPLE.read_text(encoding="utf-8")).get("datum")


def faellig(post: dict, apple: str | None) -> datetime | None:
    """Zeitpunkt eines Posts. Posts mit "nach_apple" warten auf die App-Store-Freigabe
    und erscheinen so viele Tage danach; vorher sind sie nicht fällig (None)."""
    if "nach_apple" in post:
        if not apple:
            return None
        tag = datetime.fromisoformat(apple).date() + timedelta(days=int(post["nach_apple"]))
        return datetime.fromisoformat(f"{tag.isoformat()}T{post['time']}").replace(tzinfo=BERLIN)
    return datetime.fromisoformat(f"{post['date']}T{post['time']}").replace(tzinfo=BERLIN)


def text(post: dict, kanal: str) -> str:
    """Eigener Text je Kanal, sonst die gemeinsame Caption."""
    return post.get("captions", {}).get(kanal) or post["caption"]


def media_url(path: str) -> str:
    return env("MEDIA_BASE_URL").rstrip("/") + "/" + path


_page_token: str | None = None


def page_token() -> str:
    """Seiten-Token aus dem Systemnutzer-Token. Facebook verlangt, dass Seitenbeiträge
    als die Seite selbst entstehen; der Systemnutzer-Token allein reicht dafür nicht."""
    global _page_token
    if _page_token is None:
        data = graph("GET", env("FB_PAGE_ID"), fields="access_token")
        _page_token = data.get("access_token") or env("META_PAGE_TOKEN")
    return _page_token


def graph(method: str, path: str, token: str | None = None, **params) -> dict:
    params["access_token"] = token or env("META_PAGE_TOKEN")
    r = requests.request(method, f"{GRAPH}/{path}", data=params if method == "POST" else None,
                         params=None if method == "POST" else params, timeout=120)
    body = r.json()
    if r.status_code >= 400 or "error" in body:
        raise RuntimeError(f"Graph {path}: {body.get('error', body)}")
    return body


def wait_ready(container: str) -> None:
    """Instagram verarbeitet Videos asynchron; erst bei FINISHED veröffentlichen."""
    for _ in range(60):
        status = graph("GET", container, fields="status_code").get("status_code")
        if status == "FINISHED":
            return
        if status in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"Instagram-Verarbeitung: {status}")
        time.sleep(10)
    raise RuntimeError("Instagram-Verarbeitung dauert zu lange")


def instagram_id() -> str:
    """IG_USER_ID ist optional: ohne ihn wird das mit der Seite verknüpfte Konto genommen."""
    if env("IG_USER_ID"):
        return env("IG_USER_ID")
    linked = graph("GET", env("FB_PAGE_ID"), fields="instagram_business_account").get("instagram_business_account")
    if not linked:
        raise RuntimeError("Kein Instagram-Konto mit der Facebook-Seite verknüpft")
    os.environ["IG_USER_ID"] = linked["id"]
    return linked["id"]


def post_instagram(post: dict) -> str:
    ig = instagram_id()
    if post["kind"] == "reel":
        c = graph("POST", f"{ig}/media", media_type="REELS", video_url=media_url(post["media"]["video"]),
                  caption=text(post, "instagram"), share_to_feed="true")["id"]
    else:
        children = []
        for path in post["media"]["instagram"]:
            children.append(graph("POST", f"{ig}/media", image_url=media_url(path), is_carousel_item="true")["id"])
        for child in children:
            wait_ready(child)
        c = graph("POST", f"{ig}/media", media_type="CAROUSEL", children=",".join(children),
                  caption=post["caption"])["id"]
    wait_ready(c)
    return graph("POST", f"{ig}/media_publish", creation_id=c)["id"]


def kanaele(post: dict) -> list[str]:
    """Kanäle eines Posts. Jeder Instagram-Post erscheint zusätzlich als Story,
    außer er hat "keine_story": true. TikTok-Reels laufen zusätzlich über die API
    (greift nur, wenn deren Secrets gesetzt sind, sonst bleibt der Kanal offen)."""
    liste = list(post["channels"])
    if "instagram" in liste and not post.get("keine_story"):
        liste.append("story")
    if "tiktok" in liste and post.get("kind") == "reel":
        liste.append("tiktok_api")
    return liste


def story_medium(post: dict) -> tuple[str, str]:
    """Video-Story für Reels, sonst das erste Hochformatbild (1080x1920)."""
    if post["kind"] == "reel":
        return "video_url", post["media"]["video"]
    return "image_url", post["media"]["tiktok"][0]


def post_story(post: dict) -> str:
    ig = instagram_id()
    feld, pfad = story_medium(post)
    c = graph("POST", f"{ig}/media", media_type="STORIES", **{feld: media_url(pfad)})["id"]
    wait_ready(c)
    return graph("POST", f"{ig}/media_publish", creation_id=c)["id"]


def post_facebook(post: dict) -> str:
    page = env("FB_PAGE_ID")
    token = page_token()
    if post["kind"] == "reel":
        return graph("POST", f"{page}/videos", token, file_url=media_url(post["media"]["video"]),
                     description=text(post, "facebook"))["id"]
    ids = [graph("POST", f"{page}/photos", token, url=media_url(p), published="false")["id"]
           for p in post["media"]["instagram"]]
    params = {f"attached_media[{i}]": json.dumps({"media_fbid": x}) for i, x in enumerate(ids)}
    return graph("POST", f"{page}/feed", token, message=post["caption"], **params)["id"]


def post_youtube(post: dict) -> str:
    if post["kind"] != "reel":
        return "nicht zutreffend"
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload

    creds = Credentials(None, refresh_token=env("YT_REFRESH_TOKEN"), client_id=env("YT_CLIENT_ID"),
                        client_secret=env("YT_CLIENT_SECRET"), token_uri="https://oauth2.googleapis.com/token")
    yt = build("youtube", "v3", credentials=creds, cache_discovery=False)
    body = {
        "snippet": {"title": (post.get("yt_titel") or f"{post['hook']} #shorts")[:100],
                    "description": text(post, "youtube"),
                    "categoryId": "22", "defaultLanguage": "de"},
        "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False,
                   # KI-Kennzeichnung ("Veränderte oder synthetische Inhalte")
                   "containsSyntheticMedia": bool(post.get("ki"))},
    }
    req = yt.videos().insert(part="snippet,status", body=body,
                             media_body=MediaFileUpload(str(ROOT / post["media"]["video"]), resumable=True))
    resp = None
    while resp is None:
        _, resp = req.next_chunk()
    return resp["id"]


def tiktok_modus() -> str:
    return "direct" if env("TIKTOK_MODUS").lower() == "direct" else "upload"


def tiktok_teile(groesse: int) -> list[tuple[int, int]]:
    """Byte-Bereiche für den Upload. TikTok nimmt bis 64 MB in einem Stück, sonst
    Stücke von 5 bis 64 MB; das letzte Stück nimmt den Rest auf (bis 128 MB)."""
    if groesse <= 64 * MB:
        return [(0, groesse - 1)]
    stueck = 10 * MB
    anzahl = groesse // stueck
    teile = [(i * stueck, (i + 1) * stueck - 1) for i in range(anzahl - 1)]
    return teile + [((anzahl - 1) * stueck, groesse - 1)]


def tiktok_post_info(post: dict, privacy_optionen: list[str]) -> dict:
    """Angaben für Direct Post. Öffentlich, sobald TikTok es erlaubt (nach App-Prüfung),
    sonst nur privat. Eigene App = Werbung für die eigene Marke."""
    return {
        "title": text(post, "tiktok"),
        "privacy_level": "PUBLIC_TO_EVERYONE" if "PUBLIC_TO_EVERYONE" in privacy_optionen else "SELF_ONLY",
        "disable_duet": False,
        "disable_stitch": False,
        "disable_comment": False,
        "brand_organic_toggle": True,
        "brand_content_toggle": False,
        "is_aigc": bool(post.get("ki")),
    }


def tiktok(path: str, token: str, **body) -> dict:
    r = requests.post(f"{TIKTOK}/{path}", json=body, timeout=120,
                      headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=UTF-8"})
    data = r.json()
    if r.status_code >= 400 or data.get("error", {}).get("code", "ok") != "ok":
        raise RuntimeError(f"TikTok {path}: {data.get('error', data)}")
    return data.get("data", {})


def tiktok_token() -> str:
    """Access-Token (24 h gültig) aus dem Refresh-Token (365 Tage gültig)."""
    r = requests.post(f"{TIKTOK}/oauth/token/", timeout=60, data={
        "client_key": env("TIKTOK_CLIENT_KEY"), "client_secret": env("TIKTOK_CLIENT_SECRET"),
        "grant_type": "refresh_token", "refresh_token": env("TIKTOK_REFRESH_TOKEN")})
    data = r.json()
    if "access_token" not in data:
        raise RuntimeError(f"TikTok-Token: {data.get('error_description') or data.get('error') or r.status_code}")
    if data.get("refresh_token") and data["refresh_token"] != env("TIKTOK_REFRESH_TOKEN"):
        print("HINWEIS TikTok hat ein neues Refresh-Token ausgegeben: scripts/tiktok_auth.py erneut ausführen",
              file=sys.stderr)
    return data["access_token"]


def post_tiktok(post: dict) -> str:
    """Reel per Content Posting API. Upload-Modus: Entwurf landet im TikTok-Postfach,
    Caption, KI-Kennzeichnung und Werbehinweis setzt die Gründerin dort. Direct Post:
    erscheint sofort mit allen Angaben."""
    if post["kind"] != "reel":
        return "nicht zutreffend"
    token = tiktok_token()
    datei = ROOT / post["media"]["video"]
    groesse = datei.stat().st_size
    teile = tiktok_teile(groesse)
    quelle = {"source": "FILE_UPLOAD", "video_size": groesse,
              "chunk_size": teile[0][1] + 1, "total_chunk_count": len(teile)}
    if tiktok_modus() == "direct":
        optionen = tiktok("post/publish/creator_info/query/", token).get("privacy_level_options", [])
        init = tiktok("post/publish/video/init/", token, post_info=tiktok_post_info(post, optionen),
                      source_info=quelle)
    else:
        init = tiktok("post/publish/inbox/video/init/", token, source_info=quelle)
    with datei.open("rb") as f:
        for anfang, ende in teile:
            f.seek(anfang)
            r = requests.put(init["upload_url"], data=f.read(ende - anfang + 1), timeout=600, headers={
                "Content-Type": "video/mp4", "Content-Range": f"bytes {anfang}-{ende}/{groesse}"})
            if r.status_code >= 400:
                raise RuntimeError(f"TikTok-Upload {anfang}-{ende}: {r.status_code} {r.text[:200]}")
    for _ in range(60):
        status = tiktok("post/publish/status/fetch/", token, publish_id=init["publish_id"])
        if status.get("status") in ("SEND_TO_USER_INBOX", "PUBLISH_COMPLETE"):
            return init["publish_id"]
        if status.get("status") == "FAILED":
            raise RuntimeError(f"TikTok-Verarbeitung: {status.get('fail_reason')}")
        time.sleep(10)
    raise RuntimeError("TikTok-Verarbeitung dauert zu lange")


READY = {
    "instagram": lambda: env("META_PAGE_TOKEN") and (env("IG_USER_ID") or env("FB_PAGE_ID")),
    "facebook": lambda: env("META_PAGE_TOKEN") and env("FB_PAGE_ID"),
    "youtube": lambda: env("YT_REFRESH_TOKEN") and env("YT_CLIENT_ID") and env("YT_CLIENT_SECRET"),
    "tiktok_api": lambda: env("TIKTOK_CLIENT_KEY") and env("TIKTOK_CLIENT_SECRET") and env("TIKTOK_REFRESH_TOKEN"),
}
READY["story"] = READY["instagram"]
POSTERS = {"instagram": post_instagram, "facebook": post_facebook, "youtube": post_youtube, "story": post_story,
           "tiktok_api": post_tiktok}


def check() -> int:
    """Liest nur: Seite, verknüpftes Instagram-Konto, Rechte des Tokens."""
    ok = True
    if READY["facebook"]():
        page = graph("GET", env("FB_PAGE_ID"), fields="name,instagram_business_account{username}")
        print(f"Facebook-Seite: {page.get('name')}")
        ig = page.get("instagram_business_account")
        print(f"Instagram: {ig.get('username') if ig else 'NICHT verknüpft'}")
        ok = ok and bool(ig)
        perms = graph("GET", "debug_token", input_token=env("META_PAGE_TOKEN")).get("data", {})
        print(f"Token gültig: {perms.get('is_valid')}, läuft ab: {perms.get('expires_at') or 'nie'}")
        print(f"Rechte: {', '.join(sorted(perms.get('scopes', [])))}")
        ok = ok and bool(perms.get("is_valid"))
    else:
        # Nur Längen, nie Werte ausgeben.
        print(f"Meta: Zugangsdaten fehlen (Token {len(env('META_PAGE_TOKEN'))} Zeichen, Seiten-ID {len(env('FB_PAGE_ID'))} Zeichen)")
        ok = False
    if READY["youtube"]():
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials

        creds = Credentials(None, refresh_token=env("YT_REFRESH_TOKEN"), client_id=env("YT_CLIENT_ID"),
                            client_secret=env("YT_CLIENT_SECRET"), token_uri="https://oauth2.googleapis.com/token")
        creds.refresh(Request())  # wirft, wenn der Zugang nicht gilt
        print("YouTube: Zugang gültig")
    else:
        print("YouTube: noch nicht eingerichtet")
    if READY["tiktok_api"]():
        tiktok_token()  # wirft, wenn der Zugang nicht gilt
        print(f"TikTok: Zugang gültig (Modus {tiktok_modus()})")
    else:
        print("TikTok-API: noch nicht eingerichtet (Reels weiter über den Browser)")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--now", help="Testzeit, z. B. 2026-10-01T12:31")
    ap.add_argument("--check", action="store_true", help="nur Zugänge prüfen, nichts posten")
    args = ap.parse_args()

    if args.check:
        return check()

    now = datetime.fromisoformat(args.now).replace(tzinfo=BERLIN) if args.now else datetime.now(BERLIN)
    posts = json.loads(PLAN.read_text(encoding="utf-8"))
    state = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {}
    failures = 0

    apple = apple_datum()
    for post in posts:
        due = faellig(post, apple)
        if due is None or due > now:
            continue
        for channel in CHANNELS:
            if channel not in kanaele(post) or f"{post['id']}:{channel}" in state:
                continue
            key = f"{post['id']}:{channel}"
            if now - due > MAX_DELAY:
                state[key] = {"status": "verpasst", "at": now.isoformat()}
                print(f"verpasst  {key}")
                continue
            if not READY[channel]():
                continue  # Kanal noch nicht eingerichtet; bleibt offen
            if args.dry_run:
                print(f"würde posten  {key}")
                continue
            try:
                result = POSTERS[channel](post)
                state[key] = {"status": "ok", "id": result, "at": now.isoformat()}
                print(f"gepostet  {key}  {result}")
            except Exception as error:  # ein Kanal darf die anderen nicht blockieren
                failures += 1
                print(f"FEHLER    {key}: {error}", file=sys.stderr)

    if not args.dry_run:
        STATE.parent.mkdir(exist_ok=True)
        STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
