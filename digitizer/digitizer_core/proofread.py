"""Proof-read: what the stitch plan SEWS against what the art SHOWS, locally, in mm.

Every other reader that looks at the sewn result reads one property in one
place: `legibility` (OCR of text clusters), `glyph_read` (per-glyph shape of
text-tagged words, metrics only), `ARTWORK_UNCOVERED` (thread missing INSIDE a
shape the design sews), `ARTWORK_ELEMENT_DROPPED` (the pipeline's own drop
warnings, by area), and the offline fault readers in `tools/` (each one fault
kind, scored against Kent's pins). None of them compares the whole design's
thread with the whole art component by component, says WHERE they differ and
names the rule whose stitches differ. This does, and changes nothing: it is a
report (`cfg.proofread`, built OFF; the findings ride in preflight's
`metrics`, never as a customer finding, Kent's 2026-10-02 ruling).

## The two pictures, one grid

Both are drawn on one grid in the plan's mm frame (origin at the art bbox's
centre, y down: stage 4's `_to_mm`) at `PX_PER_MM`:

  thread  every needle-down segment of the plan, in sew order, at
          `stitchviz.THREAD_MM` wide, as the index of the run that laid it,
          so the TOP run at each pixel is known exactly: its thread, kind,
          role and shape id. Runs that start with a jump are drawn from their
          first point (a scratch renderer that skipped them drew fills as
          missing, 2026-11-13); the stitch the machine sews from one run's
          end to the next run's start when there is no jump is drawn as a
          `connector`. Cross-checked against the pipeline's own
          `stage6_stitches.png` by `tools/proofread.py check-raster`.
  art     the raster the pipeline traced (preflight's graded view: the
          re-read prep, or the photo-prepped pixels), each pixel given the
          nearest of the plan's thread colours (CIE Lab); `OTHER_INK` when
          every thread is `ART_UNMATCHED_DE` away (ink of a colour the design
          dropped whole, judged against thread of any colour); `GARMENT`
          where it is nearer the garment than any thread and within
          `GARMENT_LIKE_DE` of it (an area the design leaves as fabric);
          `BG` where stage 1's background mask says so.

Threads closer than `CLASS_MERGE_DE` are one colour class (two near greys are
not two colours to the eye); a class within `GARMENT_DE` of the garment is
invisible on it and is not judged.

## Tolerance

`tol = pull + THREAD_MM / 2`: the fabric's own pull compensation (the buffer
stage 5 grows every column by, `pipeline.fabric_for(cfg).pull_comp_mm`) plus
half a filament, since a rail's needle point lies on the outline and its
thread spreads half its width past it. 0.5 mm on the pique the corpus runs on,
which is `glyph_read.COMP_TOL_MM`. Thread within `tol` of its colour's ink is
on the ink; ink within `tol` of its colour's thread is sewn.

## Findings, per colour class unless said

  MOVED    an art component whose sewn partner (same class) matches it far
           better once shifted back by their centroid offset (`MOVE_GAIN`),
           offset at least `tol`: small-text re-set displacement.
  MISSING  an art component (area >= `ART_MIN_MM2`, holds a circle of
           `ART_MIN_HALF_MM`) with under `MISSING_COVER` of its pixels within
           `tol` of its colour's thread, and no moved partner.
  EXTRA    a sewn component (top thread, travel/tie/connector excluded, area
           >= `EXTRA_MIN_MM2`) with under `EXTRA_ON_ART` of its pixels within
           `tol` of its colour's ink: an invented border, in-fill or shape.
  CLOSED   a hole of the ink (fabric or garment enclosed by any ink), at
           least `SPACE_MIN_HALF_MM` half-wide, where the sewn thread leaves
           no clear circle of `SPACE_KEEP_HALF_MM` (glyph_read's numbers,
           with the keep floor raised to a quarter of the art's half-width).
  MERGED   two ink components whose gap (at least `SPACE_MIN_HALF_MM`
           half-wide, at most `GAP_MAX_HALF_MM`) has thread at least two
           filaments wide lying across its midline for `BRIDGE_MIN_MM`: one
           running stitch across a gap is travel, not a join (the letter
           reader's rule).
  SHAPE    what is left: a patch of ink with no thread within `tol`
           (deficit: a lost tooth, a rounded corner) or of thread with no
           ink within `tol` (excess: a filled notch, a bulge), whose deepest
           point is `SHAPE_DEPTH_MM` past the other side and whose area is
           `SHAPE_MIN_MM2`.
  WIDTH    per art component held by thread of its colour, twice the median
           depth along the skeleton, art against thread: thin when the
           thread is under `WIDTH_THIN_RATIO` of the art and `WIDTH_THIN_MM`
           narrower (pull never thins), thick when it is
           `WIDTH_THICK_RATIO` of the art and wider by more than `tol` at
           each edge (what a faithful fill reads) plus half a filament: a
           0.4 mm keyline sewn as a 1.5 mm satin reads 1.9 against 0.4.

Each finding carries its centre and box (mm, plan frame), the art component,
the shapes whose TOP thread is there (`produced_by`: shape id, share, run
kinds and roles, region tags) and the regions whose outline covers it
(`meant_for`). `explained_by` names a deliberate adaptation the regions'
`meta`, the runs' roles or the geometry show (`EXPLAINERS`): explained is not
silenced. Severity: `error` when nothing explains it, `misfire` when
something does but the departure is large (`MISFIRE_MM2`), `explained`
otherwise.

All numbers here are instrument readings, not quality claims (ROADMAP gate
4); no constant is a fabric property (gate 1): each is a share, a thread
width, or the fabric's own pull read from the preset table.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import cv2
import numpy as np

from .stitchviz import THREAD_MM

PX_PER_MM = 10.0            # the task's grid; a 0.4 mm filament is 4 px
PAD_MM = 2.0                # around the union of art and thread

CLASS_MERGE_DE = 10.0       # CIE76: threads this close read as one colour
GARMENT_DE = 5.0            # a thread colour this close to the garment is invisible on it
GARMENT_LIKE_DE = 15.0      # art nearer the garment than any thread, and this near it, is left fabric
                            # (white ink on a cream garment, 9 apart, sewn as fabric by design)
ART_UNMATCHED_DE = 25.0     # art this far from every thread is ink of a colour no thread carries

ART_MIN_MM2 = 0.5           # an art component smaller than this is a speck
ART_MIN_HALF_MM = 0.15      # ... and one that cannot hold a circle of this half-width is anti-alias fringe
MISSING_COVER = 0.2         # under this share sewn within tol = missing
EXTRA_MIN_MM2 = 1.0
EXTRA_ON_ART = 0.25         # under this share within tol of its ink = extra
MOVE_GAIN = 0.2             # the shifted match must beat the unshifted one by this much
MOVE_MATCH = 0.7            # ... and reach this
MOVE_SEARCH_MM = 4.0        # a missing component's moved partner is looked for this far
MOVE_COV0 = 0.75            # the general search runs on a shape under this share sewn in place ...
MOVE_COV1 = 0.9             # ... and calls it moved when this share is sewn after the shift
MOVE_GAIN_COV = 0.3         # ... and the shift sews this much more of it
SPACE_MIN_HALF_MM = 0.3     # a hole / gap judged when a circle this big fits (1.5 filaments across)
SPACE_KEEP_HALF_MM = 0.10   # glyph_read: a space survives with a clear circle this big
SPACE_KEEP_FRAC = 0.25      # ... or a quarter of the art's, whichever is bigger
GAP_MAX_HALF_MM = 3.0       # gaps wider than this are fields, not joins
BRIDGE_MIN_MM = 0.6         # 1.5 filaments of continuous bridge
SHAPE_MIN_MM2 = 0.5
WIDTH_THIN_RATIO = 0.7
WIDTH_THIN_MM = 0.25
WIDTH_THICK_RATIO = 1.5
WIDTH_MAX_MM = 5.0          # strokes, not fields
MISFIRE_MM2 = 4.0           # an explained departure this big is a misfire ...
MISFIRE_MM = 1.0            # ... or this far off (a re-set letter 1 mm off its line is small in mm2)
MAX_FINDINGS = 200
EXPLAIN_SHARE = 0.25        # a shape explains a finding when it lays / owns this share of its pixels

BG = -1
GARMENT = -2
OTHER_INK = -3
EXCLUDED_KINDS = ("travel", "tie", "connector")

# region meta key / run role -> the deliberate adaptation it names, and the
# finding kinds it can explain. Read off the tags the pipeline writes (see
# the departures table in the PR that added this module).
EXPLAINERS: dict[str, tuple[str, tuple[str, ...]]] = {
    "small_text_reset": ("small_text_reset", ("MOVED", "SHAPE", "WIDTH", "MERGED", "CLOSED", "EXTRA", "MISSING")),
    "small_text_enlarged": ("small_text_reset", ("MOVED", "SHAPE", "WIDTH", "MERGED", "CLOSED", "EXTRA")),
    "small_text_bar_moved_mm": ("small_text_reset", ("MOVED", "SHAPE")),
    "small_text_adopted": ("small_text_reset", ("MOVED", "SHAPE", "WIDTH", "EXTRA")),
    "small_text_inner": ("small_text_reset", ("SHAPE", "WIDTH", "CLOSED")),
    "small_text_traced_polygon": ("small_text_reset", ("MOVED", "SHAPE", "WIDTH", "MERGED", "CLOSED")),
    "small_text_restored": ("small_text_restore", ("SHAPE", "WIDTH", "CLOSED", "MERGED")),
    "small_text_stray": ("lettering_stray", ("EXTRA",)),
    "small_text_stray_line": ("lettering_stray", ("EXTRA",)),
    # NOT `lettering_ink_stray` (columns.py): it only keeps a shape out of the
    # Column lane and moves no outline; nor `subpixel_accepted`: an accuracy
    # refinement on most regions, not a departure (both explained every
    # finding on lt_k_line's first read, 2026-11-13)
    # shared key (stage5_overlap.WIDENED_LETTERING_KEY): small_text writes it
    # in a default run, regularize only under `lettering_min_column_mm`
    "text_cluster_widened_mm": ("text_widened", ("WIDTH", "SHAPE", "MERGED", "CLOSED")),
    # NOT `text_cluster_regularize_shape_changed`: that is regularize's
    # REFUSAL (textcluster.py, written with `skipped`), the plain shape kept
    "letterform_prior": ("letterform_prior", ("SHAPE", "WIDTH", "CLOSED")),   # value "refit..." only, `_tags`
    "sew_enclosed_white": ("enclosed_white", ("EXTRA", "CLOSED", "SHAPE")),
    "enclosed_background": ("enclosed_white", ("EXTRA", "CLOSED", "SHAPE")),
    "enclosed_by_garment": ("enclosed_white", ("EXTRA", "CLOSED", "SHAPE", "MISSING")),
    "border": ("border", ("EXTRA", "WIDTH", "SHAPE", "MERGED", "CLOSED")),
    "hairline_outline": ("bean_hairline", ("WIDTH", "SHAPE", "CLOSED", "MERGED")),
    "bean_letter_spines": ("bean_letter", ("WIDTH", "SHAPE", "CLOSED", "MERGED")),
    "dark_ink": ("dark_ink_bean", ("WIDTH", "SHAPE", "CLOSED")),
    "dark_ink_ground": ("dark_ink_bean", ("WIDTH", "SHAPE", "CLOSED", "MERGED")),
    "dark_ink_floor_rescued": ("dark_ink_floor_rescue", ("WIDTH", "SHAPE")),
    "rescued_small_shape": ("run_tier_rescue", ("WIDTH", "SHAPE", "CLOSED")),
    "dot_rung": ("run_tier_rescue", ("WIDTH", "SHAPE", "CLOSED")),
    "detail_spokes": ("detail_spokes", ("WIDTH", "SHAPE")),
    "color_cap_merged_from": ("colour_cap_fold", ("MISSING", "EXTRA", "SHAPE")),
    "neck_split_from": ("neck_split", ("SHAPE", "MERGED")),
    "absorbed_fragments": ("fragment_absorb", ("SHAPE", "MISSING", "EXTRA", "MERGED", "CLOSED")),
    "silhouette_underfill": ("underfill", ("SHAPE", "EXTRA", "MERGED", "CLOSED")),
    "silhouette_underfill_of": ("underfill", ("SHAPE", "EXTRA", "MERGED", "CLOSED")),
    "underfill_merged_art": ("underfill", ("SHAPE", "EXTRA", "MERGED", "CLOSED")),
    "keyline_folded": ("keyline_fold", ("SHAPE", "MISSING", "MERGED", "CLOSED", "WIDTH")),
    "holes_override": ("customer_edit", ("SHAPE", "CLOSED", "EXTRA", "MISSING", "MERGED", "MOVED", "WIDTH")),
    "boundary_override": ("customer_edit", ("SHAPE", "CLOSED", "EXTRA", "MISSING", "MERGED", "MOVED", "WIDTH")),
    "counter": ("counter", ("CLOSED", "SHAPE", "EXTRA")),
    "small_counters": ("counter", ("CLOSED", "SHAPE")),
    "cored_counter": ("counter", ("CLOSED", "SHAPE")),
    "bean_counter_held": ("counter", ("CLOSED",)),
}
ROLE_EXPLAINERS = {
    "border": ("border", ("EXTRA", "WIDTH", "SHAPE", "MERGED", "CLOSED")),
    "edge_cap": ("edge_cap", ("EXTRA", "WIDTH", "SHAPE")),
}
DROP_CODES = ("SHAPE_NOT_STITCHED", "SHAPES_LEFT_UNSEWN", "CLIP_DROPPED_SLIVER")


# ------------------------------------------------------------------ grid ----

@dataclass
class Grid:
    x0: float               # mm of pixel column 0's centre
    y0: float
    w: int
    h: int
    px: float = PX_PER_MM

    def to_px(self, x: float, y: float) -> tuple[int, int]:
        return int(round((x - self.x0) * self.px)), int(round((y - self.y0) * self.px))

    def to_mm(self, col: float, row: float) -> tuple[float, float]:
        return col / self.px + self.x0, row / self.px + self.y0


def make_grid(plan, art_mm_box: tuple[float, float, float, float] | None,
              px: float = PX_PER_MM, pad_mm: float = PAD_MM) -> Grid:
    xs, ys = [], []
    for _b, r in plan.iter_runs():
        for x, y in r.points:
            xs.append(x)
            ys.append(y)
    if art_mm_box is not None:
        xs += [art_mm_box[0], art_mm_box[2]]
        ys += [art_mm_box[1], art_mm_box[3]]
    if not xs:
        xs, ys = [0.0], [0.0]
    x0, x1 = min(xs) - pad_mm, max(xs) + pad_mm
    y0, y1 = min(ys) - pad_mm, max(ys) + pad_mm
    return Grid(x0, y0, int(math.ceil((x1 - x0) * px)) + 1, int(math.ceil((y1 - y0) * px)) + 1, px)


# --------------------------------------------------------------- colours ----

def _lab(rgb) -> np.ndarray:
    a = np.asarray(rgb, np.float32).reshape(-1, 1, 3) / 255.0
    return cv2.cvtColor(a, cv2.COLOR_RGB2LAB).reshape(-1, 3)


def colour_classes(block_rgbs: list[tuple[int, int, int]], merge_de: float = CLASS_MERGE_DE
                   ) -> tuple[list[tuple[int, int, int]], list[int]]:
    """-> (class rgb list, class index per block): threads closer than
    `merge_de` (CIE76) share a class, the first one seen naming it."""
    classes: list[tuple[int, int, int]] = []
    labs: list[np.ndarray] = []
    of_block: list[int] = []
    for rgb in block_rgbs:
        lab = _lab([rgb])[0]
        hit = next((i for i, q in enumerate(labs) if float(np.linalg.norm(lab - q)) < merge_de), None)
        if hit is None:
            classes.append(tuple(int(v) for v in rgb))
            labs.append(lab)
            hit = len(classes) - 1
        of_block.append(hit)
    return classes, of_block


# ---------------------------------------------------------------- thread ----

@dataclass
class RunInfo:
    block: int
    cls: int
    kind: str
    role: str
    shape_id: str


def thread_raster(plan, grid: Grid, class_of_block: list[int], thread_mm: float = THREAD_MM
                  ) -> tuple[np.ndarray, list[RunInfo]]:
    """-> (top run index per pixel, -1 none; the runs). Every needle-down
    segment in sew order, `thread_mm` wide, no anti-alias, so the top run is
    exact. Mirrors `stitches.iter_machine_commands`: a run with `jump` or
    `trim` starts a new path at its first point (drawn); one without is
    reached by a sewn stitch from the previous run's end (a `connector`)."""
    top = np.full((grid.h, grid.w), -1, np.int32)
    runs: list[RunInfo] = []
    tw = max(2, int(round(thread_mm * grid.px)))
    prev = None
    for bi, block in enumerate(plan.blocks):
        cls = class_of_block[bi]
        for run in block.runs:
            pts = run.points
            if not pts:
                continue
            if prev is not None and not run.jump and not run.trim:
                runs.append(RunInfo(bi, cls, "connector", "", run.shape_id))
                cv2.line(top, grid.to_px(*prev), grid.to_px(*pts[0]), len(runs) - 1, tw, cv2.LINE_8)
            runs.append(RunInfo(bi, cls, str(run.kind), str(run.role or ""), str(run.shape_id or "")))
            idx = len(runs) - 1
            arr = np.array([grid.to_px(x, y) for x, y in pts], np.int32)
            if len(arr) == 1:
                cv2.circle(top, (int(arr[0][0]), int(arr[0][1])), max(1, tw // 2), idx, -1)
            else:
                cv2.polylines(top, [arr.reshape(-1, 1, 2)], False, idx, tw, cv2.LINE_8)
            prev = pts[-1]
    return top, runs


# ------------------------------------------------------------------- art ----

def art_raster(rgb: np.ndarray, bg_mask: np.ndarray, art_bbox, px_per_mm: float, grid: Grid,
               classes: list[tuple[int, int, int]], garment_rgb) -> np.ndarray:
    """-> int16 label per grid pixel: a class index, `GARMENT` or `BG`.
    Labelled on the art's own grid, then warped (nearest) into `grid`."""
    lab = cv2.cvtColor(rgb.astype(np.float32) / 255.0, cv2.COLOR_RGB2LAB)
    cl = _lab(classes)
    best = np.full(rgb.shape[:2], np.inf, np.float32)
    arg = np.zeros(rgb.shape[:2], np.int16)
    for i, q in enumerate(cl):
        d = np.sqrt(((lab - q[None, None, :]) ** 2).sum(-1))
        sel = d < best
        best[sel] = d[sel]
        arg[sel] = i
    # ink of a colour no thread is near: an element whose whole colour was
    # dropped. Judged against thread of ANY colour (`OTHER_INK`).
    arg[best > ART_UNMATCHED_DE] = OTHER_INK
    if garment_rgb is not None:
        g = _lab([garment_rgb])[0]
        dg = np.sqrt(((lab - g[None, None, :]) ** 2).sum(-1))
        arg[(dg < best) & (dg < GARMENT_LIKE_DE)] = GARMENT
        # a class the garment hides is not judged: its ink reads as garment
        for i, q in enumerate(cl):
            if float(np.linalg.norm(q - g)) < GARMENT_DE:
                arg[arg == i] = GARMENT
    arg[np.asarray(bg_mask, bool)] = BG
    ax0, ay0, ax1, ay1 = art_bbox
    cx, cy = (ax0 + ax1) / 2.0, (ay0 + ay1) / 2.0
    k = grid.px / float(px_per_mm)
    M = np.array([[k, 0.0, grid.px * (-cx / px_per_mm - grid.x0)],
                  [0.0, k, grid.px * (-cy / px_per_mm - grid.y0)]], np.float64)
    out = cv2.warpAffine(arg.astype(np.float32), M, (grid.w, grid.h), flags=cv2.INTER_NEAREST,
                         borderMode=cv2.BORDER_CONSTANT, borderValue=float(BG))
    return np.rint(out).astype(np.int16)


def art_mm_box(art_bbox, px_per_mm: float) -> tuple[float, float, float, float]:
    ax0, ay0, ax1, ay1 = art_bbox
    cx, cy = (ax0 + ax1) / 2.0, (ay0 + ay1) / 2.0
    return ((ax0 - cx) / px_per_mm, (ay0 - cy) / px_per_mm, (ax1 - cx) / px_per_mm, (ay1 - cy) / px_per_mm)


# --------------------------------------------------------------- helpers ----

def _dist_to(mask: np.ndarray, px: float) -> np.ndarray:
    """mm from every pixel to the nearest True pixel of `mask` (inf if none)."""
    if not mask.any():
        return np.full(mask.shape, np.inf, np.float32)
    return cv2.distanceTransform((~mask).astype(np.uint8), cv2.DIST_L2, 5) / px


def _depth(mask: np.ndarray, px: float) -> np.ndarray:
    """mm from every True pixel of `mask` to the nearest False one."""
    m = np.pad(mask.astype(np.uint8), 1)
    return (cv2.distanceTransform(m, cv2.DIST_L2, 5) / px)[1:-1, 1:-1]


def _open(mask: np.ndarray, radius_px: int) -> np.ndarray:
    if radius_px <= 0:
        return mask
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * radius_px + 1, 2 * radius_px + 1))
    return cv2.morphologyEx(mask.astype(np.uint8), cv2.MORPH_OPEN, k).astype(bool)


def _close(mask: np.ndarray, radius_px: int) -> np.ndarray:
    if radius_px <= 0:
        return mask
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * radius_px + 1, 2 * radius_px + 1))
    m = np.pad(mask.astype(np.uint8), radius_px + 1)
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, k)
    r = radius_px + 1
    return m[r:-r, r:-r].astype(bool)


def _keep_components(mask: np.ndarray, min_px: float, min_half_mm: float, px: float) -> np.ndarray:
    """`mask` less its components under `min_px` pixels or too thin to hold a
    circle of `min_half_mm`."""
    n, lab, stats, _ = _components(mask, 8)
    if n <= 1:
        return mask
    depth = _depth(mask, px)
    maxd = np.zeros(n, np.float32)
    np.maximum.at(maxd, lab.ravel(), depth.ravel())
    keep = (stats[:, 4] >= min_px) & (maxd >= min_half_mm)
    keep[0] = False
    return keep[lab]


def _dilate(mask: np.ndarray, radius_px: int) -> np.ndarray:
    if radius_px <= 0:
        return mask
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * radius_px + 1, 2 * radius_px + 1))
    return cv2.dilate(mask.astype(np.uint8), k).astype(bool)


def _components(mask: np.ndarray, conn: int = 8):
    n, lab, stats, cent = cv2.connectedComponentsWithStats(mask.astype(np.uint8), connectivity=conn)
    return n, lab, stats, cent


def _skeleton(mask: np.ndarray) -> np.ndarray:
    from skimage.morphology import skeletonize
    return skeletonize(mask)


def _match(a: np.ndarray, s: np.ndarray, tol_px: int) -> float:
    """Symmetric tolerant overlap in [0, 1]: the share of both masks lying
    within `tol_px` of the other. Pull compensation reads 1.0."""
    na, ns = int(a.sum()), int(s.sum())
    if na == 0 or ns == 0:
        return 0.0
    da, ds = _dilate(a, tol_px), _dilate(s, tol_px)
    return float((a & ds).sum() + (s & da).sum()) / float(na + ns)


def _best_shift(comp: np.ndarray, stat, thread: np.ndarray, dT: np.ndarray, tol_mm: float, px: float):
    """-> ((dx, dy) px, coverage after the shift) for the shift within
    `MOVE_SEARCH_MM` that best lays `comp` onto `thread` (normalised
    cross-correlation of the shape, grown by `tol`, against the thread), or
    None when the shift is under `max(tol, 0.5)` mm."""
    x, y, w, h, _a = stat
    R = int(round(MOVE_SEARCH_MM * px))
    t = max(1, int(round(tol_mm * px)))
    H, W = comp.shape
    tx0, ty0, tx1, ty1 = max(0, x - t), max(0, y - t), min(W, x + w + t), min(H, y + h + t)
    tmpl = _dilate(comp[ty0:ty1, tx0:tx1], t).astype(np.float32)
    ix0, iy0, ix1, iy1 = max(0, tx0 - R), max(0, ty0 - R), min(W, tx1 + R), min(H, ty1 + R)
    img = thread[iy0:iy1, ix0:ix1].astype(np.float32)
    if img.shape[0] < tmpl.shape[0] or img.shape[1] < tmpl.shape[1] or tmpl.sum() == 0 or img.sum() == 0:
        return None
    res = cv2.matchTemplate(img, tmpl, cv2.TM_CCORR_NORMED)
    _mn, _mx, _ml, (bx, by) = cv2.minMaxLoc(res)
    dx, dy = (ix0 + bx) - tx0, (iy0 + by) - ty0
    if math.hypot(dx, dy) / px < max(tol_mm, 0.5):
        return None
    moved = _shift(comp, dx, dy)
    if not moved.any():
        return None
    return (dx, dy), float((dT[moved] <= tol_mm).mean())


def _shift(mask: np.ndarray, dx: int, dy: int) -> np.ndarray:
    out = np.zeros_like(mask)
    h, w = mask.shape
    xs0, xs1 = max(0, -dx), min(w, w - dx)
    ys0, ys1 = max(0, -dy), min(h, h - dy)
    if xs1 > xs0 and ys1 > ys0:
        out[ys0 + dy:ys1 + dy, xs0 + dx:xs1 + dx] = mask[ys0:ys1, xs0:xs1]
    return out


# ----------------------------------------------------------- attribution ----

class _Attrib:
    def __init__(self, top, runs, region_ids, regions, dropped_ids, grid, merged_into=None):
        self.merged_into = dict(merged_into or {})
        self.top = top
        self.runs = runs
        self.reg = region_ids
        self.regions = regions
        self.dropped = dropped_ids
        self.grid = grid

    def produced_by(self, mask: np.ndarray, limit: int = 3) -> list[dict]:
        ids = self.top[mask]
        ids = ids[ids >= 0]
        if ids.size == 0:
            return []
        uniq, cnt = np.unique(ids, return_counts=True)
        by_shape: dict[str, dict] = {}
        tot = float(cnt.sum())
        for u, c in zip(uniq, cnt):
            r = self.runs[int(u)]
            d = by_shape.setdefault(r.shape_id, {"shape_id": r.shape_id, "share": 0.0,
                                                 "kinds": set(), "roles": set()})
            d["share"] += c / tot
            d["kinds"].add(r.kind)
            if r.role:
                d["roles"].add(r.role)
        rows = sorted(by_shape.values(), key=lambda d: -d["share"])[:limit]
        out = []
        for d in rows:
            reg = self.regions.get(d["shape_id"])
            out.append({"shape_id": d["shape_id"], "share": round(d["share"], 3),
                        "kinds": sorted(d["kinds"]), "roles": sorted(d["roles"]),
                        "tags": _tags(reg)})
        return out

    def meant_for(self, mask: np.ndarray, limit: int = 3) -> list[dict]:
        ids = self.reg[mask]
        ids = ids[ids >= 0]
        if ids.size == 0:
            return []
        uniq, cnt = np.unique(ids, return_counts=True)
        order = np.argsort(-cnt)[:limit]
        tot = float(mask.sum())
        out = []
        keys = list(self.regions.keys())
        for o in order:
            sid = keys[int(uniq[o])]
            out.append({"shape_id": sid, "share": round(float(cnt[o]) / tot, 3),
                        "tags": _tags(self.regions[sid]), "dropped": sid in self.dropped,
                        "merged_into": self.merged_into.get(sid)})
        return out


def _tags(region) -> dict:
    if region is None:
        return {}
    meta = getattr(region, "meta", None) or {}
    out = {}
    for k in list(EXPLAINERS) + ["tier", "layer", "text_cluster_id"]:
        if k in meta and meta[k] not in (None, False, "", [], {}):
            v = meta[k]
            if k == "letterform_prior" and not str(v).startswith("refit"):
                continue            # "pass:..." / "refused:..." changed nothing
            out[k] = v if isinstance(v, (bool, int, float, str)) else str(v)[:60]
    if meta.get("stitched") is False:
        out["stitched"] = False     # left unsewn on purpose (enclosed, or the customer)
    return out


def _explain(kind: str, produced: list[dict], meant: list[dict], extra: list[str]) -> list[str]:
    why: list[str] = list(extra)
    for row in list(produced) + list(meant):
        if row.get("share", 1.0) < EXPLAIN_SHARE:
            continue                # a sliver of another shape's run explains nothing
        for k in row.get("tags", {}):
            if k in EXPLAINERS:
                label, kinds = EXPLAINERS[k]
                if kind in kinds and label not in why:
                    why.append(label)
        for role in row.get("roles", ()):
            if role in ROLE_EXPLAINERS:
                label, kinds = ROLE_EXPLAINERS[role]
                if kind in kinds and label not in why:
                    why.append(label)
        if row.get("dropped") and kind in ("MISSING", "SHAPE") and "dropped_by_pipeline" not in why:
            why.append("dropped_by_pipeline")
        if row.get("tags", {}).get("stitched") is False and kind in ("MISSING", "SHAPE") \
                and "left_unsewn" not in why:
            why.append("left_unsewn")
        if row.get("merged_into") and kind in ("MISSING", "SHAPE", "MERGED", "CLOSED") \
                and "merged_into_host" not in why:
            why.append("merged_into_host")
        if ("bean" in row.get("kinds", ()) or "run" in row.get("kinds", ())) and kind == "WIDTH" \
                and "line_tier" not in why:
            why.append("line_tier")
    return why


def region_raster(regions, grid: Grid) -> tuple[np.ndarray, dict]:
    """-> (index into the returned dict's order per pixel, -1 none; {shape_id: region})."""
    out = np.full((grid.h, grid.w), -1, np.int32)
    by_id = {}
    for r in regions or ():
        by_id[r.shape_id] = r
    for i, (sid, r) in enumerate(by_id.items()):
        poly = r.polygon
        geoms = getattr(poly, "geoms", [poly])
        for g in geoms:
            if g.is_empty or not hasattr(g, "exterior"):
                continue
            ext = np.array([grid.to_px(x, y) for x, y in g.exterior.coords], np.int32)
            m = np.zeros((grid.h, grid.w), np.uint8)
            cv2.fillPoly(m, [ext], 1)
            for hole in g.interiors:
                hp = np.array([grid.to_px(x, y) for x, y in hole.coords], np.int32)
                cv2.fillPoly(m, [hp], 0)
            out[m.astype(bool)] = i
    return out, by_id


# ------------------------------------------------------------------ read ----

def _box_mm(grid: Grid, mask: np.ndarray) -> list[float]:
    ys, xs = np.nonzero(mask)
    a = grid.to_mm(float(xs.min()), float(ys.min()))
    b = grid.to_mm(float(xs.max()), float(ys.max()))
    return [round(a[0], 2), round(a[1], 2), round(b[0], 2), round(b[1], 2)]


def _at(grid: Grid, mask: np.ndarray, weight: np.ndarray | None = None) -> list[float]:
    """The mask's deepest point when `weight` is given (its argmax), else its centroid."""
    ys, xs = np.nonzero(mask)
    if weight is not None:
        i = int(np.argmax(weight[ys, xs]))
        c = grid.to_mm(float(xs[i]), float(ys[i]))
    else:
        c = grid.to_mm(float(xs.mean()), float(ys.mean()))
    return [round(c[0], 2), round(c[1], 2)]


def read_arrays(art: np.ndarray, top: np.ndarray, runs: list[RunInfo], classes, grid: Grid,
                tol_mm: float, pull_mm: float, attrib: _Attrib | None = None,
                invisible: set[int] | None = None) -> list[dict]:
    """The findings, from the two label rasters. Pure array logic (the unit
    tests drive it on synthetic rasters)."""
    px = grid.px
    tol_px = max(1, int(round(tol_mm * px)))
    invisible = invisible or set()
    run_cls = np.array([r.cls for r in runs] + [-1], np.int32)
    run_vis = np.array([r.kind not in EXCLUDED_KINDS for r in runs] + [False], bool)
    top_cls = run_cls[top]                       # -1 indexes the sentinel
    top_vis = run_vis[top] & (top >= 0)
    top_cls[top < 0] = -1
    findings: list[dict] = []
    att = attrib

    def thread_of(mask: np.ndarray) -> np.ndarray:
        # rows of a fill a filament apart leave one-pixel slits on this grid
        # that the eye reads as solid cover: close them (one pixel, 0.1 mm)
        return _close(mask, 1)

    def emit(kind, cls, mask, weight, magnitude, extra=None, why_extra=(), art_comp=None):
        produced = att.produced_by(mask) if att else []
        meant = att.meant_for(mask) if att else []
        why = _explain(kind, produced, meant, list(why_extra))
        area = float(mask.sum()) / (px * px)
        f = {"kind": kind, "cls": int(cls) if cls is not None else None,
             "thread_rgb": list(classes[cls]) if cls is not None and cls >= 0 else None,
             "at_mm": _at(grid, mask, weight), "box_mm": _box_mm(grid, mask),
             "area_mm2": round(area, 2), "magnitude_mm": round(float(magnitude), 2),
             "art_component": art_comp, "produced_by": produced, "meant_for": meant,
             "explained_by": why}
        if extra:
            f.update(extra)
        f["severity"] = ("error" if not why else
                         "misfire" if (area >= MISFIRE_MM2 or float(magnitude) >= MISFIRE_MM
                                       or kind == "MOVED") else "explained")
        findings.append(f)

    ink_all = art == OTHER_INK
    for c in range(len(classes)):
        if c not in invisible:
            ink_all |= art == c
    # the gap and hole reads judge ink that holds a shape: anti-alias specks
    # (a pixel or two of a third colour along an edge) would each grow a
    # Voronoi line of their own a pull's width from the ink
    ink_vis = _keep_components(ink_all, ART_MIN_MM2 * px * px, ART_MIN_HALF_MM, px)
    thread_vis = thread_of(top_vis & ~np.isin(top_cls, list(invisible) or [-99]) & (top_cls >= 0))
    solid = _open(thread_vis, max(1, int(round(THREAD_MM * px / 2.0)) + 0))
    d_solid = _dist_to(solid, px)
    claimed_thread = np.zeros(art.shape, bool)   # thread pixels a finding already owns
    claimed_art = np.zeros(art.shape, bool)

    # --- CLOSED: holes of the ink (fabric enclosed by any visible ink) -----
    non_ink = ~ink_vis
    n, lab, stats, _ = _components(non_ink, 4)
    depth_non_ink = _depth(non_ink, px)
    for i in range(1, n):
        x, y, w, h, a = stats[i]
        if x == 0 or y == 0 or x + w >= grid.w or y + h >= grid.h:
            continue                              # the field, not a hole
        if a / (px * px) < 0.3:
            continue
        hole = lab == i
        a_half = float(depth_non_ink[hole].max())
        if a_half < SPACE_MIN_HALF_MM:
            continue
        zone = _dilate(hole, tol_px) & ~ink_vis
        clear = float(np.where(zone, d_solid, 0).max()) if zone.any() else 0.0
        keep = max(SPACE_KEEP_HALF_MM, SPACE_KEEP_FRAC * a_half)
        if clear >= keep:
            continue
        why = ["pull_comp"] if a_half <= tol_mm + 0.05 else []
        emit("CLOSED", None, hole, depth_non_ink, a_half - clear,
             {"art_half_mm": round(a_half, 2), "sewn_clear_half_mm": round(clear, 2)}, why)
        claimed_thread |= hole & thread_vis

    # --- MERGED: gaps between shapes, bridged by solid thread ---------------
    # Twice: between any two inks across FABRIC (two letters on cloth), and
    # per colour class across ANOTHER colour (two yellow letters joined over
    # their pink ground: on lt_ahora the H and O, and the A and the "!").
    merged_zone = np.zeros(art.shape, bool)

    def bridges(shapes: np.ndarray, gap_on: np.ndarray, d_bridge: np.ndarray, cls):
        nonlocal claimed_thread, merged_zone
        n_, lab_, _s, _c = _components(shapes, 8)
        if n_ <= 2:
            return
        src = (~shapes).astype(np.uint8)
        _d, vor = cv2.distanceTransformWithLabels(src, cv2.DIST_L2, 5, labelType=cv2.DIST_LABEL_CCOMP)
        # map the distance labels (per zero-pixel component) to shape ids
        lut = np.zeros(int(vor.max()) + 1, np.int32)
        ys, xs = np.nonzero(shapes)
        lut[vor[ys, xs]] = lab_[ys, xs]
        owner = lut[vor]
        b = np.zeros(art.shape, bool)
        b[:, :-1] |= owner[:, :-1] != owner[:, 1:]
        b[:-1, :] |= owner[:-1, :] != owner[1:, :]
        gap_half = _dist_to(shapes, px)
        b &= gap_on & (gap_half >= SPACE_MIN_HALF_MM) & (gap_half <= GAP_MAX_HALF_MM)
        bridged = b & (d_bridge <= SPACE_KEEP_HALF_MM)
        bridged = _dilate(bridged, 1) & _dilate(b, 1)
        nb, labb, _sb, _cb = _components(bridged, 8)
        for i in range(1, nb):
            core = (labb == i) & b
            if not core.any():
                continue
            ys, xs = np.nonzero(core)
            length = max(np.ptp(xs), np.ptp(ys)) / px + 1.0 / px
            if length < BRIDGE_MIN_MM:
                continue
            pair = sorted({int(owner[y, x]) for y, x in zip(ys, xs)} |
                          {int(owner[min(y + 1, grid.h - 1), x]) for y, x in zip(ys, xs)} |
                          {int(owner[y, min(x + 1, grid.w - 1)]) for y, x in zip(ys, xs)})
            # the median along the bridge: at its two ends the midline runs
            # past the shapes' corners and the distance to ink grows
            g = float(np.median(gap_half[core]))
            why = ["pull_comp"] if g <= tol_mm + 0.05 else []
            emit("MERGED", cls, core, None, g,
                 {"art_gap_half_mm": round(g, 2), "length_mm": round(length, 2),
                  "components": pair[:4], "across": "fabric" if cls is None else "other_ink"}, why)
            zone = _dilate(core, int(round(g * px)) + tol_px)
            claimed_thread |= zone & thread_vis & ~shapes
            merged_zone |= zone & ~shapes

    bridges(ink_vis, ~ink_all, d_solid, None)
    for c in range(len(classes)):
        if c in invisible:
            continue
        Ac = _keep_components(art == c, ART_MIN_MM2 * px * px, ART_MIN_HALF_MM, px)
        if not Ac.any():
            continue
        Tc = thread_of((top_cls == c) & top_vis)
        solid_c = _open(Tc, max(1, int(round(THREAD_MM * px / 2.0))))
        bridges(Ac, ink_all & (art != c), _dist_to(solid_c, px), c)

    # --- per colour class ---------------------------------------------------
    for c in range(len(classes)):
        if c in invisible:
            continue
        A = art == c
        Tall = thread_of(top_cls == c)
        Tvis = thread_of((top_cls == c) & top_vis)
        if not A.any() and not Tvis.any():
            continue
        dT = _dist_to(Tall, px)
        dA = _dist_to(A, px)
        depthA = _depth(A, px)
        na, labA, statsA, centA = _components(A, 8)
        ns, labS, statsS, centS = _components(Tvis, 8)
        # overlap counts art comp x sewn comp
        both = (labA > 0) & (labS > 0)
        pairs = np.stack([labA[both], labS[both]], 1)
        ov: dict[tuple[int, int], int] = {}
        if len(pairs):
            u, cnt = np.unique(pairs, axis=0, return_counts=True)
            ov = {(int(a), int(s)): int(k) for (a, s), k in zip(u, cnt)}
        partners_a: dict[int, list[int]] = {}
        partners_s: dict[int, list[int]] = {}
        for (ai, si), k in ov.items():
            if k >= 0.1 * min(statsA[ai, 4], statsS[si, 4]):
                partners_a.setdefault(ai, []).append(si)
                partners_s.setdefault(si, []).append(ai)
        moved_s: set[int] = set()
        judged = []
        for ai in range(1, na):
            area = statsA[ai, 4] / (px * px)
            if area < ART_MIN_MM2:
                continue
            x, y, w, h, _ = statsA[ai]
            comp = labA == ai
            if float(depthA[comp].max()) < ART_MIN_HALF_MM:
                continue
            judged.append(ai)
            cov = float((dT[comp] <= tol_mm).mean())
            # MOVED: a 1:1 partner, or a nearby unmatched one when nothing sews it
            cands = []
            ps = partners_a.get(ai, [])
            if len(ps) == 1 and len(partners_s.get(ps[0], [])) == 1:
                cands = ps
            elif cov < MISSING_COVER:
                r = MOVE_SEARCH_MM * px
                for si in range(1, ns):
                    if si in moved_s or partners_s.get(si):
                        continue
                    if np.hypot(*(centS[si] - centA[ai])) > r:
                        continue
                    ratio = statsS[si, 4] / max(1, statsA[ai, 4])
                    if 0.4 <= ratio <= 2.5:
                        cands.append(si)
            done = False
            for si in cands:
                off = centS[si] - centA[ai]
                if np.hypot(*off) / px < max(tol_mm, 0.5):
                    continue
                # the match on a crop around both, padded by the shift and tol
                bx0 = min(statsA[ai, 0], statsS[si, 0])
                by0 = min(statsA[ai, 1], statsS[si, 1])
                bx1 = max(statsA[ai, 0] + statsA[ai, 2], statsS[si, 0] + statsS[si, 2])
                by1 = max(statsA[ai, 1] + statsA[ai, 3], statsS[si, 1] + statsS[si, 3])
                padc = tol_px + 2 + int(np.ceil(np.abs(off).max()))
                sl = (slice(max(0, by0 - padc), by1 + padc), slice(max(0, bx0 - padc), bx1 + padc))
                ca, cs = comp[sl], labS[sl] == si
                m0 = _match(ca, cs, tol_px)
                m1 = _match(_shift(ca, int(round(off[0])), int(round(off[1]))), cs, tol_px)
                S = labS == si
                if m1 >= MOVE_MATCH and m1 - m0 >= MOVE_GAIN:
                    emit("MOVED", c, comp | S, None, np.hypot(*off) / px,
                         {"offset_mm": [round(off[0] / px, 2), round(off[1] / px, 2)],
                          "match_before": round(m0, 2), "match_after": round(m1, 2),
                          "produced_at_mm": _at(grid, S)}, art_comp=int(ai))
                    findings[-1]["produced_by"] = att.produced_by(S) if att else []
                    findings[-1]["explained_by"] = _explain("MOVED", findings[-1]["produced_by"],
                                                            findings[-1]["meant_for"], [])
                    if not findings[-1]["explained_by"]:
                        findings[-1]["severity"] = "error"
                    moved_s.add(si)
                    claimed_art |= comp
                    claimed_thread |= S
                    done = True
                    break
            if done:
                continue
            # MOVED, the general case: the letter's thread touches its
            # neighbours' (a re-set word sewn as one blob), so no 1:1 partner
            # exists. Search a local shift that lays the art shape onto its
            # colour's thread (template match within MOVE_SEARCH_MM), and call
            # it moved when the shifted shape is sewn and the unshifted is not.
            if cov < MOVE_COV0:
                hit = _best_shift(comp, statsA[ai], Tall, dT, tol_mm, px)
                if hit is not None:
                    (dx, dy), cov1 = hit
                    moved = _shift(comp, dx, dy)
                    # the thread it lands on must not be another shape's own
                    # (a missing letter next to its twin is missing, not moved)
                    away = moved & ~comp
                    others = float((dA[away] <= tol_mm).mean()) if away.any() else 0.0
                    if cov1 >= MOVE_COV1 and cov1 - cov >= MOVE_GAIN_COV and others < 0.5:
                        S = Tall & _dilate(moved, tol_px)
                        emit("MOVED", c, comp | moved, None, math.hypot(dx, dy) / px,
                             {"offset_mm": [round(dx / px, 2), round(dy / px, 2)],
                              "covered_before": round(cov, 2), "covered_after": round(cov1, 2),
                              "produced_at_mm": _at(grid, moved)}, art_comp=int(ai))
                        findings[-1]["produced_by"] = att.produced_by(S & ~comp) if att else []
                        findings[-1]["explained_by"] = _explain("MOVED", findings[-1]["produced_by"],
                                                                findings[-1]["meant_for"], [])
                        findings[-1]["severity"] = "misfire" if findings[-1]["explained_by"] else "error"
                        claimed_art |= comp
                        claimed_thread |= S & Tvis
                        continue
            if cov < MISSING_COVER:
                why = []
                emit("MISSING", c, comp, depthA, float(depthA[comp].max()) * 2,
                     {"covered_frac": round(cov, 3)}, why, art_comp=int(ai))
                claimed_art |= comp
        # EXTRA: sewn components with almost no ink of their colour under them
        for si in range(1, ns):
            if si in moved_s:
                continue
            area = statsS[si, 4] / (px * px)
            if area < EXTRA_MIN_MM2:
                continue
            S = (labS == si) & ~claimed_thread
            if S.sum() / (px * px) < EXTRA_MIN_MM2:
                continue
            on = float((dA[S] <= tol_mm).mean())
            if on >= EXTRA_ON_ART:
                continue
            under = art[S]
            what = ("over_fabric" if (np.isin(under, (BG, GARMENT))).mean() >= 0.5 else "over_other_ink")
            emit("EXTRA", c, S, dA, float(dA[S].max()), {"on_ink_frac": round(on, 3), "lies": what})
            claimed_thread |= S
        # SHAPE: residual deficit and excess patches
        deficit = A & (dT > tol_mm) & ~claimed_art & ~merged_zone
        excess = Tvis & (dA > tol_mm) & ~claimed_thread
        for mask, dist, side in ((deficit, dT, "deficit"), (excess, dA, "excess")):
            nd, labD, statsD, _ = _components(mask, 8)
            for di in range(1, nd):
                if statsD[di, 4] / (px * px) < SHAPE_MIN_MM2:
                    continue
                patch = labD == di
                deep = float(dist[patch].max())
                if not math.isfinite(deep):
                    deep = float(_depth(patch, px).max()) * 2
                if deep < tol_mm + THREAD_MM:
                    continue
                ac = int(np.bincount(labA[patch & (labA > 0)]).argmax()) if (patch & (labA > 0)).any() else None
                emit("SHAPE", c, patch, np.where(np.isfinite(dist), dist, 0), deep,
                     {"side": side, "depth_mm": round(deep, 2)}, art_comp=ac)
        # WIDTH: per judged art component held by thread of its colour
        if Tall.any():
            depthT = _depth(Tall, px)
            src = (~A).astype(np.uint8)
            _d, vorA = cv2.distanceTransformWithLabels(src, cv2.DIST_L2, 5, labelType=cv2.DIST_LABEL_CCOMP)
            lutA = np.zeros(int(vorA.max()) + 1, np.int32)
            ys, xs = np.nonzero(A)
            lutA[vorA[ys, xs]] = labA[ys, xs]
            nearestA = lutA[vorA]
            for ai in judged:
                comp = labA == ai
                # a shape a finding owns, or one joined to its neighbour (its
                # footprint is then cut at a Voronoi line, not at its edge)
                if (comp & claimed_art).any() or (_dilate(comp, tol_px + 2) & merged_zone).any():
                    continue
                x, y, w, h, _ = statsA[ai]
                pad = int(round((tol_mm + 1.5) * px))
                y0, y1 = max(0, y - pad), min(grid.h, y + h + pad)
                x0, x1 = max(0, x - pad), min(grid.w, x + w + pad)
                ca = comp[y0:y1, x0:x1]
                foot = (Tall[y0:y1, x0:x1] & (nearestA[y0:y1, x0:x1] == ai)
                        & (dA[y0:y1, x0:x1] <= tol_mm + 1.5))
                if foot.sum() < 4 or ca.sum() < 4:
                    continue
                ska = _skeleton(ca)
                sks = _skeleton(foot)
                if not ska.any() or not sks.any():
                    continue
                wa = 2.0 * float(np.median(depthA[y0:y1, x0:x1][ska]))
                ws = 2.0 * float(np.median(depthT[y0:y1, x0:x1][sks]))
                if wa > WIDTH_MAX_MM:
                    continue
                # its own pull never thins a shape, but a NEIGHBOUR's does: a
                # pink field between two yellow letters loses `tol` at each
                # edge it shares with them. Allowed thinning = 2 tol x the
                # share of its edge that touches other visible ink.
                edge = ca & ~cv2.erode(ca.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
                nb_ink = _dilate(ink_all[y0:y1, x0:x1] & ~A[y0:y1, x0:x1], 2)
                shared = float((edge & nb_ink).sum()) / max(1, int(edge.sum()))
                thin = (ws < WIDTH_THIN_RATIO * wa
                        and wa - ws >= max(WIDTH_THIN_MM, 2 * tol_mm * shared))
                # each edge's thread may sit `tol` past the ink (pull + half a
                # filament, which a faithful fill reads exactly); thicker than
                # that by half a filament more is thicker than drawn
                thick = ws >= WIDTH_THICK_RATIO * wa and ws - wa > 2 * tol_mm + THREAD_MM / 2
                if not (thin or thick):
                    continue
                fm = np.zeros(art.shape, bool)
                fm[y0:y1, x0:x1] = foot
                emit("WIDTH", c, fm if fm.any() else comp, None, ws - wa,
                     {"art_width_mm": round(wa, 2), "sewn_width_mm": round(ws, 2),
                      "which": "thin" if thin else "thick"}, art_comp=int(ai))
    # --- ink of a colour no thread carries: missing unless ANY thread sews it
    O = art == OTHER_INK
    if O.any():
        d_any = _dist_to(thread_vis | (top_cls >= 0), px)
        depthO = _depth(O, px)
        no, labO, statsO, _ = _components(O, 8)
        for oi in range(1, no):
            if statsO[oi, 4] / (px * px) < ART_MIN_MM2:
                continue
            comp = labO == oi
            if float(depthO[comp].max()) < ART_MIN_HALF_MM:
                continue
            cov = float((d_any[comp] <= tol_mm).mean())
            if cov < MISSING_COVER:
                emit("MISSING", None, comp, depthO, float(depthO[comp].max()) * 2,
                     {"covered_frac": round(cov, 3), "colour": "no_thread_near"})
    return _dedupe(findings)


def _dedupe(findings: list[dict], radius_mm: float = 1.0) -> list[dict]:
    """One finding per kind and place: a wrong-colour patch reads as excess of
    one class and deficit of another; keep the bigger, list the other's class."""
    out: list[dict] = []
    for f in sorted(findings, key=lambda f: -f["area_mm2"]):
        hit = next((g for g in out if g["kind"] == f["kind"] and
                    math.dist(g["at_mm"], f["at_mm"]) <= radius_mm and g.get("side") == f.get("side")
                    and g.get("cls") == f.get("cls")), None)
        if hit is None:
            out.append(f)
    return out


def read(p, result, plan, cfg, pull_mm: float | None = None, px: float = PX_PER_MM,
         want_rasters: bool = False) -> dict:
    """The proof-read of one finished job. `p` is the art raster the pipeline
    traced (`rgb`, `bg_mask`, `art_bbox`, `px_per_mm`), `result` the
    PipelineResult (regions + meta), `plan` the StitchPlan. -> a plain dict,
    JSON-safe (rasters only with `want_rasters`, for the CLI)."""
    if pull_mm is None:
        from .pipeline import fabric_for
        pull_mm = float(fabric_for(cfg).pull_comp_mm)
    tol = pull_mm + THREAD_MM / 2.0
    block_rgbs = [tuple(int(v) for v in b.rgb) for b in plan.blocks]
    classes, of_block = colour_classes(block_rgbs)
    garment = getattr(cfg, "garment_rgb", None)
    invisible = set()
    if garment is not None:
        g = _lab([garment])[0]
        invisible = {i for i, q in enumerate(_lab(classes)) if float(np.linalg.norm(q - g)) < GARMENT_DE}
    grid = make_grid(plan, art_mm_box(p.art_bbox, p.px_per_mm), px)
    top, runs = thread_raster(plan, grid, of_block)
    art = art_raster(p.rgb, p.bg_mask, p.art_bbox, p.px_per_mm, grid, classes, garment)
    regions = list(getattr(result, "regions", None) or ())
    reg_raster, by_id = region_raster(regions, grid)
    dropped = set()
    for w in list(getattr(plan, "warnings", None) or ()) + list(getattr(result, "warnings", None) or ()):
        if isinstance(w, dict) and w.get("code") in DROP_CODES:
            for k in ("ids", "shape_ids"):
                for sid in w.get(k) or ():
                    dropped.add(str(sid))
    att = _Attrib(top, runs, reg_raster, by_id, dropped, grid, getattr(plan, "merged_into", None))
    findings = read_arrays(art, top, runs, classes, grid, tol, pull_mm, att, invisible)
    sev_rank = {"error": 0, "misfire": 1, "explained": 2}
    findings.sort(key=lambda f: (sev_rank[f["severity"]], -f["area_mm2"]))
    counts: dict[str, int] = {}
    for f in findings:
        counts[f["kind"]] = counts.get(f["kind"], 0) + 1
    out = {
        "version": 1,
        "px_per_mm": px, "tol_mm": round(tol, 3), "pull_mm": round(pull_mm, 3), "thread_mm": THREAD_MM,
        "grid_origin_mm": [round(grid.x0, 3), round(grid.y0, 3)], "grid_px": [grid.w, grid.h],
        "classes": [list(c) for c in classes], "invisible_classes": sorted(invisible),
        "counts": counts,
        "unexplained": sum(1 for f in findings if f["severity"] == "error"),
        "misfires": sum(1 for f in findings if f["severity"] == "misfire"),
        "explained": sum(1 for f in findings if f["severity"] == "explained"),
        "findings_total": len(findings),
        "findings": findings[:MAX_FINDINGS],
    }
    if want_rasters:
        out["_rasters"] = {"art": art, "top": top, "runs": runs, "grid": grid}
    return out


def metrics(report: dict) -> dict:
    """The scalar metrics preflight carries beside the full payload."""
    return {"proofread_checked": True,
            "proofread_unexplained": report["unexplained"],
            "proofread_misfires": report["misfires"],
            "proofread_explained": report["explained"],
            "proofread_findings": report["findings_total"],
            "proofread_tol_mm": report["tol_mm"],
            "proofread": report}
