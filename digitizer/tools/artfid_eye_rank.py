#!/usr/bin/env python
"""Does ARTFID's ranking agree with an eye? A blind rank-correlation harness.

ROADMAP phase 1's exit condition is phrased as *does the metric's ranking
agree with Kent's eye*, and until now nothing in the repo measured that.
`artfidelity_self.py` produces the number; `acceptance_ab.py` produces the
contact sheet Kent judges (deliberately with no number on it, per build step
8's decision record). Neither one puts the two rankings side by side, so the
question the phase gate is written in terms of has had no instrument.

This is that instrument. It does not replace Kent's eye — it is a cheap
second judge that says where the metric and a viewer disagree MOST, so the
expensive human pass can be spent on those fixtures instead of all fourteen.

## The blinding is the whole point

A ranking produced after seeing the scores measures nothing. So the run is
split into two commands that CANNOT be collapsed into one:

    python -m tools.artfid_eye_rank --render   # pictures out, scores sealed
    python -m tools.artfid_eye_rank --reveal   # correlation, after ranking

`--render` digitizes each fixture ONCE and writes three things: a rendered
stitch-out, a normalised copy of the source artwork, and the score row. The
pictures are named by opaque label (`pair_A_*`), the score rows go into
`scores.json`, and the label -> fixture mapping goes into `order.json`.
`--render` prints the labels and NOTHING ELSE — no score, no fixture name,
no route, no stitch count. A viewer can therefore rank the pairs without any
channel back to the metric.

`--reveal` refuses to run until `ranking.json` exists. That file is the
commitment device: the ranking has to be on disk before the scores can be
read.

## Pre-registered analysis plan — fixed BEFORE any score was seen

Stated here rather than decided at reveal time, because choosing the subset
after seeing the numbers is how a null result becomes a positive one.

  * PRIMARY: Kendall tau-b, eye rank vs ARTFID rank, over NON-REFUSED rows
    only. `score_image`'s own refusals (subject mismatch, ink saturation,
    ambiguous knocked-out lettering) mark rows that must not be read as
    engine results, and a correlation that includes them is measuring the
    refusal classes, not the metric.
  * SECONDARY: the same over all fourteen, reported alongside, so dropping
    rows can never be mistaken for the headline.
  * Both are reported with a p-value and with n stated. n is 14 at most.
    A tau from fourteen points has a wide interval and this tool says so
    rather than letting a reader assume otherwise.
  * `becker_marine_logo.png` is EXCLUDED from the primary. Running
    `--verify` (the drift control above) prints that fixture's score, so
    whoever ran it is no longer blind to it. The contamination is one
    fixture out of fourteen and the honest fix is cheap: drop it from the
    headline and report the all-rows figure beside it, so the exclusion
    cannot be doing any work a reader cannot see. Recorded here BEFORE the
    ranking was made, which is the only time such an exclusion is legitimate.
    `--verify` on a different `--fixture` moves the contamination to that
    fixture instead; `CONTAMINATED` below must be updated to match.

**ROADMAP gate 4 compliance.** Gate 4 refuses a quality claim on a raw
agreement number. Kendall tau-b is chance-corrected by construction — 0 is
exactly the agreement two unrelated rankings produce — which is why it is
the primary here. This tool never prints a "% agreement", and a reader who
wants one should read the gate instead.

## What a result here does and does not license

A high tau says the metric ranks the way a viewer does ON THIS FIXTURE SET.
It is not a sew-out, it settles no physical constant (gate 1), and it is not
grounds to move a threshold — `artfidelity_tune.py` already carries the
warning about optimising the metric you are handed. The useful output is the
DISAGREEMENT list: fixtures where eye and metric are furthest apart are
where the metric is most likely to be lying.
"""

from __future__ import annotations

import argparse
import json
import random
import shutil
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from digitizer_core.adapter import plan_to_design  # noqa: E402
from digitizer_core.config import PipelineConfig  # noqa: E402
from digitizer_core.pipeline import digitize  # noqa: E402
from digitizer_core.stitchviz import render_design  # noqa: E402

from tools.artfidelity_self import (  # noqa: E402
    FIXTURES,
    INK_SATURATION_MAX,
    MISMATCH_MAX,
    WEIGHTS,
    art_ink_field,
    colour_score,
    ink_is_ambiguous,
    ink_saturation,
    ms_ssim,
    register,
    run_preflight,
    stitch_coverage_field,
)

TESTDATA = Path(__file__).resolve().parents[1] / "testdata"
OUTDIR = Path(__file__).resolve().parents[1] / "artfid_eye_out"

# Fixed so a rerun presents the same order. Changing it re-blinds the set,
# which invalidates a ranking already on disk against the old order.
SHUFFLE_SEED = 20260911

# Fixtures whose score leaked to the viewer before ranking. See the
# pre-registration above: `--verify` prints one fixture's row, so that
# fixture is dropped from the primary correlation.
CONTAMINATED = ("becker_marine_logo.png",)

# The renders are looked at by eye, so they are bigger than the 8 px/mm the
# viz module defaults to. This affects the PICTURE ONLY — every number comes
# from `stitch_coverage_field`, which rasterises independently.
VIEW_PX_PER_MM = 14.0


def _score_row(image_path: Path, cfg: PipelineConfig) -> tuple[dict, np.ndarray]:
    """`artfidelity_self.score_image`'s sequence, digitizing ONCE.

    The tool's own `score_image` digitizes and then throws the design away;
    this needs the design too, to render it. Rather than calling the tool and
    digitizing a second time — the fixture set takes minutes per photo route,
    so that is a real cost, not a tidiness point — the orchestration is
    repeated here over the tool's OWN functions, every one of them imported
    rather than copied. `--verify` checks this against `score_image` on one
    fixture so the repetition cannot drift silently.
    """
    result, plan = digitize(image_path, cfg)
    design = plan_to_design(plan)

    ours = stitch_coverage_field(design)
    art = art_ink_field(image_path, float(design["widthMM"]))

    coverage, O_f, A_f, dx_mm, dy_mm = register(ours, art)
    structure = ms_ssim(O_f, A_f)
    colour, median_excess = colour_score(image_path, result, plan, cfg)

    composite = 100.0 * (WEIGHTS[0] * coverage
                         + WEIGHTS[1] * colour
                         + WEIGHTS[2] * structure)

    ink_px = float((art >= 0.5).sum())
    sewn_px = float((ours >= 0.5).sum())
    saturation = ink_saturation(image_path)

    refusal = None
    mismatch = None
    if ink_px == 0 or sewn_px == 0:
        refusal = ("nothing to compare: no ink found in the artwork"
                   if ink_px == 0 else
                   "nothing to compare: the engine sewed nothing")
    else:
        mismatch = max(ink_px, sewn_px) / min(ink_px, sewn_px)
        if mismatch > MISMATCH_MAX:
            refusal = f"subject mismatch, {mismatch:.1f}x"
        elif saturation > INK_SATURATION_MAX:
            refusal = f"ink mask saturates the frame, {saturation:.0%}"
        elif ink_is_ambiguous(image_path):
            refusal = "ink ambiguous (knocked-out lettering)"

    pre = run_preflight(result, plan, cfg, image=image_path)

    row = {
        "fixture": image_path.name,
        "route": result.design_class,
        "stitches": int(plan.stats.stitch_count),
        "preflight_grade": pre["grade"],
        "preflight_score": int(pre["score"]),
        "coverage": round(coverage, 3),
        "colour": round(colour, 3),
        "structure": round(structure, 3),
        "artfid": round(composite, 1),
        "median_excess_de": (None if median_excess is None
                             else round(median_excess, 2)),
        "shift_x_mm": round(dx_mm, 1),
        "shift_y_mm": round(dy_mm, 1),
        "subject_ratio": None if mismatch is None else round(mismatch, 2),
        "ink_saturation": round(saturation, 3),
        "refusal": refusal,
        "width_mm": round(float(design["widthMM"]), 1),
    }
    return row, render_design(design, px_per_mm=VIEW_PX_PER_MM)


def _normalise_art(src: Path, dst: Path) -> None:
    """Copy the artwork to `dst` as a viewable PNG on white.

    Two fixtures need this rather than a plain copy: one is `.webp`, which
    not every viewer reads, and several carry alpha, which renders as black
    in a viewer that drops the channel — turning "white lettering" into
    "black lettering" and corrupting exactly the judgement being asked for.
    Compositing onto white matches `art_ink_field`'s own darkness rule.
    """
    im = Image.open(src).convert("RGBA")
    bg = Image.new("RGBA", im.size, (255, 255, 255, 255))
    Image.alpha_composite(bg, im).convert("RGB").save(dst, "PNG")


def cmd_render(argv: argparse.Namespace) -> int:
    OUTDIR.mkdir(exist_ok=True)
    cfg = PipelineConfig()

    names = list(FIXTURES)
    labels = [chr(ord("A") + i) for i in range(len(names))]
    shuffled = names[:]
    random.Random(SHUFFLE_SEED).shuffle(shuffled)

    # Resume. The photo routes take minutes apiece, so a run that dies at
    # fixture twelve must not throw away the eleven it already paid for —
    # `scores.json` is rewritten after EVERY fixture, and a label that
    # already has both its score row and its two pictures is skipped.
    rows: dict[str, dict] = {}
    scores_path = OUTDIR / "scores.json"
    if scores_path.exists():
        rows = json.loads(scores_path.read_text())
    order: dict[str, str] = {}

    for label, name in zip(labels, shuffled):
        src = TESTDATA / name
        order[label] = name
        done = (label in rows
                and (OUTDIR / f"pair_{label}_stitch.png").exists()
                and (OUTDIR / f"pair_{label}_art.png").exists())
        if done:
            print(f"[{label}] cached", file=sys.stderr, flush=True)
            continue
        # Progress goes to STDERR and names no fixture: stdout is what a
        # blinded viewer reads, and "now doing summit_badge" on either stream
        # would leak the mapping this command exists to hide.
        print(f"[{label}] digitizing...", file=sys.stderr, flush=True)
        try:
            row, img = _score_row(src, cfg)
        except Exception as exc:  # noqa: BLE001 - one bad fixture must not
            # take the other thirteen down; the failure is recorded and the
            # label is dropped from the viewable set.
            rows[label] = {"fixture": name, "error": f"{type(exc).__name__}: {exc}"}
            print(f"[{label}] FAILED", file=sys.stderr, flush=True)
            continue
        rows[label] = row
        cv2.imwrite(str(OUTDIR / f"pair_{label}_stitch.png"), img)
        _normalise_art(src, OUTDIR / f"pair_{label}_art.png")
        # Checkpoint: pictures first, then the row. In that order a crash
        # between the two leaves a label whose pictures exist but whose row
        # does not, and the resume check above re-does it rather than
        # treating it as finished.
        scores_path.write_text(json.dumps(rows, indent=2))

    scores_path.write_text(json.dumps(rows, indent=2))
    (OUTDIR / "order.json").write_text(json.dumps(order, indent=2))

    viewable = [k for k, v in rows.items() if "error" not in v]
    print("Blind pairs written to", OUTDIR)
    print("Rank these labels best-fidelity-first, then write ranking.json:")
    print("  " + " ".join(viewable))
    print()
    print("scores.json and order.json are SEALED - do not read them until")
    print("ranking.json is on disk. Then: --reveal")
    return 0


def _kendall(a: list[float], b: list[float]) -> tuple[float, float]:
    from scipy.stats import kendalltau
    t = kendalltau(a, b)
    return float(t.statistic), float(t.pvalue)


def _spearman(a: list[float], b: list[float]) -> tuple[float, float]:
    from scipy.stats import spearmanr
    s = spearmanr(a, b)
    return float(s.statistic), float(s.pvalue)


def cmd_reveal(argv: argparse.Namespace) -> int:
    rank_path = OUTDIR / "ranking.json"
    if not rank_path.exists():
        print("REFUSED: ranking.json does not exist.", file=sys.stderr)
        print("The ranking must be committed to disk BEFORE the scores are",
              file=sys.stderr)
        print("read, or it measures nothing. Write it, then rerun.",
              file=sys.stderr)
        return 2

    scores = json.loads((OUTDIR / "scores.json").read_text())
    order = json.loads((OUTDIR / "order.json").read_text())
    ranking = json.loads(rank_path.read_text())
    eye: list[str] = ranking["order_best_first"]

    recs = []
    for pos, label in enumerate(eye, start=1):
        row = scores.get(label, {})
        if "error" in row:
            continue
        recs.append({
            "label": label,
            "fixture": order[label],
            "eye_rank": pos,
            "artfid": row["artfid"],
            "route": row["route"],
            "grade": row["preflight_grade"],
            "refusal": row["refusal"],
            "coverage": row["coverage"],
            "colour": row["colour"],
            "structure": row["structure"],
        })

    # ARTFID rank: 1 = highest score.
    by_fid = sorted(recs, key=lambda r: -r["artfid"])
    for i, r in enumerate(by_fid, start=1):
        r["fid_rank"] = i
    for r in recs:
        r["delta"] = r["eye_rank"] - r["fid_rank"]

    scored = [r for r in recs
              if r["refusal"] is None and r["fixture"] not in CONTAMINATED]

    print("=" * 78)
    print("EYE vs ARTFID - blind rank correlation")
    print("=" * 78)
    print(f"{'lbl':<4}{'fixture':<30}{'eye':>4}{'fid':>5}{'d':>4}"
          f"{'ARTFID':>8}  {'route':<14}{'refusal'}")
    print("-" * 78)
    for r in sorted(recs, key=lambda r: r["eye_rank"]):
        ref = r["refusal"] or ""
        print(f"{r['label']:<4}{r['fixture']:<30}{r['eye_rank']:>4}"
              f"{r['fid_rank']:>5}{r['delta']:>+4}{r['artfid']:>8.1f}  "
              f"{r['route']:<14}{ref}")
    print()

    print("PRIMARY (pre-registered): non-refused, non-contaminated rows only")
    if len(scored) >= 3:
        e = [r["eye_rank"] for r in scored]
        f = [r["fid_rank"] for r in scored]
        tau, p = _kendall(e, f)
        rho, ps = _spearman(e, f)
        print(f"  n = {len(scored)}")
        print(f"  Kendall tau-b = {tau:+.3f}   (p = {p:.3f})")
        print(f"  Spearman rho  = {rho:+.3f}   (p = {ps:.3f})")
    else:
        print(f"  n = {len(scored)} - too few scored rows to correlate.")
    print()

    print("SECONDARY: all rows including refused")
    e = [r["eye_rank"] for r in recs]
    f = [r["fid_rank"] for r in recs]
    tau_a, p_a = _kendall(e, f)
    rho_a, ps_a = _spearman(e, f)
    print(f"  n = {len(recs)}")
    print(f"  Kendall tau-b = {tau_a:+.3f}   (p = {p_a:.3f})")
    print(f"  Spearman rho  = {rho_a:+.3f}   (p = {ps_a:.3f})")
    print()

    print("BIGGEST DISAGREEMENTS (where the metric is most suspect)")
    for r in sorted(recs, key=lambda r: -abs(r["delta"]))[:5]:
        direction = ("eye rates WORSE than metric" if r["delta"] > 0
                     else "eye rates BETTER than metric")
        print(f"  {r['fixture']:<30} d={r['delta']:+d}  {direction}")
    print()
    print("tau-b is chance-corrected (0 = the agreement of unrelated")
    print("rankings), per ROADMAP gate 4. n is small; read the p-value.")
    return 0


def cmd_verify(argv: argparse.Namespace) -> int:
    """Check the single-digitize path against the tool's own `score_image`."""
    from tools.artfidelity_self import score_image
    name = argv.fixture
    src = TESTDATA / name
    cfg = PipelineConfig()
    mine, _ = _score_row(src, cfg)
    theirs = score_image(src, cfg)
    keys = ["coverage", "colour", "structure", "artfid", "route", "refusal"]
    ok = True
    for k in keys:
        same = mine.get(k) == theirs.get(k)
        ok &= same
        print(f"  {k:<12} mine={mine.get(k)!r:<22} tool={theirs.get(k)!r:<22}"
              f" {'OK' if same else 'DRIFT'}")
    print("MATCH" if ok else "DRIFT - the repeated orchestration diverged")
    return 0 if ok else 1


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--render", action="store_true",
                    help="digitize the fixture set and write blind pairs")
    ap.add_argument("--reveal", action="store_true",
                    help="correlate a committed ranking against ARTFID")
    ap.add_argument("--verify", action="store_true",
                    help="check this file's scoring against score_image")
    ap.add_argument("--fixture", default="becker_marine_logo.png",
                    help="fixture for --verify")
    args = ap.parse_args(argv)

    if args.verify:
        return cmd_verify(args)
    if args.render:
        return cmd_render(args)
    if args.reveal:
        return cmd_reveal(args)
    ap.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
