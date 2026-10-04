# TikTok über die API (ohne Browser)

Ziel: Reels gehen wie Instagram, Facebook und YouTube automatisch aus
GitHub Actions raus (`scripts/post.py`, Kanal `tiktok_api`, alle 30 Minuten).
Slideshows plant weiter die Browser-Aufgabe (TIKTOK.md), denn die API kann
Fotobeiträge nur als Entwurf ohne Planung.

Solange die drei Secrets fehlen, passiert nichts Neues: der Kanal bleibt aus,
alles läuft wie bisher über den Browser.

## Was TikTok anbietet (Stand 04.10.2026, developers.tiktok.com)

| | Upload-Modus (Standard) | Direct Post |
|---|---|---|
| Scope | `video.upload` | `video.publish` |
| Ergebnis | Entwurf im TikTok-Postfach, Gründerin tippt auf Posten | sofort veröffentlicht |
| Caption, KI-Hinweis, Werbehinweis | **nicht** per API, in der App setzen | per API (`title`, `is_aigc`, `brand_organic_toggle`) |
| App-Prüfung durch TikTok | nicht nötig im Sandbox-Modus | nötig, vorher nur privat (`SELF_ONLY`), Konto muss privat sein |
| Grenzen | 5 offene Entwürfe je 24 h, 6 Anfragen je Minute | rund 15 Posts je Tag, 6 Anfragen je Minute |

Weitere Fakten:
- Login: Access-Token gilt 24 Stunden, Refresh-Token **365 Tage**. Danach einmal
  `scripts/tiktok_auth.py` neu ausführen. Meldet der Automat "neues
  Refresh-Token", ebenfalls neu ausführen.
- Wir laden per `FILE_UPLOAD` direkt aus dem Repository hoch. `PULL_FROM_URL`
  bräuchte eine DNS-Verifizierung der Domain, und unsere Videos liegen auf
  raw.githubusercontent.com, nicht auf mamafunke.de. **Keine Domain-Verifizierung nötig.**
- Videos bis 64 MB gehen in einem Stück, größere in 10-MB-Stücken.
- Direct Post verlangt laut TikTok-Richtlinien eine Oberfläche, in der die
  Nutzerin Sichtbarkeit und Werbehinweis selbst wählt. Für die Prüfung muss das
  ein Formular sein; deshalb startet MamaFunke im Upload-Modus.

### Was im Upload-Modus noch per Hand in der App bleibt

Für jedes Reel kommt eine Benachrichtigung im TikTok-Postfach. Antippen, dann:
1. Beschreibung einfügen (steht in `plan/PLAN.md`, Feld `caption`).
2. Mehr Optionen: **KI-generierter Inhalt** an (bei Reels mit `"ki": true`).
3. **Beitragsinhalt offenlegen** an, **Deine Marke** anhaken.
4. Posten.

## Einmalig: was die Gründerin tut

Nie Passwörter oder Tokens in den Chat schreiben.

1. **Anmelden.** In Chrome (Profil Mamafunke) https://developers.tiktok.com
   öffnen, oben rechts **Log in**, mit dem MamaFunke-TikTok-Konto anmelden.
   Beim ersten Mal fragt TikTok nach einer Entwickler-Organisation:
   "Individual" wählen und die Nutzungsbedingungen selbst bestätigen.
2. **App anlegen** (das kann Claude übernehmen, sobald du eingeloggt bist):
   oben rechts Profilbild, **Manage apps**, **Connect an app**.
   - App name: MamaFunke, Category: Lifestyle
   - Description: "MamaFunke veröffentlicht die eigenen Kurzvideos der App
     MamaFunke (Affirmationen für Mütter) aus dem Redaktionsplan auf dem
     eigenen TikTok-Konto."
   - Privacy Policy URL: https://mamafunke.deejay-geerax.chatgpt.site/datenschutz
   - Terms of Service URL: https://www.apple.com/legal/internet-services/itunes/dev/stdeula/
   - Platforms: **Desktop**
   - **Add products**: Login Kit und Content Posting API
   - Login Kit, Redirect URI (Desktop): `http://localhost:3455/callback/`
   - Content Posting API: "Direct Post" vorerst **aus** lassen
3. **Sandbox statt Prüfung.** Oben im App-Bereich auf **Sandbox** umschalten,
   **Create Sandbox**, unter **Target Users** das MamaFunke-Konto hinzufügen.
   Im Sandbox-Modus funktioniert der Upload ohne App-Prüfung.
   Client Key und Client Secret stehen unter **Credentials** (Sandbox).
4. **Zustimmung klicken.** Am PC in `C:\dev\mama-social`:

   ```
   C:\dev\mama-metrics\.venv\Scripts\python.exe scripts\tiktok_auth.py
   ```

   Client Key und Client Secret eintippen (Secret bleibt unsichtbar), im
   Browser **Autorisieren** tippen. Das Skript legt die drei Secrets
   `TIKTOK_CLIENT_KEY`, `TIKTOK_CLIENT_SECRET`, `TIKTOK_REFRESH_TOKEN` per
   Datei und `gh secret set NAME < datei` im Repo
   amanterbusiness-ai/mamafunke-social ab und löscht die Datei sofort.

## Danach automatisch

- Alle 30 Minuten prüft GitHub Actions den Plan. Ist ein Reel mit `tiktok` in
  `channels` fällig, wird es hochgeladen; Erledigtes steht in
  `state/posted.json` als `<id>:tiktok_api`.
- Zugang prüfen ohne zu posten: Actions, Workflow **Posten**, **Run workflow**
  mit "Nur Zugänge prüfen". Im Log steht "TikTok: Zugang gültig".
- Die Browser-Aufgabe plant ab dann nur noch Slideshows (TIKTOK.md), damit
  nichts doppelt erscheint.

## Später: Direct Post

Erst wenn TikTok die App geprüft hat (Einreichung nur nach Rücksprache mit der
Gründerin): in der App "Direct Post" einschalten, `tiktok_auth.py --direct`
ausführen und im Repo unter Settings, Variables die Variable
`TIKTOK_MODUS=direct` setzen. Dann gehen Caption, KI-Kennzeichnung
(`is_aigc` aus `"ki"`) und "Deine Marke" (`brand_organic_toggle`) automatisch
mit, und die Postfach-Schritte oben entfallen.

## Stand 04.10.2026: abgeschaltet

Direct Post ist laut TikTok Content Sharing Guidelines für Werkzeuge, die nur auf das eigene Konto posten, nicht zulässig, und verlangt pro Post eine manuelle Auswahl von Sichtbarkeit und Werbehinweis samt Zustimmung. Ein Antrag wurde deshalb nicht eingereicht. Der Upload-Modus funktioniert (Sandbox, getestet mit video-03-alltag), erzeugt aber nur Entwürfe mit Handarbeit in der App. Darum plant die Browser-Aufgabe wieder alle TikTok-Posts.
