"""What the Column lane takes that is not a letter.

`tools/column_capture_census.py` counts the shapes `columns.is_lettering`
admits. The house-angle group (`lettering_group`) has no ink link and no
"is this a stroke" test, so a grid of colour patches (`test_preflight`'s
12-patch fixture, #863) and a ramp of 14.4 mm discs (`photo/fur_ramp.png`)
read as lines of lettering. `cfg.lettering_columns_skip_blobs` (default ON
since Kent's ruling 2026-10-13) refuses a tagged shape that is a solid blob;
`cfg.lettering_columns_ink_link` (likewise ON) refuses a house-group-only
shape in a far ink. The OFF paths are pinned by setting the flag False.

Pins here are at the TAG level (`run_stages` + `is_lettering`): the lane's
reach, not its stitches, which is what a tripwire on "gains captures" needs
and what keeps this file cheap.
"""
from __future__ import annotations

import functools

import numpy as np
import pytest
from shapely.geometry import LineString, Point, box
from shapely.ops import unary_union

from digitizer_core import PipelineConfig
from digitizer_core.columns import (ICON_GUARD_MIN_NODES, INK_LINK_TOUCH_MM,
                                    ink_strays, is_drawing_fragment, is_lettering,
                                    is_solid_blob, skeleton_nodes, tag_ink_strays)
from digitizer_core.pipeline import plan_stitches, run_stages
from digitizer_core.regions import Region
from tests.conftest import TESTDATA
from tests.conftest import own_thread_only


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


def test_guard_is_on_by_default():
    """ON by Kent's ruling 2026-10-13; False is the pre-flip lane."""
    assert PipelineConfig().lettering_columns_skip_blobs is True


# --- the tripwire: known non-text fixtures take nothing --------------------

@pytest.mark.parametrize("fixture", ["logo_alpha.png", "ribbon_curve.png",
                                     "bg_uncertain.png", "photo/region_blobs.png"])
def test_non_text_fixtures_gain_no_lane_captures(fixture):
    """Census 2026-10-13: these scorecard fixtures carry no lettering, and the
    lane takes 0 of their shapes. A change to either tagger that makes the
    lane take one fails here, before it reaches a customer's design."""
    assert _taken(TESTDATA / fixture, garment_id="left_chest", max_colors=6) == set()


def test_colour_grid_capture_is_pinned_and_the_guard_clears_it():
    """The synthetic grid is the KNOWN false capture: with the guard OFF
    (explicitly; it is ON by default) the lane takes all 12 patches (house
    group only, `text_candidate` False); at the default, none. If the OFF
    count moves, the taggers moved: re-read the census before editing it."""
    grid = _grid_image()
    assert len(_taken(grid, target_width_mm=100.0, lettering_columns_skip_blobs=False)) == 12
    assert _taken(grid, target_width_mm=100.0) == set()


def test_fur_ramp_discs_are_the_second_known_false_capture():
    """`photo/fur_ramp.png`: eight 14.4 mm discs, all tagged by the house
    group alone (census 2026-10-13); the guard clears all eight."""
    path = TESTDATA / "photo/fur_ramp.png"
    kw = dict(garment_id="left_chest", max_colors=6)
    assert len(_taken(path, lettering_columns_skip_blobs=False, **kw)) == 8
    assert _taken(path, **kw) == set()


def test_guard_keeps_the_letters_on_enthusiast():
    """Every letter the lane takes on the enthusiast wordmark is still taken
    with the blob guard ON (the one extra shape the lane takes there, the
    shield star, is not a solid blob and is out of this guard's reach; the ink
    link is held OFF on both sides so only the blob guard differs)."""
    path = TESTDATA / "photo/enthusiast_logo.png"
    kw = dict(garment_id="left_chest", max_colors=6, lettering_columns_ink_link=False)
    off = _taken(path, lettering_columns_skip_blobs=False, **kw)
    on = _taken(path, lettering_columns_skip_blobs=True, **kw)
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


def test_ink_link_is_on_by_default_and_reads_its_key_only_when_on():
    """ON by Kent's ruling 2026-10-13; False reads no key."""
    assert PipelineConfig().lettering_columns_ink_link is True
    star = _r("star", box(-10, 0, -5, 5), 2, lettering_group=True)
    assert tag_ink_strays(_word() + [star], CHART) == 1
    assert star.meta["lettering_ink_stray"] is True
    assert not is_lettering(star, PipelineConfig())
    assert not is_lettering(star, PipelineConfig(lettering_columns_ink_link=True))
    # (the 5 mm box is also a solid blob, so the blob guard is held off here)
    assert is_lettering(star, PipelineConfig(lettering_columns_ink_link=False,
                                             lettering_columns_skip_blobs=False))


@functools.lru_cache(maxsize=None)
def _case_regions(case, rescued_link=True):
    """(regions, settings, labelled letter ids or None) for a corpus case at
    its labelled settings, from ONE `run_stages` with the ink link ON (its
    tag pass only writes a key; every other guard here is read in
    `is_lettering`), shared by every census test in this process.
    `rescued_link` is the text tagger's `text_cluster_rescued_ink_link`
    (ON since 2026-10-15); False is the pre-flip tagger, whose rescued round
    linked on size alone, the population the screenshot census was read on.
    `dissolve_phantom_blends` is held OFF (ON since Kent's 2026-10-20 flip,
    item 46): the hand labels are shape ids read on the engine without it,
    and on the screenshot the dissolve re-cuts the regions they name."""
    import json
    from tools.thin_strokes import REAL_ART
    rel, width, garment = REAL_ART[case]
    base = dict(target_width_mm=width, garment_id=garment, max_colors=6)
    res = run_stages(TESTDATA / rel, PipelineConfig(**base, lettering_columns_ink_link=True,
                                                    text_cluster_rescued_ink_link=rescued_link,
                                                    dissolve_phantom_blends=False))
    truth = json.loads((TESTDATA / "lettering_truth.json").read_text(encoding="utf-8"))
    lab = truth["fixtures"].get(case)
    letters = None
    if lab:
        letters = frozenset(s for v in lab["lines"].values() for s in v)
        if not letters <= {r.shape_id for r in res.regions}:
            letters = None                       # stale labels: not scored
    return tuple(res.regions), base, letters


def _guard_census(case, flag="lettering_columns_ink_link", already=(), rescued_link=True):
    """(regions, labelled letter ids or None, refused ids): the shapes
    `is_lettering` admits with the `already` flags ON (every other lane
    guard pinned OFF, whatever its default) and refuses once `flag` is ON
    too. The ink link's OFF reading is the same regions read with the flag
    off (`test_ink_link_off_never_reaches_the_new_code`)."""
    regions, base, letters = _case_regions(case, rescued_link)
    pins = {k: False for k in (*GUARDS_ON, ICON)}
    pins.update({k: True for k in already})
    off = PipelineConfig(**base, **{**pins, flag: False})
    on = PipelineConfig(**base, **{**pins, flag: True})
    refused = {r.shape_id for r in regions
               if is_lettering(r, off) and not is_lettering(r, on)}
    return regions, letters, refused


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


@pytest.mark.parametrize("case", ["becker", "bridge", "fremont", "drone"])
def test_ink_link_refuses_nothing_on_the_other_letter_fixtures(case):
    """Nothing refused, so every labelled letter is kept."""
    _regions, _letters, refused = _guard_census(case)
    assert refused == set()


def test_ink_link_sees_the_screenshot_icons_once_the_text_clusters_are_one_ink():
    """Until 2026-10-15 this fixture pinned a NEGATIVE: its 4.5-6 mm status
    icons read as "the text's own grey (dE 0.0, one at 9.1), so an ink link
    cannot see them". That grey was the text's own only because the tagger's
    rescued round linked on size alone and had carried Silver (0308, dE 73
    from the text's Black) and grey (dE 40) pieces -- every one on the hand
    labels' ignore list -- into its text clusters, so a "text letter" existed
    in every icon ink. With `text_cluster_rescued_ink_link` those pieces are
    no text, each cluster is one ink, and the link sees the icons: house-only,
    icon-coloured, none a labelled letter, #881's three captures among them.
    The pre-flip reading is kept as the arm it was measured on."""
    regions, letters, refused = _guard_census("screenshot")
    assert letters, "screenshot's hand labels went stale: re-read the census"
    assert refused and not (refused & letters)
    by_id = {r.shape_id: r for r in regions}
    for sid in refused:                            # every refusal is house-only
        assert by_id[sid].meta.get("lettering_group")
        assert not by_id[sid].meta.get("text_candidate")
    if SCREENSHOT_CAPTURES <= set(by_id):
        assert SCREENSHOT_CAPTURES <= refused
    _regions, _letters, refused_pre = _guard_census("screenshot", rescued_link=False)
    assert refused_pre == set(), "the pre-flip tagger's clusters hid the icons from the link"


def test_ink_link_off_never_reaches_the_new_code(monkeypatch):
    """OFF (set explicitly; the default is ON since 2026-10-13) is
    byte-identical to the pre-flip lane by construction: the tag pass is never
    called (it raises here), no key is written, and is_lettering's branch is
    behind the flag. The default (ON) stream differs (the star), so the pin
    has teeth."""
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

    on, on_keys = md5(PipelineConfig(**kw))
    assert PipelineConfig(**kw).lettering_columns_ink_link is True

    def boom(*_a, **_k):
        raise AssertionError("tag_ink_strays reached with the flag OFF")
    monkeypatch.setattr(columns, "tag_ink_strays",
                        own_thread_only(boom, columns.tag_ink_strays))
    off, off_keys = md5(PipelineConfig(**kw, lettering_columns_ink_link=False))
    assert off_keys == 0 and on_keys == 1
    assert on != off


# --- the icon guard (`cfg.lettering_columns_icon_guard`) --------------------
#
# A house-group-only shape whose pruned medial axis has
# `ICON_GUARD_MIN_NODES` or more junctions plus free ends is a piece of
# drawing. Census 2026-10-13 (PR body, `tools/column_capture_census.py
# --signals`): the phone screenshot's three captures read 36-45, the 130
# labelled letters <= 13, golden_tee's swashes <= 8. Judged with the two
# other guards ON (their default since Kent's ruling 2026-10-13).

GUARDS_ON = ("lettering_columns_skip_blobs", "lettering_columns_ink_link")
ICON = "lettering_columns_icon_guard"
# The three captures #881 found and #885 could not reach.
SCREENSHOT_CAPTURES = {"S4a2d12c4", "Sf90dec39", "S84f354eb"}


def _hatch(w=0.2):
    """4 x 4 thin crossing strokes, 4.7 mm: the screenshot captures' kind
    of shape (a grille of hairlines), sixteen crossings and sixteen ends."""
    return unary_union([box(i * 1.2, -0.5, i * 1.2 + w, 4.5) for i in range(4)]
                       + [box(-0.5, j * 1.2, 4.2, j * 1.2 + w) for j in range(4)])


def _slab_m():
    """A slab-serif M, the most node-rich letter shape in the corpus kind
    (Fremont's H and M read 13): two stems, two diagonals, four serifs."""
    return unary_union([box(0, 0, 0.7, 6.5), box(5.3, 0, 6.0, 6.5),
                        LineString([(0.35, 6.5), (3.0, 1.0)]).buffer(0.35, cap_style=2),
                        LineString([(5.65, 6.5), (3.0, 1.0)]).buffer(0.35, cap_style=2),
                        box(-0.6, 0, 1.3, 0.5), box(4.7, 0, 6.6, 0.5),
                        box(-0.6, 6.0, 1.3, 6.5), box(4.7, 6.0, 6.6, 6.5)])


def test_icon_predicate_separates_a_tangle_from_letters():
    assert skeleton_nodes(_hatch()) >= ICON_GUARD_MIN_NODES
    assert is_drawing_fragment(_hatch())
    ell = unary_union([box(0, 0, 0.8, 6.5), box(0, 0, 4, 0.8), box(0, 2.85, 3.4, 3.65),
                       box(0, 5.7, 4, 6.5)])                      # an E
    ring = Point(0, 0).buffer(3.2, 64).difference(Point(0, 0).buffer(2.4, 64))
    for letter in (ell, ring, _slab_m(), box(0, 0, 1.5, 6.5)):
        assert skeleton_nodes(letter) < ICON_GUARD_MIN_NODES / 2
        assert not is_drawing_fragment(letter)


def test_icon_predicate_is_size_free_and_fails_open():
    """The shape field's grid follows the stroke width, so the count does
    not move with scale; geometry it cannot raster is no evidence."""
    from shapely import affinity
    small, big = skeleton_nodes(_hatch()), skeleton_nodes(affinity.scale(_hatch(), 4, 4))
    assert abs(small - big) <= 4 and big >= ICON_GUARD_MIN_NODES
    assert skeleton_nodes(unary_union([box(0, 0, 1, 1), box(5, 5, 6, 6)])) == 0   # MultiPolygon
    assert skeleton_nodes(Point(0, 0).buffer(0)) == 0                            # empty


def test_icon_guard_is_on_by_default_and_judges_house_only_shapes():
    assert PipelineConfig().lettering_columns_icon_guard is True
    on = PipelineConfig()
    off = PipelineConfig(lettering_columns_icon_guard=False)
    house = _r("h", _hatch(), 1, lettering_group=True)
    text = _r("t", _hatch(), 1, lettering_group=True, text_candidate=True)
    assert is_lettering(house, off) and not is_lettering(house, on)
    assert is_lettering(text, on)                  # the text cluster is not judged
    assert not is_lettering(_r("u", _hatch(), 1), on)   # untagged stays untagged


def test_icon_guard_refuses_the_screenshot_captures_and_no_letter():
    """Read on the pre-flip tagger's clusters (`rescued_link=False`), the
    population the census was taken on: there the ink link cannot see the
    captures (see `test_ink_link_sees_the_screenshot_icons_...`), so the icon
    guard is what refuses them. On the live tagger the ink link refuses them
    first, and the icon guard's own refusals are judged the same way."""
    regions, letters, refused = _guard_census("screenshot", ICON, GUARDS_ON, rescued_link=False)
    assert letters, "screenshot's hand labels went stale: re-read the census"
    assert not (refused & letters)
    by_id = {r.shape_id: r for r in regions}
    for sid in refused:                            # every refusal is house-only
        assert by_id[sid].meta.get("lettering_group")
        assert not by_id[sid].meta.get("text_candidate")
    big = [s for s in refused
           if 4.0 <= max(by_id[s].polygon.bounds[2] - by_id[s].polygon.bounds[0],
                         by_id[s].polygon.bounds[3] - by_id[s].polygon.bounds[1]) <= 6.5]
    assert len(big) >= 3                           # the three 4.5-6 mm captures
    if SCREENSHOT_CAPTURES <= set(by_id):
        assert SCREENSHOT_CAPTURES <= refused
    regions, letters, refused = _guard_census("screenshot", ICON, GUARDS_ON)
    assert letters and not (refused & letters)
    by_id = {r.shape_id: r for r in regions}
    for sid in refused:
        assert by_id[sid].meta.get("lettering_group")
        assert not by_id[sid].meta.get("text_candidate")


@pytest.mark.parametrize("case", ["golden_tee", "enthusiast", "becker", "bridge",
                                  "fremont", "drone"])
def test_icon_guard_refuses_nothing_on_the_other_lettering_fixtures(case):
    """golden_tee's three house-only swashes (4, 4, 8 nodes) are kept, and
    no labelled letter anywhere is refused: nothing is."""
    _regions, _letters, refused = _guard_census(case, ICON, GUARDS_ON)
    assert refused == set()


def test_icon_guard_off_never_reaches_the_predicate(monkeypatch):
    """OFF is byte-identical by construction: `is_lettering` never asks."""
    from digitizer_core import columns
    regions, base, _letters = _case_regions("screenshot")

    def boom(*_a, **_k):
        raise AssertionError("is_drawing_fragment reached with the flag OFF")
    monkeypatch.setattr(columns, "is_drawing_fragment",
                        own_thread_only(boom, columns.is_drawing_fragment))
    cfg = PipelineConfig(**base, **{k: True for k in GUARDS_ON}, **{ICON: False})
    assert sum(is_lettering(r, cfg) for r in regions) > 0
    # ... and ON (the default) does reach it: the OFF test above is not vacuous.
    with pytest.raises(AssertionError, match="reached with the flag OFF"):
        for r in regions:
            is_lettering(r, PipelineConfig(**base))
