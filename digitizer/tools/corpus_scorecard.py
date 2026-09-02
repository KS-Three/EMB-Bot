#!/usr/bin/env python
"""A standing, automated answer to "did this change make the output better
or worse" — the "Evaluation corpus & harness" gap MASTER_SCOPE.md tracks as
a cross-cutting issue: corpus-law recalibrations have always needed
one-off, by-hand validation ("manually re-running the digitizer suite and
eyeballing a handful of fixtures") because nothing scored the whole
committed fixture set and remembered the last score.

This is the harness half of that gap, not the corpus half: the 37-file
`scratch_corpus/` M2/M3 needs is still inaccessible (gitignored, empty in
every checkout). What IS available is the digitizer's own committed
`testdata/` fixtures (see FIXTURES below), and `digitizer_core.preflight.run_preflight` already
computes a rich per-design quality signal (0-100 score, letter grade, typed
findings, ~20 metrics) for one design at a time — this script is the part
that was missing: run it over every committed fixture, remember the result,
and diff a fresh run against that memory.

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
        run_preflight, and writes testdata/corpus_scorecard_baseline.json,
        stamped with `captured_at_commit`/`captured_date` so staleness is
        measured, not remembered (see COOKBOOK.md, "Recapturing
        corpus_scorecard_baseline.json"). Re-run this deliberately, the same
        way tools/capture_flat_lane_golden.py works, whenever a change's new
        behaviour should become the new baseline rather than a regression to
        flag -- diff the old baseline against HEAD first and attribute every
        mover in the recapture commit message; an unattributed mover blocks
        the recapture.

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
import hashlib
import json
import subprocess
import sys
from collections import Counter
from datetime import date
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
    # the five photo-realistic fixtures (tools/make_photo_fixtures.py,
    # 2026-08-11) — in the matrix but NOT yet in the committed baseline;
    # `diff` reports them as NEW until the next deliberate recapture.
    "photo/photo_chrome_specular.png",
    "photo/photo_dof_meadow.png",
    "photo/photo_grass_macro.png",
    "photo/photo_owl_pale.png",
    "photo/photo_scene_stub.png",
    "photo/photo_subject_stub.png",
    "photo/photo_sunset_backlit.png",
    "photo/region_blobs.png",
    "photo/repro_gradient_white_icon.png",
    "photo/summit_badge.png",
    # --- Real customer artwork, delivered by Kent 2026-08-15 -----------------
    # The first fixtures in this corpus that are not synthetic or hand-picked:
    # eight files pulled straight from the jobs Kent actually digitizes. This
    # is the "labelled corpus" half of MASTER_SCOPE's evaluation-corpus gap,
    # which had been open since 2026-08-01 waiting on exactly this.
    #
    # They earn their place by disagreeing with the synthetic set. Stage 0
    # routes SIX of the seven logos to the GRADIENT lane, not the flat lane
    # (measured 2026-08-15) -- real logo art carries JPEG ringing, anti-aliased
    # edges and soft shading that the synthetic flat fixtures do not have. Any
    # claim about "flat spot-colour art" tuned only on the synthetic set is
    # therefore untested against the input this product actually receives.
    "becker_marine_logo.png",
    # Classified photo_scene despite being a clean two-colour script wordmark
    # on white -- a misroute, kept deliberately so the bug has a fixture.
    "logo_script_tires.png",
    "photo/logo_bridge_bar.jpg",
    # NOT "photo/logo_drone_thermal_badge.png" -- it is byte-identical to
    # photo/drone_render.png above, so enrolling both scored one design twice
    # and gave it double weight in every corpus-wide number. Known since
    # 2026-08-23 (tools/pro_parity/blockcensus.py documents it and includes
    # the image once); this list kept both until the 2026-09-02 recapture,
    # which is the first write that could drop a row without orphaning the
    # baseline. `_assert_no_duplicate_art` re-checks it at runtime rather
    # than trusting this comment -- if the two files ever DIVERGE, the badge
    # is real customer art again and belongs back in the list.
    "photo/logo_gaulke_roofing.png",
    "photo/logo_golden_tee.jpg",
    "photo/logo_hotel_fremont.webp",
    # A phone screenshot, status bar and UI chrome included, because that is
    # how this one arrived from the customer.
    "photo/screenshot_phone_ui_golke.jpg",
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


def _assert_no_duplicate_art() -> None:
    """No two FIXTURES entries may be the same bytes. Checked, not remembered.

    `photo/logo_drone_thermal_badge.png` was byte-identical to
    `photo/drone_render.png` and both were enrolled, so one design carried
    twice the weight of every other in every aggregate this tool produces --
    including the baseline it writes. The comment in FIXTURES says so; this
    says so at runtime, which is the difference between a note and a guard,
    and it is the pattern `tools/pro_parity/blockcensus._dup_note` already
    uses for the same pair.

    Prints rather than raises: a duplicate is a corpus-composition problem for
    a person to resolve (which copy is the real customer file?), not a reason
    to refuse to score anything.
    """
    seen: dict[str, str] = {}
    for fixture in FIXTURES:
        path = TESTDATA / fixture
        if not path.exists():
            continue
        digest = hashlib.md5(path.read_bytes()).hexdigest()
        if digest in seen:
            print(f"[warn] {fixture} is byte-identical to {seen[digest]} — "
                  f"this corpus scores that one design twice. Drop one name "
                  f"from FIXTURES at the next recapture.")
        else:
            seen[digest] = fixture


def _run_key(fixture: str, cfg_kw: dict) -> str:
    return f"{fixture} @ {cfg_kw['target_width_mm']:g}mm/{cfg_kw['garment_id']}"


def _git_head_commit() -> str:
    """The commit this capture ran against — so a later `diff` (or a human
    reading the baseline) can tell how stale the ruler is instead of having
    to remember, per COOKBOOK's "Recapturing corpus_scorecard_baseline.json"
    rule. Not caught by the per-fixture `_run_key` loop: this key lives
    alongside the fixture rows, not among them (see `capture`)."""
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()


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
    # Before writing a new ruler, check the corpus is not weighting one design
    # twice -- a recapture is exactly when that gets baked in for weeks.
    _assert_no_duplicate_art()
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
    # Stamp the capture commit/date so staleness is measured, not
    # remembered -- neither key collides with a `_run_key` string, and
    # `diff` only ever looks up baseline entries by that key, so this is
    # additive alongside the fixture rows, not a format change.
    scorecard["captured_at_commit"] = _git_head_commit()
    scorecard["captured_date"] = date.today().isoformat()
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
