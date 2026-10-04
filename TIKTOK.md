# TikTok einplanen

TikTok postet nicht über GitHub Actions. Stattdessen werden die Posts in
**TikTok Studio** (https://www.tiktok.com/tiktokstudio/upload) im Browser
eingeplant. TikTok erlaubt das bis zu 10 Tage im Voraus.

Quelle für alles: `plan/posts.json` (Einträge mit `"tiktok"` in `channels`).
Lesbar: `plan/PLAN.md`. Öffentlich abrufbar unter
https://github.com/amanterbusiness-ai/mamafunke-social

**Reels und die TikTok-API:** Die API-Anbindung (TIKTOK_API.md) ist abgeschaltet
(Stichtag TIKTOK_API_AB = 2099 in scripts/post.py). Alle TikTok-Posts, Reels und
Slideshows, werden weiter hier im Browser eingeplant.

**Uhrzeiten prüfen:** Vor jedem Planen in der Beitragsliste nachsehen, ob zur
gewünschten Minute schon ein Beitrag geplant ist. Höchstens ein Beitrag pro Uhrzeit.

## Ablauf (für Claude oder ChatGPT gleich)

1. In TikTok Studio unter **Beiträge** nachsehen, welche Posts schon geplant
   oder veröffentlicht sind. Maßgeblich ist der Hook am Anfang der Beschreibung.
   TikTok Studio ist die einzige Wahrheit, es gibt keine eigene Liste dafür.
2. Aus `posts.json` alle TikTok-Posts der **nächsten 9 Tage** nehmen, die dort
   noch fehlen. Vergangene Termine überspringen, nicht nachholen.
3. Für jeden fehlenden Post:
   - **Slideshow** (`kind: slide`): die Bilder aus `media.tiktok` hochladen
     (Fotomodus). Nimmt TikTok Studio keine Fotos an, stattdessen
     `media.tiktok_video` hochladen.
   - **Reel** (`kind: reel`): `media.video` hochladen. **Wichtig:** Videos
     verarbeitet TikTok nur, wenn der Tab sichtbar ist. Vorher per JavaScript
     `document.visibilityState` prüfen. Ist es `hidden`, Reels auslassen und im
     Bericht schreiben: "Für Reels den TikTok-Tab in Chrome nach vorne holen."
     Unter "Mehr anzeigen" den Schalter **"KI-generierter Inhalt"** einschalten
     (Hinweisfenster mit "Aktivieren" bestätigen).
   - Beschreibung: Feld leeren (Strg+A, Entf), `caption` wörtlich tippen,
     danach Escape (schließt Hashtag-Vorschläge). **Vor dem Planen prüfen**, ob
     der Text im Feld steht; sonst nicht planen, sondern neu ansetzen.
   - Unter "Mehr anzeigen": **"Beitragsinhalt offenlegen"** an und **"Deine
     Marke"** anhaken (eigene App = Werbung für die eigene Marke).
   - Titelbild: die erste Slide.
   - Wer darf ansehen: **Alle**. Kommentare: an.
   - **Planen** statt Posten: Datum `date`, Uhrzeit `time` (deutsche Zeit).
     Die Minuten der Zeitauswahl lassen sich zuverlässig per JavaScript wählen:
     Element mit Klasse `tiktok-timepicker-right` und Text der Minute anklicken,
     Stunde analog mit `tiktok-timepicker-left`. Danach die Werte prüfen.
4. Zum Schluss notieren: welche Posts neu geplant wurden, welche fehlen und
   warum.

## Regeln

- Nichts ändern oder löschen, was schon geplant oder veröffentlicht ist.
- Keine Beschreibung umschreiben, keine Hashtags ergänzen.
- Keine Kommentare beantworten, keine Nachrichten schreiben.
- Nicht einloggen: Ist die Sitzung abgelaufen, abbrechen und Bescheid geben.
- Musik: nicht auswählen. Gute Sounds wählt die Inhaberin bei Gelegenheit selbst.

## Lokale Dateien

Auf dem Windows-PC liegt das Repository unter `C:\dev\mama-social`, die
Medienpfade aus `posts.json` beziehen sich darauf (z. B.
`C:\dev\mama-social\media\01-satz\tiktok-01.jpg`).
Ohne den PC: Dateien von GitHub laden, Muster
`https://raw.githubusercontent.com/amanterbusiness-ai/mamafunke-social/main/<pfad>`.
