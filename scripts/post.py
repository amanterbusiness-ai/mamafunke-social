"""Veröffentlicht fällige Posts aus plan/posts.json auf Instagram, Facebook und YouTube.

Läuft in GitHub Actions alle 30 Minuten. Ein Post ist fällig, sobald seine
Uhrzeit (deutsche Zeit) erreicht ist. Erledigtes steht in state/posted.json,
damit nichts doppelt erscheint; der Workflow committet die Datei zurück.

TikTok wird hier nicht gepostet (siehe TIKTOK.md).

Kanäle ohne Zugangsdaten werden übersprungen, nicht als Fehler gewertet.
Umgebungsvariablen (GitHub Secrets):
    META_PAGE_TOKEN, FB_PAGE_ID, IG_USER_ID (optional)
    YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN
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
BERLIN = ZoneInfo("Europe/Berlin")
GRAPH = f"https://graph.facebook.com/{os.environ.get('GRAPH_VERSION', 'v25.0')}"
# Verspätete Posts (z. B. nach einem Ausfall) nur bis zu diesem Abstand nachholen,
# damit nicht Tage später ein Schwall alter Posts erscheint.
MAX_DELAY = timedelta(hours=10)
CHANNELS = ("instagram", "facebook", "youtube")


def env(name: str) -> str:
    return os.environ.get(name, "").strip()


def media_url(path: str) -> str:
    return env("MEDIA_BASE_URL").rstrip("/") + "/" + path


def graph(method: str, path: str, **params) -> dict:
    params["access_token"] = env("META_PAGE_TOKEN")
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
                  caption=post["caption"], share_to_feed="true")["id"]
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


def post_facebook(post: dict) -> str:
    page = env("FB_PAGE_ID")
    if post["kind"] == "reel":
        return graph("POST", f"{page}/videos", file_url=media_url(post["media"]["video"]),
                     description=post["caption"])["id"]
    ids = [graph("POST", f"{page}/photos", url=media_url(p), published="false")["id"]
           for p in post["media"]["instagram"]]
    params = {f"attached_media[{i}]": json.dumps({"media_fbid": x}) for i, x in enumerate(ids)}
    return graph("POST", f"{page}/feed", message=post["caption"], **params)["id"]


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
        "snippet": {"title": f"{post['hook']} #shorts"[:100], "description": post["caption"],
                    "categoryId": "22", "defaultLanguage": "de"},
        "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False},
    }
    req = yt.videos().insert(part="snippet,status", body=body,
                             media_body=MediaFileUpload(str(ROOT / post["media"]["video"]), resumable=True))
    resp = None
    while resp is None:
        _, resp = req.next_chunk()
    return resp["id"]


READY = {
    "instagram": lambda: env("META_PAGE_TOKEN") and (env("IG_USER_ID") or env("FB_PAGE_ID")),
    "facebook": lambda: env("META_PAGE_TOKEN") and env("FB_PAGE_ID"),
    "youtube": lambda: env("YT_REFRESH_TOKEN") and env("YT_CLIENT_ID") and env("YT_CLIENT_SECRET"),
}
POSTERS = {"instagram": post_instagram, "facebook": post_facebook, "youtube": post_youtube}


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
    print(f"YouTube: {'eingerichtet' if READY['youtube']() else 'noch nicht eingerichtet'}")
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

    for post in posts:
        due = datetime.fromisoformat(f"{post['date']}T{post['time']}").replace(tzinfo=BERLIN)
        if due > now:
            continue
        for channel in CHANNELS:
            if channel not in post["channels"] or f"{post['id']}:{channel}" in state:
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
