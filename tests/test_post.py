import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import post  # noqa: E402


def test_post_mit_datum_ist_wie_bisher_faellig():
    p = {"date": "2026-10-03", "time": "12:30"}
    assert post.faellig(p, None) == datetime(2026, 10, 3, 12, 30, tzinfo=post.BERLIN)


def test_video_wartet_auf_apple_freigabe():
    p = {"nach_apple": 1, "time": "20:15"}
    assert post.faellig(p, None) is None
    assert post.faellig(p, "2026-10-04") == datetime(2026, 10, 5, 20, 15, tzinfo=post.BERLIN)


def test_eigener_text_je_kanal_sonst_caption():
    p = {"caption": "alle", "captions": {"youtube": "nur yt"}}
    assert post.text(p, "youtube") == "nur yt"
    assert post.text(p, "instagram") == "alle"


def test_plan_ist_gueltig():
    import json
    plan = json.loads(post.PLAN.read_text(encoding="utf-8"))
    for p in plan:
        assert ("date" in p) != ("nach_apple" in p), p["id"]
        if p["kind"] == "reel":
            assert (post.ROOT / p["media"]["video"]).exists(), p["id"]
