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

    `bound_shade` follows that ladder (2026-08-23): the shade-palette-bind
    experiment's instrument, identical to `classical` except for the bind, so
    the comparison Kent judges is against column one. It sits after the
    ladder rather than beside `classical` because the ladder's adjacency is
    load-bearing for attribution and this arm's is not — a two-column read
    works from anywhere on the sheet. Its inline comment carries the contract
    and the plan-doc pointer.

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
        # `shade_palette_bind=False` is EXPLICIT here as of 2026-08-24. It used
        # to be inherited from the config default, but Kent's ruling that day
        # flipped that default ON — so without this line `classical` would
        # silently BECOME `bound_shade` and the sheet would be comparing the
        # bound route against itself. This arm's whole job is to hold the
        # pre-ruling route as column one, so every future sheet still shows
        # what the bind bought.
        {"tag": "classical",
         "config": {"forced_class": _FORCED_CLASS, "shade_palette_bind": False}},
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
            "config": {"forced_class": _FORCED_CLASS, "photo_prep": True,
                       "shade_palette_bind": False},
        },
        # The shade-palette-bind arm (2026-08-23, EXPERIMENT — option (a) of
        # docs/superpowers/plans/2026-08-23-shade-palette-binding.md, the
        # contact-sheet run that doc says settles it): identical route to
        # `classical` except `shade_palette_bind=True`, so the per-shade
        # chart snap stays inside the plan's own palette and adjacent
        # same-spool shades merge. Second column, directly beside
        # `classical`, because the ONE comparison this arm exists for is
        # Kent's eyes on today's route vs the bound route — shade
        # flattening against a loadable cone list. Not a shipped default
        # and not a recommendation: the arm is the instrument, the verdict
        # is Kent's.
        {
            "tag": "bound_shade",
            "config": {"forced_class": _FORCED_CLASS,
                       "shade_palette_bind": True},
        },
        # (a)+(b) — Kent's 2026-08-23 decision on the same plan doc: the
        # bind AND the shade-aware palette (`shade_palette_demand` feeds
        # stage-2 proxy shade demand into `select_palette`, so the palette
        # contains the anchors the bound shades land on). Directly after
        # `bound_shade` so the sheet reads bind-alone -> bind-plus-demand
        # as one column step; the comparison that matters is the pair of
        # them against `classical` (today's route). The cone-count column
        # is load-bearing for THIS arm in a way it is not for the others:
        # demand pressure trips the palette's overflow allowance more
        # eagerly (measured offline: a 7-cone photo's proxy re-fit spent 14
        # where an oracle wanted 10), and cones cost money — the arm exists
        # to put that price next to the shade-fidelity gain, not to hide it.
        {
            "tag": "bound_shade_demand",
            "config": {"forced_class": _FORCED_CLASS,
                       "shade_palette_bind": True,
                       "shade_palette_demand": True},
        },
        # The shade darkness-axis arm (2026-08-24, EXPERIMENT — defect 1 of
        # docs/superpowers/plans/2026-08-23-region-identification.md).
        # Paired with `shade_palette_bind` deliberately: measured alone the
        # normalisation looks expensive (cones 43->53, stops 75->94 on
        # sparkler_dusk), and measured WITH the bind — which is the shipped
        # default since Kent's ruling that day — the cost mostly disappears
        # (cones 15->15, stitches 14290->14336) because the bind absorbs the
        # newly-distinct shades onto the same palette. Judging it unbound
        # would price a combination nobody will ship.
        {
            "tag": "bound_axis",
            "config": {"forced_class": _FORCED_CLASS,
                       "shade_palette_bind": True,
                       "shade_axis_normalize": True},
        },
        {
            "tag": "relaxed_speckle",
            "config": {
                "forced_class": _FORCED_CLASS,
                "blend_speckle_r2_override": RAMP_R2_MIN,
                # Pinned unbound with the rest of the forced-class set
                # (2026-08-24) so this arm still isolates the speckle
                # override against `classical` and nothing else.
                "shade_palette_bind": False,
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
        #
        # These two DELIBERATELY inherit `shade_palette_bind` from the config
        # default, where every arm above now pins it False (2026-08-24).
        # Showing the shipped default is the entire job of this pair, so when
        # that default moves, these arms must move with it — pinning them
        # would defeat the point.
        {"tag": "default_stock", "config": {}},
        {
            "tag": "default_relaxed",
            "config": {"blend_speckle_r2_override": RAMP_R2_MIN},
        },
    ]
    if sam2_available:
        # Inserted as the ladder's third rung, not appended (2026-08-23):
        # only the sheet position moved, so the three ladder columns sit
        # adjacent instead of the SAM2 column landing past the
        # speckle/default arms.
        #
        # `shade_palette_bind=False` added 2026-08-24 with the rest of the
        # forced-class set. This one line is NOT config drift: the default
        # flipped ON that day, so leaving it out would have changed what this
        # arm measures. Pinning it False is what keeps every prior
        # measurement tagged "sam2" comparable, and keeps the ladder's three
        # rungs differing in prep and SAM2 alone — which is the attribution
        # the ladder exists for.
        matrix.insert(2, {
            "tag": "sam2",
            "config": {
                "forced_class": _FORCED_CLASS,
                "photo_prep": True,
                "photo_segment_sam2": True,
                "shade_palette_bind": False,
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
