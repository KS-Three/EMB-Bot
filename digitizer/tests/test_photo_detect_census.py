"""The 2026-11-06 photo detection census (MASTER_SCOPE defect 15): does
stage-1.25 detection still add a photograph the stage-0 texture gate misses?

`tools/photo_detect_census.py` replays `/classify`'s block (stage 0, prep,
stage 1.25) over the committed fixtures and the 39-row Commons corpus and
writes `testdata/photo/photo_detect_census_2026-11-06.json`. The corpus
images are gitignored and fetched on demand, so CI pins the committed SUMMARY
here (no network) and re-reads only the committed fixtures live, so the
summary cannot drift from the engine without a test saying so.

Every pinned figure is an instrument reading, not a quality claim (ROADMAP
gate 4); nothing here moves a threshold (gate 2) or a default (gate 3).
"""
from __future__ import annotations

import json

import pytest

from tests.conftest import TESTDATA
from tools import photo_detect_census as pdc

SUMMARY = TESTDATA / "photo" / "photo_detect_census_2026-11-06.json"

# --- the 2x2 the verdict turned on (docs/photo-detection-census-2026-11-06.md) --

# 19 real photographs (owl_kent + the corpus's 18 photo genres): every one a
# photo class by stage 0 with the texture gate ON; a signal fired on 3 of them
# (vintage_sepia and group_people by face, sports_action by EXIF), all three
# already photo-class. Nothing for detection to add, nothing left escaping.
PINNED_PHOTOS_2X2 = {"photo_class&detected": 3, "photo_class&silent": 16,
                     "other_class&detected": 0, "other_class&silent": 0}
PINNED_PHOTO_ESCAPES: list[str] = []
PINNED_DETECTION_RESCUES: list[str] = []
# What a Studio job (faces_route_flat=true) gets instead: the 3 face hits
# route FLAT with the photographic machinery off (Kent 2026-09-30 ruling,
# not a detection miss). Pinned so the count is visible, not judged.
PINNED_STUDIO_NOT_PHOTOGRAPHIC = ["group_people", "sports_action", "vintage_sepia"]
# Cohen's kappa against the hand label over the 49 photo + logo rows.
PINNED_KAPPA = {"photo_class": 1.0, "detected": 0.187, "studio_is_photographic": 0.867}
PINNED_N_ROWS = 55   # 16 committed fixtures + 39 corpus rows


@pytest.fixture(scope="module")
def summary() -> dict:
    return json.loads(SUMMARY.read_text(encoding="utf-8"))


def test_summary_covers_the_fixtures_and_the_corpus(summary):
    assert len(summary["rows"]) == PINNED_N_ROWS
    assert summary["errors"] == []
    slugs = {r["slug"] for r in summary["rows"]}
    assert set(pdc.FIXTURES) <= slugs


def test_no_logo_trips_a_signal(summary):
    """The false-positive count over the committed logos AND the corpus's 21
    logo rows: a logo a signal called a photograph would gain the palette
    bind, the shade bind and depth sequencing it must not have."""
    assert summary["logos"]["false_positives"] == []
    assert summary["logos"]["n"] >= len(pdc.LOGOS)


def test_the_2x2_over_real_photographs(summary):
    t = summary["photos"]
    assert t["cells"] == PINNED_PHOTOS_2X2
    assert t["detection_rescues"] == PINNED_DETECTION_RESCUES
    assert t["escapes"] == PINNED_PHOTO_ESCAPES
    assert t["studio_not_photographic"] == PINNED_STUDIO_NOT_PHOTOGRAPHIC
    assert {k: v["kappa"] for k, v in summary["kappa"].items()} == PINNED_KAPPA


def test_the_2x2_is_consistent_with_its_rows(summary):
    """The cells are recomputed from the rows, so a hand-edited count cannot
    pass on its own."""
    assert pdc.two_by_two(summary["rows"], ("photo",))["cells"] == summary["photos"]["cells"]
    assert pdc.two_by_two(summary["rows"], ("photo-of-logo",))["cells"] \
        == summary["photo_of_logo"]["cells"]
    assert {k: pdc.kappa(summary["rows"], k) for k in summary["kappa"]} == summary["kappa"]


@pytest.mark.parametrize("rel", [
    "photo/owl_kent.jpg", "photo/drone_render.png",
    "photo/summit_badge.png", "photo/logo_drone_thermal_badge.png",
])
def test_committed_fixture_rows_still_read_as_the_summary_says(summary, rel):
    """Live re-read of the four fixtures `config.is_photographic`'s docstring
    argues from: the summary's class, signal and verdict must still be the
    engine's. No network: these files are committed."""
    want = next(r for r in summary["rows"] if r["slug"] == rel)
    got = pdc.read_row(TESTDATA / rel, kind=want["kind"], genre=None)
    for key in ("class_on", "class_off", "photo_class", "signal", "detected",
                "is_photographic_off", "is_photographic_on", "studio_is_photographic"):
        assert got[key] == want[key], (rel, key, got[key], want[key])
