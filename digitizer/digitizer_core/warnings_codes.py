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

# Stage 1.25 (photograph detection — quality review 2026-09-08 item 13).
# Rides cfg.detect_photographic (default OFF) and fires ONLY when a signal
# actually said photograph; silence emits nothing, because no signal firing is
# "no opinion", not "not a photograph" (see photo_signals' module docstring).
# Info, not a problem: it names which signal fired, because the consequence —
# the palette resnap bind, the shade bind, preflight's photo yardstick — is
# something the caller may want to override with an explicit declaration.
# extra: {"signal": "exif" | "face", "detail": str}
PHOTO_DETECTED = "PHOTO_DETECTED"

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
# extra: {count, area_mm2} — colours dissolved as compression/anti-alias
# halos by the photo lane (the flat lane has always done this silently)
PHOTO_BLEND_DISSOLVED = "PHOTO_BLEND_DISSOLVED"
# Photo plan step 7 (palette k-medoids). Info: how many chart spools the
# weighted selection settled on, and the worst region's ΔE00 excess over its
# own nearest-thread floor. extra: {"colors": int, "regions": int, "max_excess_de00": float}
PHOTO_PALETTE_SELECTED = "PHOTO_PALETTE_SELECTED"
# Stage-2 shade demand (cfg.shade_palette_demand, EXPERIMENT — option (b) of
# docs/superpowers/plans/2026-08-23-shade-palette-binding.md): proxy shade
# Lab targets were fed into `select_palette` alongside the region demand, so
# the palette contains anchors for the shades the streamline decomposition
# will bind to. Info, plus the accounting the cone-cost question needs:
# "points" is how many weighted demand rows were added, from
# "regions_with_demand" regions; "palette_k" is the selected medoid count
# (may exceed cfg.max_colors up to palette.PALETTE_OVERFLOW_K — demand
# pressure trips the overflow more eagerly than region demand alone, and
# cones cost money, so the number is surfaced rather than buried);
# "anchors" is how many selected spools no region's own mean claimed
# (shade-only anchors, carried to the stage-7 bind via Quant.palette_spools).
# extra: {"points": int, "regions_with_demand": int, "palette_k": int, "anchors": int}
PHOTO_SHADE_DEMAND = "PHOTO_SHADE_DEMAND"

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
# thread out of stage 2's quantized palette. Passes that re-snap individual
# shapes to a different spool without moving them to another layer leave a
# layer holding two threads and its palette entry naming a spool no shape in
# it carries. `revalidate_threads` (fix #6.3) was the original producer; since
# the colour bundle flipped on 2026-09-10 it is `enforce_color_cap`, which
# `rehome_resnapped_regions` structurally cannot repair (wrong stamp, and it
# runs first) — 24 shapes on 3 of 26 fixtures at `max_colors=12`, 76 on two
# real-customer fixtures at the Studio's shipped 6.
#
# Stage 7 partitions blocks by (sew_index, step_key, thread) and is therefore
# right regardless — and so is the OPERATOR's list. This comment used to say
# "the cone list a human loads … is wrong"; that is false, and DOCTRINE
# recorded it so on 2026-09-07. A human loads `plan.palette`, per BLOCK,
# consistent on 26 of 26 fixtures. What is wrong is the REVIEW SCREEN's
# per-layer list — the labels a user reorders and recolours by.
#
# `cfg.layer_palette_from_regions` (default OFF) elects each layer's cone
# from its own regions and closes it; this warning is the detector for the
# OFF path. Note it is blind to the LARGER direction — a layer naming a cone
# no block sews at all, on 9 of 26 fixtures, 6 of them silent here. That one
# is reported by `tools/palette_mismatch.py`'s phantom column, never by this
# code: a layer nobody is left in produces no mismatched region.
# Full measurement: `docs/palette-mismatch-2026-09-12.md`.
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
# Stage 6 (satin tier, 2026-09-03). A stretch of a stroke inside a satin shape
# whose crosses fell under SATIN_MIN_CROSS_MM sewed as a bean run along its
# spine instead of vanishing — the E's arms, the T's bar, a script's connector.
# Info, not a problem: the stitch type changing within a letter is what a
# digitizer does by hand; reported because the letter now carries two
# techniques and a person looking at the review screen should know why.
# extra: {"count": int, "shapes": int}
HAIRLINE_STROKES_AS_RUN = "HAIRLINE_STROKES_AS_RUN"

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

# Two quantized COLOURS snapped to one physical cone, so the palette declared
# the same spool twice and the operator was sent to the rack twice for it —
# the second visit sewing a late fragment over finished work (defect 18).
# Folded upstream of stage 5 by `merge_duplicate_cone_layers`.
# extra: {"count": int, "cones": list[int]}
DUPLICATE_CONE_LAYERS_MERGED = "DUPLICATE_CONE_LAYERS_MERGED"

# Stage 6 (design-silhouette edge cap, cfg.edge_cap)
# Asked for a cap and got none — the silhouette was too small or too narrow
# for either emitter to hold a loop. Fires only when the cap was explicitly
# switched on, because silence on an opt-in the user set is how a knob comes
# to look broken. extra: {"style": str}
EDGE_CAP_EMPTY = "EDGE_CAP_EMPTY"
# What the cap actually cost, reported EVERY time it runs. Not noise: the cap
# is opt-in, so a message when you opt in is the answer to "what did that buy
# me". It exists because the cost is not predictable from the design's size —
# it scales with how FRAGMENTED the silhouette is, and a photo/gradient lane
# can shatter one visual object into dozens of parts. Measured 2026-09-01 at
# 80 mm: the repro icon caps 3 parts / 23 holes for +13.2%, but `drone_render`
# caps 38 parts / 78 holes for +56.9% — within a whisker of the "+60% of
# stitches to worsen a silhouette" DOCTRINE records for blanket bordering.
# On that design "the design silhouette" is not one edge and the feature's
# premise does not hold, so the honest move is to report the bill rather than
# to guess a fragmentation threshold nobody has sewn.
# extra: {"style": str, "stitches": int, "percent": float, "edges": int,
#         "whole_loops": int, "arcs": int, "yielded": int,
#         "cracks_filled": int, "gate_saved_pct": float,
#         "omit_cover_mm2": float, "over_budget": bool, "budget_pct": float,
#         "dropped": bool}
# `edges` is the number of silhouette RINGS the cap went around; `whole_loops`
# and `arcs` split the runs it emitted (a ring the gate cut sews as arcs, and
# an operator reading fragmentation needs the ring count, not the run count —
# see stage6_border.silhouette_cap). `gate_saved_pct` is 1 - gated/ungated on
# the same geometry: the single number that says whether the gate is working
# on THIS design, and the one whose absence let a +58.7% bill pass for a month.
EDGE_CAP_APPLIED = "EDGE_CAP_APPLIED"
# The cap's bill cleared `stage6_border.EDGE_CAP_BUDGET_PCT` (40% of the
# artwork's own stitches). Loud because the cap is DEFAULT ON: the bill was
# always reported honestly, and that was not enough — `EDGE_CAP_APPLIED` fires
# on every run, so the one run where the cap costs two-fifths of the design or
# more read exactly like the ninety that cost a tenth. Measured cause on
# `becker_marine_logo` (docs/edge-cap-cliff-2026-09-12.md): one shape carries
# ~94% of the design's linear cover, that shape's satin/fill verdict is not
# monotone in design size, and when it tiers to fill the gate's input — and
# with it the gate's saving — collapses from 72% to 3%, or to nothing at all.
# The warning carries the diagnosis, not just the number: `gate_saved_pct` and
# `omit_cover_mm2` say whether the gate had anything to work with.
# extra: {"style": str, "stitches": int, "percent": float, "budget_pct":
#         float, "gate_saved_pct": float, "omit_cover_mm2": float,
#         "dropped": bool}
EDGE_CAP_OVER_BUDGET = "EDGE_CAP_OVER_BUDGET"
# The satin cap fell back to its own bean lightening on part of the
# silhouette — `border_runs`' documented contract, surfaced rather than
# absorbed so a cap that reads lighter than expected has a reason on screen.
# extra: {"count": int}
EDGE_CAP_LIGHTENED = "EDGE_CAP_LIGHTENED"

# Stage 6 (border tier)
BORDER_SKIPPED_TOO_NARROW = "BORDER_SKIPPED_TOO_NARROW"  # no room for an outline. extra: {"count": int}
BORDER_LIGHTENED = "BORDER_LIGHTENED"                    # column would not fit; bean run instead. extra: {"count": int}
# Stage 6/7 (border tier) — two bordered shapes share an edge. Stage 5 makes
# their visible edges the identical line, so two full circuits would ride it
# as a doubled bar in two threads. `stage7_sequence._owned_by_later` settles
# it: the shape sewn LATER owns the seam (it lies on top, its column covers
# both edges) and the shape underneath skips that stretch of its own ring,
# sewing the rest as open arcs still on its edge. This is a NOTE, not a
# defect: it names the pairs so the operator can see why a shape's own
# border stops short of an edge, and the manual escape stays
# (`Region.meta["border"] = False` on either side). extra: {"count": int,
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
