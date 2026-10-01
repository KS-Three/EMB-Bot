"""Recover customer ARTWORK from a vendor's two-panel preview image.

Every digitizing vendor in `scratch_kent/` ships a preview alongside the
stitch file. Most of them put the artwork the customer sent in one panel and
a simulation of their own stitches in the other, so the artwork EMB-Bot needs
as a pipeline input is sitting there already — it just has to be cut out.

WHY THIS IS NOT AUTOMATIC, and must not become automatic without evidence:
the obvious move is to detect which panel is artwork by some image statistic.
Two were measured on five real files (2026-09-28) and BOTH fail:

    file                colour-count ratio   flatness ratio
    HOTEL FREMONT .BMP        1.18  fail          2.05  ok
    mf4b logo hat.JPG         3.12  ok            2.75  ok
    Machine beanie E.JPG        --                1.84  ok
    c golke logo hat.JPG        --                1.01  FAIL (ambiguous)
    beckers logo hat.JPG        --                1.51  FALSE POSITIVE

Colour count dies on `HOTEL FREMONT .BMP` because that file is already
palettised to 221 colours, so its simulation panel has no shading gradient
left to count. Flatness dies on `c golke logo hat.JPG` (1.01, indistinguish-
able) and — far worse — scores the Becker preview at 1.51, ABOVE a true
positive at 1.84. There is no threshold that accepts the real ones and
refuses Becker.

Getting that wrong is not a cosmetic error. Becker's preview is two stitch
simulations with no artwork at all, and feeding a simulation to the pipeline
as if it were artwork is the provenance bug `blockcensus.py`'s docstring
exists to guard: an input derived from the pro's own answer flattered the
recon lane by +11.3 points. A heuristic would commit that error SILENTLY.

So the panel choice is DATA, not inference. `MANIFEST` below records it, one
entry per design, set by a human who looked at the image. Anything not in the
MANIFEST is refused rather than guessed at. Adding a design later costs one
look; that cost is the feature.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
SCRATCH = ROOT / "scratch_kent" / "Embroidery Files"
OUT_DIR = ROOT / "digitizer" / "testdata" / "art"

# source (relative to SCRATCH) -> (which panel holds the ARTWORK, output stem,
# the prep_all.DESIGNS slug of the professional file it pairs with).
#
# "first" means top for a horizontal split and left for a vertical one;
# "second" is bottom / right. The order is NOT consistent between vendors —
# To a T Machine puts the artwork on the RIGHT while every other vendor here
# puts it on top — which is the other reason this is a table and not a rule.
#
# Deliberately absent:
#   Becker (every variant)  both panels are stitch simulations; there is no
#                           artwork in them to recover. See the module
#                           docstring and blockcensus.py's INPUT PROVENANCE.
#   gaulke_roofing_lc       no preview of its own; only the hat JPG exists.
#                           Pairing one artwork to two pro files would double-
#                           count it in aggregates, the same trap blockcensus
#                           already checks for on the drone badge.
#   multi c golke ...JPG    its .DST is not registered in prep_all.DESIGNS,
#                           so there is no pro counterpart to pair with.
MANIFEST: dict[str, tuple[str, str, str]] = {
    "MFAB/Mfab Hat & Polo/mf4b logo hat.JPG": ("first", "logo_mfab_hat", "mfab_hat"),
    "MFAB/Mfab Hat & Polo/mf4b logo lc.JPG": ("first", "logo_mfab_lc", "mfab_lc"),
    "Gaulke Roofing/c golke logo hat.JPG": ("first", "logo_golke_roofing", "gaulke_roofing_hat"),
    "To a T Machine/Machine beanie E.JPG": ("second", "logo_toat_machine", "machine_beanie"),
    "To a T-Becker Beanies/Machine beanie.JPG": ("second", "logo_toat_beanie", "toat_beanie"),
    "Hotel Fremont/Hotel Patch/HOTEL FREMONT .BMP": ("first", "logo_hotel_fremont_patch", "hotel_fremont_patch"),
}

# A row/column counts as empty when this share or less of it is ink. Not zero:
# JPEG ringing puts a few stray pixels in the gutter of every one of these.
EMPTY_FRAC = 0.005
# Ink is a pixel this far (summed over RGB) from the border-median background.
INK_DELTA = 60
# The gutter must sit inside the middle of the image; a run touching either
# end is just the margin around the art, not the separator between panels.
EDGE_MARGIN = 0.15


class NoSplit(Exception):
    """The image has no gutter separating two panels."""


class NotInManifest(Exception):
    """Refusing to guess which panel is artwork."""


def _background(a: np.ndarray) -> np.ndarray:
    edges = np.concatenate([a[0, :], a[-1, :], a[:, 0], a[:, -1]])
    return np.median(edges, axis=0)


def _longest_inner_gap(empty: np.ndarray) -> tuple[int, int] | None:
    runs: list[tuple[int, int]] = []
    start = None
    for i, e in enumerate(empty):
        if e and start is None:
            start = i
        if not e and start is not None:
            runs.append((start, i))
            start = None
    if start is not None:
        runs.append((start, len(empty)))
    n = len(empty)
    inner = [r for r in runs if r[0] > EDGE_MARGIN * n and r[1] < (1 - EDGE_MARGIN) * n]
    return max(inner, key=lambda r: r[1] - r[0]) if inner else None


def find_gutter(a: np.ndarray) -> tuple[str, int, int]:
    """-> (axis, start, end). axis is "H" (panels stacked) or "V" (side by side).

    Picks whichever orientation yields the wider gutter, because a two-panel
    image has a real gap in exactly one direction and at most a thin margin
    in the other.
    """
    ink = np.abs(a - _background(a)).sum(2) > INK_DELTA
    best: tuple[str, int, int] | None = None
    for axis, name in ((1, "H"), (0, "V")):
        gap = _longest_inner_gap(ink.sum(axis=axis) <= max(1, EMPTY_FRAC * ink.shape[axis]))
        if gap and (best is None or (gap[1] - gap[0]) > (best[2] - best[1])):
            best = (name, gap[0], gap[1])
    if best is None:
        raise NoSplit("no inner gutter found; this may not be a two-panel preview")
    return best


def panels(a: np.ndarray) -> tuple[np.ndarray, np.ndarray, str]:
    axis, s, e = find_gutter(a)
    if axis == "H":
        return a[:s], a[e:], axis
    return a[:, :s], a[:, e:], axis


def extract(rel: str) -> np.ndarray:
    """The artwork panel of `rel`, per MANIFEST. Refuses anything unlisted."""
    if rel not in MANIFEST:
        raise NotInManifest(
            f"{rel} is not in MANIFEST. Look at the image and add an entry; "
            "do not guess which panel is artwork (see module docstring)."
        )
    which, _stem, _slug = MANIFEST[rel]
    src = SCRATCH / rel
    a = np.asarray(Image.open(src).convert("RGB")).astype(int)
    first, second, _axis = panels(a)
    return first if which == "first" else second


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    missing, written = [], []
    for rel, (_which, stem, slug) in MANIFEST.items():
        if not (SCRATCH / rel).exists():
            missing.append(rel)
            continue
        art = extract(rel)
        out = OUT_DIR / f"{stem}.png"
        Image.fromarray(art.astype(np.uint8)).save(out)
        written.append(f"{out.relative_to(ROOT)}  {art.shape[1]}x{art.shape[0]}  -> {slug}")
    for line in written:
        print("[wrote]", line)
    for rel in missing:
        print("[skip ] source absent:", rel)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
