"""Machine-readable warning codes (blueprint v2.1: UI switches on codes, never prose).

Every warning the pipeline emits is {"code": <one of these>, "message": str,
and optional extra keys documented per code}. Codes are append-only — never
renumber or reuse.
"""

# Stage 0 (input classification — docs/superpowers/plans/2026-08-02-photo-digitizing-steps1-2.md)
CLASSIFIED_GRADIENT = "CLASSIFIED_GRADIENT"            # routed to the blend fill tier instead of flat quantize
CLASSIFIED_PHOTO_SUBJECT = "CLASSIFIED_PHOTO_SUBJECT"  # portrait/pet/product; no dedicated handling yet (step 3+)
CLASSIFIED_PHOTO_SCENE = "CLASSIFIED_PHOTO_SCENE"      # scenery/landscape; no dedicated handling yet (step 6+)
CLASSIFICATION_UNCERTAIN = "CLASSIFICATION_UNCERTAIN"  # below the confidence floor; treated as flat rather than guessed

# Stage 1
BACKGROUND_UNCERTAIN = "BACKGROUND_UNCERTAIN"      # border flood intruded deep past the artwork margin
INPUT_LOW_RESOLUTION = "INPUT_LOW_RESOLUTION"      # px_per_mm below floor even after capped upscale
BACKGROUND_ENCLOSED = "BACKGROUND_ENCLOSED"        # enclosed bg-colored region treated as hole (review-toggleable)

# Stage 1.5 (photo prep — photo plan §2 rows 3-4, build step 3 first slice)
# Info, not a problem: tone prep + texture kill ran on this photo-classified
# design. extra: {"technique": str, "fallback": bool (rolling_guidance
# requested but contrib absent), "kill_px": int, "tone_ms": float,
# "texture_ms": float}
PHOTO_PREP_APPLIED = "PHOTO_PREP_APPLIED"

# Stage 1.5 (YuNet face priors — photo plan §2 row 2). Both ride the same
# photo_prep double gate as PHOTO_PREP_APPLIED above.
# Info, not a problem: faces were detected and get protective treatment
# (face-local merge-threshold drop, eyes/skin palette weights, the preflight
# face-size guard reads this). extra: {"count": int, "faces": [{"span_mm":
# [w, h], "score": float}, ...]}
PHOTO_FACES_DETECTED = "PHOTO_FACES_DETECTED"
# Face detection was gated ON but cannot run in this environment (model file
# missing/corrupt, or cv2.FaceDetectorYN absent) — the documented no-op
# fallback: the job proceeds exactly as if no faces existed.
# extra: {"reason": str}
PHOTO_FACE_PRIORS_UNAVAILABLE = "PHOTO_FACE_PRIORS_UNAVAILABLE"

# Stage 1.5 (rembg background removal — photo plan §2 row 1). Rides the
# photo_prep double gate PLUS its own opt-in flag
# (cfg.photo_prep_background_removal) — see config.py's comment for why a
# third gate on top of photo_prep.
# Info, not a problem: the isolated-venv rembg subprocess ran and grew
# stage 1's border-flood bg_mask with its subject-cutout mask. extra:
# {"background_frac_before": float, "background_frac_after": float}
PHOTO_BACKGROUND_REMOVED = "PHOTO_BACKGROUND_REMOVED"
# Background removal was gated ON but cannot run here (isolated rembg venv
# not built, worker script missing, subprocess crashed or timed out, a
# first-use model download failed, ...) — the documented no-op fallback:
# the job proceeds with stage 1's border-flood bg_mask only, unchanged.
# extra: {"reason": str}
PHOTO_BACKGROUND_REMOVAL_UNAVAILABLE = "PHOTO_BACKGROUND_REMOVAL_UNAVAILABLE"

# Stage 2
COLOR_CAP_APPLIED = "COLOR_CAP_APPLIED"            # more threads than max_colors; smallest layers reassigned

# Stage 2 (photo path) — docs/superpowers/plans/2026-08-02-photo-digitizing-step4-region-former.md
# info, not a problem. "count" is the real post-merge region count
# (len(kept)); "thread_colors" is the separate, usually-smaller number of
# chart spools the palette settled on (fixed 2026-08-04 — "count" used to
# report thread_colors under a message that claimed to report regions, see
# stage2_photo_segment.segment's inline comment at the warn() call site).
# extra: {"count": int, "thread_colors": int, "slic_segments": int, "merged_regions": int}
PHOTO_SEGMENT_REGION_COUNT = "PHOTO_SEGMENT_REGION_COUNT"
# Photo plan step 7 (palette k-medoids). Info: how many chart spools the
# weighted selection settled on, and the worst region's ΔE00 excess over its
# own nearest-thread floor. extra: {"colors": int, "regions": int, "max_excess_de00": float}
PHOTO_PALETTE_SELECTED = "PHOTO_PALETTE_SELECTED"

# Stage 3
DROPPED_SMALL_SHAPES = "DROPPED_SMALL_SHAPES"      # extra: {"count": int}
ABSORBED_SMALL_SHAPES = "ABSORBED_SMALL_SHAPES"    # extra: {"count": int}
EMPTY_THREAD_LAYER = "EMPTY_THREAD_LAYER"          # a thread's every region absorbed/dropped; layer removed

# Stage 4.5 (review-screen shape edits — the shape-layers contract v1)
SHAPES_DELETED_BY_USER = "SHAPES_DELETED_BY_USER"  # shapes the user removed in review; dropped after IDs were assigned. extra: {"count": int, "ids": list[str]}
SHAPE_EDIT_UNKNOWN_ID = "SHAPE_EDIT_UNKNOWN_ID"    # a deleted/overridden shape_id matched nothing (the art may have changed under the edit). extra: {"count": int, "ids": list[str]}
# Shape identity edits (contract v1.5, `merge_shape_ids`/`split_shapes`) — the
# other half of the boundary-reshape gap: these change the SET of shapes, not
# one shape's attributes, so they get their own codes distinct from the two
# above. extra: {"count": int, "groups"/"ids": list, "new_ids": list[str]}
SHAPES_MERGED_BY_USER = "SHAPES_MERGED_BY_USER"    # 2+ same-layer shapes unioned into one new shape.
SHAPE_SPLIT_BY_USER = "SHAPE_SPLIT_BY_USER"        # one shape cut by a line into two new shapes.

# Stage 5 (overlap resolution / pull compensation)
HOLE_NEARLY_CLOSED = "HOLE_NEARLY_CLOSED"          # pull comp would swallow a hole; held open. extra: {"count": int}
SAME_THREAD_SHAPES_MERGED = "SAME_THREAD_SHAPES_MERGED"  # pull comp would fuse two shapes of one thread; gap held open. extra: {"count": int}

# Stage 6 (stitch planning)
SHAPE_TOO_THIN_TO_FILL = "SHAPE_TOO_THIN_TO_FILL"  # narrower than a fill can hold; satin's job (step 4). extra: {"count": int}
SHAPE_NOT_STITCHED = "SHAPE_NOT_STITCHED"          # geometry produced no stitches at all. extra: {"count": int}
LONG_JUMPS_TRIMMED = "LONG_JUMPS_TRIMMED"          # travel could not stay inside the shape. extra: {"count": int}
SMALL_SHAPES_AS_RUN = "SMALL_SHAPES_AS_RUN"        # too small for fill or satin; sewn as run outlines instead. extra: {"count": int}

# Stage 6 (contour fill tier)
CONTOUR_RING_UNREACHABLE = "CONTOUR_RING_UNREACHABLE"  # contour left a bare patch wider than a ring spacing (measured, barecircle.py). extra: {"count": int, "rings": int}

# Stage 6 (border tier)
BORDER_SKIPPED_TOO_NARROW = "BORDER_SKIPPED_TOO_NARROW"  # no room for an outline. extra: {"count": int}
BORDER_LIGHTENED = "BORDER_LIGHTENED"                    # column would not fit; bean run instead. extra: {"count": int}
# stage6_border's documented KNOWN LIMITATION — two bordered shapes of
# different colors abut, stage 5 makes their visible edges the same line, so
# each shape's own outline circuit would ride it at full density: a
# double-thick bar sewn in two threads. `stage7_sequence._yield_frontage` now
# fixes this automatically (sew-order tie-break: the shape sewn earlier keeps
# the line, the one sewn later insets its circuit off the shared seam before
# tracing it), so this WARNING now fires only for the residual case the
# automatic fix cannot resolve without deleting the later shape's border
# outright — its own frontage is entirely consumed by the retreat because it
# is hemmed in by an already-bordered neighbor on more than one side. That
# shape falls back to its unsuppressed geometry (a real border beats none)
# and is named here so the operator still has the manual escape
# (`Region.meta["border"] = False` on one side). extra: {"count": int,
# "pairs": list[[str, str]]}
BORDER_SEAM_SHARED = "BORDER_SEAM_SHARED"

# Stage 6 (appliqué tier) — docs/specialty-techniques-2026-08-01.md §2.12 gates.
# Every one of these is a gate the spec says "must be enforced", and every one
# describes something the operator will otherwise discover at the machine.
APPLIQUE_NO_FABRIC_VISIBLE = "APPLIQUE_NO_FABRIC_VISIBLE"
# Shape narrower than 2*|c_in| + 1.0 mm: the two inner cover rails meet and no
# appliqué fabric shows. Falls through to plain satin, and SAYS SO (§2.12).
# extra: {"count": int}
APPLIQUE_CUTTING_LINE_SUPPRESSED = "APPLIQUE_CUTTING_LINE_SUPPRESSED"
# Trim-in-place asked for, but the min inscribed diameter is under 12 mm and
# scissors do not fit. The cutting line is dropped (§2.6). extra: {"count": int}
APPLIQUE_FORCED_PRE_CUT = "APPLIQUE_FORCED_PRE_CUT"
# A hole under 15 mm cannot be trimmed in the hoop, so the piece is switched to
# pre-cut whatever was requested (§2.12). extra: {"count": int}
APPLIQUE_COVER_MARGINAL = "APPLIQUE_COVER_MARGINAL"
# The solved cover reaches less than m_edge past the outermost place the raw
# edge can land. §2.4 ships this at the "normal" default (0.05 mm of 0.50) and
# says so; it is the §2.15 "fabric peeking outside the satin" failure waiting
# to happen. extra: {"count": int, "headroom_mm": float}
APPLIQUE_PIECES_OVERLAP = "APPLIQUE_PIECES_OVERLAP"
# Two appliqué pieces overlap. Partial-cover arc suppression (§2.11) is not
# built, so two satins would stack on one band — 0.20 mm effective at the 0.40
# default, below the 0.30 fabric-damage floor. extra: {"count": int}
APPLIQUE_STEP_EMPTY = "APPLIQUE_STEP_EMPTY"
# A step generated no stitches. Its color change would vanish with it and the
# operator would lose an instruction — the §0.2 failure, caught upstream of the
# writer. extra: {"count": int}
APPLIQUE_COVER_WIDTH_CLAMPED = "APPLIQUE_COVER_WIDTH_CLAMPED"
# `solve_cover_width`'s [2.5, 5.0] mm clamp bound, not the tolerance-stack
# requirement — either §2.13's own 2.5 mm "absolute minimum (risky)" floor, or
# §2.12's named 5.0 mm snag-risk ceiling. `solve_cover_width` has always
# computed this in its own "clamped" field; no caller read it, so a design
# that hit either bound sewed with no record that the requirement and the
# stitched width disagree. extra: {"count": int, "width_mm": float,
# "bound": "floor" | "ceiling"}
APPLIQUE_PRECUT_TOO_NARROW = "APPLIQUE_PRECUT_TOO_NARROW"
# Pre-cut mode's own scissors/placement floor (§2.12: `min_inscribed_diameter
# >= 8mm`) — a DIFFERENT gate from `APPLIQUE_CUTTING_LINE_SUPPRESSED`'s 12mm
# trim-in-place floor above; the two are scoped to their own modes and never
# both fire on the same piece. Below 8mm, the piece the operator must hand-cut
# BEFORE placing it (there is no in-hoop trim step to fall back to) has a
# bottleneck too narrow for scissors to cut around cleanly. Measured by
# `narrowest_passage_diameter`, the same bottleneck-aware measure the
# trim-in-place gate uses, so a dog-bone-shaped pre-cut piece is caught the
# same way `APPLIQUE_CUTTING_LINE_SUPPRESSED` catches one. extra: {"count":
# int, "measured_mm": float, "floor_mm": float}


def warn(code: str, message: str, **extra) -> dict:
    w = {"code": code, "message": message}
    w.update(extra)
    return w
