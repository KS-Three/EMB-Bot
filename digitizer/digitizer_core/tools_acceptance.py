"""Pure logic for `tools/acceptance_ab.py`, the phase-4 eyeball-loop harness
(spec decisions 1, 5, 6). Kept here, not in `tools/`, so it is importable by
tests without a `sys.path` hack — `tools/acceptance_ab.py` is the thin CLI
that does the actual HTTP wire work (POST /digitize, poll /jobs/{id}, POST
/export) over these two functions.

Nothing here touches the network or the filesystem: that split is the point
— the wire calls are exercised live against a running service (see the CLI
and task-6-report.md's smoke evidence), not re-mocked here.
"""
from __future__ import annotations

from .stage6_blend import RAMP_R2_MIN

# The one forced_class every variant shares: it is what routes a photo
# through the auto-tier (`auto_photo_tier` in pipeline.py picks streamline)
# and the auto-split (`effective_split_tonal`) on its own, with no other
# config needed — Task 3/4/5's own "forced_class" literal, unchanged here.
_FORCED_CLASS = "photo_subject"


def variant_matrix(sam2_available: bool) -> list[dict]:
    """The A/B arms this run puts every acceptance image through.

    Always the classical arm: `{"forced_class": "photo_subject"}` alone is
    enough to hit the auto-route (streamline + tonal split), so the variant
    config carries nothing else. The SAM2 arm is included only when the
    isolated venv actually looks runnable on this machine — a caller checks
    with `digitizer_core.stage2_sam2_segment.sam2_segmentation_unavailable_
    reason() is None` and passes the answer in; a machine without SAM2 still
    gets a contact sheet minus that one column instead of a job that fails
    mid-run.
    `photo_prep`/`photo_segment_sam2` are the exact two flags Task 5 proved
    live (evidence: debug_out/task5_live_job_sam2.json's `_meta.config_sent`)
    turn on tone/texture prep and route segmentation through SAM2 instead of
    the classical SLIC+merge path.

    The first three arms are an attribution LADDER — classical (neither
    flag) → classical_prep (prep only) → sam2 (prep + SAM2) — one flag
    flipped per rung, adjacent on the sheet, so prep's effect and SAM2's own
    effect each read as a single column-to-column delta. The classical_prep
    comment below carries the confound this ladder repairs and the measured
    evidence.

    The relaxed-speckle arm (Kent's 2026-08-23 answer funding the A/B —
    `docs/tonal-eng-measurements-2026-08-22.md` §1 for why the speckle gate,
    not the r² floor, is the blend tier's real off-switch on real art) sets
    `blend_speckle_r2_override` to `RAMP_R2_MIN` itself: every region whose
    fit already clears the floor passes the speckle gate too, which is the
    maximal honest contrast — the sheet shows exactly what trusting the fit
    over the texture looks like, and Kent's eyes rule on it. Stock stays the
    first column so the comparison is always present.
    """
    matrix = [
        {"tag": "classical", "config": {"forced_class": _FORCED_CLASS}},
        # The prep-matched control (added 2026-08-23). The sam2 arm was
        # CONFOUNDED from the day it was written: its config flips
        # `photo_prep` AND `photo_segment_sam2` together, so every
        # "sam2 vs classical" delta the sheet has ever shown measured two
        # independent changes at once — and a third-arm run on the four
        # acceptance portraits showed the bigger change is prep's, not
        # SAM2's. Pre-split regions, classical → classical_prep → sam2:
        # sparkler_dusk 23 → 61 → 5, baby_deck_laugh 24 → 78 → 14,
        # boat_dog_toddler 31 → 44 → 7, face_closeup_blur 6 → 19 → 3 — prep
        # alone roughly TRIPLES the classical route's region count. The
        # stop/stitch penalty the sheet had been charging to SAM2 is largely
        # prep's as well: prep turns on face detection, whose appended FDoG
        # detail block is worth 11,676 stitches on baby_deck_laugh and
        # ~3,950 on sparkler_dusk. Prep-matched, SAM2 actually REDUCES
        # stops on all four (91→72, 140→98, 96→90, 36→33). This arm exists
        # so prep and SAM2 can be attributed separately; without it the
        # harness answers only "is prep+SAM2 better than neither?", which
        # nobody asked.
        {
            "tag": "classical_prep",
            "config": {"forced_class": _FORCED_CLASS, "photo_prep": True},
        },
        {
            "tag": "relaxed_speckle",
            "config": {
                "forced_class": _FORCED_CLASS,
                "blend_speckle_r2_override": RAMP_R2_MIN,
            },
        },
        # The DEFAULT-route pair (added 2026-08-23, first real-photo run):
        # the toggle route sews tone via split_tonal_regions + streamline and
        # never consults the blend tier, so the speckle override is inert
        # there — measured byte-identical on the first three real portraits.
        # The blend tier (and therefore the funded speckle A/B) lives on the
        # route stage 0 actually sends real photos down: gradient. These two
        # arms show what a user who never touches the toggle gets, stock vs
        # relaxed, which is where the override can matter at all.
        {"tag": "default_stock", "config": {}},
        {
            "tag": "default_relaxed",
            "config": {"blend_speckle_r2_override": RAMP_R2_MIN},
        },
    ]
    if sam2_available:
        # Inserted as the ladder's third rung, not appended (2026-08-23):
        # tag and config are byte-for-byte what they have always been —
        # every measurement pinned to "sam2" stays valid — only the sheet
        # position moved, so the three ladder columns sit adjacent instead
        # of the SAM2 column landing past the speckle/default arms.
        matrix.insert(2, {
            "tag": "sam2",
            "config": {
                "forced_class": _FORCED_CLASS,
                "photo_prep": True,
                "photo_segment_sam2": True,
            },
        })
    return matrix


def sheet_row(file: str, variant: str, stats: dict) -> dict:
    """One contact-sheet row: `file`/`variant` identity plus the raw counts
    the caller measured for that (image, variant) run.

    Deliberately a pass-through, not a scorer — this harness is the eyeball
    loop the spec calls explicitly non-authoritative on the metric; a score
    number here would be exactly the "score decided it" shortcut the sheet
    exists to avoid. `stats` is expected to carry counts only (shapes,
    stitches, trims, threads, warnings, wall_s) — whatever it holds is
    echoed verbatim, so run_preflight's score never has a path onto the
    sheet even by accident.
    """
    row = {"file": file, "variant": variant}
    row.update(stats)
    return row
