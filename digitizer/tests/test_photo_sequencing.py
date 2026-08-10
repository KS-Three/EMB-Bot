"""Photo depth sequencing + the photo underlay split (plan §2 row 14).

What this file pins, measured from the EMITTED plan — block order, run order,
underlay geometry — never from a config echo:

- a photo-classified design sews depth-sorted: background-tagged layers
  first, then dark→light by thread luminance, explicit detail tiers last —
  replacing stage 2's largest-area-first order;
- an explicit `sew_order` pin still wins within its layer (the override
  composes with depth sorting instead of fighting it);
- the returned thread_indices/palette move WITH the layers, so the palette
  stays the sew-order thread list;
- flat and gradient lanes are untouched (the full byte-identical suites in
  test_flat_lane_byte_identical.py / test_shape_overrides.py enforce the
  committed goldens; here we prove the class switch itself is inert);
- the underlay split: light-mesh fill underlay and spine-run satin underlay
  for photo classes, no underlay under the meander tier, with the per-shape
  `underlay_style` override and an explicit cfg.underlay_style both still
  beating the class default.
"""
from __future__ import annotations

from types import SimpleNamespace

import numpy as np
from shapely import affinity
from shapely.geometry import Polygon

from digitizer_core import PipelineConfig, get_fabric
from digitizer_core.pipeline import digitize
from digitizer_core.regions import Region
from digitizer_core.stage5_overlap import resolve_overlaps
from digitizer_core.stage6_blend import SourcePixels
from digitizer_core.stage7_sequence import depth_sort_layers, sequence
from digitizer_core.threads import CHART

FAB = get_fabric("pique_knit")
FAB_NAP = get_fabric("fleece_sweatshirt")   # double_lattice fill / zigzag satin


def _lum(rgb) -> float:
    r, g, b = rgb
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


# Chart-derived thread picks — found by luminance, not hard-coded ids, so a
# chart change cannot silently turn these tests vacuous.
DARK = min(range(len(CHART)), key=lambda i: (_lum(CHART[i].rgb), i))
LIGHT = max(range(len(CHART)), key=lambda i: (_lum(CHART[i].rgb), -i))
_mid_target = (_lum(CHART[DARK].rgb) + _lum(CHART[LIGHT].rgb)) / 2.0
MID = min((i for i in range(len(CHART)) if i not in (DARK, LIGHT)),
          key=lambda i: (abs(_lum(CHART[i].rgb) - _mid_target), i))


def test_the_chart_picks_actually_span_a_luminance_range():
    assert _lum(CHART[DARK].rgb) < _lum(CHART[MID].rgb) < _lum(CHART[LIGHT].rgb)


# --- helpers -----------------------------------------------------------------

def bar(w: float, h: float, cx: float = 0.0, cy: float = 0.0) -> Polygon:
    p = Polygon([(0, 0), (w, 0), (w, h), (0, h)])
    return affinity.translate(p, cx - w / 2, cy - h / 2)


def region(poly: Polygon, sid: str, thread: int, layer: int,
           meta: dict | None = None) -> Region:
    m = {"layer": layer}
    m.update(meta or {})
    return Region(shape_id=sid, polygon=poly, thread_index=thread,
                  thread_number=CHART[thread].number, area_mm2=poly.area,
                  meta=m)


def plan_for(regions: list[Region], thread_indices: list[int] | None = None,
             fabric=FAB, design_class: str = "flat", depth_sort: bool = False,
             source_pixels=None, **cfg_kw):
    """Build the emitted plan the same way pipeline.py does: (optional)
    depth sort, stage 5, stage 7. Returns (plan-ish, thread_indices)."""
    c = PipelineConfig(**cfg_kw)
    if depth_sort:
        assert thread_indices is not None
        thread_indices = depth_sort_layers(regions, thread_indices, CHART)
    planned, _ = resolve_overlaps(regions, fabric, c)
    blocks, warnings = sequence(planned, fabric, c,
                                source_pixels=source_pixels,
                                design_class=design_class)
    return SimpleNamespace(blocks=blocks, warnings=warnings), thread_indices


def block_threads(plan) -> list[str]:
    return [b.thread_number for b in plan.blocks]


def sew_rank(plan) -> dict[str, tuple[int, int]]:
    """shape_id -> (block index, first-sewn rank), from the emitted runs."""
    order: dict[str, tuple[int, int]] = {}
    for bi, b in enumerate(plan.blocks):
        for r in b.runs:
            if r.shape_id and r.shape_id not in order:
                order[r.shape_id] = (bi, len(order))
    return order


def underlay_points(plan, sid: str) -> int:
    return sum(len(r.points) for b in plan.blocks for r in b.runs
               if r.shape_id == sid and r.kind == "underlay")


def underlay_runs(plan, sid: str) -> int:
    return sum(1 for b in plan.blocks for r in b.runs
               if r.shape_id == sid and r.kind == "underlay")


# --- depth-sorted block order, from the emitted plan -------------------------

def _dark_light_regions():
    # LIGHT is the LARGER shape, so largest-area-first (the legacy order,
    # here encoded as layer 0) sews light first — the exact order depth
    # sorting must replace.
    return [
        region(bar(30, 30, cx=-25), "LGT", LIGHT, 0),
        region(bar(10, 10, cx=25), "DRK", DARK, 1),
    ]


def test_photo_class_sews_dark_before_light_replacing_area_order():
    flat, _ = plan_for(_dark_light_regions())
    assert block_threads(flat) == [CHART[LIGHT].number, CHART[DARK].number], \
        "baseline: largest-area-first sews the big light shape first"

    photo, ti = plan_for(_dark_light_regions(), thread_indices=[LIGHT, DARK],
                         design_class="photo_subject", depth_sort=True)
    assert block_threads(photo) == [CHART[DARK].number, CHART[LIGHT].number], \
        "photo: dark sews before light regardless of area"
    # The first thread the machine actually puts down is the dark shape's.
    assert photo.blocks[0].runs and photo.blocks[0].runs[0].shape_id == "DRK"
    # thread_indices moved with the layers — the palette stays sew-ordered.
    assert ti == [DARK, LIGHT]


def test_background_tagged_layer_sews_first_even_when_light():
    # Legacy layer order AND darkness would both sew the dark foreground
    # first here — only the background tag can put the light layer first.
    regions = [
        region(bar(20, 20, cx=25), "FG", DARK, 0),
        region(bar(20, 20, cx=-25), "BG", LIGHT, 1,
               {"enclosed_background": True}),
    ]
    photo, ti = plan_for(regions, thread_indices=[DARK, LIGHT],
                         design_class="photo_scene", depth_sort=True)
    assert block_threads(photo) == [CHART[LIGHT].number, CHART[DARK].number]
    assert photo.blocks[0].runs[0].shape_id == "BG"
    assert ti == [LIGHT, DARK]


def test_explicit_detail_tier_layer_sews_last_even_when_darkest():
    # The detail layer is the DARKEST thread — dark→light alone would sew it
    # first; the explicit detail tier must defer it to the end.
    regions = [
        region(bar(30, 1.4, cx=0, cy=20), "DET", DARK, 0, {"tier": "satin"}),
        region(bar(25, 25, cx=0, cy=-10), "BODY", MID, 1),
    ]
    photo, _ = plan_for(regions, thread_indices=[DARK, MID],
                        design_class="photo_subject", depth_sort=True)
    assert block_threads(photo) == [CHART[MID].number, CHART[DARK].number]
    ranks = sew_rank(photo)
    assert ranks["BODY"][0] < ranks["DET"][0]


def test_sew_order_pin_still_wins_within_its_depth_sorted_layer():
    """Composition with the shape-layers contract v1.2: depth sorting moves
    the dark LAYER first; the explicit `sew_order` pin still decides order
    WITHIN that layer, pre-empting nearest-neighbour exactly as before."""
    def build():
        return [
            region(bar(40, 10, cx=0, cy=-30), "LGT", LIGHT, 0),
            region(bar(8, 8, cx=-20), "L", DARK, 1),
            region(bar(8, 8, cx=0), "M", DARK, 1),
            region(bar(8, 8, cx=20), "R", DARK, 1, {"sew_order": 0}),
        ]

    photo, _ = plan_for(build(), thread_indices=[LIGHT, DARK],
                        design_class="photo_subject", depth_sort=True)
    ranks = sew_rank(photo)
    # The dark layer sews first as a whole...
    assert ranks["LGT"][0] == max(bi for bi, _ in ranks.values())
    # ...and within it the pinned shape leads, with the unpinned two still
    # resolved by nearest-neighbour from wherever the pinned one ended.
    dark_order = [sid for sid, _ in sorted(ranks.items(), key=lambda kv: kv[1][1])
                  if sid != "LGT"]
    assert dark_order == ["R", "M", "L"]


def test_flat_and_gradient_classes_are_inert_in_sequence():
    """The design_class switch changes nothing for flat or gradient in the
    SEQUENCING machinery this file otherwise exists to pin (block order, run
    order, the underlay split) — those lanes' byte-identity is enforced
    against committed goldens elsewhere; this pins that the parameter itself
    cannot perturb that machinery.

    `design_class` used to also change the satin-vs-fill call itself —
    `stage6_satin.is_satin_candidate`'s DT check (`tests/test_satin.py`)
    ran for non-"flat" classes only, so a compact, noisy-boundary shape
    could read differently for "gradient" than for "flat". 2026-08-06: that
    exemption is gone — the DT check now runs for every `design_class`,
    `"flat"` included, so the satin-vs-fill call is class-independent too.
    `_dark_light_regions()` is still not used here, for a related but
    narrower reason: its `DRK` region is a 10x10 square sitting right on
    `SATIN_MAX_WIDTH_MM`'s cap, which the DT check reclassifies (same reason
    `test_satin.py`'s `SQUARE 8x8` archetype does) — a real behaviour
    change from the ORIGINAL perimeter-only rule, not a bug, but orthogonal
    to what this test isolates. The two shapes below are unambiguous under
    every rule this module has ever shipped: `LGT` is an oversized square
    no rule ever satins, `DRK` is a plain long bar every rule always does.
    """
    def points(plan):
        return [(b.thread_number, r.kind, r.jump, r.trim, r.points)
                for b in plan.blocks for r in b.runs]

    def regions():
        return [
            region(bar(30, 30, cx=-25), "LGT", LIGHT, 0),
            region(bar(10, 3, cx=25), "DRK", DARK, 1),
        ]

    flat, _ = plan_for(regions())
    default, _ = plan_for(regions(), design_class="flat")
    gradient, _ = plan_for(regions(), design_class="gradient")
    assert points(flat) == points(default) == points(gradient)


# --- the underlay split ------------------------------------------------------

def test_photo_fill_underlay_is_light_mesh_not_the_nap_preset():
    sq = [region(bar(30, 30), "Q", MID, 0)]
    flat, _ = plan_for(sq, fabric=FAB_NAP)                       # double_lattice
    photo, _ = plan_for([region(bar(30, 30), "Q", MID, 0)], fabric=FAB_NAP,
                        design_class="photo_subject")
    explicit, _ = plan_for([region(bar(30, 30), "Q", MID, 0)], fabric=FAB_NAP,
                           underlay_style="edge_lattice")
    assert underlay_points(photo, "Q") == underlay_points(explicit, "Q"), \
        "photo default IS edge_lattice — same emitted underlay geometry"
    assert underlay_points(photo, "Q") < underlay_points(flat, "Q"), \
        "and it is lighter than the nap preset's double lattice"


def test_explicit_config_underlay_style_still_beats_the_photo_default():
    heavy, _ = plan_for([region(bar(30, 30), "Q", MID, 0)], fabric=FAB_NAP,
                        design_class="photo_subject",
                        underlay_style="double_lattice")
    flat, _ = plan_for([region(bar(30, 30), "Q", MID, 0)], fabric=FAB_NAP)
    assert underlay_points(heavy, "Q") == underlay_points(flat, "Q"), \
        "an explicit design-wide style wins over the class default"


def test_per_shape_underlay_override_beats_the_photo_default_both_ways():
    none, _ = plan_for(
        [region(bar(30, 30), "Q", MID, 0, {"underlay_style": "none"})],
        fabric=FAB_NAP, design_class="photo_subject")
    assert underlay_points(none, "Q") == 0, "explicit per-shape none wins"

    forced, _ = plan_for(
        [region(bar(30, 30), "Q", MID, 0, {"underlay_style": "zigzag"})],
        fabric=FAB_NAP, design_class="photo_subject", underlay=False)
    assert underlay_points(forced, "Q") > 0, \
        "explicit per-shape style wins even with underlay off design-wide"


def test_photo_satin_underlay_is_a_single_spine_run_not_zigzag():
    # 1.4 mm ribbon + fleece's 0.5 mm pull comp each side = 2.4 mm column,
    # under SATIN_ZIGZAG_ABOVE_MM (2.5) so stage 6's width upgrade never
    # fires and the style contrast is what gets measured.
    ribbon = lambda: [region(bar(30, 1.4), "T", MID, 0)]
    flat, _ = plan_for(ribbon(), fabric=FAB_NAP)                 # zigzag
    photo, _ = plan_for(ribbon(), fabric=FAB_NAP, design_class="photo_subject")
    assert underlay_runs(flat, "T") == 2, "nap preset: spine run + zigzag"
    assert underlay_runs(photo, "T") == 1, "photo: the light spine run only"


def test_meander_tier_sews_no_underlay_under_a_photo_class():
    """Row 14's 'none under meander/sketch' is true by construction (the
    tonal emitters never call an underlay path) — pinned here so a future
    underlay refactor cannot quietly start padding the fabric-as-value
    tiers."""
    w_px, h_px = 400, 280
    src = SourcePixels(rgb=np.full((h_px, w_px, 3), 96, np.uint8),
                       px_per_mm=4.0, origin_px=(w_px / 2.0, h_px / 2.0))
    poly = Polygon([(-40, -25), (40, -25), (40, 25), (-40, 25)])
    plan, _ = plan_for([region(poly, "MEA", MID, 0)],
                       design_class="photo_scene",
                       fill_technique="meander_tonal", source_pixels=src)
    assert sum(len(r.points) for b in plan.blocks for r in b.runs) > 0
    assert underlay_points(plan, "MEA") == 0


# --- end to end through the real pipeline ------------------------------------

def _two_square_image() -> np.ndarray:
    """Transparent background, one BIG light square, one small dark square —
    largest-area-first and dark-first disagree, so the emitted block order
    tells which sequencing actually ran. Near-gray colors on purpose: the
    ndarray decode path is BGR(A), and gray is channel-order-proof."""
    img = np.zeros((300, 300, 4), np.uint8)
    img[20:200, 20:200] = (245, 240, 235, 255)
    img[230:290, 230:290] = (30, 30, 35, 255)
    return img


def test_photo_class_plan_is_depth_sorted_end_to_end():
    result, plan = digitize(_two_square_image(), PipelineConfig(
        target_width_mm=80.0, forced_class="photo_subject"))
    assert len(plan.blocks) >= 2
    lums = [_lum(b.rgb) for b in plan.blocks]
    assert lums == sorted(lums), "photo blocks sew dark→light"
    # The palette is the sew-order list and must match the emitted blocks.
    assert [p["rgb"] for p in result.palette][:len(plan.blocks)] == \
        [list(plan.blocks[i].rgb) for i in range(len(plan.blocks))]


def test_flat_class_keeps_largest_area_first_end_to_end():
    _, plan = digitize(_two_square_image(), PipelineConfig(
        target_width_mm=80.0, forced_class="flat"))
    assert len(plan.blocks) >= 2
    assert _lum(plan.blocks[0].rgb) > _lum(plan.blocks[-1].rgb), \
        "flat control: the big LIGHT square still sews first"


def test_extra_flag_opts_a_non_photo_class_in():
    _, plan = digitize(_two_square_image(), PipelineConfig(
        target_width_mm=80.0, forced_class="flat",
        extra={"photo_sequencing": True}))
    lums = [_lum(b.rgb) for b in plan.blocks]
    assert lums == sorted(lums), "explicit opt-in depth-sorts a flat design"
