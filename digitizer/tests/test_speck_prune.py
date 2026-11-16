"""`cfg.speck_prune` (built OFF 2026-11-14): a kept sub-floor speck no thread
can draw goes to the masks round it (`sliver_prune.prune_specks`).

Kent's `low_poly` at 80 mm left chest is the measurement (Commons art, kept in
the gitignored corpus): the art's polygon edges are one-pixel black lines, the
quantiser labels only their crossings black, and stage 3's contrast rescue
kept each crossing as a 0.13-0.30 mm2 black run loop, sewn as a dot on the
grey facets ("Random Black Spot", 7 pins). ON: all seven gone, 10,539 ->
10,201 stitches, 97 -> 70 trims (the doc: `docs/missing-invented-traced-2026-11-14.md`).

The synthetic frame is 8 px/mm. At the native grid one source pixel is one
working pixel; the coarse case is a 1.6 px/mm source (five working pixels
each). The thread is 40 wt, 0.4 mm = 3.2 px; stage 3's detail floor is
1.5 mm, 144 px of area; the run tier's floors are 10.24 px of area and a
mask at least 9 px long. The ART is painted from the masks' colours, plus
`Scene.ink` lines the masks do not have: the line the quantiser gave to what
is round it, of which the speck is the piece it kept.
"""
from types import SimpleNamespace

import numpy as np

from digitizer_core import sliver_prune
from digitizer_core.config import PipelineConfig
from digitizer_core.stage3_segment import RegionMask
from digitizer_core.threads import load_chart, rgb_to_lab

H, W = 140, 160
PAGE = (255, 255, 255)
LIGHT = (200, 200, 200)
DARK = (120, 120, 120)
BLACK = (20, 20, 20)
NEAR_LIGHT = (196, 196, 196)
CHART = load_chart()
PPM = 8.0
FLOOR_PX = (1.5 * PPM) ** 2
THREAD_PX = 0.4 * PPM


def _thread(rgb) -> int:
    return CHART.nearest_index(rgb_to_lab(np.asarray(rgb, np.float64).reshape(1, 3))[0])


class Scene:
    """Two facets side by side (LIGHT left, DARK right) on the page; marks
    painted over them take their pixels."""

    def __init__(self):
        self.masks: list[np.ndarray] = []
        self.threads: list[int] = []
        self.colours: list[tuple] = []
        self.inks: list[tuple] = []
        self.bodies()

    def bodies(self):
        self.light = self.add(LIGHT, (20, 20, 100, 80))
        self.dark = self.add(DARK, (20, 80, 100, 140))

    def add(self, rgb, *rects) -> int:
        m = np.zeros((H, W), bool)
        for y0, x0, y1, x1 in rects:
            m[y0:y1, x0:x1] = True
        for other in self.masks:
            other &= ~m
        self.masks.append(m)
        self.threads.append(_thread(rgb))
        self.colours.append(rgb)
        return len(self.masks) - 1

    def ink(self, rgb, *rects) -> None:
        """A line in the ART only: its pixels stay with the masks round it."""
        self.inks.append((rgb, rects))

    def cross(self, rgb, y, x, w=1, reach=20) -> None:
        """Two art lines `w` px wide crossing at (y, x): low_poly's polygon edges."""
        self.ink(rgb, (y - reach, x, y + reach, x + w), (y, x - reach, y + w, x + reach))

    def build(self, input_ppm=PPM):
        covered = np.zeros((H, W), bool)
        art = np.empty((H, W, 3), np.uint8)
        art[:] = PAGE
        for m, rgb in zip(self.masks, self.colours):
            covered |= m
            art[m] = rgb
        for rgb, rects in self.inks:
            for y0, x0, y1, x1 in rects:
                art[y0:y1, x0:x1] = rgb
        p = SimpleNamespace(bg_mask=~covered, px_per_mm=PPM, input_px_per_mm=input_ppm, rgb=art)
        return [RegionMask.from_full(m, layer) for layer, m in enumerate(self.masks)], self.threads, p


def _run(scene, input_ppm=PPM):
    masks, threads, p = scene.build(input_ppm)
    before = [m.area for m in masks]
    out, stats = sliver_prune.prune_specks(masks, threads, p, CHART, FLOOR_PX, THREAD_PX)
    assert [m.area for m in masks] == before            # the caller's masks are untouched
    return masks, out, stats


def _recs(scene, input_ppm=PPM):
    masks, threads, p = scene.build(input_ppm)
    return {r["index"]: r for r in sliver_prune.specks(masks, threads, p, CHART, FLOOR_PX, THREAD_PX)}


def test_default_is_off():
    assert PipelineConfig().speck_prune is False


def test_a_black_crossing_on_the_facets_goes_to_the_facets_round_it():
    """low_poly's crossing: a 2 x 10 px black mark across the facet seam where
    two one-pixel art lines cross, the lines themselves left to the facets.
    Each pixel goes to the facet it lies nearest: the seam stays where it was."""
    s = Scene()
    k = s.add(BLACK, (50, 79, 60, 81))
    s.cross(BLACK, 55, 80)
    masks, out, stats = _run(s)
    assert stats == {"specks": 1}
    assert len(out) == 2
    assert sum(m.area for m in out) == sum(m.area for m in masks)
    assert out[s.light].area == masks[s.light].area + 10
    assert out[s.dark].area == masks[s.dark].area + 10
    rec = _recs(s)[k]
    assert rec["speck"] and rec["fragment"] and rec["arms_lost"] == 4
    assert rec["mean_width_src_px"] < sliver_prune.SPECK_WIDTH_SRC_PX
    assert rec["inscribed_px"] < THREAD_PX and rec["figure"] == 1.0 and rec["page"] == 0.0


def test_a_piece_of_a_line_the_masks_lost_goes():
    """low_poly's edge piece: the art's line runs on out of both ends of the
    mark, into the facet: a dash where the art has a line."""
    s = Scene()
    k = s.add(BLACK, (50, 40, 52, 60))
    s.ink(BLACK, (50, 25, 52, 75))
    rec = _recs(s)[k]
    assert rec["arms"] == 2 and rec["arms_lost"] == 2 and rec["speck"]
    masks, out, stats = _run(s)
    assert stats == {"specks": 1}


def test_a_mark_two_source_pixels_wide_stays():
    """4 x 10 px: 2 x area / rim = 2.5 source pixels, a drawn mark."""
    s = Scene()
    s.add(BLACK, (50, 78, 60, 82))
    s.cross(BLACK, 55, 80)
    masks, out, stats = _run(s)
    assert stats == {"specks": 0} and out is masks


def test_a_speck_too_short_to_sew_is_left_to_stage_4():
    """2 x 6 px: under the run tier's loop, so stage 4 drops it; this pass
    leaves it (and the outlines round it) exactly as they were."""
    s = Scene()
    s.add(BLACK, (50, 79, 56, 81))
    s.cross(BLACK, 53, 80)
    masks, out, stats = _run(s)
    assert stats == {"specks": 0} and out is masks


def test_one_source_pixel_on_a_coarse_source_is_real_stroke():
    """At 1.6 px/mm one source pixel is 5 working pixels, 0.63 mm: wider
    than the thread, so a 5 x 12 px mark stays though it is one source pixel
    across. A 2 x 12 px sliver on the same source still goes."""
    s = Scene()
    s.add(BLACK, (50, 78, 62, 83))
    s.cross(BLACK, 56, 79, w=2, reach=40)
    masks, out, stats = _run(s, input_ppm=1.6)
    assert stats == {"specks": 0}
    s = Scene()
    s.add(BLACK, (50, 79, 62, 81))
    s.cross(BLACK, 56, 79, w=2, reach=40)
    masks, out, stats = _run(s, input_ppm=1.6)
    assert stats == {"specks": 1}


def test_a_speck_on_the_page_stays():
    """Below the facets, page round three sides: not wedged in the figure."""
    s = Scene()
    s.add(BLACK, (100, 79, 110, 81))
    masks, out, stats = _run(s)
    assert stats == {"specks": 0} and out is masks


def test_a_speck_in_its_hosts_own_colour_stays():
    s = Scene()
    s.add(NEAR_LIGHT, (50, 40, 60, 42))
    masks, out, stats = _run(s)
    assert stats == {"specks": 0} and out is masks


def test_two_touching_specks_both_go_and_no_pixel_is_lost():
    """A black and a red sliver side by side in the light facet, on one art
    line: neither takes the other's pixels, the facet takes both."""
    s = Scene()
    s.add(BLACK, (50, 50, 60, 52))
    s.add((200, 20, 30), (50, 52, 60, 54))
    s.ink(BLACK, (55, 30, 56, 75))
    masks, out, stats = _run(s)
    assert stats == {"specks": 2} and len(out) == 2
    assert out[s.light].area == masks[s.light].area + 40
    assert sum(m.area for m in out) == sum(m.area for m in masks)


WHITE = (250, 250, 250)


class Field(Scene):
    """To a T's white field, one body across the frame."""

    def bodies(self):
        self.white = self.add(WHITE, (20, 20, 100, 140))


def test_a_whole_mark_stays():
    """To a T (2026-11-16): a speed line drawn as one bar (2 x 20 px) and the
    period in "LLC." (2 x 10 px). No ink leaves either: it is the art's whole
    mark, not a dot where the art has a line, and main sews it."""
    for rect in ((50, 40, 52, 60), (70, 40, 72, 50)):
        s = Field()
        k = s.add(BLACK, rect)
        rec = _recs(s)[k]
        assert rec["arms"] == 0 and not rec["fragment"] and not rec["speck"]
        masks, out, stats = _run(s)
        assert stats == {"specks": 0} and out is masks


def test_a_piece_of_a_line_sewn_on_in_its_own_colour_stays():
    """To a T's speed-line piece: the line goes on as another black mask,
    which `fine_bar_survive` redraws at stage 4. Its arm is not lost."""
    s = Field()
    k = s.add(BLACK, (50, 40, 52, 60))
    s.add(BLACK, (50, 60, 52, 138))
    rec = _recs(s)[k]
    assert rec["arms"] == 1 and rec["arms_lost"] == 0 and not rec["speck"]
    masks, out, stats = _run(s)
    assert stats == {"specks": 0} and out is masks


NAVY = (40, 50, 90)
MID_GREY = (110, 110, 120)


class Wing(Scene):
    """A navy body (a feather, as the crest's wing) left, the dark facet right."""

    def bodies(self):
        self.navy = self.add(NAVY, (20, 20, 100, 80))
        self.dark = self.add(DARK, (20, 80, 100, 140))


def test_a_white_quill_inside_one_body_stays():
    """The crest's quill (2026-11-15): a white slit the art cuts into a navy
    feather is a slit, not a speck, however its ink runs on; main sews it,
    and so does ON."""
    s = Wing()
    q = s.add(WHITE, (50, 49, 60, 51))
    s.cross(WHITE, 55, 49)
    rec = _recs(s)[q]
    assert rec["dl_neighbour"] >= sliver_prune.SPECK_SLIT_MIN_DL
    assert rec["slit"] and not rec["speck"]
    masks, out, stats = _run(s)
    assert stats == {"specks": 0} and out is masks


def test_a_quill_with_a_speck_on_its_rim_still_stays():
    """The crest's long quill touches five antialias scraps besides the wing.
    A speck beside it leaves anyway, so the quill still lies in one body; the
    grey speck goes to the quill and the navy, by nearness."""
    s = Wing()
    q = s.add(WHITE, (50, 49, 60, 51))
    g = s.add(MID_GREY, (50, 51, 60, 53))
    s.ink(MID_GREY, (55, 53, 56, 75))
    recs = _recs(s)
    assert recs[g]["speck"] and recs[g]["dl_neighbour"] < sliver_prune.SPECK_SLIT_MIN_DL
    assert recs[q]["slit"] and not recs[q]["speck"]
    masks, out, stats = _run(s)
    assert stats == {"specks": 1} and len(out) == len(masks) - 1
    assert sum(m.area for m in out) == sum(m.area for m in masks)
    assert any(m.layer == masks[q].layer and m.area >= masks[q].area for m in out)


def test_a_white_mark_across_a_seam_is_still_a_speck():
    """On low_poly the crossings sit on facet seams: rim on two bodies, so
    however light the mark, it is not a slit in one of them."""
    s = Wing()
    w = s.add(WHITE, (50, 79, 60, 81))          # on the navy / dark seam
    s.cross(WHITE, 55, 80)
    rec = _recs(s)[w]
    assert rec["dl_neighbour"] >= sliver_prune.SPECK_SLIT_MIN_DL
    assert rec["speck"] and not rec["slit"]
    masks, out, stats = _run(s)
    assert stats == {"specks": 1}


def test_a_mark_only_a_little_lighter_is_still_a_speck():
    """low_poly's grey slivers read 11.9-19.2 L over their facets: under the
    slit's contrast, so they still go."""
    s = Scene()
    m = s.add(LIGHT, (50, 109, 60, 111))         # light grey in the dark facet
    s.cross(LIGHT, 55, 110)
    rec = _recs(s)[m]
    assert 0 < rec["dl_neighbour"] < sliver_prune.SPECK_SLIT_MIN_DL
    assert rec["speck"] and not rec["slit"]
