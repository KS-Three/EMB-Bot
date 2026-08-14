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
