# Prompt für ChatGPT, wenn Claude ausfällt

In ChatGPT den **Agent-Modus** wählen (er kann den Browser bedienen), dann
diesen Text einfügen:

---

Du übernimmst heute die TikTok-Planung für meine App MamaFunke.

Lies zuerst die Anleitung und den Plan:
- https://github.com/amanterbusiness-ai/mamafunke-social/blob/main/TIKTOK.md
- https://github.com/amanterbusiness-ai/mamafunke-social/blob/main/plan/posts.json

Dann:
1. Öffne TikTok Studio (https://www.tiktok.com/tiktokstudio/upload). Ich bin
   eingeloggt. Wenn nicht, halte an und sag mir Bescheid; gib kein Passwort ein.
2. Prüfe unter „Beiträge“, welche Posts schon geplant oder veröffentlicht sind.
3. Plane alle TikTok-Posts der nächsten 9 Tage ein, die noch fehlen, genau wie
   in TIKTOK.md beschrieben. Die Dateien lädst du von
   https://raw.githubusercontent.com/amanterbusiness-ai/mamafunke-social/main/<pfad aus posts.json>
4. Beschreibung wörtlich aus `caption` übernehmen, nichts umformulieren, keine
   Hashtags ergänzen. Datum und Uhrzeit aus `date` und `time` (deutsche Zeit).
5. Bei Reels den Schalter „KI-generierte Inhalte“ einschalten.
6. Nichts löschen oder ändern, was schon geplant ist. Keine Kommentare oder
   Nachrichten beantworten.

Gib mir am Ende eine kurze Liste: neu geplant (Datum, Uhrzeit, Hook), übersprungen
und warum.

---

**Ohne Agent-Modus:** Den gleichen Text einfügen und am Ende ergänzen:
„Du kannst den Browser nicht bedienen. Gib mir stattdessen für jeden fehlenden
Post eine Anleitung: welche Dateien ich hochlade, die Beschreibung zum
Kopieren, Datum und Uhrzeit.“ Dann planst du selbst ein, etwa 2 Minuten pro Post.
