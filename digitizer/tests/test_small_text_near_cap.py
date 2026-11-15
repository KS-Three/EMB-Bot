"""`cfg.extra["small_text_reset_near_cap"]` (built OFF 2026-11-14): a line just
over the re-set's cap is re-set at the least growth instead of sewing its raw
trace.

ProSeal's tagline at the Studio's hat auto-fit (109.6 mm) measures 4.01 mm:
over `0.9 * cap_mm` (3.6), so the re-set skipped it as `tall_enough` and it
sewed as traced -- a 0.13 mm anti-aliased sliver snapped to teal in the P,
FOAM's A without its crossbar, COATINGS' T broken -- where at 85.7 mm the same
line (3.1 mm) was retraced, widened and read. ProSeal's art is not in the
repo; Fremont's EAT | STAY | PLAY (2.445 mm at 92.6 mm) stands at the same
height at 151.5 mm."""
from __future__ import annotations

from pathlib import Path

from digitizer_core import small_text as st


def test_the_band_is_just_over_the_cap():
    assert st.NEAR_CAP_RATIO > 1.0
    assert st.NEAR_CAP_RATIO * 4.0 > 4.05      # ProSeal's tagline at 109.6 mm


def test_a_line_just_over_the_cap_is_reset_only_on():
    from digitizer_core.pipeline import build_generation
    from digitizer_service.app import _decode
    from tools import pro_pair as pp
    art = Path(__file__).resolve().parents[1] / "testdata" / "photo" / "logo_hotel_fremont.webp"
    data = art.read_bytes()

    def rows(extra):
        gen = build_generation(_decode(data), pp.config(151.5, "hat_front", extra), exif_source=data)
        return [r for r in gen.small_text_reset or []
                if r.get("cap_mm") and 3.6 <= r["cap_mm"] < 5.0]
    off = rows(None)
    assert off and all(r.get("skipped") == "tall_enough" for r in off), off
    on = rows({"extra.small_text_reset_near_cap": True})
    assert on and all(r.get("near_cap") for r in on), on
    assert any(r.get("scale", 0) >= st.MIN_SCALE - 1e-6 for r in on), on
