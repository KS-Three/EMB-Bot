"""White-keyline art turns its own recipe on (`cfg.white_keyline_art_recipe`, ON since 2026-10-26).

EVERY JOB since 2026-10-27 (`cfg.white_keyline_art_every_job`): Kent,
verbatim, "Every job (Recommended)". With that flag on, `detect` returns True
for all art and the read below is the flag-off arm only. It was measured
first: on the 20 other paired jobs (bystander report v2, main 2c6b656c) the
recipe moved 13 closer to the pro, left 7 byte-identical and moved none
further.

Kent's ruling, 2026-10-26: "Gate to MFab art first (Recommended)" -- the
recipe turns on by default only where a dark shape carries white outlines
round letters; every other job stays as it is while the recipe's other
defects are fixed. Made a default for all art, the recipe changed 19 of 20
other paired jobs and damaged four (Gaulke's white roof line buried, Tires'
"e" counters and ProSeal's slot sewn white, a white edge past Becker's band:
the bystander report of 2026-10-26).

THE ART: a dark host shape (the under-fill's ring) holding a white field that
outlines letters -- MFab's keyline round M-FAB. Read on the stage-4 regions,
before any of the recipe's switches acts (`sew_enclosed_white` is the first,
in `finish_generation`), with the same pass `border_from_outline` already runs
(`art_outline.find_art_outlines`): some art outline is

- background the art encloses (`enclosed_background`: what
  `sew_enclosed_white` sews -- the white field),
- round at least one text-tagged body that is not background (a letter), and
- held by a host: a shape that is not background, at least
  `silhouette_underfill.RING_MIN_AREA_MM2`, whose outline covers
  `silhouette_underfill.INSIDE_MIN` of the field.

Read on the 22 paired jobs' stage-4 regions it holds on MFab hat and LC and
nowhere else: Becker's outline is its black band (not background), To a T's
and Drone's hold no letter. No new constant. A pre-pass only when a candidate
exists: a design with no enclosed background holding a hole pays nothing.

THE RECIPE (`RECIPE`): `silhouette_underfill`, `sew_enclosed_white`,
`enclosed_white_keyline`, `silhouette_underfill_panels`, `outline_loop_mitre`
and `silhouette_underfill_rim` -- the five switches of #1094's flip sheet plus
the under-fill's rim (#1096) -- and, from Kent's ruling of 2026-10-26 on the
wave-3 flip sheet ("MFab extras into the gate"), `keyline_fold_slivers` and
`skip_covered_shapes` (#1102) and `cfg.extra["absorb_fragments"]` (#1100,
`RECIPE_EXTRA`), all ON together. Every one acts in `plan_stitches`. Absorb
came in only with its panel fix (Kent 2026-10-26, "Hold all four": it bared
the counters under AND / WELDING / LLC until the join kept the riders'
panel; `docs/gate-mfab-extras-2026-10-26.md`). And `keyline_loop_chain`
(#1125): the white loops chained as the pro chains them, white-loop cuts
11 -> 5 (Kent 2026-10-27, "MFab gate only (Recommended)": only MFab-type art
changes; `docs/keyline-loop-chain-2026-10-26.md`).

The verdict is carried on the result (`PipelineResult.white_keyline_art`) and
folded into the config at each later entry point (`apply`), as stage 1.25's
photo verdict is (`photo_signals.apply_detection`). Two reads come too early
for it and keep the caller's config: `build_generation`'s colour cap ranking
(an enclosed area competing for a cone) and nothing else.
"""
from __future__ import annotations

from dataclasses import replace

from shapely.geometry import Polygon

RECIPE = ("silhouette_underfill", "sew_enclosed_white", "enclosed_white_keyline",
          "silhouette_underfill_panels", "outline_loop_mitre", "silhouette_underfill_rim",
          "keyline_fold_slivers", "skip_covered_shapes", "keyline_loop_chain")
#: the recipe's `cfg.extra` keys (Kent 2026-10-26: "MFab extras into the gate")
RECIPE_EXTRA = ("absorb_fragments",)


def detect(regions, cfg) -> bool:
    """`cfg.white_keyline_art_recipe`: is this white-keyline art (module docstring)?
    False with the flag off, or without `border_from_outline` (the loops the
    recipe sews are that pass's)."""
    if not getattr(cfg, "white_keyline_art_recipe", False) or not cfg.border_from_outline:
        return False
    if getattr(cfg, "white_keyline_art_every_job", False):
        return True                 # Kent 2026-10-27: "Every job (Recommended)"
    if not any(r.meta.get("enclosed_background") and r.polygon is not None
               and r.polygon.geom_type == "Polygon" and r.polygon.interiors for r in regions):
        return False
    from .art_outline import find_art_outlines
    from .silhouette_underfill import INSIDE_MIN, RING_MIN_AREA_MM2
    by_id = {r.shape_id: r for r in regions}
    hosts = [r for r in regions
             if not r.meta.get("enclosed_background") and r.polygon is not None
             and r.polygon.geom_type == "Polygon" and r.polygon.area >= RING_MIN_AREA_MM2]
    for oid, bodies in find_art_outlines(regions, cfg).items():
        field = by_id[oid]
        if not field.meta.get("enclosed_background"):
            continue
        if not any(by_id[b].meta.get("text_cluster_id") is not None
                   and not by_id[b].meta.get("enclosed_background") for b, _hole in bodies):
            continue
        area = field.polygon.area
        if any(Polygon(h.polygon.exterior).intersection(field.polygon).area >= INSIDE_MIN * area
               for h in hosts if h is not field):
            return True
    return False


def apply(cfg, verdict: bool):
    """Fold a verdict into a config: the recipe's switches ON when the flag is
    on and the art is white-keyline art; otherwise the same config object."""
    if not (verdict and getattr(cfg, "white_keyline_art_recipe", False)):
        return cfg
    extra = {**(cfg.extra or {}), **{k: True for k in RECIPE_EXTRA}}
    return replace(cfg, **{k: True for k in RECIPE if hasattr(cfg, k)}, extra=extra)
