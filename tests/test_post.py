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


def test_tiktok_api_nur_fuer_reels_mit_tiktok():
    assert post.kanaele({"kind": "reel", "channels": ["tiktok", "youtube"]}) == ["tiktok", "youtube", "tiktok_api"]
    assert post.kanaele({"kind": "slide", "channels": ["tiktok"]}) == ["tiktok"]
    assert post.kanaele({"kind": "reel", "channels": ["youtube"]}) == ["youtube"]


def test_tiktok_api_ohne_secrets_nicht_bereit(monkeypatch):
    for name in ("TIKTOK_CLIENT_KEY", "TIKTOK_CLIENT_SECRET", "TIKTOK_REFRESH_TOKEN"):
        monkeypatch.delenv(name, raising=False)
    assert not post.READY["tiktok_api"]()
    monkeypatch.setenv("TIKTOK_CLIENT_KEY", "k")
    monkeypatch.setenv("TIKTOK_CLIENT_SECRET", "s")
    assert not post.READY["tiktok_api"]()
    monkeypatch.setenv("TIKTOK_REFRESH_TOKEN", "r")
    assert post.READY["tiktok_api"]()


def test_tiktok_teilstuecke():
    mb = 1024 * 1024
    assert post.tiktok_teile(3 * mb) == [(0, 3 * mb - 1)]
    assert post.tiktok_teile(64 * mb) == [(0, 64 * mb - 1)]
    teile = post.tiktok_teile(100 * mb)
    assert teile[0][0] == 0 and teile[-1][1] == 100 * mb - 1
    assert all(b - a + 1 == 10 * mb for a, b in teile[:-1])
    assert 10 * mb <= teile[-1][1] - teile[-1][0] + 1 < 20 * mb
    assert all(teile[i][1] + 1 == teile[i + 1][0] for i in range(len(teile) - 1))


def test_tiktok_direct_post_angaben():
    p = {"caption": "alle", "captions": {"tiktok": "nur tt"}, "ki": True}
    info = post.tiktok_post_info(p, ["SELF_ONLY", "PUBLIC_TO_EVERYONE"])
    assert info["title"] == "nur tt"
    assert info["privacy_level"] == "PUBLIC_TO_EVERYONE"
    assert info["is_aigc"] is True
    assert info["brand_organic_toggle"] is True and info["brand_content_toggle"] is False
    # Ungeprüfte App: TikTok erlaubt nur privat
    assert post.tiktok_post_info({"caption": "x"}, ["SELF_ONLY"])["privacy_level"] == "SELF_ONLY"
    assert post.tiktok_post_info({"caption": "x"}, ["SELF_ONLY"])["is_aigc"] is False


def test_tiktok_modus_upload_ist_standard(monkeypatch):
    monkeypatch.delenv("TIKTOK_MODUS", raising=False)
    assert post.tiktok_modus() == "upload"
    monkeypatch.setenv("TIKTOK_MODUS", "Direct")
    assert post.tiktok_modus() == "direct"
    monkeypatch.setenv("TIKTOK_MODUS", "quatsch")
    assert post.tiktok_modus() == "upload"


def test_tiktok_pkce_hex_sha256():
    import hashlib
    import tiktok_auth
    verifier, challenge = tiktok_auth.pkce()
    assert 43 <= len(verifier) <= 128
    assert challenge == hashlib.sha256(verifier.encode()).hexdigest()


def test_tiktok_api_erst_ab_stichtag():
    alt = {"channels": ["tiktok"], "kind": "reel", "date": "2026-10-12"}
    neu = {"channels": ["tiktok"], "kind": "reel", "date": "2026-10-13"}
    assert "tiktok_api" not in post.kanaele(alt)
    assert "tiktok_api" in post.kanaele(neu)
