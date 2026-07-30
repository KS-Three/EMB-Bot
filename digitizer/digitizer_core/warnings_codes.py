"""Machine-readable warning codes (blueprint v2.1: UI switches on codes, never prose).

Every warning the pipeline emits is {"code": <one of these>, "message": str,
and optional extra keys documented per code}. Codes are append-only — never
renumber or reuse.
"""

# Stage 1
BACKGROUND_UNCERTAIN = "BACKGROUND_UNCERTAIN"      # border flood intruded deep past the artwork margin
INPUT_LOW_RESOLUTION = "INPUT_LOW_RESOLUTION"      # px_per_mm below floor even after capped upscale
BACKGROUND_ENCLOSED = "BACKGROUND_ENCLOSED"        # enclosed bg-colored region treated as hole (review-toggleable)

# Stage 2
COLOR_CAP_APPLIED = "COLOR_CAP_APPLIED"            # more threads than max_colors; smallest layers reassigned

# Stage 3
DROPPED_SMALL_SHAPES = "DROPPED_SMALL_SHAPES"      # extra: {"count": int}
ABSORBED_SMALL_SHAPES = "ABSORBED_SMALL_SHAPES"    # extra: {"count": int}
EMPTY_THREAD_LAYER = "EMPTY_THREAD_LAYER"          # a thread's every region absorbed/dropped; layer removed

# Stage 5 (overlap resolution / pull compensation)
HOLE_NEARLY_CLOSED = "HOLE_NEARLY_CLOSED"          # pull comp would swallow a hole; held open. extra: {"count": int}

# Stage 6 (stitch planning)
SHAPE_TOO_THIN_TO_FILL = "SHAPE_TOO_THIN_TO_FILL"  # narrower than a fill can hold; satin's job (step 4). extra: {"count": int}
SHAPE_NOT_STITCHED = "SHAPE_NOT_STITCHED"          # geometry produced no stitches at all. extra: {"count": int}
LONG_JUMPS_TRIMMED = "LONG_JUMPS_TRIMMED"          # travel could not stay inside the shape. extra: {"count": int}


def warn(code: str, message: str, **extra) -> dict:
    w = {"code": code, "message": message}
    w.update(extra)
    return w
