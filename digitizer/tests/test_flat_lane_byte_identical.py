"""The hard invariant: adding stage 0 (classifier) and the gradient blend
tier must not change ONE byte of output for any flat-classified design.

`testdata/flat_lane_golden.json` was captured by
`tools/capture_flat_lane_golden.py` BEFORE stage0_classify.py or
stage6_blend.py existed (see that script's own docstring — do not re-run it
now, that would defeat what this test pins). This test re-runs the same
fixtures through today's pipeline and asserts an exact match: shape ids,
areas, warnings, and every emitted stitch coordinate.

If this test ever goes red, the change under review is wrong — not this
test. See CLAUDE.md's hard-stop facts and
docs/superpowers/plans/2026-08-02-photo-digitizing-steps1-2.md.

**One documented exception (2026-08-04):** the `logo_whitebg.png` and
`photo/enthusiast_logo.png` entries were deliberately re-captured — not
regenerated wholesale, only those two keys — for the enclosed-background
restore fix (`docs/superpowers/plans/2026-08-04-enclosed-background-
restore-design.md`). Both fixtures have a BACKGROUND_ENCLOSED region, and
that fix's whole point is that such a region now becomes a real, tagged,
unstitched-by-default `Region` instead of silently vanishing — so their
snapshots (`shape_ids`/`areas_mm2` for `logo_whitebg.png`; those plus a
couple of small-region-absorb warnings and stitch coords for
`enthusiast_logo.png`, whose enclosed components are individually
sub-detail and get pulled into stage 3's ordinary absorb/drop handling)
were EXPECTED to move. `logo_alpha.png` (also enclosed, but already
failing here for an unrelated, pre-existing environment reason — see
COOKBOOK.md) and `ribbon_curve.png` (no enclosed region) were left
untouched; `stitch_count` for `logo_whitebg.png` and every byte of its
DST export are unchanged (verified separately in
`tests/test_stages.py`/`tests/test_pushcomp.py`) — only the NEW region's
own bookkeeping entries moved.

**Exception TAKEN 2026-09-03, defect 23 (rail dents):** the `logo_alpha.png` and
`ribbon_curve.png` entries were re-captured after `stage6_satin._rail_points`
stopped shrinking an overshooting rail to 0.85x and put it on the artwork
edge along its own normal (with a micron of containment tolerance). alpha's
one satin column keeps its 1968 stitches with rails ~0.08 mm further out;
ribbon 1001 -> 999. Region ids, areas and warnings unmoved; `logo_whitebg.png`
(byte-identical) is the control; the pre-change tree (main at 70df648)
reproduced both old entries on this machine before the capture
(`tools/recapture_flat_lane_key.py --pre-change-tree`). `enthusiast_logo`
stays the platform red.

**Exception TAKEN 2026-09-03, defect 25 (fill dust):** the `logo_whitebg.png`
and `logo_alpha.png` entries were re-captured after `stitches.split_long_moves`
gained a micron of tolerance — it had been halving every fill step that
measured 3.0000000000000004 mm against the 3.0 mm cap (180 of whitebg's 1520
fill steps, 104 of alpha's), so `stitch_count` 2162 → 1982 and 2072 → 1968.
Region ids, areas and warnings unmoved; `ribbon_curve.png` (no fill) is the
untouched control and reproduced; the pre-change tree (main at e2aa965)
reproduced both old entries on this machine before the capture
(`tools/recapture_flat_lane_key.py --pre-change-tree`). `enthusiast_logo`
stays the platform red.

**Third exception, TAKEN (2026-09-03):** the `logo_whitebg.png` entry was
re-captured for fill travel under cover (`PipelineConfig.fill_travel_under_
cover`, default ON by Kent's flip): the fill's column order now prefers a
next column reachable over ground not yet sewn, and a bridge that would lie
on finished fill is routed through unsewn ground. Travel is exactly what
moves — 2166 -> 2162 stitch coords, four fewer travel penetrations, region
ids, areas and warnings unmoved — and `tools/recapture_flat_lane_key.py
--pre-change-tree` (a worktree at origin/main f4009a6, whose digitizer_core
is identical to baf702c) reproduced the old golden byte-for-byte first, with
`ribbon_curve.png` as the untouched control. `enthusiast_logo`'s entry did
not move (its fill has no travel at all) and stays as it was.

**Second exception, SANCTIONED BUT NOT YET TAKEN (2026-08-14):** the
`photo/enthusiast_logo.png` entry is stale as of PR #146 (the pro-parity satin
work: junction entry walk + corner-fork removal —
`docs/pro-parity-program-2026-08-14.md`). That work exists to change where
satin columns start and end, so it moves letterform stitches by construction,
which is exactly what this test is for. **This test and its
`test_stage2_photo_segment` twin are therefore expected red on CI until the key
is re-captured — that is the only red they explain.**

The re-capture was earned before being authorised: on this fixture the new
output has LESS bare fabric (18.32 -> 17.22 mm², 4.75% -> 4.46% of shape area)
from FEWER stitches (2363 -> 2350), one fewer exposed travel run (2 -> 1) and
three more underlay runs (35 -> 38), with the rendered letterforms equally
legible and the remaining holes the same pre-existing ones in the badge. The
delta is 13 stitches plus ONE of 31 region areas moving 0.0576 mm² (0.3784 ->
0.3208, a sub-detail speck); `shape_ids` and `warnings` do not move.

It is NOT yet taken because **it cannot be taken on any machine.** The remote
dev container drifts from this file's pinned values on this specific fixture —
20 of 2363 coords, up to 0.16 mm, in the photo lane's segmentation, unchanged
by pinning numpy to the exact requirements version. Capturing there would write
that drift into the golden and turn CI red for everyone. Note the trap: the
flat-lane fixtures `ribbon_curve.png` and `logo_whitebg.png` reproduce
byte-for-byte in that same container, so they look like valid controls and are
not — they do not exercise the photo lane.

Use `tools/recapture_flat_lane_key.py` with `--pre-change-tree` pointed at a
checkout from before PR #146. It re-captures this one key only, and refuses to
write unless that machine first reproduces THIS key byte-for-byte on the old
engine — which is the proof that what moves afterwards is the engine and not
the machine.

**Third exception, TAKEN 2026-08-15:** the `logo_whitebg.png` key was
re-captured for the stage 6 travel fix. `_inset_ring` built the travel guide,
found the 0.6 mm inset had shattered the region into fragments, and kept only
the largest — on becker_hat_small that is one piece of 59, holding 28% of the
shape, leaving the other 72% with nothing to travel along and reachable only by
lifting the needle. It now keeps every fragment's ring and picks the one
serving both ends, and routes along a ring's own VERTICES instead of samples
taken every `TRAVEL_STITCH_MM`, because a chord across a concave corner leaves
the shape. `travel_path` now verifies containment before returning, which is
what caught that second bug: the old single-ring code, handed a guide on the far
side of a closed neck, would run along it and then strike out across bare cloth
to reach its target. On becker_hat_small it did that 31 times, and every one of
them was being counted as thread-down travel.

On THIS fixture the whole delta is ONE extra travel penetration, 2165 -> 2166.
`shape_ids`, `areas_mm2`, `warnings` and the trim/jump flag counts (153 each) do
not move. The re-capture used `--pre-change-tree` against a worktree at the
previous commit, which reproduced this key byte-for-byte on this machine first,
so the one stitch is the engine and not the environment. `ribbon_curve.png`
reproduces exactly before and after and is the control: the change is confined
to fills whose inset actually fragments.

**Fourth exception, TAKEN 2026-08-17 — the second exception's sanction finally
executed:** the `photo/enthusiast_logo.png` entry was re-captured for the
PR #157 merge, which restored the PR #146 satin stack that sanction covered,
plus the satin/travel work that accumulated with it (junction entry walk,
corner-fork removal, junction-free DT width, the stage-6 travel fix above).
The delta is 2363 -> 2351 stitches and ONLY `stitch_count`/`stitch_coords`
move: `shape_ids`, `warnings` and all 31 `areas_mm2` are unchanged — tighter
than the 2026-08-14 sanction anticipated (the 0.3784 -> 0.3208 area move it
predicted does not occur on the merged stack). Letterforms verified equally
legible from stage-6 renders of both engines.

The capture was taken on an ubuntu-latest runner — the platform whose CI
judges this golden, satisfying the ROADMAP standing item that goldens are
never captured on Windows — by `tools/recapture_flat_lane_key.py` with
`--pre-change-tree` at main before the merge (`0870c76`), which reproduced
this key byte-for-byte there first, so the delta is the engine and not the
machine. Evidence: workflow run 32060082886 on
`claude/recapture-enthusiast-golden` (temporary workflow, removed with the
same commit that landed this golden); its `recapture-evidence` artifact holds
the three-tree attribution log and the renders. The
`claude/satin-gate-attribution` tip (`2729ea5`, the promotion path `45d817a`)
produces byte-identical output to main on this fixture — the elongation floor
keeps the benchmark star `Sff37b029` out, as that commit designed — so this
one capture serves both branches.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from digitizer_core import PipelineConfig
from digitizer_core.pipeline import digitize

TESTDATA = Path(__file__).resolve().parent.parent / "testdata"
GOLDEN = json.loads((TESTDATA / "flat_lane_golden.json").read_text(encoding="utf-8"))


def _snapshot(name: str) -> dict:
    result, plan = digitize(TESTDATA / name, PipelineConfig(target_width_mm=80.0))
    return {
        "shape_ids": sorted(r.shape_id for r in result.regions),
        "areas_mm2": sorted(round(r.area_mm2, 4) for r in result.regions),
        "warnings": sorted(
            f"{w['code']}:{w.get('count', '')}" for w in result.warnings
        ),
        "stitch_count": sum(len(r.points) for _, r in plan.iter_runs()),
        "stitch_coords": [
            [round(x, 4), round(y, 4), r.kind, r.jump, r.trim]
            for _, r in plan.iter_runs()
            for x, y in r.points
        ],
    }


@pytest.mark.parametrize("fixture", sorted(GOLDEN.keys()))
def test_flat_lane_is_byte_identical_to_the_pre_change_golden(fixture):
    assert _snapshot(fixture) == GOLDEN[fixture]


def test_golden_file_actually_covers_something():
    """A guard against the golden file silently becoming empty (e.g. a
    capture-script bug) and this whole test module passing vacuously."""
    assert len(GOLDEN) == 4
    for name, snap in GOLDEN.items():
        assert snap["stitch_count"] > 0, f"{name}: golden has zero stitches"


def test_every_golden_fixture_still_classifies_as_flat():
    """The invariant only means anything if these fixtures actually take the
    unchanged code path — if stage 0 ever misclassifies one of them as
    gradient/photo, this test catches that BEFORE the byte-identical
    assertions above would (which would then be comparing against a golden
    captured under different, and now wrong, routing)."""
    from digitizer_core.stage0_classify import classify

    for name in GOLDEN:
        result = classify(TESTDATA / name, PipelineConfig())
        assert result.class_ == "flat", f"{name} classified as {result.class_!r}, not flat"
