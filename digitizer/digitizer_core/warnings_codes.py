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
BACKGROUND_ABSENT = "BACKGROUND_ABSENT"            # full-bleed art: no background found, whole canvas stitched. extra: {"agreement": float}

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

# Stage 2 (photo path) — SAM2 region former. Rides its own opt-in flag
# (cfg.photo_segment_sam2) PLUS a photo_subject/photo_scene classification;
# "gradient" deliberately does not qualify (see config.py's comment).
# Info, not a problem: the isolated-venv SAM2 subprocess ran and its instance
# masks became this design's regions instead of SLIC+RAG's superpixel merge.
# extra: {"raw_masks": int, "regions": int, "checkpoint": str}
PHOTO_SAM2_SEGMENTED = "PHOTO_SAM2_SEGMENTED"
# SAM2 segmentation was gated ON but cannot run here (isolated SAM2 venv not
# built, worker script missing, checkpoint download failed, subprocess crashed
# or timed out, output unusable, ...) — the documented fallback: the classical
# SLIC+RAG region former runs instead and the job still completes.
# extra: {"reason": str}
PHOTO_SAM2_SEGMENTATION_UNAVAILABLE = "PHOTO_SAM2_SEGMENTATION_UNAVAILABLE"

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

# Stage 4 (post-vectorization thread re-validation)
THREAD_RESNAPPED_AFTER_DRIFT = "THREAD_RESNAPPED_AFTER_DRIFT"  # a shape's simplified polygon moved off the pixels its thread was chosen from; thread re-matched to what it now covers. extra: {"count": int, "ids": list[str], "worst_before_de00": float, "worst_after_de00": float}

# Stages 5-7 entry (pipeline.plan_stitches)
# The ONE seam where a region that survived all of stages 1-4 — it has an id,
# a thread, an area, and a row in the review screen — is removed from the
# machine's work: `meta["stitched"] is False`. Today that is the enclosed-
# background default (BACKGROUND_ENCLOSED's other half) or an explicit
# `shape_overrides[sid]["stitched"] = False`.
#
# Why it is a warning at all, when the skip is deliberate: until 2026-08-14
# this seam was SILENT, and the silence was load-bearing. `compact_layers`
# keeps a palette slot for any layer that still has a Region, stitched or not,
# so a layer whose every member was skipped left a cone in the color list that
# nothing sews — and `adapter._thread_name` reads the palette BY BLOCK INDEX,
# so every block after that phantom entry was labelled with the wrong thread's
# name (measured on the pro corpus: 22 of 96 blocks across 6 of 23 designs —
# `golf_hat` block 3 shipped as "0020 Tangerine", a black cone carrying the
# orange cone's name). Nothing
# printed a word about any of it. A planned color that vanishes on the way to
# the needle is exactly the failure class COOKBOOK.md's "hard-won lessons"
# says must never be quiet again, so it names the shapes and their area.
# extra: {"count": int, "ids": list[str], "threads": list[str],
#         "total_mm2": float, "largest_mm2": float,
#         "enclosed_background": int, "by_override": int}
SHAPES_LEFT_UNSEWN = "SHAPES_LEFT_UNSEWN"

# Stage 4/5 seam (pipeline.run_stages, after compact_layers)
# The sew-order palette is per LAYER — `compact_layers` reads each layer's
# thread out of stage 2's quantized palette. `revalidate_threads` (fix #6.3)
# runs BEFORE it and re-snaps individual shapes to a different spool, without
# moving them to another layer, so a layer can end up holding two threads and
# its palette entry naming a spool no shape in it carries. Stage 7 partitions
# blocks by (sew_index, step_key, thread) and is therefore right regardless —
# it is the palette, i.e. the cone list a human loads and the review screen
# shows, that is wrong. Measured on the pro corpus 2026-08-14: 5 of 23
# designs, worst `hotel_fremont_patch` (layer 0 lists 1755 Hyacinth while
# 1,813 of its 1,815 mm² sew in 4071).
# extra: {"count": int, "layers": list[int], "ids": list[str],
#         "listed": list[str], "actual": list[str]}
PALETTE_THREAD_MISMATCH = "PALETTE_THREAD_MISMATCH"

# Stage 5 (overlap resolution / pull compensation)
HOLE_NEARLY_CLOSED = "HOLE_NEARLY_CLOSED"          # pull comp would swallow a hole; held open. extra: {"count": int}
SAME_THREAD_SHAPES_MERGED = "SAME_THREAD_SHAPES_MERGED"  # pull comp would fuse two shapes of one thread; gap held open. extra: {"count": int}

# Stage 6 (stitch planning)
SHAPE_TOO_THIN_TO_FILL = "SHAPE_TOO_THIN_TO_FILL"  # narrower than a fill can hold; satin's job (step 4). extra: {"count": int}
# Geometry produced no stitches at all — raised by stage 5 (a shape that
# vanished under pull compensation) and by stage 7 (a shape no tier could
# fill). Stage 5's now names the shapes: extra: {"count": int, "ids":
# list[str], "threads": list[str], "total_mm2": float, "largest_mm2": float};
# stage 7's still carries {"count": int} only.
SHAPE_NOT_STITCHED = "SHAPE_NOT_STITCHED"
LONG_JUMPS_TRIMMED = "LONG_JUMPS_TRIMMED"          # travel could not stay inside the shape. extra: {"count": int}
SMALL_SHAPES_AS_RUN = "SMALL_SHAPES_AS_RUN"        # too small for fill or satin; sewn as run outlines instead. extra: {"count": int}

# Stage 2 (photo segmentation)
# A region owns exactly one thread, so a region whose own pixels span more
# tone than one thread can express sews as a flat average no matter what the
# fill tier does — Kent's owl body, 4200 mm2 spanning 81 points of L*, sewn
# as one pale mass. `split_tonal_regions` cuts those into parts that each get
# their own mean, palette weight and spool. Info-level: this is the pipeline
# doing its job, reported because it changes the region and colour counts the
# other segmentation warnings report.
# extra: {"count": int, "regions_before": int, "regions_after": int}
TONAL_REGIONS_SPLIT = "TONAL_REGIONS_SPLIT"

# pipeline.run_stages, the source_pixels gate (photo auto-routing, spec
# decision 3, 2026-08-18 — `pipeline.auto_photo_tier`). Sibling to
# TONAL_REGIONS_SPLIT above: that warning announces automatic TONE (Task 2),
# this one announces the automatic FILL TIER a photo_subject design picks up
# when the caller set neither `fill_technique` nor `detail_layer`
# themselves — streamline, plus the detail layer when stage 1.5 found faces.
# `photo_scene` and every non-photo class never fire this: `photo_scene`
# stays tatami in v1 (its tone already comes from TONAL_REGIONS_SPLIT), and
# an explicit caller choice always wins over the auto-route, silently, the
# same way it always did before this code existed.
# Info, not a problem: names WHAT the auto-route picked, for the Studio
# panel. extra: {"tier": str, "detail_layer": bool}
PHOTO_AUTO_TIER = "photo_auto_tier"

# Stage 6 (blend fill tier)
# CLASSIFIED_GRADIENT announces the blend ROUTING at classification time,
# before any region has been tested. Whether a region actually decomposes
# into thread shades is a separate, per-region question `detect_ramp`
# answers much later — and measured on a real photograph (Kent's owl,
# 2026-08-12) the answer was "no" for all 25 regions: 24 rejected on
# RAMP_R2_MIN, 1 on speckle, every one then filled with a single flat
# color. This warning is what makes that outcome visible instead of
# leaving the classification copy as the user's only signal.
# extra: {"count": int, "reasons": dict[str, int], "best_r2": float}
BLEND_NO_REGIONS_DECOMPOSED = "BLEND_NO_REGIONS_DECOMPOSED"

# Stage 6 (contour fill tier)
CONTOUR_RING_UNREACHABLE = "CONTOUR_RING_UNREACHABLE"  # contour left a bare patch wider than a ring spacing (measured, barecircle.py). extra: {"count": int, "rings": int}
# `directional_comp` and `fill_technique="contour"` do not compose: contour
# takes no fill angle (rings follow the silhouette), so stage 5's directional
# compensation stretches the shape along an axis the rings then decline to sew
# along. Both flags are opt-in and the design still sews, so this is a loud
# warning rather than a config error — but nothing measures the pair, and the
# compensation geometry is applied regardless.
CONTOUR_DIRECTIONAL_COMP_UNSEWN = "CONTOUR_DIRECTIONAL_COMP_UNSEWN"

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
