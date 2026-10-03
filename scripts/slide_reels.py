"""Macht aus geplanten Slide-Posts zusätzlich kurze Reels und plant sie ein.

Bilder und Stories bekommen ohne Follower kaum Reichweite, Reels schon.
Für jeden Slide-Post ab --ab entsteht media/reels/<id>.mp4 (1080x1920, 30 fps,
H.264 + AAC) und ein Plan-Eintrag "<id>-reel" für Instagram, Facebook und YouTube.
TikTok bekommt weiter die Slideshow.

Aufruf: python scripts/slide_reels.py --ab 2026-10-04 [--nur-plan]
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import tempfile
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "plan" / "posts.json"
CREME = "0xfaf6ef"
FPS = 30
END = 1.5          # Endbild: letzter Slide steht still
MAX_LEN = 11.7     # Gesamtlänge höchstens, Sekunden
SLIDE_MAX = 3.2    # Standzeit je Slide höchstens
ZOOM = 0.06
BREITE = 1000      # Slide-Breite bei Zoom 1.0; bei 1.06 sind es 1060 von 1080
ZIEL_DB = -24.0
TAGE = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
# Ruhige Akkorde, abwechselnd, damit nicht jedes Reel gleich klingt.
AKKORDE = [
    [130.81, 196.0, 246.94, 293.66],          # Cmaj9 ohne Terz
    [87.31, 174.61, 220.0, 261.63, 329.63],   # Fmaj7
    [110.0, 164.81, 220.0, 261.63, 329.63],   # Am7
    [98.0, 146.83, 196.0, 246.94, 293.66],    # G
]


def pad(freqs: list[float], dauer: float, vol: float) -> str:
    s = "+".join(f"sin(2*PI*{f}*t)*(0.6+0.4*sin(2*PI*0.25*t+{i}))" for i, f in enumerate(freqs))
    return f"aevalsrc='{vol}*({s})/{len(freqs)}':s=48000:d={dauer}"


def run(cmd: list[str]) -> subprocess.CompletedProcess:
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode:
        raise RuntimeError(f"ffmpeg: {r.stderr[-2000:]}")
    return r


def klangbett(ziel: Path, dauer: float, nr: int) -> None:
    """Leises Pad, auf ca. -24 dB mittleren Pegel gebracht, mit Ein- und Ausblenden."""
    roh = ziel.with_suffix(".roh.wav")
    kette = (f"aformat=channel_layouts=stereo,lowpass=f=1600,aecho=0.8:0.7:60:0.3,"
             f"afade=t=in:d=0.6,afade=t=out:st={dauer - 1.0:.2f}:d=1.0")
    run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", pad(AKKORDE[nr % len(AKKORDE)], dauer, 0.2),
         "-af", kette, str(roh)])
    out = run(["ffmpeg", "-hide_banner", "-i", str(roh), "-af", "volumedetect", "-f", "null", "-"]).stderr
    mittel = float(re.search(r"mean_volume: (-?[\d.]+) dB", out).group(1))
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(roh), "-af", f"volume={ZIEL_DB - mittel:.2f}dB",
         "-t", f"{dauer}", str(ziel)])
    roh.unlink()


def reel(bilder: list[str], ziel: Path, nr: int) -> float:
    n = len(bilder)
    frames = int(min(SLIDE_MAX, (MAX_LEN - END) / n) * FPS)
    end_frames = int(END * FPS)
    gesamt = (frames * n + end_frames) / FPS
    args, kette = [], []
    for i, bild in enumerate(bilder):
        letzt = i == n - 1
        f = frames + (end_frames if letzt else 0)
        args += ["-loop", "1", "-framerate", str(FPS), "-t", f"{f / FPS:.4f}", "-i", str(ROOT / bild)]
        # Slide mittig auf Creme, dann in doppelter Auflösung zoomen: ruckelfrei,
        # und weil nur der Rand wegfällt, wird vom Slide nichts abgeschnitten.
        z = f"min(1+{ZOOM}*on/{frames - 1},{1 + ZOOM})"
        kette.append(
            f"[{i}:v]scale={BREITE}:-2:flags=lanczos,format=rgb24,"
            f"pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color={CREME},scale=2160:3840:flags=lanczos,"
            f"zoompan=z='{z}':x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2':d=1:s=1080x1920:fps={FPS},"
            f"trim=end_frame={f},setpts=PTS-STARTPTS,setsar=1[v{i}]")
    kette.append("".join(f"[v{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=0,"
                 f"scale=out_color_matrix=bt709:out_range=tv,format=yuv420p[v]")
    with tempfile.TemporaryDirectory() as tmp:
        ton = Path(tmp) / "ton.wav"
        klangbett(ton, gesamt, nr)
        args += ["-i", str(ton)]
        run(["ffmpeg", "-y", "-loglevel", "error", *args, "-filter_complex", ";".join(kette),
             "-map", "[v]", "-map", f"{n}:a", "-c:v", "libx264", "-preset", "slow", "-crf", "21",
             "-profile:v", "high", "-pix_fmt", "yuv420p", "-color_range", "tv",
             "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-r", str(FPS),
             "-c:a", "aac", "-b:a", "128k", "-ar", "48000", "-movflags", "+faststart",
             "-t", f"{gesamt}", str(ziel)])
    return gesamt


def ohne_hashtags(caption: str) -> str:
    text = re.sub(r"(^|\s)#\S+", "", caption)
    return re.sub(r"[ \t]+\n", "\n", text).strip()


def termin(slide: dict, belegt: dict[str, list[datetime]]) -> datetime:
    """Slide plus 4 h; nachts (22:00 bis 07:00) 07:30 am Folgetag; mindestens 2 h
    Abstand zu jedem anderen Post des Tages, sonst nächster freier 30-Minuten-Slot."""
    t = datetime.fromisoformat(f"{slide['date']}T{slide['time']}") + timedelta(hours=4)
    if t.hour >= 22 or t.hour < 7:
        tag = t.date() + timedelta(days=1 if t.hour >= 22 else 0)
        t = datetime.combine(tag, datetime.min.time()).replace(hour=7, minute=30)
    while True:
        frei = all(abs(t - o) >= timedelta(hours=2) for o in belegt.get(t.date().isoformat(), []))
        if frei and not (t.hour >= 22 or t.hour < 7):
            return t
        # nächster Slot im 30-Minuten-Raster ab 07:30
        t = t.replace(minute=0 if t.minute < 30 else 30) + timedelta(minutes=30)
        if t.hour >= 22 or (t.hour == 21 and t.minute > 30):
            t = datetime.combine(t.date() + timedelta(days=1), datetime.min.time()).replace(hour=7, minute=30)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ab", required=True, help="erster Tag, z. B. 2026-10-04")
    ap.add_argument("--nur-plan", action="store_true")
    ap.add_argument("--neu", action="store_true", help="vorhandene Reels neu rendern")
    args = ap.parse_args()
    ab = date.fromisoformat(args.ab)

    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    ids = {p["id"] for p in plan}
    belegt: dict[str, list[datetime]] = {}
    for p in plan:
        if p.get("date"):
            belegt.setdefault(p["date"], []).append(datetime.fromisoformat(f"{p['date']}T{p['time']}"))

    slides = sorted((p for p in plan if p["kind"] == "slide" and p.get("date")
                     and date.fromisoformat(p["date"]) >= ab and f"{p['id']}-reel" not in ids),
                    key=lambda p: (p["date"], p["time"]))
    for nr, s in enumerate(slides):
        video = f"media/reels/{s['id']}.mp4"
        ziel = ROOT / video
        if not args.nur_plan and (args.neu or not ziel.exists()):
            dauer = reel(s["media"]["instagram"], ziel, nr)
            print(f"{video}  {dauer:.1f} s  {ziel.stat().st_size / 1e6:.1f} MB")
        t = termin(s, belegt)
        belegt.setdefault(t.date().isoformat(), []).append(t)
        e = {"id": f"{s['id']}-reel", "date": t.date().isoformat(), "weekday": TAGE[t.weekday()],
             "time": t.strftime("%H:%M"), "kind": "reel", "channels": ["instagram", "facebook", "youtube"]}
        for k in ("impulse", "hook", "hook_type"):
            if k in s:
                e[k] = s[k]
        e["caption"] = s["caption"]
        e["captions"] = {"youtube": ohne_hashtags(s["caption"]) + "\nKostenlos laden: mamafunke.de/yt"}
        e["yt_titel"] = f"{s['hook']} #shorts"
        e["media"] = {"video": video}
        plan.append(e)
        print(f"{e['id']}: {s['date']} {s['time']} -> {e['date']} {e['time']}")

    PLAN.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
