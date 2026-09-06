#!/usr/bin/env python
"""Which cones does a design sew TWICE, and what would folding each one cost?

Not the same question as `tools/cone_merge_survey.py`. That one asks whether
two DIFFERENT cones are close enough to fold into one, and trades colour
fidelity to do it. This asks about the free case: the SAME cone number sewn in
more than one block, which costs the operator a machine stop and a manual
re-thread for no colour gain at all.

`cfg.merge_duplicate_cones` (default ON since 2026-09-01) folds these at
quantize time, and `COLOR_STOPS_HEAVY`'s `repeated_cones` field reports the
survivors. MASTER_SCOPE defect 16 records that survivors remain and names two
routes the fold cannot see; the blend-band half is still open and "owed its own
measured work". This is that measurement. **It changes nothing and recommends
nothing; it counts, and it prices.**

## What it reports, and why each column

  * **gap** — how many blocks lie between the two occurrences. This is the
    price. A gap of 1 is a small reorder; a gap of 8 means moving regions past
    everything in between, and stage 5 built `covered_by` from the un-merged
    order (the distinction `cone_merge_survey.py` had to draw between a
    within-layer fold and an across-layer one). A gap says how expensive the
    fix is BEFORE anyone writes it.
  * **route** — where the duplicate came from, read off the shapes each block
    actually sews:
      - `band`   every shape carries a `-blend`/`-shade` suffix, so the block
                 is a gradient band built in stage 6, long after the
                 quantize-time fold runs;
      - `resnap` some region in the block carries stage 4's
                 `thread_resnapped_de00` stamp, i.e. the cone was INVENTED
                 after quantize and no layer declares it;
      - `plain`  neither, on EITHER block — the fold's own territory, and a
                 survivor here would be a defect in the fold rather than a gap
                 in its reach.

    A duplicate can be both `band` and `resnap`; both are printed. `plain` is
    the residual and never appears beside another route: a duplicate with one
    re-snapped block and one ordinary one was caused by the re-snap.

## What it found, 2026-09-06 — 26 fixtures x 2 garments

Reproduces MASTER_SCOPE's count exactly, and prices it:

    fixture                     garment      cone  blocks   gap  route
    photo/region_blobs.png      left_chest   0182  [1, 12]   11  band
    photo/region_blobs.png      hat_front    0182  [1, 12]   11  band
    photo/screenshot_phone_ui   left_chest   3971  [5, 12]    7  resnap
    photo/screenshot_phone_ui   hat_front    3971  [5, 12]    7  resnap

**4 of 52 combos, and NOT ONE of the four is adjacent** — min gap 7, max 11.
That corrects the framing the defect is recorded under. "Each merge is FREE
(the cone is already loaded)" is true of THREAD cost and false of SEQUENCING
cost: folding block 12 into block 1 on `region_blobs` moves a gradient band
past ELEVEN intervening blocks, and stage 5 built `covered_by` from the
un-merged order. That is `cone_merge_survey.py`'s across-layer case, which it
already measured as the expensive kind.

**Both halves of the recorded split are confirmed here independently**, by
re-running with the flag rather than trusting the earlier session:

    screenshot_phone_ui   bind_resnap_all_classes=False   17 blocks, duplicate
    screenshot_phone_ui   bind_resnap_all_classes=True    11 blocks, NONE
    region_blobs          False                           16 blocks, duplicate
    region_blobs          True                            16 blocks, duplicate

So the `resnap` half is closed by a flag that already exists (and buys
`screenshot` six blocks on its own), and the open `band` half is **ONE design,
`region_blobs`, which is a GENERATED fixture** — `tools/make_photo_region_fixture.py`
renders it as "three overlapping Gaussian-falloff color blobs". No client
artwork in the corpus produces it.

**That is the case against building the band fold**, stated with numbers
rather than as a preference: one synthetic design, an 11-block reorder through
`covered_by`, against a flag already built that closes the other half. Re-run
this after any sequencing change; if a real design ever shows up here, the
arithmetic changes.

    .venv/bin/python -m tools.cone_revisits
"""
from __future__ import annotations

import re
import sys

from digitizer_core import preflight as pf
from digitizer_core.config import PipelineConfig
from digitizer_core.pipeline import digitize

# stage 6's derived-shape suffixes. `preflight._SHADE_SHAPE_ID_RE` is the same
# rule for the same reason; kept separate here so this tool measures the ids
# rather than importing the thing it is auditing.
_DERIVED = re.compile(r"-(?:blend|shade)\d+$")


def _block_routes(plan, result) -> list[set[str]]:
    """-> one route set per block."""
    resnapped = set()
    if result is not None:
        for r in getattr(result, "regions", ()) or ():
            if "thread_resnapped_de00" in (getattr(r, "meta", None) or {}):
                resnapped.add(r.shape_id)
    out = []
    for b in plan.blocks:
        sids = {run.shape_id for run in b.runs if run.shape_id}
        tags = set()
        if sids and all(_DERIVED.search(s) for s in sids):
            tags.add("band")
        # A derived id is "<region>-blend2"; the owning region is the stem.
        stems = {_DERIVED.sub("", s) for s in sids}
        if stems & resnapped:
            tags.add("resnap")
        out.append(tags)
    return out


def revisits(plan, result) -> list[dict]:
    """Cones sewn in more than one block, with the price of folding each."""
    where: dict[str, list[int]] = {}
    for i, entry in enumerate(plan.palette):
        where.setdefault(str(entry["number"]), []).append(i)
    routes = _block_routes(plan, result)
    out = []
    for num, idx in sorted(where.items()):
        if len(idx) < 2:
            continue
        tags = set()
        for i in idx:
            if i < len(routes):
                tags |= routes[i]
        # `plain` is the RESIDUAL for the duplicate, not a label on one block.
        # A duplicate with one re-snapped block and one ordinary one was
        # caused by the re-snap; calling it "plain,resnap" would send a reader
        # to `merge_duplicate_cones` looking for a defect that is not there,
        # because `plain` means "the fold's own territory". A test pins this.
        if not tags:
            tags.add("plain")
        out.append({"cone": num, "blocks": idx, "gap": idx[-1] - idx[0],
                    "route": ",".join(sorted(tags))})
    return out


def main(argv: list[str]) -> int:
    from tests.conftest import TESTDATA
    from tools.corpus_scorecard import FIXTURES, MATRIX

    hdr = (f"{'fixture':40} {'garment':11} {'cone':>6} {'blocks':>14} "
           f"{'gap':>4}  route")
    print(hdr)
    print("-" * len(hdr))
    combos = hits = 0
    by_route: dict[str, int] = {}
    gaps: list[int] = []
    for fx in FIXTURES:
        for m in MATRIX:
            art = TESTDATA / fx
            cfg = PipelineConfig(**m)
            try:
                result, plan = digitize(art, cfg)
            except Exception as exc:                      # pragma: no cover
                print(f"SKIP {fx} {m['garment_id']}: {exc}")
                continue
            combos += 1
            rows = revisits(plan, result)
            if rows:
                hits += 1
            for r in rows:
                by_route[r["route"]] = by_route.get(r["route"], 0) + 1
                gaps.append(r["gap"])
                print(f"{fx:40} {m['garment_id']:11} {r['cone']:>6} "
                      f"{str(r['blocks']):>14} {r['gap']:4}  {r['route']}")
                sys.stdout.flush()

    print(f"\n{hits} of {combos} design/garment combos sew a cone twice "
          f"({sum(by_route.values())} duplicate cones in all)")
    for route, n in sorted(by_route.items(), key=lambda kv: -kv[1]):
        print(f"  {route:16} {n}")
    if gaps:
        gaps.sort()
        print(f"  gap between the two blocks: min {gaps[0]}, "
              f"median {gaps[len(gaps) // 2]}, max {gaps[-1]}")
        free = sum(1 for g in gaps if g == 1)
        print(f"  adjacent (gap 1, the cheap fold): {free} of {len(gaps)}")
    return 0


if __name__ == "__main__":                                # pragma: no cover
    raise SystemExit(main(sys.argv[1:]))
