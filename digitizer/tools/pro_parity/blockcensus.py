#!/usr/bin/env python
"""Block/element census and grouping join — the element-level instrument.

Option A of `docs/superpowers/plans/2026-08-23-region-identification.md`:
the current scorecard grades pixels (coverage, direction, type) and cannot
see ELEMENT STRUCTURE at all, so the block-layer work (option B) and the
blocked items (option F) are unmeasurable. This tool measures the three
structural properties the craft actually exercises:

  1. ELEMENT COUNT AND GROUPING — how many separately-sewn things each side
     produces, and whether a grouping of OUR regions can reproduce the pro's
     colour-block structure (`grouping_join`). The join is best-case by
     construction: each of our regions is assigned to the pro block its own
     visible pixels sit on most, so the number reads "if a block layer
     grouped today's regions optimally, how much of the pro's visible block
     allocation would it reproduce" — an upper bound on option B's win with
     regions held fixed, not a measure of any existing grouping code.
  2. LAYERING ORDER — background->foreground. Corpus law 32 (round-3 doc):
     77% of overlapping ordered block pairs put the smaller block later.
     That 77% was measured on the 40-file corpus (36 gitignored
     `scratch_corpus` DSTs + commissioned files) with a script that predates
     this tool; `layering_stats` is this repo's maintained re-implementation
     and is run on whatever corpus it is pointed at — the 23-design zip
     number it prints is its own measurement, compared against the law as a
     trend, not an identity.
  3. THREAD RETURNS — 55% of the pro's colour stops are returns to a thread
     already used (n=14 palette designs: 92 blocks over 41 distinct
     threads). `census_structure` computes ours the same way as the pro's so
     the gap is REPORTED — the headline finding option B addresses. Nuance
     measured 2026-08-24: the FLAT lane emits one block per thread and
     cannot express a return, but the tonal lane's shade emission already
     repeats threads — hotel_fremont sews ours [0, 1, 2, 2, 1]: one
     ADJACENT same-thread stop (a machine-pointless stop, the shade-defect
     class the region-identification doc flags) and one non-adjacent
     reuse. Neither is a block layer's chosen background->detail->
     background order (the pro's reads [0, 1, 2, 0, 1, 0, 2, 1, 2, 1, 0]),
     so a nonzero ours return count is not yet evidence of option B —
     `thread_seq` shows which kind each repeat is.

READ EVERY NUMBER WITH THE CEILING. This instrument measures conformance to
ONE digitizer's choices — the known phase-1 trap. The scorecard-scale
pro-vs-pro ceiling is 75.2-83.6 points (`selfconsistency.py`: the two
genuinely independent same-logo pairs), i.e. a professional agrees with
another professional rendition well short of 100. `ceiling` mode measures
the same floor in THIS tool's own currency by running `grouping_join` on
the pro's own same-logo file pairs — quote fixture kappas against those,
never against 1.0. Measured 2026-08-24: independent same-logo pairs join at
kappa 0.83-0.89; the same-job-saved-twice pairs self-test at ~1.0; and
becker_hat_vs_chest_small — same stitch geometry, re-blocked — joins at
0.65, i.e. one pro's own two saves of ONE job already disagree on block
structure. Run `ceiling` for live numbers.

Chance correction (hard gate 4): `grouping_join` reports the raw agreement,
the label-mix chance floor (sum over blocks of p_pro * p_grouped, the kappa
baseline `scorecard.type_chance` uses), and the corrected kappa. Unlike
`scorecard.chance_correct` the kappa here is NOT clamped at zero — this is
a diagnostic, and "worse than chance" is a finding, not a score to protect.

WHAT THIS INSTRUMENT CANNOT SEE — read before trusting any row:

  * The pro's true object list. The vendor's editable `.EMB` sources are
    encrypted (probe closed); everything here is decoded from the delivered
    PES/DST stitch stream, which records needle penetrations, not objects.
  * Elements bridged by travel. Needle-down travel inside a run joins what
    the digitizer drew as separate objects, so `count_components` UNDERcounts
    elements per block; it measures "pieces after the pro's chaining", the
    sewing-relevant unit. (Same caveat as the census this replaces.)
  * Thread returns on DST-only designs. DST carries no palette;
    `prep_all.decode` substitutes a synthetic grey ramp, so distinct-thread
    and return counts would be format artifacts. Such designs report
    `thread_source: "synthetic"` and None for thread fields, and are
    excluded from every thread aggregate. (The 9 DST designs still count
    blocks, paths, elements and layering — those need no colour.)
  * Thread on fabric. Everything here is geometry; pull, loft and coverage
    on cloth are gate-1 territory and no number below claims them.
  * Anything registration hides. The join registers ours onto the pro by
    TRANSLATION ONLY (`scorecard.register`); a size or aspect mismatch is
    not corrected, it just scores low — which is why every join row carries
    `reg_iou`, and a low one means "read this row as misregistration, not
    grouping failure".

INPUT PROVENANCE — the classes are load-bearing (see MASTER_SCOPE
"Corrections", PR #222): `digitizer/testdata/reference/becker_*.jpg` are NOT
artwork; they are the vendor's two-panel preview renders of the pro's own
stitches, md5-identical to files in the delivery zip. A run on them
digitizes two half-scale copies of an input derived from the pro's answer —
the same provenance class whose recon-lane cousin flatters the engine by
+11.3 points. They are tagged `pro-derived-render`, SKIPPED by default
(`--include-derived` runs them, labeled), and never enter an aggregate.
Genuine committed artwork: `becker_marine_logo.png`, `logo_script_tires.png`,
plus the three photo-dir logos with pro counterparts in the zip. Also:
`photo/logo_drone_thermal_badge.png` is byte-identical to
`photo/drone_render.png` (the scorecard's FIXTURES carries both, so its
aggregates double-count one image); this tool includes the badge copy once
and verifies the duplication at runtime rather than trusting this comment.

Deliberately a REPORTING tool, not a CI gate — same posture as
`tools/corpus_scorecard.py`, same reason: thresholds invented at a desk in
phase 1 have had to be walked back before.

Usage (from `digitizer/`, venv python):

    python -m tools.pro_parity.blockcensus census   # pro corpus structure
    python -m tools.pro_parity.blockcensus join     # ours-vs-pro grouping join
    python -m tools.pro_parity.blockcensus ceiling  # pro-vs-pro join floor
    ... [--json out.json] [--only SLUG] [--include-derived] [--forced-class C]

Pro files resolve via PRO_PARITY_ROOT; when that is unset or missing, the
tracked `Embroidery Files.zip` at the repo root is extracted to a temp dir
OUTSIDE the working tree (this repo is public; loose customer files must
never land in it) and used for the run.

Memory: `join` carries the pipeline's own stage-2 peak (the multi-GB class
MASTER_SCOPE tracks; a full sequential run also accumulates allocator
fragmentation across fixtures — measured 2026-08-24: one all-fixtures
process was cgroup-OOM-killed at 13.3 GB on golden_tee while the same
fixtures pass run one per process). On a shared box run fixtures
individually: `--only NAME --json NAME.json`.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
import tempfile
import zipfile
from collections import Counter
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
DIGITIZER = HERE.parents[1]
sys.path.insert(0, str(DIGITIZER))
sys.path.insert(0, str(HERE))

import prep_all  # noqa: E402  (decode, DESIGNS, find_file, GREYS)
import scorecard  # noqa: E402  (register, bounds, CHANCE_DEGENERATE)

# --- raster settings, carried over from the 2026-08-23 census these numbers
# were first measured with (pro_structure.py, session scratchpad) so the
# committed tool reproduces that census rather than founding a new one -----
PXMM = 5.0            # px per mm for block/element rasters
STROKE_MM = 0.4       # painted thread width
CLOSE_MM = 0.8        # morphological close that fuses rows into one element
MIN_COMP_MM2 = 1.0    # ignore ink specks below this when counting elements

# A block pair counts as OVERLAPPING for layering when the raw painted
# footprints share at least this much area. The round-3 law-32 script lived
# outside this repo and its floor is unrecoverable, so this is this tool's
# own operationalization — pinned here so the number is at least stable.
LAYER_MIN_OVERLAP_MM2 = 2.0

_SYNTH = set(prep_all.GREYS)


# ======================================================================
# pure census math (unit-tested in tests/test_blockcensus.py)
# ======================================================================

def palette_is_synthetic(threads, n_blocks) -> bool:
    """True when the palette is `prep_all.decode`'s fabricated grey ramp
    (DST input), i.e. thread identity is NOT real. Heuristic: every used
    entry is one of the six GREYS — a real palette that coincides with all
    of them is theoretically possible and would misread, but no PES in the
    corpus does, and DST can never carry a real palette at all."""
    used = threads[:n_blocks] if n_blocks else threads
    return bool(used) and all(tuple(t) in _SYNTH for t in used)


def census_structure(blocks, breaks, threads, synthetic: bool | None = None) -> dict:
    """Structural census of one decoded design (`prep_all.decode` output).

    Thread fields (`threads`, `thread_returns`, `return_share`) are None
    when the palette is synthetic — a DST cannot say which stops reuse a
    thread, and pretending the grey ramp is a palette biases returns DOWN
    (any design with <= 6 blocks would read zero returns by construction).

    `return_share` is returns/blocks — "55% of colour stops are returns"
    counts every block as a stop, matching the 2026-08-23 census the 55%
    headline came from (92 blocks over 41 threads -> 51/92 = 55.4%).
    """
    if synthetic is None:
        synthetic = palette_is_synthetic(threads, len(blocks))
    n_st = sum(len(r) for b in blocks for r in b)
    kinds = Counter({"start": 0, "trim": 0, "color": 0, "jump": 0, "hop": 0})
    for bb in breaks:
        kinds.update(bb)
    uniq: list = []
    for t in threads[: len(blocks)]:
        if t not in uniq:
            uniq.append(t)
    returns = max(0, len(blocks) - len(uniq))
    # The RETURN PATTERN, not just the count: [0, 1, 0, 1, 0] is a pro
    # layering base->detail->base; [.., 2, 2, ..] is a split/shade artifact.
    # Option B's sequencing needs the pattern, so the census keeps it.
    seq = ([uniq.index(t) for t in threads[: len(blocks)]]
           if not synthetic else None)
    return {
        "stitches": n_st,
        "blocks": len(blocks),
        "threads": None if synthetic else len(uniq),
        "thread_seq": seq,
        "thread_returns": None if synthetic else returns,
        "return_share": (None if synthetic or not blocks
                         else round(returns / len(blocks), 3)),
        "thread_source": "synthetic" if synthetic else "palette",
        "paths_total": sum(len(bb) for bb in breaks),
        "paths_cut": kinds["start"] + kinds["trim"] + kinds["color"],
        "paths_float": kinds["jump"] + kinds["hop"],
        "break_kinds": dict(kinds),
        "trims_per_1k": round(1000.0 * kinds["trim"] / max(1, n_st), 2),
    }


def runs_to_segs(blocks):
    """Decoded runs -> `scorecard` segment tuples, so this tool's
    registration is the shipped scorecard's, not a parallel one."""
    segs = []
    for bi, runs in enumerate(blocks):
        for run in runs:
            for a, b in zip(run, run[1:]):
                segs.append((a[0], a[1], b[0], b[1], math.dist(a, b), bi, False))
    return segs


def _frame(bb, pxmm):
    x0, y0, x1, y1 = bb
    w = max(2, int(math.ceil((x1 - x0) * pxmm)) + 8)
    h = max(2, int(math.ceil((y1 - y0) * pxmm)) + 8)
    return h, w


def paint_block_masks(blocks, bb, pxmm=PXMM, stroke_mm=STROKE_MM,
                      close_mm=CLOSE_MM, shift=(0.0, 0.0)):
    """Rasterize each block's thread coverage into the shared frame `bb`.

    -> (closed, raw, areas_mm2): `raw[i]` is the painted thread footprint
    (stroke width only), `closed[i]` adds the morphological close that fuses
    satin/fill rows into one solid element, `areas_mm2[i]` is the RAW
    footprint area — the census's "block coverage" (~414 mm2 median) and
    layering's size axis both use raw, so a sparse fill is not inflated by
    the close.
    """
    h, w = _frame(bb, pxmm)
    x0, y0 = bb[0], bb[1]
    t = max(1, int(round(stroke_mm * pxmm)))
    k = max(1, int(round(close_mm * pxmm)))
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * k + 1, 2 * k + 1))
    closed, raw, areas = [], [], []
    for runs in blocks:
        img = np.zeros((h, w), np.uint8)
        for run in runs:
            if len(run) < 2:
                continue
            pts = np.array([[(px + shift[0] - x0) * pxmm + 4,
                             (py + shift[1] - y0) * pxmm + 4]
                            for px, py in run], np.int32)
            cv2.polylines(img, [pts], False, 255, thickness=t)
        raw_m = img > 0
        closed.append(cv2.morphologyEx(img, cv2.MORPH_CLOSE, kernel) > 0)
        raw.append(raw_m)
        areas.append(float(raw_m.sum() / (pxmm * pxmm)))
    return closed, raw, areas


def paint_polygon_masks(polygons, bb, pxmm=PXMM, shift=(0.0, 0.0)):
    """Rasterize region polygons (shapely, mm, y-down — the frame stage 4
    emits and `export.write_dst` scales without flip or recenter) into the
    shared frame. Holes are subtracted; MultiPolygons paint every part."""
    h, w = _frame(bb, pxmm)
    x0, y0 = bb[0], bb[1]

    def ring(coords):
        return np.array([[(x + shift[0] - x0) * pxmm + 4,
                          (y + shift[1] - y0) * pxmm + 4]
                         for x, y in coords], np.int32)

    masks = []
    for poly in polygons:
        img = np.zeros((h, w), np.uint8)
        parts = poly.geoms if poly.geom_type == "MultiPolygon" else [poly]
        for p in parts:
            cv2.fillPoly(img, [ring(p.exterior.coords)], 255)
            for hole in p.interiors:
                cv2.fillPoly(img, [ring(hole.coords)], 0)
        masks.append(img > 0)
    return masks


def count_components(mask, pxmm=PXMM, min_mm2=MIN_COMP_MM2) -> int:
    """Contiguous coverage elements in one mask, specks below the floor
    dropped. Run on CLOSED block masks this is "elements per block" — the
    pro's median is exactly 1 (one block = one design element)."""
    n, _lab, stats, _c = cv2.connectedComponentsWithStats(
        mask.astype(np.uint8), connectivity=8)
    min_px = min_mm2 * pxmm * pxmm
    return sum(1 for i in range(1, n) if stats[i, cv2.CC_STAT_AREA] >= min_px)


def layering_stats(raw_masks, areas_mm2, pxmm=PXMM,
                   min_overlap_mm2=LAYER_MIN_OVERLAP_MM2) -> dict:
    """Law-32 check: of ordered block pairs whose RAW footprints overlap,
    how many sew the smaller block later (background->foreground)?

    Ties (equal raster area) count as NOT smaller-later — conservative.
    """
    n = len(raw_masks)
    pairs = smaller_later = 0
    for i in range(n):
        for j in range(i + 1, n):
            inter = float((raw_masks[i] & raw_masks[j]).sum() / (pxmm * pxmm))
            if inter < min_overlap_mm2:
                continue
            pairs += 1
            if areas_mm2[j] < areas_mm2[i]:
                smaller_later += 1
    return {
        "overlapping_pairs": pairs,
        "smaller_later": smaller_later,
        "smaller_later_share": round(smaller_later / pairs, 3) if pairs else None,
    }


def _kappa(raw, chance):
    """Chance-corrected agreement. Same degenerate pass-through as
    `scorecard.chance_correct`, but NOT clamped at zero: this is a
    diagnostic, and worse-than-chance must be visible, not floored."""
    if chance >= scorecard.CHANCE_DEGENERATE:
        return raw
    return (raw - chance) / (1.0 - chance)


def grouping_join(pro_masks, our_masks, pxmm=PXMM) -> dict:
    """Can a grouping of OUR regions reproduce the pro's block structure?

    Each our-region is assigned to the pro block whose VISIBLE surface it
    overlaps most (best-case grouping — no grouping code is being tested,
    only whether region GEOMETRY permits the pro's allocation). Both sides
    label the frame visible-surface style (painted in sew order, later wins
    — mirroring `scorecard.surface`; hidden under-layers are
    layering_stats' job), and agreement is scored on the area BOTH sides
    cover:

      raw    share of jointly-covered px where grouped label == pro label
      chance sum over blocks of p_pro * p_grouped (kappa baseline, the
             same construction as `scorecard.type_chance`)
      kappa  (raw - chance) / (1 - chance), unclamped

    Everything a merge cannot fix shows up structurally: `regions_per_block`
    (pro: ~1 element per block; ours: how many regions land on each),
    `blocks_unhit` (VISIBLE pro blocks no region maps to),
    `pro_blocks_hidden` (pro blocks the pro's own later blocks fully cover —
    their layering, not our miss), `regions_unassigned` (regions visible on
    no pro ink), `regions_hidden` (regions our own later regions fully
    cover), and the coverage asymmetries that bound how representative the
    joint domain is.
    """
    if not pro_masks or not our_masks:
        return {"error": "empty side", "pro_blocks": len(pro_masks),
                "regions": len(our_masks)}
    shape = pro_masks[0].shape
    P = np.full(shape, -1, np.int32)
    for i, m in enumerate(pro_masks):
        P[m] = i
    O = np.full(shape, -1, np.int32)
    for k, m in enumerate(our_masks):
        O[m] = k
    # Assign each region by majority vote of P over the pixels where the
    # region is ITSELF visible in our stacking (O == k) — not over its full
    # mask, and not over the full pro block masks. Both restrictions are
    # load-bearing, measured on first runs:
    #   * full PRO masks: the pro's base runs continuous UNDER later blocks,
    #     so a region on a foreground detail also sits on the hidden base and
    #     a tie dumps it on the background (46/55 hotel_fremont regions).
    #   * full OUR mask: a base block mostly covered by its own later blocks
    #     votes with pixels that are invisible in our own surface — the
    #     machine_hat_vs_lc SAME-FILE self-test then assigned both blocks to
    #     one label and scored kappa 0.0 where ~1.0 is the only right answer.
    assign: list[int | None] = []
    hidden = 0
    for k in range(len(our_masks)):
        vis_k = O == k
        if not vis_k.any():
            hidden += 1          # fully covered by our own later regions
            assign.append(None)
            continue
        under = P[vis_k]
        under = under[under >= 0]
        if under.size == 0:
            assign.append(None)  # visible, but on no pro ink
            continue
        assign.append(int(np.argmax(np.bincount(under, minlength=len(pro_masks)))))
    lut = np.array([-2 if a is None else a for a in assign], np.int32)
    G = np.where(O >= 0, lut[np.clip(O, 0, None)], -1).astype(np.int32)
    pro_cov = P >= 0
    our_cov = O >= 0
    D = pro_cov & our_cov
    nd = int(D.sum())
    px2 = pxmm * pxmm
    out = {
        "pro_blocks": len(pro_masks),
        "regions": len(our_masks),
        "regions_assigned": sum(1 for a in assign if a is not None),
        "regions_unassigned": sum(1 for a in assign if a is None) - hidden,
        "regions_hidden": hidden,
        "regions_per_block": {i: 0 for i in range(len(pro_masks))},
        "pro_area_mm2": round(float(pro_cov.sum()) / px2, 1),
        "our_area_mm2": round(float(our_cov.sum()) / px2, 1),
        "joint_area_mm2": round(nd / px2, 1),
        "our_outside_pro_share": round(
            float((our_cov & ~pro_cov).sum() / max(1, our_cov.sum())), 3),
        "pro_uncovered_share": round(
            float((pro_cov & ~our_cov).sum() / max(1, pro_cov.sum())), 3),
        "assign": assign,
    }
    for a in assign:
        if a is not None:
            out["regions_per_block"][a] += 1
    # A pro block the pro's OWN later blocks fully cover (a 3D-puff underpass,
    # a buried base) has no visible surface for any region to land on — that
    # is the pro's layering, not our miss, so it is listed apart.
    out["pro_blocks_hidden"] = [
        i for i in range(len(pro_masks)) if not (P == i).any()]
    out["blocks_unhit"] = [
        i for i, c in out["regions_per_block"].items()
        if c == 0 and i not in out["pro_blocks_hidden"]]
    if nd == 0:
        out.update({"raw_agreement": 0.0, "chance": 0.0, "kappa": 0.0,
                    "error": "no joint coverage"})
        return out
    p, g = P[D], G[D]
    raw = float((p == g).mean())
    labels = sorted(set(np.unique(p).tolist()) | set(np.unique(g).tolist()))
    chance = sum(float((p == c).mean()) * float((g == c).mean())
                 for c in labels if c >= 0)
    out.update({"raw_agreement": round(raw, 3), "chance": round(chance, 3),
                "kappa": round(_kappa(raw, chance), 3),
                # chance ~1 means the joint domain is effectively ONE label —
                # there was nothing to discriminate, so the kappa passthrough
                # is the raw number, not evidence of grouping skill. Read the
                # structural fields (blocks_unhit, pro_uncovered_share).
                "degenerate": bool(chance >= scorecard.CHANCE_DEGENERATE)})
    return out


def _median(vals):
    s = sorted(vals)
    n = len(s)
    if not n:
        return None
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2


# ======================================================================
# corpus acquisition
# ======================================================================

def corpus_root() -> Path:
    """PRO_PARITY_ROOT when it resolves; otherwise extract the tracked
    `Embroidery Files.zip` into a temp dir OUTSIDE the working tree (public
    repo — loose customer files must never land in a checkout)."""
    env = os.environ.get("PRO_PARITY_ROOT")
    if env and Path(env).is_dir():
        return Path(env)
    zip_path = DIGITIZER.parent / "Embroidery Files.zip"
    if not zip_path.exists():
        sys.exit("PRO_PARITY_ROOT is not set/resolvable and the tracked "
                 f"'Embroidery Files.zip' is missing at {zip_path}")
    dest = Path(tempfile.mkdtemp(prefix="embfiles_")) / "x"
    print(f"[corpus] extracting {zip_path.name} -> {dest}", flush=True)
    with zipfile.ZipFile(zip_path) as z:
        z.extractall(dest)
    root = dest / "Embroidery Files"
    return root if root.is_dir() else dest


def _decode_design(slug_rel):
    slug, rel = slug_rel
    p = prep_all.find_file(rel)
    if p is None:
        return slug, None, f"file not found: {rel}"
    try:
        return slug, prep_all.decode(p), None
    except Exception as e:  # noqa: BLE001 — a bad file is a row, not a crash
        return slug, None, f"{type(e).__name__}: {e}"


def census_design(blocks, breaks, threads, bounds, synthetic=None) -> dict:
    """Full per-design census: structure + elements + areas + layering."""
    row = census_structure(blocks, breaks, threads, synthetic=synthetic)
    closed, raw, areas = paint_block_masks(blocks, bounds)
    row["ink_components_per_block"] = [count_components(m) for m in closed]
    row["ink_components_total"] = sum(row["ink_components_per_block"])
    row["block_areas_mm2"] = [round(a, 1) for a in areas]
    row["layering"] = layering_stats(raw, areas)
    x0, y0, x1, y1 = bounds
    row["width_mm"] = round(x1 - x0, 1)
    row["height_mm"] = round(y1 - y0, 1)
    return row


# ======================================================================
# modes
# ======================================================================

def run_census(args) -> list[dict]:
    prep_all.ROOT = corpus_root()
    rows = []
    for slug, rel in prep_all.DESIGNS:
        if args.only and args.only != slug:
            continue
        slug, decoded, err = _decode_design((slug, rel))
        if err:
            rows.append({"slug": slug, "ok": False, "error": err})
            print(f"[{slug}] ERR {err}", flush=True)
            continue
        blocks, breaks, threads, bounds, _jumps, _trims = decoded
        row = {"slug": slug, "ok": True, **census_design(blocks, breaks, threads, bounds)}
        rows.append(row)
        lay = row["layering"]
        print(f"[{slug}] blocks={row['blocks']} threads={row['threads']} "
              f"returns={row['thread_returns']} cutpaths={row['paths_cut']} "
              f"elements={row['ink_components_total']} "
              f"layer={lay['smaller_later']}/{lay['overlapping_pairs']} "
              f"trims/1k={row['trims_per_1k']}", flush=True)

    ok = [r for r in rows if r.get("ok")]
    if len(ok) > 1:
        pal = [r for r in ok if r["thread_source"] == "palette"]
        blocks_pal = sum(r["blocks"] for r in pal)
        returns_pal = sum(r["thread_returns"] for r in pal)
        pairs = sum(r["layering"]["overlapping_pairs"] for r in ok)
        later = sum(r["layering"]["smaller_later"] for r in ok)
        comps = [c for r in ok for c in r["ink_components_per_block"]]
        areas = [a for r in ok for a in r["block_areas_mm2"]]
        print(f"\n=== corpus structure (n={len(ok)} designs, "
              f"{sum(r['blocks'] for r in ok)} blocks) ===")
        for k in ("blocks", "paths_cut", "ink_components_total", "trims_per_1k"):
            v = [r[k] for r in ok]
            print(f"  {k}: med {_median(v)}  min {min(v)}  max {max(v)}")
        print(f"  threads (palette designs only, n={len(pal)}): "
              f"med {_median([r['threads'] for r in pal])}")
        print(f"  elements per block: med {_median(comps)}  max {max(comps)}")
        print(f"  block area mm2: med {round(_median(areas), 1)}  "
              f"p10 {sorted(areas)[len(areas) // 10]}  min {min(areas)}")
        print(f"  thread returns (palette designs only): {returns_pal}/{blocks_pal} "
              f"blocks = {100.0 * returns_pal / max(1, blocks_pal):.1f}% of colour "
              f"stops reuse a loaded thread — EMB-Bot's flat lane emits one "
              f"block per thread (cannot express this); the tonal lane's "
              f"shade emission repeats threads, but not as chosen layering "
              f"(join mode's thread_seq shows the patterns)")
        print(f"  layering: {later}/{pairs} overlapping pairs put the smaller "
              f"block later = {100.0 * later / max(1, pairs):.1f}% "
              f"(law 32 measured 77% on the 40-file corpus; this is the "
              f"{len(ok)}-design zip under this tool's own overlap floor)")
    return rows


# Committed-artwork fixtures with a pro counterpart in the zip corpus.
# input_class is load-bearing (see module docstring):
#   artwork            what the customer actually sent, committed in testdata
#   pro-derived-render vendor preview of the pro's own stitches (two-panel);
#                      NEVER aggregated, skipped without --include-derived
# Deliberately absent: logo_gaulke_roofing.png (phone screenshot whose black
# bars dominate stage 1 without real_art.py's bar-crop — a run here would
# measure input trash, not grouping) and screenshot_phone_ui_golke.jpg (no
# verified pro counterpart).
TD = DIGITIZER / "testdata"
FIXTURES = [
    ("becker_marine", TD / "becker_marine_logo.png", "artwork", "becker_chest_small"),
    ("script_tires", TD / "logo_script_tires.png", "artwork", "tires_hat_3d"),
    ("hotel_fremont", TD / "photo/logo_hotel_fremont.webp", "artwork", "hotel_fremont_hat"),
    ("golden_tee", TD / "photo/logo_golden_tee.jpg", "artwork", "golf_hat"),
    ("drone_thermal", TD / "photo/logo_drone_thermal_badge.png", "artwork", "precision_drone"),
    ("becker_chest_small_render",
     TD / "reference/becker_chest_small_beckers_logo_lc_2_a.jpg",
     "pro-derived-render", "becker_chest_small"),
    ("becker_hat_small_render",
     TD / "reference/becker_hat_small_beckers_logo_hat_2_a.jpg",
     "pro-derived-render", "becker_hat_small"),
    ("becker_hat_large_render",
     TD / "reference/becker_hat_polo_large_beckers_logo_hat.jpg",
     "pro-derived-render", "becker_hat_large"),
    ("becker_lc_large_render",
     TD / "reference/becker_hat_polo_large_beckers_logolc.jpg",
     "pro-derived-render", "becker_lc_large"),
]


def _md5(p: Path) -> str:
    return hashlib.md5(p.read_bytes()).hexdigest()


def _dup_note():
    """The drone artwork double-count, checked at runtime, not remembered."""
    a = TD / "photo/logo_drone_thermal_badge.png"
    b = TD / "photo/drone_render.png"
    if a.exists() and b.exists():
        if _md5(a) == _md5(b):
            print("[note] logo_drone_thermal_badge.png is byte-identical to "
                  "drone_render.png; this tool runs the image ONCE (the "
                  "scorecard's FIXTURES still carries both).")
        else:
            print("[note] logo_drone_thermal_badge.png and drone_render.png "
                  "have DIVERGED (were byte-identical 2026-08-23) — re-check "
                  "which is the real customer file before trusting either.")


def join_fixture(name, art, input_class, pro_slug, forced_class=None) -> dict:
    """Digitize one committed artwork at the pro's decoded width, then census
    ours and join our regions onto the pro's blocks."""
    from digitizer_core.config import PipelineConfig
    from digitizer_core.export import write_dst
    from digitizer_core.pipeline import digitize

    by_slug = dict(prep_all.DESIGNS)
    pro_path = prep_all.find_file(by_slug[pro_slug])
    if pro_path is None:
        return {"fixture": name, "ok": False, "error": f"pro file missing: {pro_slug}"}
    p_blocks, p_breaks, p_threads, p_bounds, _j, _t = prep_all.decode(pro_path)
    width = p_bounds[2] - p_bounds[0]

    cfg = PipelineConfig(target_width_mm=round(width, 1))
    if forced_class:
        cfg.forced_class = forced_class
    result, plan = digitize(str(art), cfg)

    with tempfile.TemporaryDirectory() as td:
        dst = Path(td) / "ours.dst"
        write_dst(plan, dst)
        o_blocks, o_breaks, o_threads, o_bounds, _oj, _ot = prep_all.decode(dst)

    # Our DST is as palette-blind as anyone's, so decoding it back yields the
    # synthetic ramp — but OUR thread identity is not unknowable, the plan
    # carries it. Census the machine stream with the plan's palette so the
    # thread-return line reports the structural 0 instead of hiding as None.
    plan_threads = [b.thread_number for b in plan.blocks]
    ours = census_design(o_blocks, o_breaks, plan_threads, o_bounds,
                         synthetic=False)
    ours["thread_source"] = "plan-palette"
    row = {
        "fixture": name, "ok": True, "input_class": input_class,
        "pro_counterpart": pro_slug,
        "target_width_mm": round(width, 1),
        "design_class": result.design_class,
        "config": f"forced-{forced_class}" if forced_class else "default",
        "pro": census_design(p_blocks, p_breaks, p_threads, p_bounds),
        "ours": ours,
    }

    # --- the join: our REGION polygons onto the pro's blocks --------------
    # Registration runs on stitches (scorecard.register, translation only);
    # region polygons share the plan's mm frame (export is scale-only, no
    # flip, no recenter — export.py docstring), and the plan is rebuilt from
    # those polygons, so the plan-vs-pro shift applies to the polygons.
    pro_segs = runs_to_segs(p_blocks)
    plan_blocks = [[list(r.points) for r in b.runs] for b in plan.blocks]
    our_segs = runs_to_segs(plan_blocks)
    bb0 = scorecard.bounds(pro_segs, our_segs)
    dx, dy, reg_iou = scorecard.register(pro_segs, our_segs, bb0)
    bb = scorecard.bounds(pro_segs, scorecard.shifted(our_segs, dx, dy))
    pro_closed, _pro_raw, _pro_areas = paint_block_masks(p_blocks, bb)
    region_masks = paint_polygon_masks(
        [r.polygon for r in result.regions], bb, shift=(dx, dy))
    join = grouping_join(pro_closed, region_masks)
    join["registration"] = {"dx": round(dx, 2), "dy": round(dy, 2),
                            "reg_iou": round(reg_iou, 3)}
    row["join"] = join
    row["regions_by_thread"] = dict(Counter(
        r.thread_number for r in result.regions))
    return row


def _print_join_row(row):
    if not row.get("ok"):
        print(f"[{row['fixture']}] ERR {row['error']}", flush=True)
        return
    j = row["join"]
    pro, ours = row["pro"], row["ours"]
    lay_p = pro["layering"]
    lay_o = ours["layering"]
    print(f"[{row['fixture']}] ({row['input_class']}, {row['config']}, "
          f"class={row['design_class']}, {row['target_width_mm']}mm)")
    print(f"  pro : {pro['blocks']} blocks / {pro['threads']} threads / "
          f"{pro['thread_returns']} returns / {pro['paths_cut']} cut paths / "
          f"{pro['ink_components_total']} elements / "
          f"layer {lay_p['smaller_later']}/{lay_p['overlapping_pairs']}")
    print(f"  ours: {j['regions']} regions -> {ours['blocks']} blocks / "
          f"{ours['threads']} threads / {ours['thread_returns']} returns / "
          f"{ours['paths_cut']} cut paths / "
          f"layer {lay_o['smaller_later']}/{lay_o['overlapping_pairs']}")
    if pro.get("thread_seq") or ours.get("thread_seq"):
        print(f"        thread seq: pro {pro.get('thread_seq')} "
              f"ours {ours.get('thread_seq')}")
    if "error" in j:
        print(f"  join: ERROR {j['error']}")
        return
    degen = (" DEGENERATE: joint area is single-label, kappa is the raw "
             "passthrough — read blocks_unhit" if j.get("degenerate") else "")
    print(f"  join: kappa {j['kappa']} (raw {j['raw_agreement']}, "
          f"chance {j['chance']}, reg_iou {j['registration']['reg_iou']})"
          f"{degen}")
    rpb = " ".join(f"b{i}<-{c}" for i, c in sorted(j["regions_per_block"].items()))
    print(f"        regions/block: {rpb}"
          + (f"  unassigned={j['regions_unassigned']}" if j["regions_unassigned"] else "")
          + (f"  hidden={j['regions_hidden']}" if j.get("regions_hidden") else "")
          + (f"  blocks_unhit={j['blocks_unhit']}" if j["blocks_unhit"] else "")
          + (f"  pro_hidden={j['pro_blocks_hidden']}"
             if j.get("pro_blocks_hidden") else ""))
    print(f"        our area off pro ink {j['our_outside_pro_share']:.0%}, "
          f"pro ink we leave bare {j['pro_uncovered_share']:.0%}")


def run_join(args) -> list[dict]:
    prep_all.ROOT = corpus_root()
    _dup_note()
    rows = []
    for name, art, input_class, pro_slug in FIXTURES:
        if args.only and args.only != name:
            continue
        if input_class == "pro-derived-render" and not args.include_derived:
            print(f"[{name}] SKIP {input_class} (vendor render of the pro's own "
                  f"stitches — not artwork; --include-derived runs it, labeled)")
            continue
        if not art.exists():
            rows.append({"fixture": name, "ok": False,
                         "error": f"missing fixture {art}"})
            continue
        try:
            row = join_fixture(name, art, input_class, pro_slug,
                               forced_class=args.forced_class)
        except Exception as e:  # noqa: BLE001 — one bad fixture is a row
            import traceback
            row = {"fixture": name, "ok": False,
                   "error": f"{type(e).__name__}: {e}",
                   "trace": traceback.format_exc()[-600:]}
        rows.append(row)
        _print_join_row(row)

    scored = [r for r in rows if r.get("ok") and r["input_class"] == "artwork"
              and "kappa" in r.get("join", {})]
    if scored:
        print(f"\n=== artwork-class joins (n={len(scored)}; pro-derived renders "
              f"excluded from aggregates always) ===")
        graded = [r for r in scored if not r["join"].get("degenerate")]
        if len(graded) < len(scored):
            print(f"  ({len(scored) - len(graded)} degenerate join(s) excluded "
                  f"from the kappa aggregate — single-label joint domain says "
                  f"nothing about grouping)")
        if graded:
            print(f"  kappa: med {_median([r['join']['kappa'] for r in graded])}  "
                  f"range {min(r['join']['kappa'] for r in graded)}"
                  f"..{max(r['join']['kappa'] for r in graded)}")
        per_visible_block = [
            c for r in scored
            for i, c in r["join"]["regions_per_block"].items()
            if i not in r["join"].get("pro_blocks_hidden", [])]
        print(f"  regions per visible pro block: med {_median(per_visible_block)}"
              f"  max {max(per_visible_block, default=None)}"
              f"  (pro elements per block: med 1)")
        print("  READ AGAINST THE CEILING, NOT 1.0: pro-vs-pro on the same logo "
              "runs 75.2-83.6 scorecard points; `ceiling` mode prints the "
              "same-logo kappa floor in this tool's own currency.")
        o_blocks = sum(r["ours"]["blocks"] for r in scored)
        o_returns = sum(r["ours"]["thread_returns"] for r in scored)
        p_blocks = sum(r["pro"]["blocks"] for r in scored)
        p_returns = sum(r["pro"]["thread_returns"] or 0 for r in scored)
        print(f"  Thread-return gap: pro {p_returns}/{p_blocks} colour stops "
              f"reuse a loaded thread on these designs (corpus-wide 55%); ours "
              f"{o_returns}/{o_blocks}. The flat lane emits one block per "
              f"thread (0 by construction); nonzero ours comes from the tonal "
              f"lane's shade emission — read thread_seq to see whether a "
              f"repeat is an adjacent same-thread stop (machine-pointless) or "
              f"a reuse; neither is yet a chosen background->foreground "
              f"return.")
    return rows


def run_ceiling(args) -> list[dict]:
    """The pro-vs-pro floor in this tool's currency: `grouping_join` over the
    pro's own same-logo pairs (selfconsistency.PAIRS). Side B's blocks stand
    in for "regions". The pairs selfconsistency marks as one-job-saved-twice
    double as the real-data self-test (~1.0) — except the becker pair, whose
    two saves share geometry but genuinely differ in block structure (5 vs 4
    blocks); see the footer this mode prints."""
    root = corpus_root()
    os.environ["PRO_PARITY_ROOT"] = str(root)
    prep_all.ROOT = root
    import selfconsistency  # deferred: its import reads PRO_PARITY_ROOT
    selfconsistency.prep_all.ROOT = root

    rows = []
    for name, rel_a, rel_b, what in selfconsistency.PAIRS:
        if args.only and args.only != name:
            continue
        pa, pb = prep_all.find_file(rel_a), prep_all.find_file(rel_b)
        if pa is None or pb is None:
            rows.append({"pair": name, "ok": False, "error": "file not found"})
            continue
        A = prep_all.decode(pa)
        B = prep_all.decode(pb)
        wa = A[3][2] - A[3][0]
        wb = B[3][2] - B[3][0]
        delta = abs(wa - wb) / max(wa, wb)
        if delta > selfconsistency.MAX_SIZE_DELTA:
            rows.append({"pair": name, "ok": False, "skipped": True,
                         "error": f"size delta {delta:.1%} > "
                                  f"{selfconsistency.MAX_SIZE_DELTA:.0%} "
                                  f"(translation-only registration)"})
            print(f"[{name}] SKIP size delta {delta:.1%}")
            continue
        a_segs, b_segs = runs_to_segs(A[0]), runs_to_segs(B[0])
        bb0 = scorecard.bounds(a_segs, b_segs)
        dx, dy, reg_iou = scorecard.register(a_segs, b_segs, bb0)
        bb = scorecard.bounds(a_segs, scorecard.shifted(b_segs, dx, dy))
        a_closed, _ar, _aa = paint_block_masks(A[0], bb)
        b_closed, _br, _ba = paint_block_masks(B[0], bb, shift=(dx, dy))
        join = grouping_join(a_closed, b_closed)
        join["registration"] = {"dx": round(dx, 2), "dy": round(dy, 2),
                                "reg_iou": round(reg_iou, 3)}
        rows.append({"pair": name, "ok": True, "what": what, "join": join})
        print(f"[{name}] kappa {join['kappa']} (raw {join['raw_agreement']}, "
              f"chance {join['chance']}, reg_iou {reg_iou:.3f}) — {what}")
    ok = [r for r in rows if r.get("ok")]
    if ok:
        print("\nHow to read these: machine_hat_vs_lc and toat_beanie_two_files "
              "are one job saved twice — the ~1.0 they score is the join's "
              "real-data self-test. becker_hat_vs_chest_small shares stitch "
              "GEOMETRY but not block structure (5 vs 4 blocks: the hat file "
              "splits one thread's work into a first and a last block — a "
              "return — where the chest file sews it once), so its score is a "
              "same-pro re-blocking data point, not a self-test failure. The "
              "genuinely independent renditions (hotel_hat_vs_patch, "
              "machine_beanie_two_files) are the ceiling any fixture kappa "
              "should be read against.")
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("mode", choices=["census", "join", "ceiling"])
    ap.add_argument("--json", type=Path, help="also write rows as JSON")
    ap.add_argument("--only", help="run a single design/fixture/pair")
    ap.add_argument("--include-derived", action="store_true",
                    help="also run the pro-derived render fixtures (labeled; "
                         "never aggregated)")
    ap.add_argument("--forced-class", default=None,
                    help="join mode: pin stage 0's class (e.g. 'flat')")
    args = ap.parse_args(argv)
    rows = {"census": run_census, "join": run_join, "ceiling": run_ceiling}[args.mode](args)
    if args.json:
        args.json.write_text(json.dumps(rows, indent=1))
        print(f"\nwrote {args.json}")
    return rows


if __name__ == "__main__":
    main()
