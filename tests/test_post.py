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


def test_keine_zwei_posts_zur_selben_zeit():
    import json
    from collections import Counter
    plan = json.loads(post.PLAN.read_text(encoding="utf-8"))
    doppelt = [k for k, n in Counter((p["date"], p["time"]) for p in plan if "date" in p).items() if n > 1]
    assert not doppelt, doppelt


def test_jeder_instagram_post_bekommt_eine_story():
    assert post.kanaele({"channels": ["instagram", "facebook"]}) == ["instagram", "facebook", "story"]
    assert post.kanaele({"channels": ["tiktok", "youtube"]}) == ["tiktok", "youtube"]
    assert post.kanaele({"channels": ["instagram"], "keine_story": True}) == ["instagram"]


def test_story_medium_video_oder_erstes_hochformatbild():
    reel = {"kind": "reel", "media": {"video": "media/videos/a.mp4"}}
    slide = {"kind": "slide", "media": {"tiktok": ["media/x/tiktok-01.jpg", "media/x/tiktok-02.jpg"],
                                        "instagram": ["media/x/instagram-01.jpg"]}}
    assert post.story_medium(reel) == ("video_url", "media/videos/a.mp4")
    assert post.story_medium(slide) == ("image_url", "media/x/tiktok-01.jpg")
