#!/usr/bin/env python
"""Which palette is wrong when `PALETTE_THREAD_MISMATCH` fires — and which is not.

`PALETTE_THREAD_MISMATCH` (warnings_codes.py) fires when a region sews in a
thread its LAYER's palette entry does not name. `rehome_resnapped_regions`
closed most of it on 2026-08-31 by moving a re-snapped region to the layer
DECLARING its new cone.

**What survives is no longer a re-snap at all, and this line used to say it
was.** Re-measured 2026-09-12 after the 2026-09-10 colour-bundle flip: every
diverged region on the corpus carries `color_cap_merged_from`, not
`thread_resnapped_de00` — `enforce_color_cap` is the producer, it runs AFTER
the rehome, and the rehome could not repair it even in the other order
because it keys on the re-snap stamp. `repro_gradient_white_icon`, the
rehome's own live-proof fixture, now diverges on nothing.

## Read the contract before the numbers, because there are TWO palettes

    result.palette   per LAYER.  What the REVIEW SCREEN edits against
                     (service `review.palette`). This is the one that goes
                     wrong.
    plan.palette     per BLOCK, in sew order. `palette[i]` describes
                     `blocks[i]`; the service ships it as `stats.blocks` and
                     the download's own thread list is `design.colors`.
                     **This is what the operator threads from, and it is
                     right by construction** — `StitchPlan.palette`'s own
                     comment says reading the LAYER list positionally against
                     blocks is what shipped `golf_hat`'s black block labelled
                     "0020 Tangerine" until 2026-08-14.

**This tool overstated its finding TWICE before it said anything true**, and
both are recorded rather than quietly deleted, because the whole subject here
is an instrument reporting more than it knows.

1. **It compared `result.palette` against what sews and printed
   "RACK-WRONG" — the operator loads a cone that never runs.** That is the
   REVIEW list, not the rack. The operator threads from `plan.palette`, and
   the verdict was wrong on all six fixtures. The "by construction" claim is
   now CHECKED per fixture (`_operator_list_is_consistent`) so it cannot rot
   back into an assumption.
2. **It then reported "threads that sew but are absent from the review
   list", which is BY DESIGN and not this defect.** A blend or tonal region
   sews several shades inside one layer (`shade_thread_index` blocks); the
   layer list names the layer, and the shades ride in the service's
   `stats.blocks` — `StitchPlan.palette` and `_stats_payload` both say so.
   `gradient_ramp_linear` made it obvious: **one** mismatched shape beside
   **four** "missing" threads. A layer whose regions all went unstitched
   (`SHAPES_LEFT_UNSEWN`, 10 of 26 fixtures) confounds the other direction
   the same way.

**What is left is not confounded.** `mismatched` is computed over REGIONS and
each region's own `thread_number`, so blend bands never enter it. The one
extra question worth asking of it — and the one the payload cannot answer on
its own — is whether the thread a mismatched shape ACTUALLY sews appears
anywhere in the review list, or nowhere in it.

## The PHANTOM column (added 2026-09-12) — the direction that costs money

`PALETTE_THREAD_MISMATCH` only sees a layer naming a DIFFERENT cone from its
regions. **It is structurally blind to a layer naming a cone no block sews at
all** — a layer nobody is left in produces no mismatched region — and that is
the direction a new consumer would turn into a spool bought for nothing.
Measured 2026-09-12: **9 of 26 fixtures, 14 cone entries, and 6 of the 9 never
fire the warning.** So the tool now reports every fixture whose two lists
differ, not only the ones that fire, and splits the phantom in two, because
only one half is a defect:

    PHANTOM (mislabelled)   no region in that layer carries the cone. WRONG,
                            and what `cfg.layer_palette_from_regions` fixes.
    phantom (unsewn)        the layer really carries it; nothing sews it.
                            LEGITIMATE — an unstitched layer (the
                            enclosed-background default) and a blend layer
                            whose blocks are `shade_thread_index` shades are
                            both real review rows that keep real colours.

Which is why the invariant is `palette[i] ∈ {the layer's own regions' cones}`
and never `palette ⊆ block cones`: the blend tier breaks the second by design.

## What is actually at stake

The review screen labels a layer with a cone the layer does not sew, and a
sewn thread can be absent from that list entirely — so a user reordering or
recolouring by those labels is acting on a wrong one. A labelling defect on
the editing surface, not a wasted cone at the machine.

    .venv/bin/python -m tools.palette_mismatch [--on] [--max-colors N]

`--on` runs `cfg.layer_palette_from_regions` (default OFF), so a before/after
corpus read is one flag apart. `--max-colors` because every published number
for this defect was taken at the engine default of 12 while the Studio's
slider ships **6**, and the colour cap is the producer — 76 diverged regions
on two real-customer fixtures at 6 against 24 corpus-wide at 12.
"""
from __future__ import annotations

import sys

from digitizer_core.config import PipelineConfig
from digitizer_core.pipeline import digitize


def _operator_list_is_consistent(plan) -> bool:
    """`plan.palette[i]` must name `plan.blocks[i]`'s own thread.

    The claim that the operator's list cannot be wrong rests entirely on
    this, so it is asserted per fixture rather than believed.
    """
    return (len(plan.palette) == len(plan.blocks)
            and all(str(c.get("number")) == str(b.thread_number)
                    for c, b in zip(plan.palette, plan.blocks)))


def _phantoms(result, plan) -> tuple[list[tuple[int, str, list[str]]],
                                     list[tuple[int, str]]]:
    """Cones the LAYER list names that no block sews, split by which kind.

    The warning cannot see either one — a layer nobody is left in produces
    no mismatched region — and they are not the same finding:

    `mislabelled`  no region in that layer carries the cone at all. The
                   label is simply WRONG, and this is the population
                   `cfg.layer_palette_from_regions` drives to zero.
                   -> [(layer, listed cone, what its regions really sew)]
    `unsewn`       the layer really does carry that cone; nothing sews it.
                   LEGITIMATE and deliberately left alone — an unstitched
                   layer (`SHAPES_LEFT_UNSEWN`, the enclosed-background
                   default) and a blend layer whose blocks are
                   `shade_thread_index` shades of its base cone are both
                   real review rows that must keep a real colour.
                   -> [(layer, cone)]
    """
    block_cones = {str(getattr(b, "thread_number", "")) for b in plan.blocks}
    carried: dict[int, set[str]] = {}
    for r in result.regions:
        layer = r.meta.get("layer")
        if layer is not None:
            carried.setdefault(int(layer), set()).add(str(r.thread_number))

    mislabelled, unsewn = [], []
    for i, cone in enumerate(result.palette or []):
        number = str(cone.get("number"))
        mine = carried.get(i, set())
        if number not in mine:
            mislabelled.append((i, number, sorted(mine)))
        elif number not in block_cones:
            unsewn.append((i, number))
    return mislabelled, unsewn


def main(argv: list[str]) -> int:
    from tests.conftest import TESTDATA
    from tools.corpus_scorecard import FIXTURES

    # `--max-colors N` because every published number for this defect was
    # taken at the engine default of 12 while the Studio's slider ships 6,
    # and the cap is the producer: 76 diverged regions on two real-customer
    # fixtures at 6 against 24 on the whole corpus at 12 (2026-09-12).
    # `--on` runs the fix (`cfg.layer_palette_from_regions`, default OFF) so
    # a corpus read before and after is one flag apart.
    on = "--on" in argv
    max_colors = 12
    if "--max-colors" in argv:
        max_colors = int(argv[argv.index("--max-colors") + 1])

    fired = 0
    operator_ok = 0
    rows: list[tuple] = []
    for fx in FIXTURES:
        cfg = PipelineConfig(target_width_mm=80.0, garment_id="left_chest",
                             max_colors=max_colors,
                             layer_palette_from_regions=on)
        try:
            result, plan = digitize(TESTDATA / fx, cfg)
        except Exception as exc:                          # pragma: no cover
            print(f"SKIP {fx}: {exc}")
            continue
        operator_ok += 1 if _operator_list_is_consistent(plan) else 0

        hit = next((w for w in (getattr(plan, "warnings", None) or [])
                    if w.get("code") == "PALETTE_THREAD_MISMATCH"), None)
        mislabelled, unsewn = _phantoms(result, plan)
        # The plain set difference §1.1 of the doc published (9 fixtures, 14
        # cone entries at max_colors=12), kept beside the per-layer split so
        # the instrument reproduces its own paper number. It differs from
        # `mislabelled + unsewn` two ways, both on purpose: two layers can
        # list the SAME phantom cone (one entry, two rows), and a
        # mislabelled layer's cone can be sewn by some OTHER layer's block
        # (a row, no phantom entry).
        set_phantom = sorted({str(c.get("number")) for c in (result.palette or [])}
                             - {str(b.thread_number) for b in plan.blocks})
        if hit is None and not mislabelled and not unsewn:
            continue
        fired += 1 if hit is not None else 0

        review = {str(c.get("number")) for c in (result.palette or [])}
        listed = sorted(str(x) for x in ((hit or {}).get("listed") or []))
        actual = sorted(str(x) for x in ((hit or {}).get("actual") or []))
        rows.append((fx, (hit or {}).get("count", 0),
                     sorted((hit or {}).get("layers") or []),
                     listed, actual, sorted(set(actual) - review),
                     mislabelled, unsewn, set_phantom))

    orphans = 0
    n_mislabelled = sum(1 for r in rows if r[6])
    n_rows_mislabelled = sum(len(r[6]) for r in rows)
    n_phantom = sum(1 for r in rows if r[8])
    n_cones = sum(len(r[8]) for r in rows)
    silent = sum(1 for r in rows if r[8] and not r[1])
    print(f"max_colors={max_colors}  layer_palette_from_regions={on}")
    print(f"{'fixture':40} {'shapes':>6}  layers")
    print("-" * 88)
    for fx, n, layers, listed, actual, off_list, mis, uns, ph in rows:
        print(f"{fx:40} {n:6}  {layers}" if n else f"{fx:40} {'—':>6}")
        if n:
            print(f"{'':40}   the layer lists {listed}, the shapes sew {actual}")
        if off_list:
            orphans += 1
            print(f"{'':40}   and {off_list} is on NO review layer at all")
        for layer, cone, really in mis:
            print(f"{'':40}   PHANTOM (mislabelled): layer {layer} lists "
                  f"{cone}, its regions sew {really or '[]'}")
        for layer, cone in uns:
            print(f"{'':40}   phantom (unsewn, legitimate): layer {layer} "
                  f"lists {cone}; its own regions carry it, no block sews it")
        if ph:
            print(f"{'':40}   set(review) - set(blocks) = {ph}")

    print(f"\n{fired} of {len(FIXTURES)} fixtures fire PALETTE_THREAD_MISMATCH, "
          f"and on {orphans} of them the thread those shapes sew is on NO "
          f"review layer at all — so the review screen cannot show it, not "
          f"merely show it in the wrong place.")
    print(f"PHANTOM CONES — set(review) - set(blocks), a layer naming a cone "
          f"no block sews, which the warning is structurally blind to: "
          f"{n_phantom} of {len(FIXTURES)} fixtures, {n_cones} cone entries, "
          f"{silent} of those fixtures silent (no warning at all).")
    print(f"MISLABELLED LAYERS — palette[i] names a cone NO region in layer i "
          f"carries: {n_rows_mislabelled} layers on {n_mislabelled} of "
          f"{len(FIXTURES)} fixtures. That is defect 30's real population and "
          f"what `--on` drives to zero; every other phantom is legitimate "
          f"(an unstitched layer, or a blend layer's base cone) and stays.")
    print(f"The OPERATOR list (plan.palette against plan.blocks) is consistent "
          f"on {operator_ok} of {len(FIXTURES)} — checked, not assumed. "
          f"Everything above is the REVIEW screen's per-layer list, which is "
          f"what a user reorders and recolours by.")
    return 0


if __name__ == "__main__":                                # pragma: no cover
    raise SystemExit(main(sys.argv[1:]))
