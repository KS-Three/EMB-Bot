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

# Stage 2
COLOR_CAP_APPLIED = "COLOR_CAP_APPLIED"            # more threads than max_colors; smallest layers reassigned

# Stage 2 (photo path) — docs/superpowers/plans/2026-08-02-photo-digitizing-step4-region-former.md
PHOTO_SEGMENT_REGION_COUNT = "PHOTO_SEGMENT_REGION_COUNT"  # info, not a problem: extra: {"count": int}
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


def warn(code: str, message: str, **extra) -> dict:
    w = {"code": code, "message": message}
    w.update(extra)
    return w
