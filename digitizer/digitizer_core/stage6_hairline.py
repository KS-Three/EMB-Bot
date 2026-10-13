"""The hairline tier: a one-thread stroke sewn as ONE run along its skeleton.

Kent, 2026-10-12: *"Thread is extremely thin, we should be able to embroider
hair!"* The research behind this (docs/fine-detail-hair-research-2026-10-12.md,
PR #843) found the engine never asks what weight it sews, and that a stroke
under the satin floor sews as a THREE-pass bean on its outline — three widths
of mark for a one-width stroke. A single strand of 40 wt already lays about
0.40 mm; 60 wt about 0.32. So a stroke at or under 1.5 laid widths
(`machine.HAIRLINE_MAX_WIDTHS`) sews here as one pass down its middle.

Built DEFAULT OFF (`cfg.hairline`). Every number is a CANDIDATE from a source,
not a setting — ROADMAP gate 1; the card that would settle them is restated
in docs/hairline-prototype-2026-10-12.md.

How a shape is sewn:

1. **Measure.** Rasterize the ARTWORK polygon fine enough that the stroke is
   at least `_PX_ACROSS` pixels wide (the same rule `stage6_satin._rasterize`
   uses, with a higher cap because a hair network spans the design), take the
   medial axis and its distance, and read the stroke width off the skeleton.
   The width is read on the strands' BODIES — a disk around every branch
   pixel is left out, because a crossing reads wider than either strand
   (1.41x at right angles) and a hair network is full of them. The shape is
   admitted when the MEDIAN body width is at or under the limit and the 95th
   percentile at or under twice it (a real blob is not a crossing).
   The gate is per SHAPE, and a hair network the tracer delivers as one
   region is all-or-nothing: a strand inside it drawn wider than the limit
   still sews as one run when the network's median admits it.
2. **Decompose.** `stage6_satin._skeleton_edges` (reused, not copied) splits
   the skeleton into edges between nodes. End-cap spurs — a free edge shorter
   than two stroke widths hanging off a node — are dropped.
3. **Walk.** Every edge is sewn exactly once. A path starts at the edge end
   nearest the needle and, at each node, continues onto the unsewn edge that
   turns least — so at a crossing the needle follows the strand straight
   through instead of turning onto its neighbour. When a node has nothing
   left, the path ends and the next starts at the nearest unsewn end
   (nearest-neighbour chaining, the same economy `stage6_detail.detail_runs`
   orders its lines by).
4. **Stitch.** Each path is divided into equal stitches nearest
   `stitch_mm` (`cfg.hairline_stitch_mm`, Melco's 1.5 mm walk floor). Where a
   stitch's chord leaves the drawn line by more than half a thread width (a
   curl), it is halved — but never below `machine.MIN_STITCH_MM`, which is
   the needle's floor and does not move with thread weight. A path shorter
   than `machine.RUN_MIN_LOOP_MM` is dropped and counted.
5. **Hop.** Between paths: a jump, and a trim when the hop is longer than
   `trim_at_mm` — the rule `detail_runs` already applies. No underlay, no
   travel, and no lock of its own; stage 7's existing tie rules see these
   runs like any other.

Reused, said once: `_skeleton_edges` (stage6_satin), the equal-division
arc-length resample idea and the jump/trim rule (stage6_detail), and stage 7's
per-shape emission slot, so sequencing, colour blocks and every exporter take
these runs with no change.

Step 2 (2026-10-12, docs/hairline-ground-2026-10-12.md), still under
`cfg.hairline`:

- **The width is read off the SOURCE** (finding 1 of the prototype doc,
  corrected: its "0.11 mm wide" was a units error, but the tracer's error
  is real and has no fixed sign — a lone 0.33 mm stroke traces at 0.24, a
  hair network near the truth because crossings absorb cells). `InkSource`
  carries the artwork's own pixels —
  native resolution when stage 1 upscaled, the way `stage4_vectorize`'s
  native edge read and `_coverage_parts` get at them — and
  `source_width_mm` integrates ink coverage across the stroke along the
  skeleton's normals. The traced width is the fallback when the source has
  no contrast edge there.
- **Who is a hairline at all** (`hairline_candidates`, finding 4): a thin
  shape whose thread also sews a shape the gate rejects — a ground colour —
  qualifies only when it is DARKER than the colours around it. A sliver of
  skin between two strands is a piece of the ground, not a hair.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import cv2
import numpy as np
from shapely.geometry import LineString, Point
from shapely.ops import unary_union
from shapely.strtree import STRtree
from skimage.morphology import medial_axis

from . import machine, stitches
from .stage6_satin import _skeleton_edges
from .stitches import StitchRun
from .threads import chart_for, rgb_to_lab

# Pixels across the narrowest stroke when rasterizing. stage6_satin's rule is
# 8 ("thinning a wall under ~8 px wide invents branch points at every
# wiggle"); this tier also GATES on the width, and at 8 px one pixel is 12%
# of it — a 0.55 mm stroke read 0.47 and passed the 60 wt gate. 16 holds the
# read to about a twentieth of a millimetre.
_PX_ACROSS = 16.0
# Never coarser than this, whatever the stroke.
_PX_PER_MM_MIN = 20.0
# Grid cap on the long side. A hair network can span the whole design;
# stage6_satin's 900 px would put a 0.3 mm strand on 3 px at 80 mm.
_MAX_PX = 2400
_PAD_PX = 2

# Gate percentiles (see the module docstring, step 1).
_GATE_PCT = 50.0
_BLOB_PCT = 95.0
_BLOB_FACTOR = 2.0

# A free skeleton edge shorter than this many stroke widths is an end-cap
# artifact of the medial axis, not a strand.
_SPUR_WIDTHS = 2.0

# How far back along a path (mm) its heading is read when choosing the
# straightest continuation at a node — at least this, and at least
# `_HEADING_WIDTHS` stroke widths, so the read starts outside the crossing's
# core where the medial axis bends toward the junction.
_HEADING_MM = 0.6
_HEADING_WIDTHS = 4.0

# An edge between two NODES shorter than this many stroke widths is the
# inside of one crossing (an X thins to two branch points and a bridge):
# its two nodes are merged into one and the bridge is not sewn — it lies
# under the crossing strands' own thread.
_BRIDGE_WIDTHS = 2.5

# A stitch's chord may leave the drawn line by at most this fraction of the
# run's own width before the stitch is halved. Half a thread: the needle line
# stays inside the mark the thread lays. candidate: geometry, unsewn.
_CURL_TOL_WIDTHS = 0.5

# --- the source width read (step 2) ---
# Skeleton samples the source read takes per shape, spread evenly over the
# strands' bodies (crossings already excluded by `measure`).
_SRC_SAMPLES = 240
# Profile step along each normal, in SOURCE pixels. Bilinear samples of an
# aliased edge integrate to its exact pixel count, so a quarter pixel is
# plenty; the read is an integral, not an edge fit.
_SRC_STEP_PX = 0.25
# How far past the traced half-width each profile reaches, in source pixels,
# so both ends land on the surround even where the tracer under-reads.
_SRC_MARGIN_PX = 2.0
# Least contrast between ink and the surround on one side of a profile, in
# the field's units (CIELAB with alpha x 100 as a fourth axis — the space
# `stage4_vectorize._native_profile_image` reads edges in). Under it that side
# has no edge to read, and the sample is skipped.
_SRC_MIN_CONTRAST = 12.0
# Coverage at or under this is surround: the integral along a profile stops
# at the first such sample walking out from the skeleton.
_SRC_GAP = 0.05
# The source width is used when at least this share of the samples read;
# otherwise the gate falls back to the traced width.
_SRC_MIN_VALID = 0.5

# --- the per-strand gate (step 3, 2026-10-12) ---
# Source profiles read per skeleton edge, spread evenly over the edge's body
# pixels; an edge's source width is the median of those that found an edge.
_EDGE_SAMPLES = 12
# A hairline ribbon is the edge's width read plus this much (mm), subtracted
# from the shape; what is left is opened by half a laid width, so a rim the
# tracer left beside a thin strand (narrower than a thread) is not sewn.
_RIBBON_PAD_MM = 0.02
# At a node where a hairline edge meets an edge that is NOT one, the ribbon is
# cut back by a disk of this many local radii, so the thick strand keeps its
# own polygon whole through the junction.
_JUNCTION_CUT = 1.0

# --- the line test (the photo trial, 2026-10-12) ---
# A branch is a strand only when its core leaves the straight path between
# the colours on its two sides by at least this much (CIELAB + alpha x 100,
# `_SRC_MIN_CONTRAST`'s units and value). Measured on owl_kent.jpg: eye rims
# and beak bristles read 14-66, the grey blur rim of a feather bar and
# slivers of smooth down 0-10. Candidate, unsewn (ROADMAP gate 1).
_LINE_MIN_CONTRAST = _SRC_MIN_CONTRAST

# --- the ground-fragment rule (step 2) ---
# A thin shape of a ground colour is a hairline only when it is darker than
# the colours its edge touches by more than this many L* units.
_DARKER_L = 2.0
# Two shapes "touch" within this distance (mm) — the bean-letter ground rule's.
_TOUCH_MM = 0.1


@dataclass
class InkSource:
    """The artwork's own pixels, for reading what a stroke was DRAWN at.

    `rgb` is the source as stage 1 delivered it: `Prep.native_rgb` when it
    upscaled (with `Prep.native_alpha`, and the per-axis `upscale` that maps
    the traced grid onto it by cv2's half-pixel-centre rule), else `Prep.rgb`
    itself with `bg` (`Prep.bg_mask`) standing in for alpha. `px_per_mm` and
    `origin_px` are the TRACED grid's mm <-> px mapping (the art bbox centre,
    `SourcePixels`' origin). The field is built on first use and cached: a
    flat design that never turns `cfg.hairline` on never pays for it."""
    rgb: np.ndarray
    alpha: np.ndarray | None
    bg: np.ndarray | None
    upscale: tuple[float, float]
    px_per_mm: float
    origin_px: tuple[float, float]
    _field: np.ndarray | None = field(default=None, repr=False, compare=False)

    @classmethod
    def from_prep(cls, p, origin_px: tuple[float, float]) -> "InkSource":
        if p.native_rgb is not None:
            return cls(rgb=p.native_rgb, alpha=p.native_alpha, bg=None,
                       upscale=(float(p.upscale[0]), float(p.upscale[1])),
                       px_per_mm=float(p.px_per_mm), origin_px=origin_px)
        return cls(rgb=p.rgb, alpha=None, bg=p.bg_mask, upscale=(1.0, 1.0),
                   px_per_mm=float(p.px_per_mm), origin_px=origin_px)

    def field(self) -> np.ndarray:
        """(H, W, 4) float32: CIELAB of the source composited over white by
        its alpha, and alpha x 100 — `stage4_vectorize._native_profile_image`'s
        space, so a transparent-to-ink edge has contrast whatever the ink."""
        if self._field is None:
            h, w = self.rgb.shape[:2]
            if self.alpha is not None:
                a = self.alpha.astype(np.float32) / 255.0
            elif self.bg is not None:
                a = (~self.bg).astype(np.float32)
            else:
                a = np.ones((h, w), np.float32)
            a = a[..., None]
            comp = np.clip(self.rgb.astype(np.float32) * a + 255.0 * (1.0 - a), 0, 255)
            lab = rgb_to_lab(comp.reshape(-1, 3)).reshape(h, w, 3).astype(np.float32)
            self._field = np.concatenate([lab, a * 100.0], axis=-1).astype(np.float32)
        return self._field

    def to_src(self, xy_mm: np.ndarray) -> np.ndarray:
        """(N, 2) mm -> (N, 2) source pixel coordinates (x, y)."""
        sx, sy = self.upscale
        cx, cy = self.origin_px
        X = xy_mm[:, 0] * self.px_per_mm + cx
        Y = xy_mm[:, 1] * self.px_per_mm + cy
        return np.column_stack([(X + 0.5) / sx - 0.5, (Y + 0.5) / sy - 0.5])

    @property
    def src_px_per_mm(self) -> float:
        return self.px_per_mm / max(self.upscale)


def _parts(poly):
    return list(poly.geoms) if hasattr(poly, "geoms") else [poly]


def _rasterize(poly, est_width_mm: float):
    """-> (mask uint8, scale px/mm, x0 mm, y0 mm) with `_PAD_PX` of margin."""
    x0, y0, x1, y1 = poly.bounds
    dim = max(x1 - x0, y1 - y0, 1e-6)
    need = max(_PX_PER_MM_MIN, _PX_ACROSS / max(est_width_mm, 1e-3))
    scale = min(need, _MAX_PX / dim)
    w = int(math.ceil((x1 - x0) * scale)) + 2 * _PAD_PX + 1
    h = int(math.ceil((y1 - y0) * scale)) + 2 * _PAD_PX + 1
    img = np.zeros((h, w), np.uint8)

    def to_px(coords):
        a = np.asarray(coords, np.float64)
        return np.round(np.column_stack([(a[:, 0] - x0) * scale + _PAD_PX,
                                         (a[:, 1] - y0) * scale + _PAD_PX])).astype(np.int32)

    for part in _parts(poly):
        cv2.fillPoly(img, [to_px(part.exterior.coords)], 255)
        for ring in part.interiors:
            cv2.fillPoly(img, [to_px(ring.coords)], 0)
    return img, scale, x0, y0


def _estimate_width_mm(poly) -> float:
    """2A/P: a thin ribbon of length L and width w has A = wL, P ~ 2L."""
    per = poly.length
    return 2.0 * poly.area / per if per > 0 else 0.0


def measure(poly, max_width_mm: float, ink: InkSource | None = None):
    """-> dict(admit, width_mm, width_traced_mm, width_source_mm, width_p95_mm,
    skel, scale, x0, y0) or None.

    `width_mm` is what the gate read: the SOURCE width (`source_width_mm`)
    when `ink` is given and the source has an edge to read, else the traced
    median — so with no `ink` this is exactly the 2026-10-12 prototype's
    gate. `width_p95_mm`, the blob check, stays on the traced raster.

    `None` means the cheap 2A/P estimate already says the shape is far too
    wide to be a hairline, so nothing was rasterized."""
    if poly is None or poly.is_empty or poly.area <= 0:
        return None
    est = _estimate_width_mm(poly)
    if est > _BLOB_FACTOR * max_width_mm:
        return None
    mask, scale, x0, y0 = _rasterize(poly, max(est, 0.05))
    skel, dist = medial_axis(mask > 0, return_distance=True, rng=0)
    if not skel.any():
        return None
    # Read the width on the strands' BODIES: where strands cross, the medial
    # axis sits in the crossing's wider core (1.41x at right angles, more at a
    # shallow angle), and a hair network is full of crossings. A disk of 1.5
    # local radii around every branch pixel is excluded; if that leaves
    # nothing (a tiny shape that is all junction), every pixel counts.
    sk = skel.astype(np.uint8)
    nbrs = cv2.filter2D(sk, -1, np.ones((3, 3), np.float32),
                        borderType=cv2.BORDER_CONSTANT) - sk
    branch = (sk > 0) & (nbrs >= 3)
    body = skel.copy()
    if branch.any():
        veto = np.zeros_like(sk)
        for y, x in zip(*np.nonzero(branch)):
            cv2.circle(veto, (int(x), int(y)), int(math.ceil(1.5 * dist[y, x])) + 1, 1, -1)
        body &= veto == 0
        if not body.any():
            body = skel
    d = dist[body]
    # `cv2.fillPoly` paints the boundary pixels on BOTH sides, so a stroke
    # w*scale px wide fills ~w*scale + 1, and the EDT at its middle reads half
    # of that plus half a pixel: w*scale = 2d - 2. (Checked on buffered lines
    # 0.25 / 0.4 / 0.6 mm: 2d - 1 read +0.03 to +0.06 mm high.)
    widths = np.maximum(2.0 * d - 2.0, 1.0) / scale
    med = float(np.percentile(widths, _GATE_PCT))
    p95 = float(np.percentile(widths, _BLOB_PCT))
    src = None
    ink_colour = None
    if ink is not None:
        got = _source_widths(ink, skel, body, dist, scale, x0, y0)
        if got is not None and len(got[0]) >= _SRC_MIN_VALID * got[1]:
            src = float(np.median(got[0]))
            ink_colour = got[2]
    gate = src if src is not None else med
    m = {"admit": False, "width_mm": gate, "width_traced_mm": med,
         "width_source_mm": src, "width_p95_mm": p95,
         "skel": skel, "body": body, "dist": dist,
         "scale": scale, "x0": x0, "y0": y0}
    # Step 3: the gate is PER STRAND. The shape-level read above is the
    # shape's own summary (and what the prototype's all-or-nothing gate
    # tested: `shape_admit`); what is sewn is decided edge by edge.
    m["shape_admit"] = gate <= max_width_mm and p95 <= _BLOB_FACTOR * max_width_mm
    _decide_edges(m, poly, max_width_mm, ink, ink_colour)
    return m


def _decide_edges(m: dict, poly, max_width_mm: float, ink, ink_colour) -> None:
    """Walk the skeleton graph the tier builds (`_graph`) and decide each
    branch on its OWN width: the SOURCE read along the branch when `ink` gives
    an edge there, else the traced median of its body pixels. A branch is a
    hairline when that width is at or under `max_width_mm` and its 95th
    percentile is at or under `_BLOB_FACTOR` times it.

    A branch with no body pixel of its own (a short piece between two
    crossings, all inside the crossings' disks) cannot be read: it follows its
    neighbours — a hairline when every branch it touches is, thick when any
    is not — and on a branch with no neighbours at all, the traced width over
    every pixel of it.

    Sets `hair_edges`, `thick_edges`, `admit` (any hairline branch), and, when
    some branch is thick, `rest` (the shape's polygon minus the hairline
    ribbons, opened by half a laid width, pieces under `RUN_MIN_AREA_MM2`
    dropped) and `hair_geom` (the shape minus `rest`: the hairline parts'
    own territory, which is what stage 5's ground goes under). Both are None
    when every branch is a hairline — the prototype's shape, untouched.
    Candidate geometry, unsewn (ROADMAP gate 1)."""
    skel, body, dist, scale, x0, y0 = (m["skel"], m["body"], m["dist"],
                                       m["scale"], m["x0"], m["y0"])
    edges = _graph(m, max(m["width_traced_mm"], 1e-3))
    blob_lim = _BLOB_FACTOR * max_width_mm
    picks_y, picks_x, owner = [], [], []
    for k, e in enumerate(edges):
        a = np.asarray(e["px"], np.int64)
        xs, ys = a[:, 0], a[:, 1]
        e["w"] = e["w_traced"] = e["p95"] = None
        e["decided"] = False
        on = body[ys, xs]
        if on.any():
            w = np.maximum(2.0 * dist[ys[on], xs[on]] - 2.0, 1.0) / scale
            e["w_traced"] = float(np.median(w))
            e["p95"] = float(np.percentile(w, _BLOB_PCT))
            e["decided"] = True
            idx = np.nonzero(on)[0]
            take = idx[np.unique(np.round(np.linspace(0, len(idx) - 1,
                                                       min(len(idx), _EDGE_SAMPLES))).astype(int))]
            picks_y.extend(ys[take].tolist())
            picks_x.extend(xs[take].tolist())
            owner.extend([k] * len(take))
        else:
            w = np.maximum(2.0 * dist[ys, xs] - 2.0, 1.0) / scale
            e["w_all"] = float(np.median(w))
            e["p95_all"] = float(np.percentile(w, _BLOB_PCT))
    if ink is not None and ink_colour is not None and picks_y:
        got = _source_widths(ink, skel, body, dist, scale, x0, y0,
                             pick=(np.asarray(picks_y), np.asarray(picks_x)),
                             ink_colour=ink_colour)
        if got is not None:
            per: dict[int, list] = {}
            for k, w in zip(owner, got[3]):
                per.setdefault(k, []).append(w)
            for k, ws in per.items():
                ok = [w for w in ws if w is not None]
                if ok and len(ok) >= _SRC_MIN_VALID * len(ws):
                    edges[k]["w_source"] = float(np.median(ok))
    # The photo trial (2026-10-12): with the source in hand, a branch is a
    # strand only where the photograph shows a LINE there (`_line_contrasts`)
    # — read whether or not the width read found an ink colour, because a
    # sliver with no edge at all is exactly the case that used to fall back
    # to the traced width and pass.
    if ink is not None and picks_y:
        lines = _line_contrasts(ink, skel, dist, scale, x0, y0,
                                np.asarray(picks_y), np.asarray(picks_x))
        per_l: dict[int, list] = {}
        for k, v in zip(owner, lines):
            if v is not None:
                per_l.setdefault(k, []).append(v)
        for k, vs in per_l.items():
            edges[k]["line"] = float(np.median(vs))
    for e in edges:
        if not e["decided"]:
            continue
        e["w"] = e.get("w_source", e["w_traced"])
        e["admit"] = e["w"] <= max_width_mm and e["p95"] <= blob_lim
        if e["admit"] and e.get("line") is not None and e["line"] < _LINE_MIN_CONTRAST:
            e["admit"] = False
            e["refused"] = "no_line"
    # Branches too short to read follow their neighbours.
    by_node: dict[int, list[int]] = {}
    for i, e in enumerate(edges):
        for key in ("a", "b"):
            if e[key] is not None and e[key] >= 0:
                by_node.setdefault(e[key], []).append(i)
    for e in edges:
        if e["decided"]:
            continue
        nb = {j for key in ("a", "b") if e[key] is not None and e[key] >= 0
              for j in by_node.get(e[key], []) if edges[j] is not e and edges[j]["decided"]}
        if nb:
            e["admit"] = all(edges[j]["admit"] for j in nb)
            e["w"] = float(np.median([edges[j]["w"] for j in nb]))
        else:
            e["w"] = e["w_all"]
            e["admit"] = e["w"] <= max_width_mm and e["p95_all"] <= blob_lim
            if e["admit"] and ink is not None:
                # No neighbour to follow: the line test reads its own pixels.
                a = np.asarray(e["px"], np.int64)
                take = np.unique(np.round(np.linspace(0, len(a) - 1,
                                                      min(len(a), _EDGE_SAMPLES))).astype(int))
                vs = [v for v in _line_contrasts(ink, skel, dist, scale, x0, y0,
                                                 a[take, 1], a[take, 0]) if v is not None]
                if vs:
                    e["line"] = float(np.median(vs))
                    if e["line"] < _LINE_MIN_CONTRAST:
                        e["admit"] = False
                        e["refused"] = "no_line"
    hair = [e for e in edges if e["admit"]]
    thick = [e for e in edges if not e["admit"]]
    m.update(hair_edges=hair, thick_edges=thick, admit=bool(hair), rest=None, hair_geom=None)
    if not hair or not thick:
        return
    laid = max_width_mm / machine.HAIRLINE_MAX_WIDTHS
    mixed = ({e[key] for e in hair for key in ("a", "b") if e[key] is not None and e[key] >= 0}
             & {e[key] for e in thick for key in ("a", "b") if e[key] is not None and e[key] >= 0})
    ribbons = []
    for e in hair:
        rib = LineString(e["pts"]).buffer(max(e["w"], e["w_traced"] or 0.0) / 2.0 + _RIBBON_PAD_MM)
        for key, end in (("a", 0), ("b", -1)):
            if e[key] in mixed:
                px, py = e["px"][end]
                rib = rib.difference(Point(e["pts"][end]).buffer(
                    _JUNCTION_CUT * float(dist[py, px]) / scale + _RIBBON_PAD_MM))
        ribbons.append(rib)
    rest = poly.difference(unary_union(ribbons)).buffer(-0.5 * laid).buffer(0.5 * laid)
    parts = [g for g in _parts(rest)
             if g.geom_type == "Polygon" and g.area >= machine.RUN_MIN_AREA_MM2]
    if parts:
        rest = unary_union(parts)
        m["rest"] = rest
        m["hair_geom"] = poly.difference(rest)


def source_width_mm(ink: InkSource, skel, body, dist, scale: float,
                    x0: float, y0: float) -> float | None:
    """The stroke's DRAWN width, read off the source along the skeleton.

    At up to `_SRC_SAMPLES` body pixels of the skeleton, a profile runs
    along the local normal (the principal axis of the skeleton pixels round
    it) out to the traced half-width plus `_SRC_MARGIN_PX` source pixels each
    side, so both ends sit on the surround. Each profile point is unmixed
    between the surround colour at that side's end and the stroke's ink (the
    median over profiles of each profile's most ink-like point): coverage
    c = (F - S).(I - S) / |I - S|^2, clipped to 0..1, in the alpha-extended
    CIELAB field. The width is the integral of c across the profile — the
    area of ink per unit length, which is the drawn width whatever the
    anti-aliasing, and on an aliased edge the exact pixel count (a bilinear
    sample of a step integrates to the step). Median over the samples.

    -> mm, or None when fewer than `_SRC_MIN_VALID` of the profiles found an
    edge on both sides (an opaque source with no contrast edge there): the
    caller then gates on the traced width."""
    got = _source_widths(ink, skel, body, dist, scale, x0, y0)
    if got is None:
        return None
    widths, n = got[0], got[1]
    if len(widths) < _SRC_MIN_VALID * n:
        return None
    return float(np.median(widths))


def _source_widths(ink, skel, body, dist, scale, x0, y0, pick=None, ink_colour=None):
    """`source_width_mm`'s per-profile widths -> (widths mm, profiles tried,
    the ink colour read, widths aligned to the samples asked for — None where
    a sample read nothing) or None.

    `pick` is an explicit (ys, xs) of skeleton pixels to profile (the
    per-strand gate reads each edge's own); `ink_colour` fixes the ink the
    profiles are unmixed against instead of taking it from these profiles."""
    if pick is None:
        ys, xs = np.nonzero(body)
        if len(xs) < 4:
            return None
        k = max(1, len(xs) // _SRC_SAMPLES)
        ys, xs = ys[::k][:_SRC_SAMPLES], xs[::k][:_SRC_SAMPLES]
    else:
        ys, xs = pick
    prof = _profiles(ink, skel, dist, scale, x0, y0, ys, xs)
    if prof is None:
        return None
    t, V, inside, S_l, S_r, which, step_mm, C, _N = prof
    rows = np.arange(len(C))
    score = np.minimum(np.linalg.norm(V - S_l[:, None], axis=2),
                       np.linalg.norm(V - S_r[:, None], axis=2))
    score[~inside] = -1.0
    if ink_colour is None:
        I = np.median(V[rows, np.argmax(score, axis=1)], axis=0)
    else:
        I = ink_colour
    widths = []
    aligned = [None] * len(ys)
    mid = int(np.argmin(np.abs(t)))
    for i in range(len(C)):
        ok = True
        total = 0.0
        for S, idx in ((S_l[i], np.arange(mid, -1, -1)), (S_r[i], np.arange(mid + 1, len(t)))):
            d = I - S
            n2 = float(d @ d)
            if math.sqrt(n2) < _SRC_MIN_CONTRAST:
                ok = False
                break
            idx = idx[inside[i, idx]]
            c = np.clip((V[i, idx] - S) @ d / n2, 0.0, 1.0)
            # Only the ink CONNECTED to the skeleton: walking out from the
            # middle, the integral stops at the first gap of surround, so a
            # neighbouring strand inside the reach is not added to this one.
            gap = np.nonzero(c <= _SRC_GAP)[0]
            total += float(c[:gap[0]].sum() if len(gap) else c.sum())
        if ok:
            widths.append(total * step_mm)
            aligned[which[i]] = total * step_mm
    return widths, len(C), I, aligned


def _profiles(ink, skel, dist, scale, x0, y0, ys, xs):
    """Profiles across the stroke at skeleton pixels (`ys`, `xs`) — the
    geometry `_source_widths` and `_line_contrasts` share -> (t mm, V (n, m,
    4) field samples, `inside` mask, S_l, S_r (each profile's two ends), the
    index into `ys` of each profile, step mm, centres) or None.

    Each normal is the principal axis of the skeleton pixels round the
    sample; each profile reaches the traced half-width plus
    `_SRC_MARGIN_PX` source pixels each side, so both ends sit on the
    surround."""
    sk_y, sk_x = np.nonzero(skel)
    sk = np.column_stack([sk_x, sk_y]).astype(np.float64)
    src_ppm = ink.src_px_per_mm
    step_mm = _SRC_STEP_PX / src_ppm
    centres, normals, reach, which = [], [], [], []
    for j, (y, x) in enumerate(zip(ys, xs)):
        rr = max(4.0, 3.0 * float(dist[y, x]))
        near = sk[(np.abs(sk[:, 0] - x) <= rr) & (np.abs(sk[:, 1] - y) <= rr)]
        if len(near) < 3:
            continue
        c = near - near.mean(axis=0)
        _w, v = np.linalg.eigh(c.T @ c)
        tx, ty = v[:, -1]
        centres.append(((x - _PAD_PX) / scale + x0, (y - _PAD_PX) / scale + y0))
        normals.append((-ty, tx))
        reach.append(float(dist[y, x]) / scale + _SRC_MARGIN_PX / src_ppm)
        which.append(j)
    if not centres:
        return None
    R = max(reach)
    t = np.arange(-R, R + step_mm * 0.5, step_mm)
    C = np.asarray(centres)
    N = np.asarray(normals)
    pts = C[:, None, :] + t[None, :, None] * N[:, None, :]          # (n, m, 2) mm
    src = ink.to_src(pts.reshape(-1, 2)).astype(np.float32)
    F = ink.field()
    V = cv2.remap(F, src[:, 0].reshape(len(C), -1), src[:, 1].reshape(len(C), -1),
                  cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)   # (n, m, 4)
    # Each profile's own reach: points past it are left out, so a profile
    # does not wander onto a neighbouring strand the longest one reaches.
    inside = np.abs(t)[None, :] <= np.asarray(reach)[:, None] + 1e-9
    last = inside.sum(axis=1)
    first = np.argmax(inside, axis=1)
    rows = np.arange(len(C))
    S_l = V[rows, first]
    S_r = V[rows, first + last - 1]
    return t, V, inside, S_l, S_r, which, step_mm, C, N


def _line_contrasts(ink, skel, dist, scale, x0, y0, ys, xs) -> list:
    """How far each profile's CORE stands out of the straight path between
    its two ends, in the source field's units -> list aligned to `ys` (None
    where no profile was taken).

    The photo trial's finding (docs/hairline-photo-trial-2026-10-12.md): on
    a photograph most thin shapes are not strands. They are the blur band
    between two colours (a grey rim between a black feather bar and white
    down, its colour ON the path from one side to the other), or a sliver
    of a smooth gradient the segmenter cut (no edge at all). A strand is a
    LINE: its ink leaves the path between its two sides — darker (or
    lighter, or another hue) than both. So: the largest distance, over the
    profile's core (the traced half-width, at least half a source pixel), of
    a sample from the segment S_l..S_r. A band ON that segment reads near 0
    whatever its two sides are; a strand reads its own contrast.

    A profile with an end still INSIDE the shape's own traced raster (`dist`
    > 0 there: the normal ran along the strand at a curl, or the tracer fused
    two strands) has the ink itself for a side, so it would read ~0 on a real
    strand; it is not read (None). Measured on the drawn hair fixtures,
    where every refusal before this rule was such a profile."""
    prof = _profiles(ink, skel, dist, scale, x0, y0, ys, xs)
    out: list = [None] * len(ys)
    if prof is None:
        return out
    t, V, inside, _S_l, _S_r, which, _step, C, N = prof
    src_ppm = ink.src_px_per_mm
    h, w = dist.shape
    first = np.argmax(inside, axis=1)
    last = inside.shape[1] - 1 - np.argmax(inside[:, ::-1], axis=1)
    for i, j in enumerate(which):
        ends_in = False
        for k in (first[i], last[i]):
            ex, ey = C[i] + t[k] * N[i]
            px = int(round((ex - x0) * scale + _PAD_PX))
            py = int(round((ey - y0) * scale + _PAD_PX))
            if 0 <= px < w and 0 <= py < h and dist[py, px] > 0:
                ends_in = True
        if ends_in:
            continue
        y, x = ys[j], xs[j]
        half = max(float(dist[y, x]) / scale, 0.5 / src_ppm)
        core = inside[i] & (np.abs(t) <= half + 1e-9)
        if not core.any():
            core = inside[i] & (np.abs(t) == np.abs(t).min())
        # Each side's surround is the sample on that half of the profile
        # that differs MOST from the middle, not the profile's far end: a
        # strand lying beside another strand has ink at its far end, and
        # the skin between them is its real surround. A ramp band still
        # reads its two fields (the extremes ARE its sides); a flat sliver
        # still reads nothing.
        mid = V[i, int(np.argmin(np.abs(t)))]
        sides = []
        for half_mask in (inside[i] & (t < 0), inside[i] & (t > 0)):
            Sv = V[i, half_mask] if half_mask.any() else V[i, inside[i]]
            sides.append(Sv[int(np.argmax(np.linalg.norm(Sv - mid, axis=1)))])
        s_l, s_r = sides
        # Exactly one side indistinguishable from the middle: the strand is
        # fused with ink on that side (a touching neighbour), or it is a
        # sliver of one field along its edge. The profile cannot tell which,
        # so it is not read (the width gate decides, as before). Both sides
        # like the middle is a flat field: read as such (0 below).
        near = [float(np.linalg.norm(s - mid)) < _LINE_MIN_CONTRAST for s in sides]
        if near[0] != near[1]:
            continue
        d = s_r - s_l
        n2 = float(d @ d)
        P = V[i, core] - s_l
        u = np.clip(P @ d / n2, 0.0, 1.0) if n2 > 1e-12 else np.zeros(len(P))
        off = P - u[:, None] * d[None, :]
        out[j] = float(np.sqrt((off * off).sum(axis=1)).max())
    return out


def block_thread_wt(regions, cfg) -> dict[int, int]:
    """Per colour block, the finest weight any of its shapes names through
    `shape_overrides[sid].thread_wt` — `stage7_sequence.sequence`'s rule."""
    out: dict[int, int] = {}
    for r in regions:
        ov = r.meta.get("thread_wt")
        if ov is not None:
            out[r.thread_index] = max(out.get(r.thread_index, 0), int(ov))
    return out


def hairline_candidates(regions, cfg, ink: InkSource | None = None) -> "HairlineSet":
    """The shapes the hairline tier will sew -> `HairlineSet` ({shape_id:
    `measure` dict}, plus `.fragments`, the thin shapes rule 2 handed back).

    Computed once per plan (`pipeline.plan_stitches`) and read by stage 5
    (the ground under them, `cfg.hairline_over_ground`) and stage 7 (the
    tier), so the two can never disagree about which shape is a strand.

    1. **The width gate** (`measure`, against the block's thread weight),
       "auto"-tier shapes only — a tier the user set is an instruction.
    2. **The ground-fragment rule.** A colour that sews ANY shape the gate
       rejects (a real area somewhere: the skin's big cells) is a ground
       colour. A thin shape of a ground colour qualifies only when it is
       darker than the colours its edge touches (boundary-length-weighted
       L* of the touching shapes of other threads, by more than `_DARKER_L`)
       — a hair line drawn in the same black as a filled logo still does; a
       sliver of skin pinched between two dark strands does not, because it
       is lighter than what surrounds it: it is a piece of the ground, and it
       fills with the ground. A thin shape touching no other colour lies on
       the garment and qualifies. A colour with no rejected shape (the hair,
       a pen line) is never a ground and every thin shape of it qualifies.
       Known limit: a LIGHT strand of a colour that also fills an area
       elsewhere (blonde highlights over brown hair, when blonde is also a
       patch) is read as ground; nothing here can tell it from a sliver."""
    chart = chart_for(cfg)
    bw = block_thread_wt(regions, cfg)
    out = HairlineSet()
    measured: dict[str, dict] = {}
    for r in regions:
        if str(r.meta.get("tier", "auto")).lower() != "auto":
            continue
        prof = machine.thread_profile(bw.get(r.thread_index, cfg.thread_wt))
        m = measure(r.polygon, prof.hairline_max_width_mm, ink=ink)
        if m is not None and m["admit"]:
            measured[r.shape_id] = m
    if not measured:
        return out
    ground = {r.thread_index for r in regions if r.shape_id not in measured}
    tree = STRtree([r.polygon for r in regions])
    for r in regions:
        m = measured.get(r.shape_id)
        if m is None:
            continue
        if r.thread_index not in ground:
            out[r.shape_id] = m
            continue
        edge = r.polygon.boundary
        tot = wsum = 0.0
        for i in tree.query(r.polygon.buffer(_TOUCH_MM)):
            o = regions[int(i)]
            if o is r or o.thread_index == r.thread_index:
                continue
            shared = edge.intersection(o.polygon.buffer(_TOUCH_MM)).length
            if shared > 0:
                tot += shared
                wsum += shared * float(chart.lab[o.thread_index][0])
        if tot <= 0 or float(chart.lab[r.thread_index][0]) < wsum / tot - _DARKER_L:
            out[r.shape_id] = m
        else:
            out.fragments.add(r.shape_id)
    return out


class HairlineSet(dict):
    """`hairline_candidates`' verdict: {shape_id: measure} for the strands,
    and `fragments`, the thin shapes the ground-fragment rule handed back to
    the ground (stage 5's `_hairline_ground` closes the ground over them)."""

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.fragments: set[str] = set()


def _arc(pts) -> float:
    return sum(math.dist(a, b) for a, b in zip(pts, pts[1:]))


def _heading(pts, at_end: bool, reach_mm: float = _HEADING_MM) -> tuple[float, float] | None:
    """Unit direction of travel at a path's end (`at_end`) or start, read
    `reach_mm` back along it."""
    seq = list(reversed(pts)) if at_end else list(pts)
    tip = seq[0]
    acc = 0.0
    far = seq[-1]
    for a, b in zip(seq, seq[1:]):
        acc += math.dist(a, b)
        if acc >= reach_mm:
            far = b
            break
    dx, dy = (tip[0] - far[0], tip[1] - far[1]) if at_end else (far[0] - tip[0], far[1] - tip[1])
    n = math.hypot(dx, dy)
    return (dx / n, dy / n) if n > 1e-9 else None


def _graph(m: dict, width_mm: float):
    """Skeleton -> list of edges {pts (mm), a, b} with node ids; spurs pruned."""
    scale, x0, y0 = m["scale"], m["x0"], m["y0"]

    def mm(p):
        return ((p[0] - _PAD_PX) / scale + x0, (p[1] - _PAD_PX) / scale + y0)

    raw = _skeleton_edges(m["skel"].astype(np.uint8))
    # Node ids: non-free endpoints that touch (a clique) are one node.
    node_px: list[tuple[int, int]] = []

    def node_of(p) -> int:
        for i, q in enumerate(node_px):
            if max(abs(p[0] - q[0]), abs(p[1] - q[1])) <= 2:
                return i
        node_px.append(p)
        return len(node_px) - 1

    edges = []
    free_id = -1
    for e in raw:
        pts = [mm(p) for p in e["pts"]]
        if len(pts) < 2:
            continue
        if e["closed"]:
            edges.append({"pts": pts, "a": None, "b": None, "closed": True,
                          "free_a": False, "free_b": False, "px": e["pts"]})
            continue
        if e["free_start"]:
            a = free_id
            free_id -= 1
        else:
            a = node_of(e["pts"][0])
        if e["free_end"]:
            b = free_id
            free_id -= 1
        else:
            b = node_of(e["pts"][-1])
        edges.append({"pts": pts, "a": a, "b": b, "closed": False,
                      "free_a": e["free_start"], "free_b": e["free_end"],
                      "px": e["pts"]})

    # Spurs: a free edge hanging off a node, shorter than two stroke widths.
    spur_mm = _SPUR_WIDTHS * width_mm
    degree: dict[int, int] = {}
    for e in edges:
        for k in ("a", "b"):
            if e[k] is not None and e[k] >= 0:
                degree[e[k]] = degree.get(e[k], 0) + 1
    kept = []
    for e in edges:
        one_free = (not e["closed"]) and (e["free_a"] != e["free_b"])
        hub = e["b"] if e["free_a"] else e["a"]
        if one_free and _arc(e["pts"]) < spur_mm and degree.get(hub, 0) >= 3:
            degree[hub] -= 1
            continue
        kept.append(e)

    # Bridges: a short node-to-node edge is the inside of one crossing.
    # Merge its ends into one node and do not sew it (see `_BRIDGE_WIDTHS`).
    parent: dict[int, int] = {}

    def find(n: int) -> int:
        while parent.get(n, n) != n:
            n = parent[n]
        return n

    bridge_mm = _BRIDGE_WIDTHS * width_mm
    out = []
    for e in kept:
        a, b = e["a"], e["b"]
        if (not e["closed"] and a is not None and b is not None and a >= 0 and b >= 0
                and _arc(e["pts"]) < bridge_mm):
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[max(ra, rb)] = min(ra, rb)
            continue
        out.append(e)
    for e in out:
        for k in ("a", "b"):
            if e[k] is not None and e[k] >= 0:
                e[k] = find(e[k])
    return out


def _walk(edges, entry, reach_mm: float = _HEADING_MM):
    """Every edge once, straightest continuation at nodes, nearest-neighbour
    between paths. -> list of point lists (mm)."""
    by_node: dict[int, list[int]] = {}
    for i, e in enumerate(edges):
        for k in ("a", "b"):
            if e[k] is not None:
                by_node.setdefault(e[k], []).append(i)
    left = set(range(len(edges)))
    paths = []
    cur = entry

    # A path that starts where an odd number of unsewn edges meet (a strand's
    # free tip is the commonest case) can end at another such point having
    # swept up everything between — Euler's rule for the fewest paths. An
    # even node is a mid-strand start that leaves a stub behind it.
    rem = {n: len(js) for n, js in by_node.items()}

    def odd(node) -> bool:
        return node is None or rem.get(node, 0) % 2 == 1   # None: a closed loop

    def take(j: int) -> None:
        left.discard(j)
        for k in ("a", "b"):
            n = edges[j][k]
            if n is not None:
                rem[n] -= 1

    while left:
        best = None
        for i in sorted(left):
            e = edges[i]
            for flip in (0, 1):
                start = e["pts"][0] if flip == 0 else e["pts"][-1]
                at = e["a"] if flip == 0 else e["b"]
                d = 0.0 if cur is None else math.dist(cur, start)
                key = (0 if odd(at) else 1, round(d, 6), i, flip)
                if best is None or key < best[0]:
                    best = (key, i, flip)
        _key, i, flip = best
        take(i)
        e = edges[i]
        path = list(e["pts"]) if flip == 0 else list(reversed(e["pts"]))
        node = None if e["closed"] else (e["b"] if flip == 0 else e["a"])
        while node is not None:
            cands = [j for j in by_node.get(node, []) if j in left]
            if not cands:
                break
            h_in = _heading(path, at_end=True, reach_mm=reach_mm)
            pick = None
            for j in cands:
                ej = edges[j]
                fwd = ej["a"] == node
                pts = list(ej["pts"]) if fwd else list(reversed(ej["pts"]))
                h_out = _heading(pts, at_end=False, reach_mm=reach_mm)
                turn = 0.0 if (h_in is None or h_out is None) else \
                    -(h_in[0] * h_out[0] + h_in[1] * h_out[1])
                key = (round(turn, 9), j)
                if pick is None or key < pick[0]:
                    pick = (key, j, pts, ej["b"] if fwd else ej["a"])
            _k, j, pts, nxt = pick
            take(j)
            if math.dist(path[-1], pts[0]) < 1e-9:
                pts = pts[1:]
            path.extend(pts)
            node = nxt
        paths.append(path)
        cur = path[-1]
    return paths


def _cum(pts):
    out = [0.0]
    for a, b in zip(pts, pts[1:]):
        out.append(out[-1] + math.dist(a, b))
    return out


def _at(pts, cum, s):
    """Point at arc length `s` along `pts`."""
    if s <= 0:
        return pts[0]
    if s >= cum[-1]:
        return pts[-1]
    lo, hi = 0, len(cum) - 1
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if cum[mid] <= s:
            lo = mid
        else:
            hi = mid
    seg = cum[hi] - cum[lo]
    f = (s - cum[lo]) / seg if seg > 0 else 0.0
    (ax, ay), (bx, by) = pts[lo], pts[hi]
    return (ax + (bx - ax) * f, ay + (by - ay) * f)


def _deviation(pts, cum, s0, s1, a, b) -> float:
    """Largest distance of the drawn line between arc lengths s0..s1 from the
    chord a-b."""
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    L = math.hypot(dx, dy)
    worst = 0.0
    for k in range(len(pts)):
        if s0 < cum[k] < s1:
            px, py = pts[k]
            if L < 1e-9:
                d = math.hypot(px - ax, py - ay)
            else:
                d = abs(dx * (ay - py) - dy * (ax - px)) / L
            worst = max(worst, d)
    return worst


def stitch_path(pts, stitch_mm: float, tol_mm: float,
                min_mm: float = machine.MIN_STITCH_MM) -> list[tuple[float, float]]:
    """A drawn polyline -> needle positions.

    Marches along the line: each stitch is `stitch_mm` of arc unless its
    chord strays more than `tol_mm` from the line (a curl), in which case it
    shortens in 10% steps — never under `min_mm`, the needle's floor
    (`machine.MIN_STITCH_MM`). Halving would not do: half of 1.5 is under
    1.0, so a halving rule never fires at the default length. The last two
    stitches share what is left, so the path does not end on a stub; and a
    final pass drops any interior point closer than `min_mm` to the one
    before (a chord can be shorter than its arc)."""
    cum = _cum(pts)
    total = cum[-1]
    if total <= 0:
        return []
    out_s = [0.0]
    s = 0.0
    while total - s > 1e-9:
        rest = total - s
        if rest <= stitch_mm:
            out_s.append(total)
            break
        step = stitch_mm
        a = _at(pts, cum, s)
        while step > min_mm:
            b = _at(pts, cum, s + step)
            if _deviation(pts, cum, s, s + step, a, b) <= tol_mm:
                break
            step = max(min_mm, step * 0.9)
        if rest - step < min_mm:
            # Two stitches share what is left rather than leave a stub.
            half = rest / 2.0
            if half >= min_mm:
                out_s.append(s + half)
            out_s.append(total)
            break
        s += step
        out_s.append(s)
    raw = [_at(pts, cum, s) for s in out_s]
    kept = [raw[0]]
    for p in raw[1:-1]:
        if math.dist(kept[-1], p) >= min_mm:
            kept.append(p)
    last = raw[-1]
    while len(kept) > 1 and math.dist(kept[-1], last) < min_mm:
        kept.pop()
    kept.append(last)
    if len(kept) == 2 and math.dist(kept[0], kept[1]) < min_mm:
        return []
    return kept


REST_KEY = "_hairline_rest"


def rest_sew_parts(p, m: dict):
    """-> [(piece, [sewing parts, largest first])]: each connected piece of
    `m["rest"]` (the thick branches) with the connected parts of `p.polygon`
    (underlap and pull compensation included) clipped to it grown by the mean
    outward growth stage 5 gave this shape. A clip across a junction, or
    stage 5's clip of the shape by an earlier colour, can leave a piece's
    sewing polygon in several parts; `rest_planned` decides which to sew and
    `tools/hairline_rest_pieces` counts what it leaves. A piece with no
    sewable part is omitted."""
    rest = m.get("rest")
    if rest is None or rest.is_empty:
        return []
    art = p.region.polygon
    grow = max(0.0, (p.polygon.area - art.area)
               / max(0.5 * (p.polygon.length + art.length), 1e-6))
    out = []
    for piece in sorted(_parts(rest), key=lambda g: (round(g.centroid.x, 6),
                                                      round(g.centroid.y, 6))):
        sew = p.polygon.intersection(piece.buffer(grow + 0.01))
        sew = [g for g in _parts(sew) if g.geom_type == "Polygon" and g.area > 1e-6]
        if not sew:
            continue
        out.append((piece, sorted(sew, key=lambda g: -g.area)))
    return out


def rest_planned(p, m: dict, floor: float | None = None, dropped: list | None = None):
    """The parts of a planned shape the per-strand gate left to the ladder:
    one copy of `p` per connected piece of `m["rest"]` (the thick branches),
    its artwork polygon the piece and its sewing polygon cut to match; []
    when every branch is a hairline or the thick part came to nothing
    sewable. One piece per copy because the ladder takes one Polygon.

    The sewing polygon is `p.polygon` (underlap and pull compensation
    included) clipped to the piece grown by the mean outward growth stage 5
    gave this shape, so the thick branches keep their compensation and the
    hairline ribbons' slot is not sewn twice. Each copy carries `REST_KEY`
    in its region's meta so stage 7 does not offer it to the tier again.

    A piece's sewing polygon can come in several parts (`rest_sew_parts`) --
    stage 5's clip of the shape by an earlier colour can cut a rest piece in
    two while a hairline branch still holds the shape together round the
    outside. The hairline twin of defect 61: this used to sew the largest
    part and drop the rest with their ink, unreported. Now it is stage 5's
    `_split_clip` over the parts: the part carrying the most artwork is the
    piece's main copy (the single part of every piece measured, so those
    copies are what they always were); every other part whose artwork clears
    `clip_piece_floor_mm2` is a copy of its own, its artwork the share of the
    piece inside it (the main copy gives that share up, so a tier that sews
    the ARTWORK does not sew it twice); parts under the floor are dropped and
    each one's artwork appended to `dropped` as `(shape_id, mm2)`, the
    caller's `CLIP_DROPPED_SLIVER` count. A part with no artwork in it is
    underlap beside the piece and drops uncounted. Rides `cfg.hairline`: this
    function only runs under it."""
    import dataclasses
    from shapely.geometry import MultiPolygon
    from .stage5_overlap import _largest_polygon, _split_clip, clip_piece_floor_mm2
    if floor is None:
        from .config import PipelineConfig
        floor = clip_piece_floor_mm2(PipelineConfig())
    out = []
    for piece, sew in rest_sew_parts(p, m):
        if len(sew) == 1:
            main, kept, lost = sew[0], [], []
        else:
            main, kept, lost = _split_clip(MultiPolygon(sew), piece, floor)
        if dropped is not None:
            dropped.extend((p.shape_id, a) for a in lost)
        shares = []
        for g in kept:
            share = _largest_polygon(piece.intersection(g))
            if share is not None:
                shares.append((g, share))
        art = piece
        if shares:
            left = _largest_polygon(piece.difference(unary_union([s for _g, s in shares])))
            art = left if left is not None else piece
        copies = [(main, art)] + [(g, s) for g, s in shares]
        for sew_poly, art_poly in copies:
            region = dataclasses.replace(p.region, polygon=art_poly,
                                         area_mm2=float(art_poly.area),
                                         meta={**p.region.meta, REST_KEY: True})
            vis = None if p.visible is None else p.visible.intersection(sew_poly)
            out.append(dataclasses.replace(p, region=region, polygon=sew_poly, visible=vis))
    return out

def hairline_runs(poly, shape_id: str, *, max_width_mm: float, run_width_mm: float,
                  stitch_mm: float, entry: tuple[float, float] | None,
                  trim_at_mm: float, ink: InkSource | None = None,
                  m: dict | None = None) -> tuple[list[StitchRun], dict]:
    """One shape through the hairline tier -> (runs, report).

    Report keys: the shared tier vocabulary (`empty`, `jumps`, `too_thin` —
    always False) plus `admitted` (the width gate's verdict), `width_mm`
    (median body width), `strands` (paths sewn), `dropped` (paths under
    `RUN_MIN_LOOP_MM`) and `edges` (skeleton edges walked). `empty` with
    `admitted` False means "not a hairline — take the ladder"; `empty` with
    `admitted` True means the whole shape was too short to sew as a run,
    which stage 7 also treats as "take the ladder" so nothing is dropped
    silently.

    `m` is a `measure` result already taken (`hairline_candidates`), so the
    gate is not read twice; `ink` is only used when `m` is not given. The
    skeleton's own thresholds (spurs, bridges, heading reach) read the TRACED
    width, since they are properties of the raster being walked."""
    report = {"empty": True, "jumps": 0, "too_thin": False, "admitted": False,
              "width_mm": None, "strands": 0, "dropped": 0, "edges": 0}
    if m is None:
        m = measure(poly, max_width_mm, ink=ink)
    if m is None:
        return [], report
    report["width_mm"] = round(m["width_mm"], 4)
    if not m["admit"]:
        return [], report
    report["admitted"] = True
    traced = m.get("width_traced_mm", m["width_mm"])
    # Step 3: only the branches the per-strand gate admitted are walked;
    # the thick ones are the caller's (`m["rest"]`, sewn by the ladder).
    edges = m["hair_edges"]
    report["edges"] = len(edges)
    report["thick_edges"] = len(m["thick_edges"])
    if not edges:
        return [], report
    paths = _walk(edges, entry,
                  reach_mm=max(_HEADING_MM, _HEADING_WIDTHS * traced))
    tol = _CURL_TOL_WIDTHS * run_width_mm
    runs: list[StitchRun] = []
    for path in paths:
        if _arc(path) < machine.RUN_MIN_LOOP_MM:
            report["dropped"] += 1
            continue
        pts = stitch_path(path, stitch_mm, tol)
        if len(pts) < 2:
            report["dropped"] += 1
            continue
        jump = trim = False
        if runs:
            d = math.dist(runs[-1].points[-1], pts[0])
            if d >= machine.TINY_STITCH_MM:
                jump = True
                trim = d > trim_at_mm
                report["jumps"] += 1
        runs.append(StitchRun(points=stitches.split_long_moves(pts),
                              kind=stitches.RUN, jump=jump, trim=trim,
                              shape_id=shape_id))
    report["strands"] = len(runs)
    report["empty"] = not runs
    return runs, report
