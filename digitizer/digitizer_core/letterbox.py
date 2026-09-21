"""Strip letterbox/pillarbox bars from an upload before anything reads it.

## The defect this exists for

`testdata/photo/logo_gaulke_roofing.png` is a real customer-shaped input: a
PHONE SCREENSHOT of a logo, 1284x2778, with the logo in a white band and huge
pure-black bars filling the rest of the frame. Those bars are not artwork.
Every ink rule in this codebase reads darkness as ink, so the bars read as
ink, and the consequence is not a slightly worse design — it is a POLARITY
INVERSION. The engine sewed the GROUND in near-white thread and left the logo
as negative space: white thread on white cloth, an unusable file.

Measured 2026-09-11 in the blind eye-vs-ARTFID run
(`docs/artfid-eye-agreement-2026-09-11.md`): that fixture was ranked worst of
fourteen by eye and scored ARTFID 32.2, coverage 0.065 — the only fixture in
the set whose output was unusable rather than merely inaccurate.

## Why the conservative guard is the whole design

The naive detector — "strip uniform rows at the edge" — is WORSE THAN
NOTHING here, and would have been a silent, repo-wide regression. Most
fixtures in this repo are logos on a plain white field with a uniform white
margin. A naive strip eats that margin, cropping the frame down to the ink
bbox, and then `stage1_prep`'s border-flood background detection finds INK
on the border ring instead of ground. That breaks background removal on
almost every flat logo we have, to fix one screenshot.

So a bar is only stripped when it is a bar rather than a margin, and the
discriminator is **colour contrast against the interior**: after computing a
candidate crop, the dominant colour just inside the bar must differ from the
bar's own colour by more than `min_interior_delta`. Black bars around a white
band pass easily. A white margin on a white field fails, because the bar and
the interior are the same colour — which is exactly what "margin" means.

That contrast test is necessary but NOT sufficient, and the guard that
actually saves the repo is the next one:

  * **letterboxing is one-dimensional.** Bars are added on a single axis to
    fit a different aspect ratio — that is what the word means — so a uniform
    border on BOTH axes is a margin and is never stripped. `bg_uncertain.png`
    (a navy block in a white margin) is detected on all four edges with a
    perfectly distinct interior, so contrast alone ACCEPTS it and crops
    800x500 -> 601x341. That fixture scores ARTFID 95.6 and was ranked best
    of fourteen by eye. This rule is why it survives, and it is semantic
    rather than tuned.

Three further guards, each of which alone would have let something through:

  * a bar must end at a HARD EDGE. A ramp's consecutive rows really are
    near-identical (0..255 over 200 rows steps ~1.3 per row), so without this
    a gradient grows a spurious bar off its flat end — measured at 5 rows;
  * a bar must be at least `min_frac` of the dimension, so noise at an edge
    is not a bar;
  * the bars may not consume more than `max_frac`, so a dark design on a
    dark ground is never cropped to nothing.

**Blast radius, pinned by `tests/test_letterbox.py`:** of the 14 tracked
fixtures exactly one — the screenshot — crops. Black letterboxing round-trips
byte-identically on both axes across five fixtures and three bar sizes. White
bars on a white-background logo are deliberately NOT stripped: such a bar is
indistinguishable from a wider margin, and leaving it costs nothing because
the ink bbox (and so the design's physical width) is unchanged.

## What this deliberately does NOT do

It does not touch `art_ink_field` in `tools/artfidelity_self.py`, which
applies its own darkness rule to the ORIGINAL file. That asymmetry is
intentional and is called out in the docs: once the engine stops sewing the
bars, the metric — still counting the bars as ink — sees a bigger subject
mismatch, so the fixture's ARTFID gets WORSE as the embroidery file gets
BETTER. Changing the metric in the same commit would have hidden that, and it
is the cleanest live demonstration of the cross-route comparability problem
that same run found. Fix the metric deliberately, on its own evidence.
"""

from __future__ import annotations

import numpy as np

# A run shorter than this fraction of the dimension is edge noise, not a bar.
MIN_FRAC = 0.02
# Bars may not eat more than this much of a dimension. A dark design on a
# dark ground must never be cropped to nothing.
MAX_FRAC = 0.45
# Max spread within one line, and between a line and the run's first line,
# for the line to count as part of a uniform bar. 0-255 per channel.
LINE_TOL = 6.0
# The bar's colour must differ from the interior's dominant colour by more
# than this (Euclidean RGB, 0-255) or it is a margin, not a bar.
MIN_INTERIOR_DELTA = 40.0
# A chrome strip left on the band's other edges must sit further than this
# (Lab dE76) from the band's ground. Equal to stage 1's own flood tolerance,
# `PipelineConfig.bg_tolerance_lab`, on purpose — see `detect_edge_strips`.
EDGE_STRIP_DELTA_E = 6.0


def _run_length(lines: np.ndarray, tol: float,
                step_min: float = 24.0) -> int:
    """How many leading `lines` form one near-uniform bar ending in a STEP.

    `lines` is (n, m, 3): n lines to walk, each m pixels wide. A line joins
    the run only if it is uniform in itself AND matches the run's first line.

    The run must then end at a hard edge. **A letterbox bar has a hard edge —
    that is what makes it a bar and not the flat end of a ramp.** Without this
    test a smooth vertical gradient gets a short bar detected off its flat
    end: consecutive rows of a ramp really are near-identical (a 0..255 ramp
    over 200 rows steps ~1.3 per row, well inside `tol`), so they satisfy
    every other condition here. Measured: that ramp yielded a spurious 5-row
    bar before this test existed.
    """
    if len(lines) == 0:
        return 0
    first = lines[0].reshape(-1, 3).astype(np.float64)
    if first.std(axis=0).max() > tol:
        return 0
    ref = first.mean(axis=0)
    n = 0
    for line in lines:
        px = line.reshape(-1, 3).astype(np.float64)
        if px.std(axis=0).max() > tol:
            break
        if float(np.abs(px.mean(axis=0) - ref).max()) > tol:
            break
        n += 1
    if n == 0 or n >= len(lines):
        return n
    nxt = lines[n].reshape(-1, 3).astype(np.float64).mean(axis=0)
    return n if float(np.linalg.norm(nxt - ref)) > step_min else 0


def _dominant(px: np.ndarray) -> np.ndarray:
    """Modal colour of `px` (n,3), coarsely binned so near-identical pixels
    vote together. Same construction as `stage1_prep._dominant_border_color`."""
    b = px.astype(np.int32) // 16
    keys = b[:, 0] * 65536 + b[:, 1] * 256 + b[:, 2]
    vals, counts = np.unique(keys, return_counts=True)
    sel = keys == vals[int(np.argmax(counts))]
    return px[sel].astype(np.float64).mean(axis=0)


def detect_letterbox(rgb: np.ndarray,
                     min_frac: float = MIN_FRAC,
                     max_frac: float = MAX_FRAC,
                     line_tol: float = LINE_TOL,
                     min_interior_delta: float = MIN_INTERIOR_DELTA,
                     ) -> tuple[int, int, int, int]:
    """-> (top, bottom, left, right) bar thicknesses in pixels, 0 where none.

    Pure measurement, no cropping: a caller that wants to log or test the
    decision can read it without touching pixels.
    """
    if rgb.ndim != 3 or rgb.shape[2] != 3:
        return 0, 0, 0, 0
    h, w = rgb.shape[:2]
    if h < 8 or w < 8:
        return 0, 0, 0, 0

    top = _run_length(rgb, line_tol)
    bottom = _run_length(rgb[::-1], line_tol)
    left = _run_length(np.swapaxes(rgb, 0, 1), line_tol)
    right = _run_length(np.swapaxes(rgb, 0, 1)[::-1], line_tol)

    # A run that swallowed the whole image means the image is one flat
    # colour; there is no subject to keep, so there is nothing to strip.
    if top >= h or left >= w:
        return 0, 0, 0, 0

    def keep(n: int, span: int) -> int:
        return n if (n >= max(1, int(round(min_frac * span)))
                     and n <= int(max_frac * span)) else 0

    top, bottom = keep(top, h), keep(bottom, h)
    left, right = keep(left, w), keep(right, w)
    if not (top or bottom or left or right):
        return 0, 0, 0, 0

    # Letterboxing is ONE-DIMENSIONAL. Bars are added on a single axis to fit
    # content into a different aspect ratio - that is what the word means.
    # A uniform border on BOTH axes is a margin or a frame, and cropping it
    # removes the design's background rather than padding.
    #
    # This is not a tuned threshold, and it is load-bearing: `bg_uncertain.png`
    # (a navy block inside a white margin) is detected on all four edges with
    # a perfectly distinct interior, so the contrast guard alone ACCEPTS it and
    # crops 800x500 -> 601x341. That fixture scores ARTFID 95.6 and was ranked
    # best of fourteen by eye; cropping it would have been a straight
    # regression introduced to fix one screenshot. Measured 2026-09-11.
    if (top or bottom) and (left or right):
        return 0, 0, 0, 0

    # Guard: the interior must actually look different from the bars. This is
    # what separates a letterbox bar from an ordinary margin, and dropping it
    # would crop every white-margined logo down to its ink bbox.
    inner = rgb[top:h - bottom, left:w - right]
    if inner.size == 0 or min(inner.shape[:2]) < 4:
        return 0, 0, 0, 0
    ring = np.concatenate([
        inner[:2].reshape(-1, 3), inner[-2:].reshape(-1, 3),
        inner[:, :2].reshape(-1, 3), inner[:, -2:].reshape(-1, 3)])
    interior = _dominant(ring)

    def distinct(n: int, bar_px: np.ndarray) -> int:
        if n == 0:
            return 0
        bar = bar_px.reshape(-1, 3).astype(np.float64).mean(axis=0)
        return n if float(np.linalg.norm(bar - interior)) > min_interior_delta else 0

    top = distinct(top, rgb[:top]) if top else 0
    bottom = distinct(bottom, rgb[h - bottom:]) if bottom else 0
    left = distinct(left, rgb[:, :left]) if left else 0
    right = distinct(right, rgb[:, w - right:]) if right else 0
    return top, bottom, left, right


def detect_edge_strips(band: np.ndarray, axis: int,
                       max_frac: float = MIN_FRAC,
                       line_tol: float = LINE_TOL,
                       delta_e: float = EDGE_STRIP_DELTA_E,
                       ) -> tuple[int, int]:
    """-> thicknesses of the thin chrome strips on the two edges of `band`
    that lie ACROSS `axis` (axis=1: left, right; axis=0: top, bottom).

    ## Why the bars alone were not enough

    Cropping `logo_gaulke_roofing.png`'s bars leaves a white band whose left
    and right edges are each a 9-px shadow strip — the phone app's card edge,
    RGB 234 fading to 219, Lab dE76 8.1-14.4 from the white band. The bars are
    gone, but stage 1's border ring is 2 px on every side, so those strips
    are 30% of it: agreement read 0.693 against `bg_border_agreement_min`
    0.75, stage 1 reported BACKGROUND_ABSENT, and the white card sewed as the
    design's largest shape — 79.9% of the stitching, `GROUND_SEWN` at block —
    with a grey satin column down each side. Measured 2026-09-15.

    ## Why this cannot reach an ordinary upload

    It is only asked after `detect_letterbox` found bars, i.e. on a
    screenshot, and it trims a strip only when every guard holds:

      * each line is UNIFORM along its length (`line_tol`) — artwork touching
        the edge is not a uniform line;
      * each line's mean colour is further than `delta_e` from the band's own
        ground, read off the band's edges on the bar axis (the edges the bars
        were cut from, which ARE the ground stage 1 will flood);
      * the strip ends at a line INSIDE `delta_e` of that ground — a step
        into the ground, not a wide frame or border running inward;
      * it is no wider than `max_frac` of the dimension (`MIN_FRAC`, the
        size below which `detect_letterbox` calls a run edge noise) — a thin
        strip, never a margin;
      * both edges carry one, at least 2 px each and within 1 px of each
        other — chrome round a centred card is mirrored (see the end).

    `delta_e` defaults to stage 1's own flood tolerance
    (`PipelineConfig.bg_tolerance_lab` = 6.0), so a trimmed line is exactly a
    line stage 1 would have refused to call ground: no new threshold.
    """
    from .threads import rgb_to_lab  # local: keep this module import-light

    h, w = band.shape[:2]
    if min(h, w) < 8:
        return 0, 0
    # Ground reference: the band's two edges ALONG the bar axis.
    if axis == 1:
        ground_px = np.concatenate([band[:2].reshape(-1, 3), band[-2:].reshape(-1, 3)])
        lines, span = np.swapaxes(band, 0, 1), w
    else:
        ground_px = np.concatenate([band[:, :2].reshape(-1, 3), band[:, -2:].reshape(-1, 3)])
        lines, span = band, h
    ground = rgb_to_lab(_dominant(ground_px).round().astype(np.uint8).reshape(1, 3))[0]
    limit = max(1, int(max_frac * span))

    def far(line: np.ndarray) -> bool | None:
        px = line.reshape(-1, 3).astype(np.float64)
        mean = rgb_to_lab(px.mean(axis=0).round().astype(np.uint8).reshape(1, 3))[0]
        d = float(np.linalg.norm(mean - ground))
        if d <= delta_e:
            return False          # ground: the strip (if any) ends here
        if px.std(axis=0).max() > line_tol:
            return None           # not uniform: artwork or noise, refuse
        return True

    def run(seq: np.ndarray) -> int:
        n = 0
        for line in seq[:limit + 1]:
            verdict = far(line)
            if verdict is False:
                return n
            if verdict is None:
                return 0
            n += 1
        return 0                  # ran past `limit` without reaching ground

    a, b = run(lines), run(lines[::-1])
    # MIRRORED, or nothing. A screenshot's band is a card centred on the
    # screen, so its chrome is the same on both edges (gaulke: 9 and 9). A
    # one-sided line is something else, and `becker_marine_logo.png` is the
    # case that proved it: a 1-px uniform white column at its left edge only
    # (exporter residue under transparency) passed every guard above, and
    # trimming it broke the exact round trip `test_letterbox.py` pins.
    if min(a, b) < 2 or abs(a - b) > 1:
        return 0, 0
    return a, b


def strip_letterbox(rgb: np.ndarray, alpha: np.ndarray | None = None,
                    ) -> tuple[np.ndarray, np.ndarray | None]:
    """Crop detected letterbox bars off `rgb`, and off `alpha` identically.

    Returns the inputs unchanged when no bar is found, which is the common
    case and must stay free: every fixture in this repo that is NOT a
    screenshot should come back byte-identical.
    """
    t, b, l, r = detect_letterbox(rgb)
    if not (t or b or l or r):
        return rgb, alpha
    h, w = rgb.shape[:2]
    # The band the bars leave behind can still carry the host app's CHROME on
    # its other two edges — see `detect_edge_strips`. Only ever asked once
    # bars were found, so a file that is not a screenshot never reaches it.
    band = rgb[t:h - b, l:w - r]
    if t or b:
        sl, sr = detect_edge_strips(band, axis=1)
        l, r = l + sl, r + sr
    else:
        st, sb = detect_edge_strips(band, axis=0)
        t, b = t + st, b + sb
    # `ascontiguousarray`, not a bare slice. A top/bottom-only crop stays
    # contiguous, but a PILLARbox crop (left/right bars) does not, and several
    # cv2 entry points downstream reject a non-contiguous buffer. The
    # screenshot that motivated this module happens to be the safe direction,
    # so a bare slice would have passed every test here and failed later on
    # the first side-barred upload a customer sent.
    out = np.ascontiguousarray(rgb[t:h - b, l:w - r])
    out_a = (np.ascontiguousarray(alpha[t:h - b, l:w - r])
             if alpha is not None else None)
    return out, out_a
