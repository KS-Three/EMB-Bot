"""WHERE does a stage-0 signal come from — which pixels, and how stably?

`stage0_classify` prints two numbers and a confidence. This prints what those
numbers are made of: the share of `unique_color_mass` contributed by the
background interior, the ink interior and the anti-aliased edge band; the
k-means centres it spent on each; how far apart those centres actually are in
CIEDE2000; the spread of the verdict across k-means seeds; and one-variable
ablations that say which property of the raster is doing the work.

**It measures and changes nothing.** No threshold is read from it and none is
moved by it — ROADMAP gate 2 refuses stage-0 recalibration without real tonal
artwork, and this tool exists to explain a verdict, not to re-site one.

Written 2026-09-11 for `docs/stage0-tires-photo-scene-2026-09-11.md`, and
committed rather than left in a scratch directory on purpose: the 2026-08-15
classification census (`docs/classifier-misroutes-real-logos-2026-08-15.md`
§2) was a throwaway probe, and its `tires_hat_3d` row — `unique_color_mass`
0.048, `gradient_smoothness` 0.205 — cannot be reproduced today at any export
width from the same bytes. `gradient_smoothness` has no RNG in it, so that
probe fed a raster nobody can now identify. A committed tool cannot lose its
own definition that way.

    cd digitizer && .venv/Scripts/python tools/stage0_signal_origin.py \
        testdata/logo_script_tires.png
    # --seeds N      how many k-means seeds to sweep (default 8)
    # --ablations    the one-variable arms (slow: N classifies per arm)
    # --sweep        the export-resolution sweep, PIL LANCZOS as the
    #                scale-invariance test resamples

On Linux the interpreter is `.venv/bin/python` (CLAUDE.md).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from digitizer_core import stage0_classify as s0            # noqa: E402
from digitizer_core.config import PipelineConfig            # noqa: E402
from digitizer_core.threads import rgb_to_lab               # noqa: E402

# Pixels within this many px of the ink boundary are the "edge band" — the
# anti-aliased ramp plus any sharpening halo. Wide enough to hold both at the
# resolutions real logo art arrives at; the zone shares are printed so a
# reader can see what it caught.
BAND_PX = 3


def zones(rgb: np.ndarray, band_px: int = BAND_PX,
          fg: np.ndarray | None = None) -> dict[str, np.ndarray]:
    """Split an image into background interior / ink interior / edge band.

    Otsu on grey, then a distance transform either side of that boundary. This
    is a READING aid, not a segmentation the engine uses — stage 1 owns that.

    `fg` is stage 0's own foreground (`_fg_mask`): pass it for artwork with an
    alpha channel, where the transparent region is not background-coloured ink
    but pixels the statistic never sees. Every zone is intersected with it, so
    the shares printed are shares of what was actually measured.
    """
    grey = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    _, inkm = cv2.threshold(grey, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    ink = inkm > 0
    d_in = cv2.distanceTransform(ink.astype(np.uint8), cv2.DIST_L2, 3)
    d_out = cv2.distanceTransform((~ink).astype(np.uint8), cv2.DIST_L2, 3)
    band = (ink & (d_in <= band_px)) | (~ink & (d_out <= band_px))
    out = {"bg_interior": ~ink & ~band, "ink_interior": ink & ~band, "edge_band": band}
    if fg is not None:
        out = {k: v & fg for k, v in out.items()}
    return out


def ucm_parts(rgb: np.ndarray, fg: np.ndarray, seed: int):
    """`_unique_color_mass`, opened up: -> (ucm, disagree mask, labels, centres).

    Deliberately re-uses `stage0_classify`'s own `_kmeans_lab` / `_assign` and
    its own constants, so this cannot drift into measuring a different
    statistic than the one that ships.
    """
    h, w = rgb.shape[:2]
    idx = np.nonzero(fg.reshape(-1))[0]
    px = rgb.reshape(-1, 3)[idx]
    lab = rgb_to_lab(px.astype(np.float64))
    k = max(1, min(s0.UCM_K, len(np.unique(px, axis=0))))
    centres = s0._kmeans_lab(lab, k, seed)
    labels = np.full(h * w, -1, np.int32)
    labels[idx] = s0._assign(lab, centres)
    labels = labels.reshape(h, w)
    win = (s0.UCM_NEIGHBORHOOD, s0.UCM_NEIGHBORHOOD)
    counts = np.empty((k, h, w), np.float32)
    for j in range(k):
        counts[j] = cv2.boxFilter((labels == j).astype(np.float32), -1, win, normalize=False)
    diff = (np.argmax(counts, axis=0) != labels) & fg
    return float(diff.sum()) / float(fg.sum()), diff, labels, centres


def _bgr(img: np.ndarray, alpha: np.ndarray | None = None) -> np.ndarray:
    """RGB -> the ndarray `classify` expects to be handed, alpha included.

    **Carrying alpha is not optional.** `_fg_mask` treats alpha<=127 as
    background, so handing back three channels silently re-declares every
    transparent pixel as foreground and the arms then measure a different
    image than the shipped classifier reads. Measured on
    `photo/enthusiast_logo.png`: `flat` (GS 0.0000) through the file, and
    `gradient` (GS 0.0434) through the same pixels with alpha dropped. Four of
    the repo's real-artwork fixtures carry alpha.
    """
    out = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    if alpha is None:
        return out
    return np.dstack([out, alpha])


def seed_spread(img_bgr: np.ndarray, seeds: int) -> tuple[list[float], dict[str, int]]:
    """The verdict across k-means seeds. `classify`'s own confidence is the
    distance of ONE draw from the threshold, so it cannot see this."""
    ucms, classes = [], []
    for sd in range(seeds):
        cfg = PipelineConfig()
        cfg.seed = sd
        r = s0.classify(img_bgr, cfg)
        ucms.append(r.signals["unique_color_mass"])
        classes.append(r.class_)
    return ucms, {c: classes.count(c) for c in sorted(set(classes))}


def _median_of(img: np.ndarray, mask: np.ndarray) -> np.ndarray:
    return np.median(img[mask].reshape(-1, 3), axis=0).astype(np.uint8)


def ablations(rgb: np.ndarray, z: dict[str, np.ndarray]) -> list[tuple[str, np.ndarray]]:
    """One-variable arms: each changes exactly one property of the raster."""
    grey = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    _, binm = cv2.threshold(grey, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    hard = cv2.cvtColor(binm, cv2.COLOR_GRAY2RGB)

    flat_bg = rgb.copy()
    flat_bg[z["bg_interior"]] = _median_of(rgb, z["bg_interior"])
    flat_ink = rgb.copy()
    flat_ink[z["ink_interior"]] = _median_of(rgb, z["ink_interior"])
    both = flat_bg.copy()
    both[z["ink_interior"]] = _median_of(rgb, z["ink_interior"])
    hard_edge = rgb.copy()
    hard_edge[z["edge_band"]] = hard[z["edge_band"]]
    # A clean anti-aliased edge with interiors that are EXACTLY one value, so
    # the AA half can be read without the interior noise underneath it.
    aa_only = cv2.cvtColor(cv2.GaussianBlur(binm, (0, 0), 0.8), cv2.COLOR_GRAY2RGB)
    return [
        ("original", rgb),
        ("background interior -> its median", flat_bg),
        ("ink interior -> its median", flat_ink),
        ("both interiors flat, AA band kept", both),
        ("AA band hardened, grain kept", hard_edge),
        ("binarized (no AA, no grain)", hard),
        ("clean AA only (flat interiors, sigma 0.8)", aa_only),
    ]


def report(path: Path, seeds: int, do_ablations: bool, do_sweep: bool) -> int:
    rgb, alpha = s0._load(str(path))
    fg = s0._fg_mask(rgb, alpha)
    cfg = PipelineConfig()
    base = s0.classify(str(path), cfg)
    h, w = rgb.shape[:2]
    print(f"{path}  {w}x{h}  unique RGB {len(np.unique(rgb.reshape(-1, 3), axis=0))}")
    print(f"  class={base.class_} confidence={base.confidence:.3f} "
          f"UCM={base.signals['unique_color_mass']:.4f} (gate {s0.UCM_PHOTO_MIN}) "
          f"GS={base.signals['gradient_smoothness']:.5f} "
          f"(flat/gradient gate {s0.GRAD_VAR_GRADIENT_MIN}, "
          f"scene/subject gate {s0.GRAD_VAR_SUBJECT_MIN})")

    z = zones(rgb, fg=fg)
    ucm, diff, labels, centres = ucm_parts(rgb, fg, cfg.seed)
    total = max(1.0, float(diff.sum()))
    print(f"\n  unique_color_mass = {ucm:.4f}, by zone:")
    for name, m in z.items():
        if not m.any():
            # Legitimately empty — e.g. `becker_marine_logo.png`, whose whole
            # ground is transparent, so alpha leaves no background pixel to
            # measure. Say so rather than printing nan.
            print(f"    {name:13s}   0.0% of image  (empty — nothing measured here)")
            continue
        grey = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)[m]
        print(f"    {name:13s} {m.mean():6.1%} of image  disagree {diff[m].mean():6.1%}  "
              f"share of disagreement {diff[m].sum() / total:6.1%}  "
              f"grey {grey.mean():6.2f} +/- {grey.std():.2f}")

    print(f"\n  the {len(centres)} k-means centres it spent (Lab, by L), "
          f"and where they landed:")
    for j in np.argsort(centres[:, 0]):
        m = labels == j
        n = int(m.sum())
        if not n:
            continue
        where = " ".join(f"{k[:3]}={(m & v).sum() / n:.2f}" for k, v in z.items())
        print(f"    L={centres[j][0]:6.2f} a={centres[j][1]:6.2f} b={centres[j][2]:6.2f}  "
              f"{n / labels.size:6.2%} of image  {where}")
    _print_centre_distances(centres, labels, z["bg_interior"])

    ucms, tally = seed_spread(_bgr(rgb, alpha), seeds)
    print(f"\n  across {seeds} k-means seeds: UCM {min(ucms):.3f}..{max(ucms):.3f} "
          f"(gate {s0.UCM_PHOTO_MIN}), classes {tally}")
    if max(ucms) - min(ucms) > s0.UCM_MARGIN:
        print(f"    the spread exceeds UCM_MARGIN ({s0.UCM_MARGIN}) — the printed "
              f"confidence is one draw, not a stability claim")

    if do_ablations:
        print("\n  one-variable ablations (class per seed):")
        for name, arm in ablations(rgb, z):
            a_ucms, a_tally = seed_spread(_bgr(arm, alpha), seeds)
            gs = s0.classify(_bgr(arm, alpha), cfg).signals["gradient_smoothness"]
            print(f"    {name:42s} UCM {min(a_ucms):.3f}..{max(a_ucms):.3f}  "
                  f"GS {gs:.5f}  {a_tally}")

    if do_sweep:
        _print_sweep(path, seeds)
    return 0


def _print_centre_distances(centres, labels, bg_interior) -> None:
    """How far apart, perceptually, are the centres that share the ground?

    A quantize that splits one flat area into several centres is only
    measuring texture if those centres are different COLOURS. CIEDE2000 says
    whether they are; `preflight.DELTA_E_VISIBLE` is the repo's own constant
    for "most people call these two different colours".
    """
    from skimage.color import deltaE_ciede2000

    from digitizer_core.preflight import DELTA_E_VISIBLE
    owned = [j for j in range(len(centres))
             if (labels == j).sum() and (bg_interior & (labels == j)).sum()
             / max(1, (labels == j).sum()) > 0.5]
    if len(owned) < 2:
        return
    pairs = [float(deltaE_ciede2000(centres[i:i + 1], centres[j:j + 1])[0])
             for ai, i in enumerate(owned) for j in owned[ai + 1:]]
    print(f"    {len(owned)} of these centres sit inside the background: "
          f"pairwise dE00 {min(pairs):.2f}..{max(pairs):.2f}, against "
          f"DELTA_E_VISIBLE = {DELTA_E_VISIBLE}")


def _print_sweep(path: Path, seeds: int) -> None:
    """Export-resolution sweep, resampled as tests/test_classifier_scale_
    invariance.py does (PIL LANCZOS), so the two agree on method."""
    from PIL import Image

    src = Image.open(path)
    # RGBA when the file has alpha, for the reason `_bgr` documents: resampling
    # to RGB would hand every arm a foreground the classifier never uses.
    im = src.convert("RGBA" if src.mode in ("RGBA", "LA", "P") else "RGB")
    print("\n  export-resolution sweep (PIL LANCZOS):")
    for w in (146, 250, 400, 640, 900, im.width, 2000):
        h = max(1, round(im.height / im.width * w))
        arr = np.array(im if w == im.width else im.resize((w, h), Image.LANCZOS))
        rgb, a = (arr[:, :, :3], arr[:, :, 3]) if arr.shape[2] == 4 else (arr, None)
        ucms, tally = seed_spread(_bgr(rgb, a), seeds)
        cfg = PipelineConfig()
        gs = s0.classify(_bgr(rgb, a), cfg).signals["gradient_smoothness"]
        tag = "native" if w == im.width else ("up" if w > im.width else "down")
        print(f"    {w:5d}px ({tag:6s}) UCM {min(ucms):.3f}..{max(ucms):.3f}  "
              f"GS {gs:.4f}  {tally}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("image", type=Path)
    ap.add_argument("--seeds", type=int, default=8)
    ap.add_argument("--ablations", action="store_true")
    ap.add_argument("--sweep", action="store_true")
    a = ap.parse_args(argv)
    if not a.image.exists():
        ap.error(f"{a.image} does not exist")
    return report(a.image, a.seeds, a.ablations, a.sweep)


if __name__ == "__main__":
    raise SystemExit(main())
