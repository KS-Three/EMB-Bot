#!/usr/bin/env python
"""Search `PipelineConfig` for settings that raise artwork fidelity.

The point of `artfidelity_self.py` is not the number — it is that a number
computed from the ARTWORK ALONE turns engine tuning from a manual A/B into a
search. This repo currently moves roughly one threshold per working session,
and its own measurements keep concluding that single-threshold moves are null:
"no one-directional adjustment of the satin/fill gate - cap, `p90`, aspect, or
regularity - can fix this" (MASTER_SCOPE, measured negatives). A search over
several parameters at once is a different instrument than a human moving one.

**This tool never writes `config.py`.** It prints proposed deltas and the
measurement behind each. Applying them is Kent's call, and a config change that
survives this search still has to survive review — the search optimises the
metric it is given, which is exactly how `scorecard.py`'s `direction`
component came to hold 20 points nobody can defend.

## The gates are enforced in code, not in a comment

ROADMAP gate 1 refuses physical constants without a sew-out — fill row spacing,
the satin width floor, link cover tolerance, fabric presets, DST orientation —
and gate 3 refuses flipping a default-OFF tier whose instrument has not been
rebuilt (`chain_links`, contour, `split_tonal_regions`). A search that hunted
freely over `PipelineConfig` would walk straight into both, and would do it
invisibly, because a config sweep produces a number rather than a diff anyone
reads.

So the search space is an ALLOWLIST (`TUNABLE`), every entry carrying why it is
safe, and `_check_space()` refuses to start if anything outside it is
requested. `DENIED` records the ones deliberately left out and the ruling that
excludes each, so a later session can see they were considered rather than
missed.

## Method

Coordinate descent: one parameter at a time, each candidate value scored over
the fixture subset, keep a move only if the mean rises. Cheap, resumable, and
its output is readable as "this parameter, this value, this much" — which
matters more here than reaching a true optimum, because every proposal has to
be argued to a human afterwards. It will sit in a local optimum; that is an
accepted cost, not an oversight.

Objective is the mean ARTFID over the TRUSTWORTHY rows only. A flagged fixture
is comparing two different pictures (see `artfidelity_self`), so letting one
into the objective would let the search optimise an artifact.

## Usage

    python tools/artfidelity_tune.py --list                 # show the space
    python tools/artfidelity_tune.py --max-evals 40 --workers 6
    python tools/artfidelity_tune.py --fixtures logo_whitebg.png ...
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

# --- the search space --------------------------------------------------------

# name -> (candidate values, why this one is safe to move)
TUNABLE: dict[str, tuple[tuple, str]] = {
    "max_colors": (
        (6, 8, 10, 12, 14, 16),
        "How many threads the design may use. A cost/quality tradeoff the "
        "operator already sees on the job sheet, not a property of cloth.",
    ),
    "merge_delta_e": (
        (3.0, 4.5, 6.0, 8.0, 10.0),
        "Flat-lane region merge distance. NOT stage2_photo_segment's "
        "MERGE_DELTAE00_THRESH, which a standing ruling holds at 26.0 - that "
        "constant is module-level and is not reachable from here.",
    ),
    "aa_iterations": (
        (0, 1, 2, 3, 4),
        "How hard stage 1 works to undo the source image's anti-aliasing. A "
        "property of the INPUT FILE, not of thread or fabric.",
    ),
    "aa_phantom_edge_frac": (
        (0.7, 0.8, 0.9, 0.95),
        "Same lane as aa_iterations: which soft edges are the encoder's "
        "artifacts rather than the artist's intent.",
    ),
    "bg_tolerance_lab": (
        (3.0, 4.5, 6.0, 8.0, 10.0),
        "Background detection. Decides what is artwork; nothing downstream of "
        "it is a physical constant.",
    ),
    "bg_border_agreement_min": (
        (0.6, 0.7, 0.75, 0.85, 0.9),
        "How much of the image border must agree on one colour before it is "
        "called background. A statement about the FILE's composition - what "
        "the artist put behind the logo - not about thread or cloth.",
    ),
    "bg_border_rival_min": (
        (0.05, 0.1, 0.15, 0.25),
        "How large a competing border colour must be before the background "
        "call is treated as contested. Same lane: it decides what counts as "
        "artwork, and nothing it feeds is a physical constant.",
    ),
    "bg_margin_mm": (
        (1.0, 2.0, 3.0, 5.0),
        "Width of the border band the background test samples. Millimetres of "
        "IMAGE, not of stitch - it never reaches a needle, and no sew-out "
        "could settle it.",
    ),
    "bg_intrusion_min_mm": (
        (1.0, 2.0, 3.0, 4.0),
        "How far the background may reach into the artwork before it is read "
        "as a hole rather than as surrounding ground. Geometry of the source "
        "image; decided before any stitch exists.",
    ),
    "min_px_per_mm": (
        (2.0, 3.0, 4.0, 6.0),
        "When stage 1 judges the source too coarse to trust. A statement "
        "about the input's resolution.",
    ),
    "upscale_cap": (
        (2.0, 3.0, 4.0, 6.0),
        "Ceiling on how far a low-resolution source may be enlarged before "
        "stage 1 works on it. A limit on trusting interpolated pixels, which "
        "is a property of the input file.",
    ),
    "photo_prep_clahe_clip": (
        (1.5, 2.0, 2.5, 3.5, 5.0),
        "Contrast prep on the photo route - an image operation applied before "
        "any stitch decision exists.",
    ),
    "photo_prep_clahe_tiles": (
        (4, 6, 8, 12),
        "Tile grid for that same CLAHE call - how local the contrast "
        "equalisation is. An image operation applied before any stitch "
        "decision exists.",
    ),
}

# Deliberately OUT, each with the reason. Kept so a later session can see these
# were weighed rather than overlooked.
DENIED: dict[str, str] = {
    "target_width_mm": "The user's chosen design size - an INPUT, not a tuning knob.",
    "seed": "Determinism. Tuning it would be fitting noise.",
    "simplify_tol_mm": (
        "Standing ruling (MASTER_SCOPE, measured negatives): the fixed 0.2 mm "
        "constant is correct as-is and the investigation is CLOSED, not open."
    ),
    "min_detail_mm": (
        "Gate 1 territory. It is the floor on what can physically sew, and "
        "stage3's chained-small-region rescue is measured against 'the same "
        "bar' - moving it moves a needle-and-thread limit."
    ),
    "overlap_mm": (
        "Gate 1 territory - close kin to the link cover tolerance the gate "
        "names outright. How far shapes must overlap so no bare cloth shows "
        "between them is settled by thread, not geometry."
    ),
    "photo_segment_sam2_max_side_px": (
        "Standing ruling: stays 1024. SAM2 also ships OFF, so this is dead "
        "weight in the search."
    ),
    "photo_segment_sam2_points_per_side": (
        "SAM2 ships OFF and its re-measurement is an explicit post-v1 item "
        "in PRODUCT.md."
    ),
    "report_absorb_frac": "Reporting threshold. Changes what is SAID, not what is sewn.",
    "photo_prep_background_removal_timeout_s": "A timeout. Not a quality parameter.",
    "photo_segment_sam2_timeout_s": "A timeout. Not a quality parameter.",
}

# Default-OFF tiers, refused outright rather than listed value-by-value.
# `contour` is NOT a boolean: it is a VALUE of `fill_technique` (default
# "tatami"), so the whole field is refused - a search that could set it could
# reach the contour tier. This list said `contour_fill` until 2026-09-01, a
# name `PipelineConfig` has never carried, so the gate-3 refusal for contour
# pointed at nothing while the live knob went unnamed; caught by
# tests/test_artfidelity_tune.py, which now pins every name here to a real
# field.
GATE3_FLAGS = ("chain_links", "split_tonal_regions", "fill_technique")


def _check_space(names) -> None:
    for n in names:
        if n in GATE3_FLAGS:
            raise SystemExit(
                f"REFUSED: '{n}' is a default-OFF tier. ROADMAP gate 3 - no "
                "default-OFF tier is flipped on until its instrument is "
                "rebuilt. A green suite has already concealed needle-down "
                "thread on bare fabric here."
            )
        if n in DENIED:
            raise SystemExit(f"REFUSED: '{n}' is excluded.\n  {DENIED[n]}")
        if n not in TUNABLE:
            raise SystemExit(
                f"REFUSED: '{n}' is not on the allowlist. Add it to TUNABLE "
                "with a written reason it is not a physical constant, or to "
                "DENIED with the ruling that excludes it - do not widen the "
                "search by passing it in."
            )


# --- evaluation --------------------------------------------------------------

def _eval_one(job):
    """Score one fixture under one config override set. Module-level for spawn.

    **One OpenCV thread per worker.** cv2 parallelises internally across every
    core it can see, so N worker processes each spawning N threads oversubscribe
    the box badly: measured here at 6 workers on 8 cores, a baseline sweep that
    takes 292s serially burned over 840s of CPU and had not finished. The CI
    workflow already records the same mechanism from the other direction -
    "GitHub's standard runners are 2-core, so `-n auto` gets two workers and
    OpenCV's threading competes with them". Process-level parallelism is the
    one we want here, so thread-level is turned off rather than left to fight
    it. Set before any pipeline import so it binds the whole worker.
    """
    name, overrides = job
    import cv2
    cv2.setNumThreads(1)
    import artfidelity_self as A
    from digitizer_core.config import PipelineConfig
    cfg = PipelineConfig(**overrides)
    # `artfidelity_self`'s API moved between this tuner being written
    # (2026-08-26) and the scorer landing on main: `score_one` became
    # `score_image`, `_resolve` took a LIST, and the per-row verdict became
    # `refusal is None` instead of a `trustworthy` bool. Adapted here, at the
    # two call sites, rather than by reviving the old names - the scorer is
    # the shipped instrument and this is the caller.
    path = A._resolve([name])[0]
    t = time.time()
    try:
        r = A.score_image(path, cfg=cfg)
        r["trustworthy"] = r.get("refusal") is None
    except Exception as exc:                      # a config can be out of range
        return {"fixture": name, "spec": name,
                "error": f"{type(exc).__name__}: {exc}",
                "trustworthy": False, "artfid": 0.0,
                "elapsed_s": round(time.time() - t, 1)}
    # `score_image` reports the artwork's BASENAME, which is not what
    # `_resolve` takes: the fixture list carries `photo/`-prefixed specs and
    # several basenames are only unique with that prefix. Carry the spec we
    # were given so the second pass can re-resolve it. (Without this the
    # search silently drops every photo/ fixture after the baseline.)
    r["spec"] = name
    r["elapsed_s"] = round(time.time() - t, 1)
    return r


def evaluate(fixtures, overrides, workers) -> tuple[float, list]:
    jobs = [(f, overrides) for f in fixtures]
    if workers <= 1:
        rows = [_eval_one(j) for j in jobs]
    else:
        with ProcessPoolExecutor(max_workers=workers) as ex:
            rows = list(ex.map(_eval_one, jobs))
    ok = [r for r in rows if r.get("trustworthy")]
    return (float(np.mean([r["artfid"] for r in ok])) if ok else 0.0), rows


# --- search ------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--fixtures", nargs="*", default=None,
                    help="fixtures to tune over (default: the trustworthy "
                         "subset of artfidelity_self.FIXTURES)")
    ap.add_argument("--params", nargs="*", default=None,
                    help="parameters to search (default: all of TUNABLE)")
    ap.add_argument("--max-evals", type=int, default=60)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--json", metavar="PATH")
    ap.add_argument("--list", action="store_true",
                    help="print the search space and exit")
    args = ap.parse_args()

    if args.list:
        print("TUNABLE (searchable):")
        for k, (vals, why) in TUNABLE.items():
            print(f"  {k:34s} {list(vals)}\n      {why}")
        print("\nDENIED (excluded, with the ruling):")
        for k, why in DENIED.items():
            print(f"  {k:34s} {why}")
        print("\nGATE-3 FLAGS (refused outright): " + ", ".join(GATE3_FLAGS))
        return 0

    import artfidelity_self as A

    params = args.params or list(TUNABLE)
    _check_space(params)

    fixtures = args.fixtures or list(A.FIXTURES)
    print(f"baseline over {len(fixtures)} fixtures, {args.workers} workers ...",
          flush=True)
    t0 = time.time()
    best_score, rows = evaluate(fixtures, {}, args.workers)
    for r in rows:
        if r.get("error"):
            print(f"  {r['fixture']}: {r['error']}")
    trust = [r["spec"] for r in rows if r.get("trustworthy")]
    print(f"baseline mean ARTFID {best_score:.2f} over {len(trust)} trustworthy "
          f"({time.time() - t0:.0f}s)")
    print("  slowest: " + ", ".join(
        f"{r['spec']} {r.get('elapsed_s', 0):.0f}s"
        for r in sorted(rows, key=lambda x: -x.get("elapsed_s", 0))[:4]))
    if not trust:
        print("no trustworthy fixture to optimise - stopping")
        return 1

    # Only the trustworthy ones enter the objective from here.
    fixtures = trust
    best_cfg: dict = {}
    history = [{"param": None, "value": None, "mean": round(best_score, 3)}]
    evals = 0

    for name in params:
        values, _why = TUNABLE[name]
        from digitizer_core.config import PipelineConfig
        current = getattr(PipelineConfig(**best_cfg), name)
        for v in values:
            if v == current or evals >= args.max_evals:
                continue
            trial = dict(best_cfg, **{name: v})
            score, _ = evaluate(fixtures, trial, args.workers)
            evals += 1
            delta = score - best_score
            keep = delta > 0
            print(f"  {name}={v!r:>8}  mean {score:6.2f}  "
                  f"{delta:+6.2f}  {'KEEP' if keep else ''}", flush=True)
            history.append({"param": name, "value": v, "mean": round(score, 3),
                            "delta": round(delta, 3), "kept": keep})
            if keep:
                best_cfg, best_score = trial, score
        if evals >= args.max_evals:
            print(f"\nstopped at --max-evals {args.max_evals}")
            break

    print(f"\n{evals} evaluations, {time.time() - t0:.0f}s total")
    print(f"baseline mean {history[0]['mean']:.2f} -> {best_score:.2f} "
          f"({best_score - history[0]['mean']:+.2f})")
    if best_cfg:
        print("\nPROPOSED (not applied - config.py is untouched):")
        from digitizer_core.config import PipelineConfig
        base = PipelineConfig()
        for k, v in best_cfg.items():
            print(f"  {k}: {getattr(base, k)!r} -> {v!r}")
        print("\nBefore any of this is applied: it is a fit to ONE metric over "
              "a handful of fixtures, on a metric whose own weights are not "
              "yet validated against a human ranking. Read it as a hypothesis "
              "to test, not a result.")
    else:
        print("\nNo parameter improved the objective. The shipped defaults are "
              "a local optimum for this metric over these fixtures.")

    if args.json:
        Path(args.json).write_text(json.dumps(
            {"baseline_mean": history[0]["mean"], "best_mean": best_score,
             "proposed": best_cfg, "fixtures": fixtures, "history": history},
            indent=2), encoding="utf-8")
        print(f"\nwrote {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
