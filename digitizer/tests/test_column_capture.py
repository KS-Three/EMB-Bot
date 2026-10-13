"""What the Column lane takes that is not a letter.

`tools/column_capture_census.py` counts the shapes `columns.is_lettering`
admits. The house-angle group (`lettering_group`) has no ink link and no
"is this a stroke" test, so a grid of colour patches (`test_preflight`'s
12-patch fixture, #863) and a ramp of 14.4 mm discs (`photo/fur_ramp.png`)
read as lines of lettering. `cfg.lettering_columns_skip_blobs` (default OFF)
refuses a tagged shape that is a solid blob.

Pins here are at the TAG level (`run_stages` + `is_lettering`): the lane's
reach, not its stitches, which is what a tripwire on "gains captures" needs
and what keeps this file cheap.
"""
from __future__ import annotations

import numpy as np
import pytest
from shapely.geometry import Point, box
from shapely.ops import unary_union

from digitizer_core import PipelineConfig
from digitizer_core.columns import (INK_LINK_TOUCH_MM, ink_strays, is_lettering,
                                    is_solid_blob, tag_ink_strays)
from digitizer_core.pipeline import plan_stitches, run_stages
from digitizer_core.regions import Region
from tests.conftest import TESTDATA


def _grid_image():
    colors = [(230, 40, 40), (40, 180, 40), (40, 40, 230), (230, 230, 40),
              (230, 40, 230), (40, 230, 230), (140, 70, 20), (250, 140, 20),
              (120, 20, 160), (20, 120, 90), (90, 90, 90), (10, 10, 10)]
    img = np.full((340, 460, 3), 255, np.uint8)
    for i, c in enumerate(colors):
        row, col = divmod(i, 4)
        y, x = 20 + row * 105, 20 + col * 110
        img[y:y + 85, x:x + 90] = c
    return img


def _taken(source, **kw) -> set[str]:
    cfg = PipelineConfig(target_width_mm=kw.pop("target_width_mm", 80.0), **kw)
    res = run_stages(source, cfg)
    return {r.shape_id for r in res.regions if is_lettering(r, cfg)}


# --- the predicate ----------------------------------------------------------

def test_blob_predicate_separates_patches_from_strokes():
    assert is_solid_blob(box(0, 0, 14.4, 14.4))                 # a patch
    assert is_solid_blob(Point(0, 0).buffer(8.0, 64))           # a disc
    assert not is_solid_blob(box(0, 0, 1.5, 6.5))               # an I
    assert not is_solid_blob(box(0, 0, 6.5, 1.5))               # a bar
    ell = unary_union([box(0, 0, 1.6, 6.5), box(0, 0, 4.5, 1.6)])
    assert not is_solid_blob(ell)                               # an L
    ring = Point(0, 0).buffer(3.2, 64).difference(Point(0, 0).buffer(1.9, 64))
    assert not is_solid_blob(ring)                              # an O
    bold = box(0, 0, 5.0, 16.7)                                 # Becker's bold cap stem
    assert not is_solid_blob(bold)


def test_guard_is_off_by_default():
    assert PipelineConfig().lettering_columns_skip_blobs is False


# --- the tripwire: known non-text fixtures take nothing --------------------

@pytest.mark.parametrize("fixture", ["logo_alpha.png", "ribbon_curve.png",
                                     "bg_uncertain.png", "photo/region_blobs.png"])
def test_non_text_fixtures_gain_no_lane_captures(fixture):
    """Census 2026-10-13: these scorecard fixtures carry no lettering, and the
    lane takes 0 of their shapes. A change to either tagger that makes the
    lane take one fails here, before it reaches a customer's design."""
    assert _taken(TESTDATA / fixture, garment_id="left_chest", max_colors=6) == set()


def test_colour_grid_capture_is_pinned_and_the_guard_clears_it():
    """The synthetic grid is the KNOWN false capture: with the guard OFF the
    lane takes all 12 patches (house group only, `text_candidate` False);
    with it ON, none. If the OFF count moves, the taggers moved: re-read the
    census before editing the number."""
    grid = _grid_image()
    assert len(_taken(grid, target_width_mm=100.0)) == 12
    assert _taken(grid, target_width_mm=100.0, lettering_columns_skip_blobs=True) == set()


def test_fur_ramp_discs_are_the_second_known_false_capture():
    """`photo/fur_ramp.png`: eight 14.4 mm discs, all tagged by the house
    group alone (census 2026-10-13); the guard clears all eight."""
    path = TESTDATA / "photo/fur_ramp.png"
    kw = dict(garment_id="left_chest", max_colors=6)
    assert len(_taken(path, **kw)) == 8
    assert _taken(path, lettering_columns_skip_blobs=True, **kw) == set()


def test_guard_keeps_the_letters_on_enthusiast():
    """Every letter the lane takes on the enthusiast wordmark is still taken
    with the guard ON (the one extra shape the lane takes there, the shield
    star, is not a solid blob and is out of this guard's reach)."""
    path = TESTDATA / "photo/enthusiast_logo.png"
    off = _taken(path, garment_id="left_chest", max_colors=6)
    on = _taken(path, garment_id="left_chest", max_colors=6, lettering_columns_skip_blobs=True)
    assert len(off) >= 10        # tag level: stage 7 builds columns for 11 of them
    assert on == off


# --- the ink link (`cfg.lettering_columns_ink_link`) ------------------------
#
# A house-group-only shape whose thread is further than the text cluster's
# own link (CIEDE2000 20) from every text letter's thread, and that does not
# abut a text letter (`columns.INK_LINK_TOUCH_MM`), is not a letter of the
# text. Census 2026-10-13 (PR body): it refuses enthusiast's shield star and
# nothing else on the corpus; it cannot reach the phone screenshot's status
# icons, which are sewn in the text's own grey.

class _Chart:
    """delta_e from a table, symmetric; a pair it does not know raises the
    way a chart that cannot place a thread does."""
    def __init__(self, table):
        self.t = {}
        for (a, b), d in table.items():
            self.t[(a, b)] = self.t[(b, a)] = d

    def delta_e(self, a, b):
        if a == b:
            return 0.0
        if (a, b) not in self.t:
            raise IndexError(a)
        return self.t[(a, b)]


def _r(sid, poly, thread, **meta):
    return Region(shape_id=sid, polygon=poly, thread_index=thread,
                  thread_number=str(thread), area_mm2=poly.area, meta=dict(meta))


def _word(thread=1):
    return [_r(f"L{i}", box(i * 7.0, 0, i * 7.0 + 6.0, 6.5), thread,
               text_candidate=True, lettering_group=True) for i in range(4)]


CHART = _Chart({(1, 2): 34.2, (1, 3): 12.0, (2, 3): 30.0})


def test_ink_link_refuses_a_far_ink_house_only_shape():
    star = _r("star", Point(-10.0, 3.0).buffer(2.7, 16), 2, lettering_group=True)
    assert ink_strays(_word() + [star], CHART) == ["star"]


def test_ink_link_keeps_a_near_ink_and_a_same_ink_shape():
    near = _r("near", box(-10, 0, -5, 5), 3, lettering_group=True)
    same = _r("same", box(-20, 0, -15, 5), 1, lettering_group=True)
    assert ink_strays(_word() + [near, same], CHART) == []


def test_ink_link_exempts_a_far_ink_shape_that_abuts_the_text():
    """The swash case: a far ink, but as close to a letter as the word's own
    letters are to each other. Just inside and just outside the 1.0 mm."""
    t = INK_LINK_TOUCH_MM
    inside = _r("in", box(-t + 0.05 - 5.0, 0, -t + 0.05, 6), 2, lettering_group=True)
    outside = _r("out", box(-t - 0.05 - 5.0, 10, -t - 0.05, 16), 2, lettering_group=True)
    assert ink_strays(_word() + [inside, outside], CHART) == ["out"]


def test_ink_link_never_refuses_a_text_letter_nor_fails_closed():
    """A text-cluster letter is never judged; no text in the design, or an
    ink the chart cannot place, is no evidence and refuses nothing."""
    odd = _word()
    odd[0].thread_index = 2                       # a far ink, but a text letter
    assert ink_strays(odd, CHART) == []
    lone = _r("star", box(-10, 0, -5, 5), 2, lettering_group=True)
    assert ink_strays([lone], CHART) == []        # no text cluster at all
    unknown = _r("u", box(-10, 0, -5, 5), 7, lettering_group=True)
    assert ink_strays(_word() + [unknown], CHART) == []


def test_ink_link_is_off_by_default_and_reads_its_key_only_when_on():
    assert PipelineConfig().lettering_columns_ink_link is False
    star = _r("star", box(-10, 0, -5, 5), 2, lettering_group=True)
    assert tag_ink_strays(_word() + [star], CHART) == 1
    assert star.meta["lettering_ink_stray"] is True
    assert is_lettering(star, PipelineConfig())
    assert not is_lettering(star, PipelineConfig(lettering_columns_ink_link=True))


def _guard_census(case):
    """(regions, labelled letter ids or None, refused ids) for a corpus case
    at its labelled settings, from ONE `run_stages` with the guard ON: the
    tag pass only writes a key, so the OFF reading is the same regions read
    with the flag off (`test_ink_link_off_never_reaches_the_new_code`)."""
    import json
    from tools.thin_strokes import REAL_ART
    rel, width, garment = REAL_ART[case]
    base = dict(target_width_mm=width, garment_id=garment, max_colors=6)
    on = PipelineConfig(**base, lettering_columns_ink_link=True)
    off = PipelineConfig(**base)
    res = run_stages(TESTDATA / rel, on)
    truth = json.loads((TESTDATA / "lettering_truth.json").read_text(encoding="utf-8"))
    lab = truth["fixtures"].get(case)
    letters = None
    if lab:
        letters = {s for v in lab["lines"].values() for s in v}
        if not letters <= {r.shape_id for r in res.regions}:
            letters = None                       # stale labels: not scored
    refused = {r.shape_id for r in res.regions
               if is_lettering(r, off) and not is_lettering(r, on)}
    return res.regions, letters, refused


def test_ink_link_refuses_the_enthusiast_star_and_keeps_every_letter():
    regions, letters, refused = _guard_census("enthusiast")
    assert letters, "enthusiast's hand labels went stale: re-read the census"
    assert len(refused) == 1
    star = next(r for r in regions if r.shape_id in refused)
    x0, y0, x1, y1 = star.polygon.bounds
    assert not star.meta.get("text_candidate") and star.meta.get("lettering_group")
    assert 4.5 <= x1 - x0 <= 6.5 and 4.5 <= y1 - y0 <= 6.5      # the 5.5 mm star
    assert not (refused & letters)


def test_ink_link_keeps_golden_tees_swashes():
    """The three house-group-only swashes (the script T and its swash, 8-39
    mm) are in the text's own inks; the guard refuses nothing here."""
    regions, _letters, refused = _guard_census("golden_tee")
    swashes = [r for r in regions if r.meta.get("lettering_group")
               and not r.meta.get("text_candidate")
               and max(r.polygon.bounds[2] - r.polygon.bounds[0],
                       r.polygon.bounds[3] - r.polygon.bounds[1]) >= 20.0]
    assert len(swashes) >= 2
    assert refused == set()


@pytest.mark.parametrize("case", ["becker", "bridge", "fremont", "drone", "screenshot"])
def test_ink_link_refuses_nothing_on_the_other_letter_fixtures(case):
    """Nothing refused, so every labelled letter is kept. On `screenshot` this
    pins the measured NEGATIVE too: its 4.5-6 mm status icons are the text's
    own grey (dE 0.0, one at 9.1), so an ink link cannot see them."""
    _regions, _letters, refused = _guard_census(case)
    assert refused == set()


def test_ink_link_off_never_reaches_the_new_code(monkeypatch):
    """OFF is byte-identical by construction: the tag pass is never called
    (it raises here), no key is written, and is_lettering's new branch is
    behind the flag. The ON stream differs (the star), so the pin has teeth."""
    import hashlib
    import json
    from digitizer_core import columns

    path = TESTDATA / "photo/enthusiast_logo.png"
    kw = dict(target_width_mm=80.0, garment_id="left_chest", max_colors=6)

    def md5(cfg):
        res = run_stages(path, cfg)
        keys = sum("lettering_ink_stray" in r.meta for r in res.regions)
        plan = plan_stitches(res, cfg)
        coords = [[round(x, 4), round(y, 4), r.kind, r.jump, r.trim]
                  for _, r in plan.iter_runs() for x, y in r.points]
        return hashlib.md5(json.dumps(coords).encode()).hexdigest(), keys

    on, on_keys = md5(PipelineConfig(**kw, lettering_columns_ink_link=True))

    def boom(*_a, **_k):
        raise AssertionError("tag_ink_strays reached with the flag OFF")
    monkeypatch.setattr(columns, "tag_ink_strays", boom)
    off, off_keys = md5(PipelineConfig(**kw))
    assert off_keys == 0 and on_keys == 1
    assert on != off
