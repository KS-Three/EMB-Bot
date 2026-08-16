"""Real-art lane for the pro-parity harness.

`prep_all.py` reconstructs each design's artwork FROM THE PRO'S OWN STITCHES,
which is the load-bearing caveat on every parity number it has ever produced:
the artwork already carries the pro's segmentation and stitch-treatment
decisions, so the engine is graded on art that was derived from the answer.
`pro-parity-program-2026-08-14.md` §2 estimated the flattery at +10-18 points
by extrapolating from `hotel_fremont_patch`, the one design that had any real
source image at all.

Kent supplied the actual customer artwork on 2026-08-15. This module prepares
it, and `prep_both.py` runs BOTH lanes over the same designs so the flattery is
MEASURED per design instead of extrapolated from one.

What this deliberately does NOT do:

  * It does not remove backgrounds, flatten alpha, posterise, sharpen, or
    upscale. `stage1_prep` has its own background flood and its own
    low-resolution warning; pre-cleaning the art here would measure this file's
    taste instead of the engine's. Whatever the customer sent is the input.

  * It does not rescale to the pro's size. `stage1_prep` derives px_per_mm from
    the art's OWN foreground bbox against `cfg.target_width_mm` (stage1_prep.py:
    317-319), so margins never affect scale and cropping them is not needed for
    registration.

The one transform applied is a UNIFORM-BAR CROP, and only because it changes
what the art IS rather than how it is graded: `Gaulke Roofing Logo.png` is a
1284x2778 phone screenshot with the logo in a band between two solid black
bars. Those bars are opaque non-background pixels, so stage 1's foreground
bbox would span the whole frame and the engine would be asked to digitize the
bars. Trimming leading/trailing rows and columns that are BOTH near-uniform and
near-black-or-near-white removes them, and is a no-op on art that has none.
"""
import numpy as np
from PIL import Image

# A row/column counts as a bar if it is this flat...
BAR_STD_MAX = 6.0
# ...and its mean channel value sits within this much of pure black or white.
BAR_EXTREME_TOL = 24.0
# Refuse to trim past this fraction of either dimension — a guard against
# eating real artwork on a design that is legitimately mostly white.
BAR_TRIM_MAX_FRAC = 0.45


def _bar_rows(gray, alpha):
    """-> bool per row: near-uniform and near-black/near-white (or fully clear)."""
    clear = alpha.max(axis=1) == 0
    flat = gray.std(axis=1) <= BAR_STD_MAX
    mu = gray.mean(axis=1)
    extreme = (mu <= BAR_EXTREME_TOL) | (mu >= 255.0 - BAR_EXTREME_TOL)
    return clear | (flat & extreme)


def _trim_span(is_bar):
    """-> (lo, hi) slice bounds after eating bars off both ends, guarded."""
    n = len(is_bar)
    limit = int(n * BAR_TRIM_MAX_FRAC)
    lo = 0
    while lo < limit and is_bar[lo]:
        lo += 1
    hi = n
    while hi > n - limit and is_bar[hi - 1]:
        hi -= 1
    return (lo, hi) if hi - lo >= 8 else (0, n)


def prepare(src, dest):
    """Copy the customer's artwork to `dest` as RGBA, uniform bars trimmed.

    Returns a dict recording what was done, for the manifest — including the
    effective DPI against `design_mm` when the caller supplies it, because a
    low number there is a fact about the ART and has to be reported next to any
    score it depresses.
    """
    im = Image.open(src)
    src_mode = im.mode
    im = im.convert("RGBA")
    a = np.asarray(im)
    gray = a[..., :3].astype(np.float32).mean(axis=2)
    alpha = a[..., 3]

    r0, r1 = _trim_span(_bar_rows(gray, alpha))
    c0, c1 = _trim_span(_bar_rows(gray.T, alpha.T))
    cropped = (r0, r1, c0, c1) != (0, a.shape[0], 0, a.shape[1])
    a = a[r0:r1, c0:c1]

    Image.fromarray(a, "RGBA").save(dest)

    # Ink bbox on the trimmed art, by the same test stage 1 will apply first:
    # transparent is background where alpha exists, else near-white is.
    if alpha[r0:r1, c0:c1].min() < 255:
        ink = a[..., 3] > 16
    else:
        ink = a[..., :3].astype(np.int32).sum(axis=2) < 720
    ys, xs = np.nonzero(ink)
    ink_w = int(xs.max() - xs.min() + 1) if len(xs) else 0
    ink_h = int(ys.max() - ys.min() + 1) if len(ys) else 0

    return {
        "art_source": str(src),
        "src_mode": src_mode,
        "src_size_px": list(Image.open(src).size),
        "cropped": cropped,
        "crop_box": [c0, r0, c1, r1] if cropped else None,
        "size_px": [a.shape[1], a.shape[0]],
        "ink_bbox_px": [ink_w, ink_h],
        "has_alpha": bool(alpha.min() < 255),
    }


def dpi(ink_w_px, design_mm):
    """Effective art resolution: ink pixels across the width the pro sewed."""
    if not design_mm:
        return 0.0
    return round(ink_w_px / (design_mm / 25.4), 1)
