#!/usr/bin/env python
"""A standing, automated answer to "did this change make the output better
or worse" — the "Evaluation corpus & harness" gap MASTER_SCOPE.md tracks as
a cross-cutting issue: corpus-law recalibrations have always needed
one-off, by-hand validation ("manually re-running the digitizer suite and
eyeballing a handful of fixtures") because nothing scored the whole
committed fixture set and remembered the last score.

This is the harness half of that gap, not the corpus half: the 37-file
`scratch_corpus/` M2/M3 needs is still inaccessible (gitignored, empty in
every checkout). What IS available is the digitizer's own 14 committed
`testdata/` fixtures, and `digitizer_core.preflight.run_preflight` already
computes a rich per-design quality signal (0-100 score, letter grade, typed
findings, ~20 metrics) for one design at a time — this script is the part
that was missing: run it over every fixture, remember the result, and diff
a fresh run against that memory.

Deliberately a REPORTING tool, not a CI gate, at least for now: this
project's own history (the corpus-laws-23/26 revert, see MASTER_SCOPE.md)
shows a "desk-safe" threshold picked without real validation can carry a
bigger blast radius than expected. Better to let this get used by hand
against a few real changes first and see what a genuine regression looks
like here, than to invent pass/fail numbers today and have them turn into
the next thing that needs walking back.

Usage:
    .venv/Scripts/python tools/corpus_scorecard.py capture
        Digitizes every fixture at every config in MATRIX, scores each with
        run_preflight, and writes testdata/corpus_scorecard_baseline.json.
        Re-run this deliberately, the same way tools/capture_flat_lane_golden.py
        works, whenever a change's new behaviour should become the new
        baseline rather than a regression to flag.

    .venv/Scripts/python tools/corpus_scorecard.py diff
        Re-digitizes everything and prints what moved against the stored
        baseline: score deltas, findings that appeared/disappeared (by
        code), COUNT changes on finding codes present in both runs (a code
        going 5x -> 6x is drift too -- the set-based blind spot pinned in
        commit 76af7a6, fixed 2026-08-11), and metric drift beyond a noise
        threshold. Exit code is non-zero only for the one low-noise,
        high-confidence signal this script is willing to call a real
        regression outright: a "block"-severity finding that was not there
        before -- including one MORE instance of a block code the baseline
        already carried. Everything else is reported, not enforced -- read
        it, don't just check the exit code.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from digitizer_core import PipelineConfig, digitize  # noqa: E402
from digitizer_core.preflight import run_preflight  # noqa: E402

TESTDATA = ROOT / "testdata"
OUT = TESTDATA / "corpus_scorecard_baseline.json"

FIXTURES = [
    "bg_uncertain.png",
    "logo_alpha.png",
    "logo_whitebg.png",
    "ribbon_curve.png",
    "photo/drone_render.png",
    "photo/enthusiast_logo.png",
    "photo/fur_ramp.png",
    "photo/gradient_ramp_linear.png",
    "photo/gradient_ramp_radial.png",
    "photo/photo_scene_stub.png",
    "photo/photo_subject_stub.png",
    "photo/region_blobs.png",
    "photo/repro_gradient_white_icon.png",
    "photo/summit_badge.png",
]

# Two garments covering two distinct fabric presets (pique_knit / structured_cap
# via fabrics.GARMENT_FABRIC) at the width nearly every test in this repo already
# defaults to -- not exhaustive, just enough fabric/geometry diversity to catch
# a change that only shows up under compensation or a different stitch budget.
MATRIX = [
    {"target_width_mm": 80.0, "garment_id": "left_chest"},
    {"target_width_mm": 80.0, "garment_id": "hat_front"},
]

# Metric drift below this fraction of the baseline value is noise (raster/
# resample quantisation, float rounding) -- not worth a report line.
_METRIC_NOISE_FRAC = 0.05


def _run_key(fixture: str, cfg_kw: dict) -> str:
    return f"{fixture} @ {cfg_kw['target_width_mm']:g}mm/{cfg_kw['garment_id']}"


def _score_one(fixture: str, cfg_kw: dict) -> dict:
    path = TESTDATA / fixture
    cfg = PipelineConfig(**cfg_kw)
    try:
        result, plan = digitize(path, cfg)
        report = run_preflight(result, plan, cfg, image=path)
    except Exception as exc:  # noqa: BLE001 -- one bad fixture must not sink the run
        return {"error": f"{type(exc).__name__}: {exc}"}
    return {
        "score": report["score"],
        "grade": report["grade"],
        # code+severity only -- prose "message" text can be reworded for
        # clarity without any real geometry change, and would just make
        # every diff noisy with wording churn instead of real signal.
        "findings": sorted(f"{f['code']}:{f['severity']}" for f in report["findings"]),
        "metrics": report["metrics"],
    }


def capture() -> dict:
    scorecard = {}
    for fixture in FIXTURES:
        for cfg_kw in MATRIX:
            key = _run_key(fixture, cfg_kw)
            scorecard[key] = _score_one(fixture, cfg_kw)
            row = scorecard[key]
            if "error" in row:
                print(f"{key}: ERROR {row['error']}")
            else:
                print(f"{key}: grade={row['grade']} score={row['score']} "
                      f"findings={len(row['findings'])}")
    return scorecard


def _finding_changes(old: list[str], new: list[str]
                     ) -> tuple[list[str], list[str], list[str], bool]:
    """Count-aware findings comparison. -> (appeared, resolved, count_lines,
    new_block).

    `appeared`/`resolved` are the codes present in only one run — the same
    lists the old set-based diff printed, so that half of the output format
    is unchanged. `count_lines` is the half the set diff could not see
    (pinned in commit 76af7a6): a "{code}:{severity}" string present in BOTH
    runs at different multiplicities, e.g. fix #6.1 taking drone_render from
    5 THREAD_MATCH_POOR findings to 6 while `diff` reported only a metric
    delta. The baseline already stores findings as a sorted LIST, duplicates
    preserved, so no baseline format change is needed — only this comparison
    ever collapsed them.

    `new_block` is True when the new run carries MORE instances of any
    ":block" code than the baseline did — a brand-new block code, or one
    more of an existing one. Both are "a block finding that was not there
    before", the one signal diff() hard-fails on.
    """
    oc, nc = Counter(old), Counter(new)
    appeared = sorted(k for k in nc if k not in oc)
    resolved = sorted(k for k in oc if k not in nc)
    count_lines = [f"{k}: x{oc[k]} -> x{nc[k]}"
                   for k in sorted(oc.keys() & nc.keys()) if oc[k] != nc[k]]
    new_block = any(k.endswith(":block") and nc[k] > oc.get(k, 0) for k in nc)
    return appeared, resolved, count_lines, new_block


def _metric_deltas(old: dict, new: dict) -> list[str]:
    lines = []
    for k in sorted(set(old) & set(new)):
        a, b = old.get(k), new.get(k)
        if not isinstance(a, (int, float)) or not isinstance(b, (int, float)):
            continue
        if isinstance(a, bool) or isinstance(b, bool):
            continue
        if a == b:
            continue
        denom = abs(a) if a else max(abs(b), 1e-9)
        if abs(b - a) / denom < _METRIC_NOISE_FRAC:
            continue
        lines.append(f"    {k}: {a} -> {b}")
    return lines


def diff() -> int:
    if not OUT.exists():
        print(f"no baseline at {OUT} -- run `capture` first.", file=sys.stderr)
        return 2
    baseline = json.loads(OUT.read_text(encoding="utf-8"))

    hard_fail = False
    any_report = False
    for fixture in FIXTURES:
        for cfg_kw in MATRIX:
            key = _run_key(fixture, cfg_kw)
            old = baseline.get(key)
            new = _score_one(fixture, cfg_kw)
            if old is None:
                print(f"{key}: NEW fixture/config, not in baseline -- run capture "
                      f"to adopt it.")
                any_report = True
                continue
            if "error" in new:
                print(f"{key}: ERROR {new['error']}")
                hard_fail = True
                any_report = True
                continue
            if "error" in old:
                old = {"score": None, "grade": None, "findings": [], "metrics": {}}

            lines = []
            if old["score"] != new["score"]:
                arrow = "worse" if new["score"] < old["score"] else "better"
                lines.append(f"  score: {old['score']} -> {new['score']} ({arrow})")
            if old["grade"] != new["grade"]:
                lines.append(f"  grade: {old['grade']} -> {new['grade']}")

            # Count-aware since 2026-08-11 (`_finding_changes`) -- the blind
            # spot commit 76af7a6 pinned here, where the old set difference
            # collapsed duplicate "{code}:{severity}" strings and answered
            # "no finding drift" across a real 5 -> 6 THREAD_MATCH_POOR move.
            appeared, resolved, count_lines, new_block = _finding_changes(
                old["findings"], new["findings"])
            if appeared:
                lines.append(f"  findings APPEARED: {appeared}")
            if resolved:
                lines.append(f"  findings resolved: {resolved}")
            for change in count_lines:
                lines.append(f"  finding count changed: {change}")
            if new_block:
                hard_fail = True

            lines.extend(_metric_deltas(old["metrics"], new["metrics"]))

            if lines:
                any_report = True
                print(f"{key}:")
                for line in lines:
                    print(line)

    if not any_report:
        print("no drift against the baseline.")
    return 1 if hard_fail else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mode", choices=["capture", "diff"])
    args = ap.parse_args()

    if args.mode == "capture":
        scorecard = capture()
        OUT.write_text(json.dumps(scorecard, indent=1, sort_keys=True), encoding="utf-8")
        print(f"wrote {OUT}")
        return 0
    return diff()


if __name__ == "__main__":
    sys.exit(main())
