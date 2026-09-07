"""`enforce_color_cap` — making "Colors (max N)" true on every lane.

`stage2_quantize` has always capped the FLAT lane hard: past `cfg.max_colors`
it keeps the largest populations, merges the rest into their closest match and
emits `COLOR_CAP_APPLIED`. The SLIC+RAG lane has no equivalent — it passes
`max_k=cfg.max_colors` into k-medoids, which is a clustering parameter, and
the re-snap can pull further spools in afterwards.

**Stage 0 routes six of seven real customer logos to GRADIENT**, so the one
control a customer has over thread count was enforced on the artwork type they
do not have. Measured at the Studio's shipped default of 6
(`tools/color_cap.py`, 2026-09-07): **6 of 26 designs sew more cones than the
slider promises and all six are gradient** — flat 0 of 6, photo_scene 0 of 7,
photo_subject 0 of 2 — worst `drone_render` at **22 cones and 21 colour stops**
against a promised 6, with `COLOR_CAP_APPLIED` never firing.

Every distinct cone is a spool to buy and, on a single-needle machine, a
manual re-thread mid-job. It is a pricing promise, not a preference.
"""
from __future__ import annotations

from shapely.geometry import Polygon

from digitizer_core.regions import Region
from digitizer_core.stage4_vectorize import enforce_color_cap
from digitizer_core.threads import chart_for
from digitizer_core.config import PipelineConfig

CHART = chart_for(PipelineConfig())


def _sq(x: float, size: float) -> Polygon:
    return Polygon([(x, 0), (x + size, 0), (x + size, size), (x, size)])


def _region(sid: str, thread: int, area: float, enclosed: bool = False) -> Region:
    return Region(shape_id=sid, polygon=_sq(0.0, max(area, 0.01) ** 0.5),
                  thread_index=thread, thread_number=CHART[thread].number,
                  area_mm2=area,
                  meta={"enclosed_background": True} if enclosed else {})


def test_under_the_cap_is_a_no_op():
    """The flag is byte-identical off AND inert on, on any design already
    inside its budget — which is every flat-lane fixture in the corpus."""
    regions = [_region(f"S{i}", i, 100.0) for i in range(4)]
    before = [(r.thread_index, r.thread_number) for r in regions]
    assert enforce_color_cap(regions, CHART, 6) == []
    assert [(r.thread_index, r.thread_number) for r in regions] == before


def test_exactly_at_the_cap_is_a_no_op():
    regions = [_region(f"S{i}", i, 100.0) for i in range(6)]
    assert enforce_color_cap(regions, CHART, 6) == []
    assert len({r.thread_index for r in regions}) == 6


def test_over_the_cap_lands_on_exactly_the_promised_number():
    regions = [_region(f"S{i}", i, 100.0 * (10 - i)) for i in range(10)]
    out = enforce_color_cap(regions, CHART, 6)
    assert len({r.thread_index for r in regions}) == 6
    assert len(out) == 1 and out[0]["code"] == "COLOR_CAP_APPLIED"
    assert out[0]["before"] == 10 and out[0]["after"] == 6
    assert out[0]["dropped"] == 4
    # The four smallest by area are the four that move.
    assert out[0]["shapes"] == 4


def test_the_biggest_areas_keep_their_cones():
    """Keeping by area is the flat lane's own rule, ported."""
    regions = [_region(f"S{i}", i, 100.0 * (10 - i)) for i in range(10)]
    enforce_color_cap(regions, CHART, 3)
    kept = {r.thread_index for r in regions}
    # 0, 1, 2 carry the three largest areas; nothing else may survive as a
    # DISTINCT cone (a dropped region takes a kept index, it does not vanish).
    assert kept <= {0, 1, 2}
    assert len(kept) == 3


def test_a_thread_only_enclosed_background_carries_buys_no_slot():
    """Enclosed-background regions do not sew by default.

    Letting their area evict a thread that DOES sew would spend the customer's
    colour budget on bare fabric — a slot bought by something the machine
    never threads. They are still remapped, so nothing is left naming a cone
    the design dropped.
    """
    regions = [
        _region("Huge-but-unsewn", 7, 100_000.0, enclosed=True),
        _region("A", 0, 300.0), _region("B", 1, 200.0), _region("C", 2, 100.0),
    ]
    enforce_color_cap(regions, CHART, 2)
    kept = {r.thread_index for r in regions}
    assert len(kept) == 2
    assert 7 not in kept, "an unsewn thread took a slot from a sewn one"
    # And the unsewn region did not keep a cone nobody loads.
    assert regions[0].thread_index in kept
    assert regions[0].thread_number == CHART[regions[0].thread_index].number


def test_a_dropped_colour_lands_on_the_nearest_kept_one():
    """Not on an arbitrary survivor — the merge has to be invisible-ish."""
    import numpy as np
    from digitizer_core.stage4_vectorize import deltaE_ciede2000

    regions = [_region(f"S{i}", i, 100.0 * (10 - i)) for i in range(10)]
    dropped_idx = [r.thread_index for r in regions[6:]]
    enforce_color_cap(regions, CHART, 6)
    kept = sorted({r.thread_index for r in regions})
    for src, r in zip(dropped_idx, regions[6:]):
        d = deltaE_ciede2000(np.array([CHART.lab[src]])[:, None, :],
                             np.array([CHART.lab[k] for k in kept])[None, :, :])[0]
        assert r.thread_index == kept[int(np.argmin(d))], (
            f"{src} merged into {r.thread_index}, not its nearest kept cone")


def test_thread_number_follows_thread_index():
    """A region naming one cone and carrying another index is the exact shape
    of PALETTE_THREAD_MISMATCH (MASTER_SCOPE defect 30). Not from here."""
    regions = [_region(f"S{i}", i, 100.0 * (10 - i)) for i in range(10)]
    enforce_color_cap(regions, CHART, 4)
    for r in regions:
        assert r.thread_number == CHART[r.thread_index].number


def test_the_merge_is_recorded_on_the_region():
    regions = [_region(f"S{i}", i, 100.0 * (10 - i)) for i in range(10)]
    enforce_color_cap(regions, CHART, 6)
    moved = [r for r in regions if "color_cap_merged_from" in r.meta]
    assert len(moved) == 4
    for r in moved:
        assert r.meta["color_cap_merged_from"] != r.thread_number


def test_equal_areas_break_on_the_index_not_on_set_order():
    """Two threads of identical area must give the same answer every run.

    Set iteration order is not a promise, and a cap whose result flips between
    runs would show up as a design that "randomly" changes colour.
    """
    first = None
    for _ in range(5):
        regions = [_region(f"S{i}", i, 100.0) for i in range(8)]
        enforce_color_cap(regions, CHART, 3)
        got = sorted({r.thread_index for r in regions})
        first = got if first is None else first
        assert got == first
    assert first == [0, 1, 2]


def test_a_cap_of_one_is_legal_and_collapses_the_design():
    regions = [_region(f"S{i}", i, 100.0 * (5 - i)) for i in range(5)]
    out = enforce_color_cap(regions, CHART, 1)
    assert len({r.thread_index for r in regions}) == 1
    assert out[0]["after"] == 1 and out[0]["dropped"] == 4


def test_a_nonsense_cap_does_nothing_rather_than_raising():
    """`max_colors` arrives from a wire field. Zero must not empty the design."""
    regions = [_region(f"S{i}", i, 100.0) for i in range(5)]
    assert enforce_color_cap(regions, CHART, 0) == []
    assert enforce_color_cap([], CHART, 6) == []
    assert len({r.thread_index for r in regions}) == 5
