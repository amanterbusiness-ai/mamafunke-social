"""Bringt alle Videos auf Social-Media-Lautheit (-14 LUFS).

Stumme Videos bekommen vorher eine ruhige Musik aus den eigenen
Soundtracks (C:\\dev\\mama-app\\videos\\*\\assets). Das Bild wird nicht neu
kodiert. Aufruf: python scripts/ton.py [dateien...]  (ohne Argumente: alle
Videos unter media/videos und media/reels).
"""

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MUSIK_ORDNER = Path(r"C:\dev\mama-app\videos")
MUSIK = ["v03-alltag", "v01b-tabs", "v04-schlaf", "v05-schuld", "v01-tabs"]
ZIEL_LUFS = -14.0
TOLERANZ = 1.0


def lauf(args):
    return subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace")


def dauer(datei):
    out = lauf(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(datei)])
    return float(out.stdout.strip())


def lautheit(datei):
    """Integrierte Lautheit in LUFS, None bei Stille."""
    out = lauf(["ffmpeg", "-hide_banner", "-i", str(datei), "-af", "ebur128", "-vn", "-f", "null", "-"]).stderr
    werte = re.findall(r"I:\s+(-?[\d.]+|-inf) LUFS", out)
    if not werte or werte[-1] == "-inf" or float(werte[-1]) < -60:
        return None
    return float(werte[-1])


def normalisieren(quelle, ziel, musik=None):
    d = dauer(quelle)
    if musik:
        aus = max(d - 1.5, 0)
        args = ["ffmpeg", "-y", "-loglevel", "error", "-i", str(quelle), "-i", str(musik),
                "-filter_complex",
                f"[1:a]atrim=0:{d},asetpts=N/SR/TB,afade=t=in:d=0.4,afade=t=out:st={aus}:d=1.5,"
                f"loudnorm=I={ZIEL_LUFS}:TP=-1.5:LRA=11[a]",
                "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                "-ar", "48000", "-shortest", "-movflags", "+faststart", str(ziel)]
    else:
        args = ["ffmpeg", "-y", "-loglevel", "error", "-i", str(quelle),
                "-af", f"loudnorm=I={ZIEL_LUFS}:TP=-1.5:LRA=11",
                "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
                "-movflags", "+faststart", str(ziel)]
    r = lauf(args)
    if r.returncode:
        raise RuntimeError(r.stderr)


def main(dateien):
    if not dateien:
        dateien = sorted((ROOT / "media" / "videos").glob("*.mp4")) + sorted((ROOT / "media" / "reels").glob("*.mp4"))
    stumm_nr = 0
    bericht = []
    for datei in map(Path, dateien):
        vorher = lautheit(datei)
        if vorher is not None and abs(vorher - ZIEL_LUFS) <= TOLERANZ:
            bericht.append((datei.name, vorher, vorher, "ok"))
            continue
        musik = None
        if vorher is None:
            musik = MUSIK_ORDNER / MUSIK[stumm_nr % len(MUSIK)] / "assets" / "soundtrack.mp3"
            stumm_nr += 1
        tmp = datei.with_suffix(".tmp.mp4")
        normalisieren(datei, tmp, musik)
        tmp.replace(datei)
        bericht.append((datei.name, vorher, lautheit(datei), "musik " + musik.parent.parent.name if musik else "lauter"))
    for name, a, b, art in bericht:
        print(f"{name:40} {str(a):>6} -> {b:>6}  {art}")


if __name__ == "__main__":
    main(sys.argv[1:])
