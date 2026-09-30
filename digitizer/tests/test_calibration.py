"""The service's half of closed-loop sew-out calibration
(`digitizer_core.calibration.profile` and the `/calibration/*` routes):
the card comes down in the customer's format, a photo comes back as a
draft profile, and the arithmetic between the reader's deltas and the
three profile numbers is pinned.

The card is built ONCE per module (~15 s: block 5 runs the pipeline four
times) and the reference read once more, through the same cache the
service uses. Skipped, not failed, without a TrueType font.
"""
from __future__ import annotations

import base64
import io

import cv2
import numpy as np
import pystitch
import pytest

from digitizer_core.calibration import card as v1
from digitizer_core.calibration import profile as P
from digitizer_core.calibration import reader as R
from digitizer_core.fabrics import get_fabric

pytestmark = pytest.mark.skipif(v1.FONT is None, reason="block 5 needs a TrueType font")


@pytest.fixture(scope="module")
def bundle():
    return P.card_bundle()


# --- the mapping, on synthetic compare() output ----------------------------------

def _cmp(pull_in=None, d_cov=None, square="fill-D-0.15", seams=None):
    feats = []
    if d_cov is not None:
        feats.append({"name": square, "role": "square", "d_width_mm": -0.1, "d_height_mm": 0.0,
                      "d_coverage": d_cov, "note": ""})
    return {"features": feats, "seam_gap_delta_mm": seams or {},
            "draft_profile_delta": {"satin_pull_in_mm": pull_in, "satin_push_out_mm": 0.2,
                                    "fill_pull_in_mm": 0.1, "fill_coverage_deficit": None}}


def test_pull_comp_delta_is_half_the_pull_in_minus_the_preset():
    polo = get_fabric("pique_knit")                       # 0.3 per rail
    out = P.draft_profile(_cmp(pull_in=0.5), polo)
    # 0.5 mm across = 0.25 per rail wanted; the preset gives 0.30.
    assert out["profile"] == {"pull_comp_delta_mm": -0.05}
    assert out["in_force"]["pull_comp_mm"] == 0.25
    assert out["preset"]["pull_comp_mm"] == 0.3
    assert any("pulled in 0.50 mm" in n for n in out["notes"])
    # A bigger pull wants more than the preset: a positive delta.
    assert P.draft_profile(_cmp(pull_in=0.9), polo)["profile"]["pull_comp_delta_mm"] == 0.15


def test_density_only_tightens_and_reads_the_shipped_row_square():
    polo = get_fabric("pique_knit")
    # 12% of the cloth showing through the 0.15 mm square: rows tighten by 12%.
    out = P.draft_profile(_cmp(pull_in=0.6, d_cov=-0.12), polo)
    assert out["profile"]["density_scale"] == 0.88
    assert out["measured"]["coverage_square"] == "fill-D-0.15"
    assert out["in_force"]["density_adjust"] == 0.88
    # Coverage BETTER than the render never loosens the rows.
    # (A 0.6 mm pull-in is exactly the polo's 0.3 per rail, so with nothing
    # else to say the profile is None — a no-op, dropped — not {}.)
    out = P.draft_profile(_cmp(pull_in=0.6, d_cov=0.05), polo)
    assert out["profile"] is None
    # Noise-level deficit is left alone too.
    out = P.draft_profile(_cmp(pull_in=0.6, d_cov=-0.01), polo)
    assert out["profile"] is None
    # v1's card has no 0.15 square; the 0.20 one is read instead.
    out = P.draft_profile(_cmp(pull_in=0.6, d_cov=-0.1, square="fill-B-0.20"), polo)
    assert out["profile"]["density_scale"] == 0.9 and out["measured"]["coverage_square"] == "fill-B-0.20"


def test_trim_never_moves_and_the_reading_says_why():
    out = P.draft_profile(_cmp(pull_in=0.6), get_fabric("terry_towel"))
    assert "trim_at_delta_mm" not in out["profile"]          # 0 is a no-op, dropped
    assert any("no float-length arm" in n for n in out["notes"])
    assert out["in_force"]["trim_at_mm"] == 4.0


def test_nothing_readable_is_no_profile_not_a_crash():
    out = P.draft_profile(_cmp(), get_fabric("pique_knit"))
    assert out["profile"] is None
    assert out["in_force"] == {"pull_comp_mm": 0.3, "density_adjust": 1.0, "trim_at_mm": 3.0}
    assert len(out["notes"]) == 3


def test_the_clamp_holds_through_the_draft():
    """A wild reading lands on the table's edge, never past it."""
    out = P.draft_profile(_cmp(pull_in=3.0, d_cov=-0.6), get_fabric("canvas_tote"))
    assert out["in_force"]["pull_comp_mm"] == 0.6           # terry's, the table's max
    assert out["in_force"]["density_adjust"] == 0.85         # terry's, the table's min


# --- the card, cached and served ---------------------------------------------------

def test_the_bundle_is_built_once_and_describes_itself(bundle):
    assert P.card_bundle() is bundle
    assert bundle.card_mm[0] == pytest.approx(82.0, abs=0.1)
    assert bundle.card_mm[1] == pytest.approx(103.0, abs=0.1)
    info = P.card_info(bundle)
    assert info["built"] and info["hoop"]["preset"] == "5x7"
    assert info["color_blocks"] == 7 and info["stitch_count"] > 5000
    assert P.card_info(None)["built"] is False and P.card_info(None)["card_mm"] is None


def test_the_card_downloads_in_the_customers_format(client, bundle):
    r = client.get("/calibration/card?format=dst")
    assert r.status_code == 200, r.text
    assert 'EMBBOT_CALIBRATION_CARD_V2.dst' in r.headers["content-disposition"]
    assert r.headers["x-card-hoop"] == "5x7"
    pat = pystitch.read_dst(io.BytesIO(r.content))
    sewn = [s for s in pat.stitches if s[2] == pystitch.STITCH]
    w = (max(s[0] for s in sewn) - min(s[0] for s in sewn)) / 10.0
    h = (max(s[1] for s in sewn) - min(s[1] for s in sewn)) / 10.0
    assert w == pytest.approx(82.0, abs=0.3) and h == pytest.approx(103.0, abs=0.3)
    assert sum(1 for s in pat.stitches if s[2] == pystitch.COLOR_CHANGE) == 6
    # And in a home-machine format, read back by an independent reader.
    r = client.get("/calibration/card?format=pes")
    assert r.status_code == 200
    assert len([s for s in pystitch.read_pes(io.BytesIO(r.content)).stitches if s[2] == pystitch.STITCH]) == len(sewn)
    assert client.get("/calibration/card?format=bmp").status_code == 400
    info = client.get("/calibration/info").json()
    assert info["built"] is True and "dst" in info["formats"]


# --- a photo, read ----------------------------------------------------------------

def test_a_photo_of_the_card_drafts_a_profile_for_the_garment(client, bundle):
    """A simulated photo with every wide satin bar pulled in 0.5 mm: the
    draft wants 0.25 per rail against the polo's 0.30 — delta -0.05."""
    truth = [R.Distortion("satin-3mm", dy_mm=-0.5), R.Distortion("satin-4mm", dy_mm=-0.5),
             R.Distortion("satin-5mm", dy_mm=-0.5)]
    photo, _ = R.simulate_photo(R.distort(bundle.design, truth), 10.0, seed=21)
    ok, buf = cv2.imencode(".jpg", photo, [cv2.IMWRITE_JPEG_QUALITY, 92])
    assert ok
    r = client.post("/calibration/read", files={"photo": ("card.jpg", buf.tobytes(), "image/jpeg")},
                    data={"garment_id": "left_chest"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["confidence"]["mode"] == "fiducials"
    assert body["preset"]["id"] == "pique_knit"
    assert body["profile"]["pull_comp_delta_mm"] == pytest.approx(-0.05, abs=0.05)
    assert body["in_force"]["pull_comp_mm"] == pytest.approx(0.25, abs=0.05)
    assert body["measured"]["satin_pull_in_mm"] == pytest.approx(0.5, abs=0.06)
    assert body["card_mm"] == bundle.card_mm
    assert len(body["features"]) > 10 and body["notes"]
    img = cv2.imdecode(np.frombuffer(base64.b64decode(body["overlay_jpeg_base64"]), np.uint8), cv2.IMREAD_COLOR)
    assert img is not None and img.shape[1] <= P.OVERLAY_MAX_W
    # An explicit fabric wins over the garment, as in the engine.
    r = client.post("/calibration/read", files={"photo": ("card.jpg", buf.tobytes(), "image/jpeg")},
                    data={"garment_id": "left_chest", "fabric_id": "terry_towel"})
    assert r.status_code == 200 and r.json()["preset"]["id"] == "terry_towel"


def test_a_photo_without_the_card_is_a_422_that_says_what_to_do(client, bundle):
    blank = np.full((600, 480, 3), (196, 203, 208), np.uint8)
    ok, buf = cv2.imencode(".jpg", blank)
    r = client.post("/calibration/read", files={"photo": ("blank.jpg", buf.tobytes(), "image/jpeg")},
                    data={"garment_id": "left_chest"})
    assert r.status_code == 422, r.text
    assert "corner marks" in r.json()["detail"]
    r = client.post("/calibration/read", files={"photo": ("x.txt", b"not an image", "text/plain")})
    assert r.status_code == 400
