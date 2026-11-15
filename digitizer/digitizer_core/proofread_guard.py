"""Proof-read guards: undo a departing step where the proof-read shows it left
a region worse than the plain traced shape.

The first one, `cfg.proofread_guard_clipped` (built OFF 2026-11-14), was
picked by the defect-marks kit census (Table A, `eye_pairs_out/proofread-1113/
census/`): of the departing steps not already being fixed elsewhere that
night (small-text re-set, group tier/thread, outline redraw, stage-5 growth),
stage 5's clip misfired most -- 42 misfires over 2,577 mm2 on 6 of 26 designs,
once on a design Kent graded Good. Stage 5 never grows a shape back over a
colour that is already down; when a shape's own art lies under an earlier
colour's sewn polygon, the clip removes it, and the shape is reported
`SHAPE_NOT_STITCHED` (whole) or loses `CLIP_DROPPED_SLIVER` pieces. qr_code's
three finder squares go that way.

The rule, per shape stage 5 dropped or cut (`SHAPE_NOT_STITCHED` /
`CLIP_DROPPED_SLIVER` ids on the plan):

  1. TRIGGER: the proof-read of the plan has a MISSING or SHAPE-deficit
     finding explained by `clipped_stage5` whose `meant_for` names the shape.
  2. INK: at least `GUARD_MIN_FRAC` of the shape's pixels on the proof-read's
     grid are art in the shape's own thread colour: its ink, not a field the
     earlier colour rightly owns.
  3. With at least `GUARD_MIN_MM2` of such ink across the candidates, the
     design is re-planned with those shapes' artwork sewn over the earlier
     colours (`stage5_overlap.keep_art_scope`: the clip keeps the art
     polygon, growth only where the cloth is bare -- the same remedy
     `cfg.small_glyph_keep` gives a rescued small glyph). The re-plan is
     KEPT only when the proof-read's error and misfire area of kinds
     MISSING / SHAPE / EXTRA / MERGED / CLOSED (`worse_mm2`) falls by more
     than `GUARD_MIN_MM2`; otherwise the first plan is returned.

The decision rides on `plan.proofread_guard` (a plain dict), which preflight
copies into metrics when the flag is on. No warning, no finding: Kent's
2026-10-02 ruling. The guard re-plans from the same result (it changes no
region), so the Studio's shape list is untouched. OFF: never imported.
"""
from __future__ import annotations

import time

from . import proofread

GUARD_MIN_FRAC = 0.5        # half the shape must be ink of its own thread colour
GUARD_MIN_MM2 = 5.0         # preflight's `_THREAD_MATCH_MIN_PATCH_MM2`: the smallest patch a finding names
WORSE_KINDS = ("MISSING", "SHAPE", "EXTRA", "MERGED", "CLOSED")
CLIP_CODES = ("SHAPE_NOT_STITCHED", "CLIP_DROPPED_SLIVER")


def worse_mm2(report: dict) -> float:
    """The departure area the guard compares: error and misfire findings of
    the kinds a wrong decision about a whole shape produces."""
    return round(sum(f["area_mm2"] for f in report["findings"]
                     if f["kind"] in WORSE_KINDS and f["severity"] in ("error", "misfire")), 2)


def clipped_ids(plan) -> set[str]:
    ids: set[str] = set()
    for w in getattr(plan, "warnings", None) or ():
        if isinstance(w, dict) and w.get("code") in CLIP_CODES:
            ids.update(str(s) for s in (w.get("ids") or ()))
    return ids


def triggered(report: dict, clipped: set[str]) -> set[str]:
    """Clipped shapes a `clipped_stage5` MISSING / SHAPE-deficit finding names."""
    out: set[str] = set()
    for f in report["findings"]:
        if f["kind"] not in ("MISSING", "SHAPE") or "clipped_stage5" not in f["explained_by"]:
            continue
        if f["kind"] == "SHAPE" and f.get("side") != "deficit":
            continue
        out.update(row["shape_id"] for row in (f.get("meant_for") or ()) if row["shape_id"] in clipped)
    return out


def own_ink(rasters: dict, report: dict, regions_by_id: dict, sids: set[str], cfg) -> dict[str, tuple[float, float]]:
    """-> {shape_id: (share of its pixels that are art in its own thread
    colour, that ink in mm2)}."""
    import numpy as np
    art, reg, ids = rasters["art"], rasters["regions"], rasters["region_ids"]
    px2 = rasters["grid"].px ** 2
    classes = [tuple(c) for c in report["classes"]]
    labs = proofread._lab(classes)
    out = {}
    for i, sid in enumerate(ids):
        if sid not in sids:
            continue
        r = regions_by_id[sid]
        from .threads import chart_for
        rgb = chart_for(cfg)[r.thread_index].rgb
        lab = proofread._lab([tuple(int(v) for v in rgb)])[0]
        c = int(np.argmin([float(np.linalg.norm(lab - q)) for q in labs]))
        m = reg == i
        n = int(m.sum())
        if n:
            ink = int((art[m] == c).sum())
            out[sid] = (ink / n, ink / px2)
    return out


def guard_clipped(result, cfg, plan, replan):
    """-> the plan to keep. `replan(ids)` plans `result` again with those
    shapes' artwork kept over earlier colours (the caller's scopes and cfg)."""
    t0 = time.time()
    view = result.proof_art
    rep = proofread.read(view, result, plan, cfg, want_rasters=True)
    ras = rep.pop("_rasters")
    by_id = {r.shape_id: r for r in result.regions}
    trig = triggered(rep, clipped_ids(plan))
    share = own_ink(ras, rep, by_id, trig, cfg)
    cands = sorted(sid for sid, (frac, _mm2) in share.items() if frac >= GUARD_MIN_FRAC)
    rec = {"rule": "clipped_stage5", "triggered": len(trig), "candidates": len(cands),
           "candidate_ink_mm2": round(float(sum(share[s][1] for s in cands)), 1),
           "worse_mm2_before": worse_mm2(rep), "worse_mm2_after": None, "accepted": False,
           "shapes": cands[:50], "read_s": round(time.time() - t0, 2), "replan_s": None}
    if not cands or rec["candidate_ink_mm2"] < GUARD_MIN_MM2:
        plan.proofread_guard = rec
        return plan
    t1 = time.time()
    plan2 = replan(cands)
    rec["replan_s"] = round(time.time() - t1, 2)
    rep2 = proofread.read(view, result, plan2, cfg)
    rec["worse_mm2_after"] = worse_mm2(rep2)
    if rec["worse_mm2_after"] < rec["worse_mm2_before"] - GUARD_MIN_MM2:
        rec["accepted"] = True
        plan2.proofread_guard = rec
        return plan2
    plan.proofread_guard = rec
    return plan
