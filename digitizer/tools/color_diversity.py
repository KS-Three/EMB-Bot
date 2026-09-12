#!/usr/bin/env python
"""The 2026-08-15 spec's candidate stage-0 signal, re-measured on the real
artwork that exists today.

`docs/superpowers/specs/2026-08-15-stage0-flat-gradient-recalibration-design.md`
§6: **the number of distinct 3-bit-per-channel colours needed to cover 90% of
FOREGROUND pixels.** A fraction of the pixels rather than a count of them, so
it is scale-invariant by construction, and 3-bit quantisation swallows
anti-aliasing and JPEG speckle. On the seven artworks reachable in August it
was invariant across a 14x resolution range and NOT sitable: flat max 17
(`bridge`, the one JPEG) against gradient min 19 (`drone`) — a two-wide gap
resting on one positive example.

**The blocker was never the signal, it is the label distribution** (spec §6),
and ROADMAP gate 2 is the same sentence with teeth: no stage-0 recalibration
without real TONAL artwork, and synthetic fixtures are barred as substitutes.
This tool therefore does two things and refuses a third:

  1. measures the statistic across a resolution sweep, per artwork;
  2. reports the margin — flat max, tonal min, and the gap between them;
  3. **refuses to call a boundary sitable on fewer than `MIN_TONAL` real
     tonal artworks**, and says which ones it had.

The corpus is labelled by hand below, and the labels carry PROVENANCE:
`real` artwork a customer sent, or `synthetic` art this repo generated
(`tools/make_photo_fixtures.py`). Only `real` rows count toward the margin;
the synthetic ones are printed so a reader can see what was excluded and
why, which is the calibration/validation inversion the spec was blocked on.

    .venv/bin/python tools/color_diversity.py              # the sweep + the margin
    .venv/bin/python tools/color_diversity.py --json
    .venv/bin/python tools/color_diversity.py --art PATH --label tonal --provenance real

**On Kent's box there is more to measure**: the original Instagram icon (the
committed `repro_gradient_white_icon.png` is a synthetic reproduction and is
BARRED here), MFab, and any real portraits dropped into
`testdata/photo/acceptance/` — that directory is gitignored, holds only its
README in a fresh clone, and is where the spec's missing positives live.
Anything found there is picked up automatically and labelled real/tonal.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

from digitizer_core.config import PipelineConfig      # noqa: E402
from digitizer_core.stage1_prep import prep           # noqa: E402

TESTDATA = ROOT / "testdata"

# The resolution sweep, in SOURCE pixel widths. A width above an artwork's
# own is skipped rather than upscaled: an upscale invents no 3-bit colour
# and only smooths the anti-aliasing the statistic is built to swallow, so
# a reading taken there would be measuring cv2, not the art.
#
# **This sweep is NOT the spec's, and the two are not comparable.** The
# 08-15 table's `src146..src2000` columns hold one artwork at four sizes
# with becker constant at 3 across all four — becker's only file is 146 px
# wide, so those rungs were UPSCALES. This tool downscales instead, and an
# INTER_AREA downscale AVERAGES neighbouring pixels, which manufactures
# intermediate colours and can only push the count UP: `golden_tee` reads
# 15 at its native 2193 px and 45 at 146 px. So the sweep here is a
# robustness reading — how much the number moves when the customer sends a
# smaller file — and the MARGIN below is taken at each artwork's NATIVE
# resolution, which is the size the file actually arrives at.
WIDTHS = (146, 400, 900, 2000)

# Cover this fraction of the foreground before counting stops. The spec's
# number; a fraction, not a count, is what makes the statistic invariant.
COVERAGE = 0.90
# 3 bits per channel: 8 levels, 512 cells.
BITS = 3

# Four or five real tonal artworks is what the spec asked for before a
# boundary could be called defensible ("Four or five would make a boundary
# defensible"). Below this the tool reports and refuses.
MIN_TONAL = 4

# name -> (path relative to testdata, label, provenance)
#
# `label` is what stage 0 would have to decide; `provenance` is whether the
# ARTWORK is a customer's or this repo's own generator. Gate 2 bars the
# synthetic rows from siting anything, so they are measured and excluded.
CORPUS: dict[str, tuple[str, str, str]] = {
    # Real customer/flat artwork — the spec's own six, plus the two that
    # arrived since (Golden Tee, the phone screenshot).
    "becker":      ("becker_marine_logo.png",              "flat",  "real"),
    "tires":       ("logo_script_tires.png",               "flat",  "real"),
    "enthusiast":  ("photo/enthusiast_logo.png",           "flat",  "real"),
    "fremont":     ("photo/logo_hotel_fremont.webp",       "flat",  "real"),
    "bridge":      ("photo/logo_bridge_bar.jpg",           "flat",  "real"),
    "gaulke":      ("photo/logo_gaulke_roofing.png",       "flat",  "real"),
    "golden_tee":  ("photo/logo_golden_tee.jpg",           "flat",  "real"),
    "screenshot":  ("photo/screenshot_phone_ui_golke.jpg", "flat",  "real"),
    # A REAL PHOTOGRAPH, enrolled as a real tonal positive — Kent's ruling,
    # 2026-09-11. It counts because stage 0's photo gate already fails on it:
    # `owl_kent.jpg` reads `unique_color_mass` 0.1107 against `UCM_PHOTO_MIN`
    # 0.28, so a real photograph falls THROUGH to the flat/gradient gate and
    # that is the gate which has to separate it. Enrolling it is not free and
    # is not meant to be: it takes the margin from flat max 16 / tonal min 20
    # (+4) to 16 against its own 16 — gap 0, separating at no rung of the
    # sweep. That is the honest state of the signal under his ruling, and the
    # number PR 6a has to clear. See docs/stage0-tires-photo-scene-2026-09-11
    # §9a-bis. Note it is a 554 px re-save (no EXIF, same reason), so its
    # diversity may be deflated by the re-encode — a caution on the number,
    # not on the labelling.
    "owl_kent":    ("photo/owl_kent.jpg",                  "tonal", "real"),
    # Real tonal artwork. `drone_render` is the spec's one positive;
    # `logo_drone_thermal_badge` is byte-identical to it (thin_strokes'
    # `corpus_cases` records the same) and is not enrolled twice.
    "drone":       ("photo/drone_render.png",              "tonal", "real"),
    # Synthetic — measured, printed, and EXCLUDED from the margin. These are
    # `tools/make_photo_fixtures.py`'s output and the repro of Kent's icon;
    # enrolling them is exactly the fixture bias that produced the original
    # miscalibration (spec §6).
    "owl":         ("photo/photo_owl_pale.png",            "tonal", "synthetic"),
    "meadow":      ("photo/photo_dof_meadow.png",          "tonal", "synthetic"),
    "grass":       ("photo/photo_grass_macro.png",         "tonal", "synthetic"),
    "sunset":      ("photo/photo_sunset_backlit.png",      "tonal", "synthetic"),
    "chrome":      ("photo/photo_chrome_specular.png",     "tonal", "synthetic"),
    "repro_icon":  ("photo/repro_gradient_white_icon.png", "tonal", "synthetic"),
    "summit":      ("photo/summit_badge.png",              "tonal", "synthetic"),
    "ramp_lin":    ("photo/gradient_ramp_linear.png",      "tonal", "synthetic"),
    "ramp_rad":    ("photo/gradient_ramp_radial.png",      "tonal", "synthetic"),
}

# Dropped into the gitignored acceptance directory by hand (its README says
# so). Real photographs, and the positives the spec is waiting for.
ACCEPTANCE = TESTDATA / "photo" / "acceptance"
ACCEPTANCE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff"}


def diversity(rgb: np.ndarray, fg: np.ndarray) -> int:
    """Distinct 3-bit-per-channel colours needed to cover `COVERAGE` of the
    foreground pixels — the spec's statistic, most-common colour first.

    `rgb` is (H, W, 3) uint8; `fg` is (H, W) bool, True where foreground.
    Returns 0 when nothing is foreground (an artwork stage 1 flooded away).
    """
    px = np.asarray(rgb)[np.asarray(fg, bool)].reshape(-1, 3)
    if len(px) == 0:
        return 0
    q = (px >> (8 - BITS)).astype(np.int32)
    keys = (q[:, 0] << (2 * BITS)) | (q[:, 1] << BITS) | q[:, 2]
    counts = np.sort(np.bincount(keys)[np.bincount(keys) > 0])[::-1]
    need = COVERAGE * counts.sum()
    return int(np.searchsorted(np.cumsum(counts), need) + 1)


def foreground(rgb_bgr: np.ndarray, mode: str = "engine") -> tuple[np.ndarray, np.ndarray, str]:
    """-> (rgb, foreground mask, note).

    Two definitions of "foreground", because the spec says the word and does
    not define it, and the choice moves the statistic by an order of
    magnitude:

    * `engine` — the pixels stage 1 would DIGITIZE: inside the art bbox and
      not background, by `stage1_prep.prep`'s own rule, so the instrument
      and stage 0 never disagree.
    * `bbox` — every pixel inside the art bbox, background included. This is
      the reading that reproduces the 08-15 table's shape (becker 3, not 1:
      white ground, black ink, and the halo between them), so it is almost
      certainly what that table measured.

    Both are reported. A claim about the signal that holds under only one of
    them is a claim about the definition, not about the artwork.

    The upscale is disabled (`upscale_cap=1.0`): prep never downscales, so
    without this a low-resolution rung would be Lanczos-enlarged and the
    sweep would measure the resize instead of the artwork. When stage 1's
    existence guards refuse to find a background at all (full-bleed art),
    every pixel inside the art bbox is foreground — which is what the
    engine itself then digitizes.
    """
    cfg = PipelineConfig(target_width_mm=80.0, upscale_cap=1.0)
    p = prep(rgb_bgr, cfg)                    # ndarray in = cv2's BGR (DOCTRINE)
    x0, y0, x1, y1 = p.art_bbox
    inside = np.zeros(p.rgb.shape[:2], bool)
    inside[y0:y1, x0:x1] = True
    if mode == "bbox":
        return p.rgb, inside, ""
    fg = inside & ~p.bg_mask
    note = ""
    if not fg.any():
        fg, note = inside, "no background found; the whole art bbox is foreground"
    return p.rgb, fg, note


def sweep(path: Path, widths=WIDTHS, mode: str = "engine") -> dict:
    """The statistic at each rung of the resolution sweep, for one artwork."""
    src = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if src is None:
        return {"error": f"cv2 could not read {path}"}
    h, w = src.shape[:2]
    rungs, notes = {}, set()
    for target in sorted({*widths, w}):
        if target > w:
            continue                      # never upscale: see `sweep`'s docstring
        scaled = (src if target == w else
                  cv2.resize(src, (target, max(1, round(h * target / w))),
                             interpolation=cv2.INTER_AREA))
        try:
            rgb, fg, note = foreground(scaled, mode)
        except Exception as exc:          # noqa: BLE001 — one bad rung must not sink the sweep
            rungs[target] = None
            notes.add(f"{target}px: {type(exc).__name__}: {exc}")
            continue
        rungs[target] = diversity(rgb, fg)
        if note:
            notes.add(f"{target}px: {note}")
    vals = [v for v in rungs.values() if v]
    return {"source_px": w, "rungs": rungs,
            # The artwork as it arrives — what the margin is read on.
            "native": rungs.get(w),
            "min": min(vals) if vals else None, "max": max(vals) if vals else None,
            "spread": (max(vals) - min(vals)) if vals else None,
            "notes": sorted(notes)}


def corpus_rows() -> list[tuple[str, Path, str, str]]:
    """-> [(name, path, label, provenance)], the table plus anything real
    dropped into the gitignored acceptance directory."""
    rows = [(name, TESTDATA / rel, label, prov)
            for name, (rel, label, prov) in CORPUS.items()
            if (TESTDATA / rel).exists()]
    if ACCEPTANCE.is_dir():
        for p in sorted(ACCEPTANCE.iterdir()):
            if p.suffix.lower() in ACCEPTANCE_SUFFIXES:
                rows.append((f"acceptance/{p.stem}", p, "tonal", "real"))
    return rows


def report(results: list[dict], mode: str = "engine") -> int:
    """The sweep, then the margin — or the refusal, with what it lacked."""
    print(f"# The 08-15 spec's colour-diversity signal, re-measured "
          f"({int(COVERAGE * 100)}% of foreground, {BITS} bits/channel, "
          f"foreground = {mode})\n")
    head = f"{'artwork':<20} {'label':<6} {'prov':<10} {'source':>7}  " + \
           "".join(f"{str(w) + 'px':>8}" for w in WIDTHS) + f"{'spread':>8}"
    print(head)
    print("-" * len(head))
    for r in results:
        if "error" in r:
            print(f"{r['name']:<20} {r['label']:<6} {r['provenance']:<10} {'—':>7}  {r['error']}")
            continue
        cells = "".join(f"{(str(r['rungs'].get(w)) if r['rungs'].get(w) is not None else '—'):>8}"
                        for w in WIDTHS)
        native = f"  native {r['source_px']}px: {r['native']}"
        print(f"{r['name']:<20} {r['label']:<6} {r['provenance']:<10} "
              f"{r['source_px']:>7}  {cells}{str(r['spread']):>8}{native}")
    for r in results:
        for n in r.get("notes", ()):
            print(f"  [note] {r['name']}: {n}")

    real = [r for r in results if r.get("provenance") == "real" and r.get("native")]
    flat = [r for r in real if r["label"] == "flat"]
    tonal = [r for r in real if r["label"] == "tonal"]
    print(f"\n## The margin — REAL artwork at its NATIVE resolution "
          f"({len(flat)} flat, {len(tonal)} tonal; gate 2 bars the synthetic rows)\n")
    gap = None
    if not flat or not tonal:
        print("  not computable: one side of the boundary has no real artwork.")
    else:
        fmax = max(flat, key=lambda r: r["native"])
        tmin = min(tonal, key=lambda r: r["native"])
        print(f"  flat max   {fmax['native']:>3}  ({fmax['name']})")
        print(f"  tonal min  {tmin['native']:>3}  ({tmin['name']})")
        gap = tmin["native"] - fmax["native"]
        print(f"  gap        {gap:>3}  " +
              ("— the classes SEPARATE on this corpus" if gap > 0 else
               "— the classes OVERLAP: a flat artwork reads HIGHER than the "
               "tonal one, so no threshold on this statistic orders them"))
        # The same question asked of the sweep, because a customer's file can
        # arrive at any size: does ANY rung order the two classes?
        ordered = [w for w in sorted({*WIDTHS})
                   if all(r["rungs"].get(w) for r in flat + tonal)
                   and min(r["rungs"][w] for r in tonal) > max(r["rungs"][w] for r in flat)]
        rungs_common = [w for w in sorted({*WIDTHS})
                        if all(r["rungs"].get(w) for r in flat + tonal)]
        if rungs_common:
            print(f"  across the sweep: the classes separate at "
                  f"{ordered if ordered else 'NO'} of the rungs every artwork reaches "
                  f"({rungs_common})")
    print()
    if gap is not None and gap <= 0:
        # This used to end "They DO under `bbox`" unconditionally, which was
        # true only while `bbox` ordered them — and on 2026-09-11, when Kent
        # ruled a real photograph counts as a tonal positive, `bbox` stopped
        # doing so. The sentence then fired ON bbox and contradicted the line
        # above it. Say what THIS run measured and name the other definition
        # as something to check, never as something that works.
        other = "engine" if mode == "bbox" else "bbox"
        print(f"**The classes do not order under `foreground = {mode}`.** Try "
              f"`--foreground {other}` before concluding anything about the "
              f"signal — the two count different pixels and disagree by an order "
              f"of magnitude on a compressed file (excluding the background "
              f"removes the flat ground that dominates the 90% and leaves a "
              f"JPEG's compression noise to be counted on its own), and `bbox` "
              f"is the definition that reproduces the 08-15 table (bridge 16-17 "
              f"against its 17, drone 19-20 against its 19). Neither is evidence "
              f"about the other's ordering; run both and quote the mode.\n")
    if len(tonal) < MIN_TONAL:
        print(f"**NOT SITABLE — {len(tonal)} real tonal artwork(s), the spec asks for "
              f"{MIN_TONAL}.** Gate 2: no stage-0 recalibration without real tonal "
              f"artwork, and synthetic fixtures are barred as substitutes. This is the "
              f"SAME blocker the 08-15 spec recorded — the label distribution, not the "
              f"signal.\n\n  What would settle it, in one command on Kent's box: drop "
              f"3-5 real tonal artworks (his Instagram icon's ORIGINAL, airbrushed or "
              f"shaded logos, photo patches) into `digitizer/testdata/photo/acceptance/` "
              f"and re-run this tool — they are picked up automatically, and nothing "
              f"there is ever committed.")
        return 1
    print(f"{len(tonal)} real tonal artworks measured — at or above the spec's floor of "
          f"{MIN_TONAL}. The margin above is the boundary evidence; the lane change "
          f"(plan §5a, PR 6a/6b) is the next step and is Kent's to approve.")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--art", type=Path, action="append", default=None,
                    help="extra artwork to measure (repeatable)")
    ap.add_argument("--label", default="tonal", choices=["flat", "tonal"],
                    help="label for --art (default tonal)")
    ap.add_argument("--provenance", default="real", choices=["real", "synthetic"],
                    help="provenance for --art (default real)")
    ap.add_argument("--foreground", default="engine", choices=["engine", "bbox"],
                    help="which pixels count (see `foreground`); default engine")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)

    rows = corpus_rows()
    for extra in (a.art or []):
        rows.append((extra.stem, extra, a.label, a.provenance))
    results = []
    for name, path, label, prov in rows:
        r = sweep(path, mode=a.foreground)
        r.update({"name": name, "path": str(path), "label": label, "provenance": prov})
        results.append(r)
    if a.json:
        print(json.dumps(results, indent=1))
        return 0
    return report(results, a.foreground)


if __name__ == "__main__":
    raise SystemExit(main())
