#!/usr/bin/env python
"""Legibility of lettering, read by OCR on the RENDER against the artwork.

PR 1 of `docs/superpowers/plans/2026-09-08-real-logo-lane-and-thin-strokes.md`,
and the phase-1 exit instrument for "lost": `docs/kent-review-2026-09-03.md`
records `dropped_elements` reading 0.2% on Hotel Fremont while Kent calls its
tagline "completely lost" — the instrument sees sewn-but-illegible as
covered, and nothing in this repo reads what the thread SAYS.

This does. For every text cluster stage 4 tagged (`meta["text_cluster_id"]`,
`textcluster.detect_text_clusters`), it crops the same millimetres out of the
prepped artwork and out of `stitchviz.render_design`'s thread render, runs
tesseract on both, and reports the normalised edit similarity between the
two readings — 1.0 when the thread says what the art says, 0.0 when the art
reads and the thread does not. The design-level figure is weighted by the
length of the artwork reading, so a cluster tesseract cannot read on the ART
side contributes nothing rather than a false zero. When a design has no text
cluster, the whole artwork and the whole render are read once, as one row.

Gate 4: a per-cluster edit similarity is a distance, not an agreement rate,
and no chance floor is claimed for it. It is also not a quality score — a
design can read perfectly and sew badly — it answers one question the eye
has been asking and no number could: is the lettering still there.

Needs the `tesseract` binary. CI installs it; a box without it gets the
same skip the OCR tests take (`tests/conftest.py`, `requires_tesseract`).

    .venv/bin/python tools/legibility.py photo/logo_hotel_fremont.webp --width 92.5 --garment patch
    .venv/bin/python tools/legibility.py --corpus [--dump DIR]
"""
from __future__ import annotations

import argparse
import difflib
import json
import re
import shutil
import sys
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

from digitizer_core import PipelineConfig                              # noqa: E402
from digitizer_core.adapter import plan_to_design                       # noqa: E402
from digitizer_core.pipeline import (build_generation, finish_generation,  # noqa: E402
                                     plan_stitches)
from digitizer_core.stage1_prep import Prep                            # noqa: E402
from digitizer_core.stitchviz import UNITS_PER_MM, _bounds, render_design  # noqa: E402
from digitizer_core.textcluster import _one_tesseract_thread            # noqa: E402
from thin_strokes import _plan_frame, corpus_cases, parse_flag               # noqa: E402

RENDER_PX_PER_MM = 12.0     # the review renders' scale
RENDER_PAD_MM = 2.0         # `render_design`'s own default pad
CROP_PAD_MM = 1.0           # around a cluster's box, both sides
OCR_MIN_HEIGHT_PX = 96      # tesseract reads capitals well from ~30 px; give it margin
OCR_BORDER_PX = 24


def normalise(text: str) -> str:
    """Upper-case letters and digits only: OCR punctuation and spacing are
    noise the question does not care about."""
    return re.sub(r"[^A-Z0-9]", "", (text or "").upper())


def similarity(art_text: str, render_text: str) -> float | None:
    """Edit similarity of the two normalised readings; None when the ART side
    read nothing (no truth to compare against)."""
    a, b = normalise(art_text), normalise(render_text)
    if not a:
        return None
    return difflib.SequenceMatcher(None, a, b).ratio()


def tesseract_available() -> bool:
    return shutil.which("tesseract") is not None


def prepare_for_ocr(img: np.ndarray, blur_px: float = 0.0, thin_px: float = 0.0) -> np.ndarray:
    """Grey, upscaled so the crop is at least `OCR_MIN_HEIGHT_PX` tall,
    optionally blurred, Otsu-binarised with a WHITE background whichever way
    the art was printed, and padded — tesseract's own preferred input.

    `blur_px` (a sigma, in the INPUT's pixels) and `thin_px` (an erosion of
    the ink after binarising, in the INPUT's pixels) exist for the render.
    Thread is drawn as lit filaments at real width on a compensated outline,
    so a sewn letter is bolder than its art and its counters close; tesseract
    read the ENTHUSIAST render as NOTHING at every blur, and as "ENTHUSIAST"
    at confidence 94 once the strokes were thinned by three pixels
    (measured 2026-09-08 on the dumped crop). The same variants run on the
    art, where they change little, so neither side is favoured.
    """
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img.copy()
    if g.size == 0:
        return np.full((OCR_MIN_HEIGHT_PX, OCR_MIN_HEIGHT_PX), 255, np.uint8)
    if blur_px > 0:
        g = cv2.GaussianBlur(g, (0, 0), blur_px)
    h, w = g.shape
    k = max(1.0, OCR_MIN_HEIGHT_PX / max(1, h))
    if k > 1.0:
        g = cv2.resize(g, (max(1, int(round(w * k))), max(1, int(round(h * k)))),
                       interpolation=cv2.INTER_CUBIC)
    _t, bw = cv2.threshold(g, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    border = np.concatenate([bw[0, :], bw[-1, :], bw[:, 0], bw[:, -1]])
    if border.mean() < 127:          # dark ground, light lettering: flip it
        bw = 255 - bw
    if thin_px > 0:
        r = max(1, int(round(thin_px * k)))          # in the upscaled raster
        bw = cv2.dilate(bw, np.ones((2 * r + 1, 2 * r + 1), np.uint8))   # grow the white = thin the ink
    return cv2.copyMakeBorder(bw, OCR_BORDER_PX, OCR_BORDER_PX, OCR_BORDER_PX, OCR_BORDER_PX,
                              cv2.BORDER_CONSTANT, value=255)


def ocr(img: np.ndarray, psm: int = 6, blur_px: float = 0.0, thin_px: float = 0.0) -> tuple[str, float]:
    """One tesseract read of `img` (BGR or grey) -> (text, mean word
    confidence 0-100). `psm` 6 is a uniform block of text; 7 a single line;
    11 sparse text.

    The confidence is returned beside the text because the text alone can
    lie. On Fremont's THE the render shows a plain "T H C" — the E's middle
    arm never sews (the dumped crop shows it) — and tesseract returns "THE",
    its language model filling the letter in. Read in single-line mode with
    no preprocessing the confidence said so (art 80, render 40); read the
    way `read_side` reads, best over modes and variants, the filled-in
    reading scores 95 and the loss is INVISIBLE to this instrument. So a
    per-cluster 1.00 certifies the WORD, not the glyphs: legibility is a
    lower bound on lettering loss, and a missing arm is a thin stroke, which
    `thin_strokes.py` reads directly. Measured 2026-09-08.
    """
    import pytesseract
    from PIL import Image

    prepared = prepare_for_ocr(img, blur_px, thin_px)
    with _one_tesseract_thread():
        data = pytesseract.image_to_data(Image.fromarray(prepared), config=f"--psm {psm}",
                                         output_type=pytesseract.Output.DICT)
    words = [(w, float(c)) for w, c in zip(data["text"], data["conf"]) if w and w.strip() and float(c) >= 0]
    text = " ".join(w for w, _c in words).strip()
    conf = sum(c for _w, c in words) / len(words) if words else 0.0
    return text, conf


# A cluster's box is not always one clean line: on Fremont one cluster's
# members include the Wisconsin silhouette above THE, and another's box has
# the banner under HOTEL FREMON. Single-line mode read NOTHING on both
# (measured 2026-09-08); block mode reads them. So the ART side is read in
# each mode and the reading with the most letters wins — the art is the
# truth, so the mode that recovers the most of it is the right mode — and the
# RENDER is then read in that same mode, so the two sides are compared like
# for like.
OCR_MODES = (6, 7, 11)
# Preprocessing variants tried on each side, (blur sigma, ink thinning) in
# millimetres of that side's own raster: as is; a blur of half the 0.4 mm
# satin pitch; a thinning of about the thread's half-width. The same variants
# run on both sides so neither is favoured; each side keeps its most
# confident reading.
VARIANTS_MM = ((0.0, 0.0), (0.2, 0.0), (0.0, 0.25))
# An ART reading under this confidence is not a truth to compare against.
# Tesseract reads a real word off clean art at 85-96; its garbage reads sit
# under 50 (Becker's outlined BECKER at 1.46 px/mm source: "OE" at 11, "I" at
# 43, while the RENDER of the same cluster reads "BECKER" at 96). A row whose
# art reading is under the floor is reported as unreadable and left out of
# the design figure — and its render reading is still printed, because a
# render that reads confidently where the art does not is the one case where
# the thread says more than the source could.
ART_CONF_MIN = 60.0
RENDER_CONF_MIN = 60.0


def read_side(imgs, px_per_mm: float, psms) -> tuple[str, float, int]:
    """-> (text, confidence, psm): the most confident reading over the
    candidate crops, the psm modes and the preprocessing variants, letters
    counted as the tie-break. A crop that reads nothing scores -1."""
    best = ("", -1.0, psms[0])
    for img in imgs:
        if img is None or img.size == 0:
            continue
        for psm in psms:
            for blur_mm, thin_mm in VARIANTS_MM:
                txt, conf = ocr(img, psm, blur_mm * px_per_mm, thin_mm * px_per_mm)
                key = (conf if normalise(txt) else -1.0, len(normalise(txt)))
                if key > (best[1], len(normalise(best[0]))):
                    best = (txt, conf, psm)
    return best


def read_pair(art_imgs, render_imgs,
              art_px_per_mm: float, render_px_per_mm: float = RENDER_PX_PER_MM) -> dict:
    """-> {art_text, art_conf, render_text, render_conf, psm, readable}.

    Each side is a list of candidate crops (masked to the cluster's members,
    and unmasked — Becker's letters are enclosed BODIES whose masked crop is
    white on white, while the unmasked one shows the keyline a person reads).
    The ART side picks the crop and mode that read it most confidently (the
    art is the truth, so whatever recovers it is right); the RENDER is then
    read in that same mode, so the two sides are compared like for like.
    """
    a_txt, a_conf, psm = read_side(art_imgs, art_px_per_mm, OCR_MODES)
    r_txt, r_conf, _ = read_side(render_imgs, render_px_per_mm, (psm,))
    return {"art_text": a_txt, "art_conf": round(max(a_conf, 0.0), 1),
            "render_text": r_txt, "render_conf": round(max(r_conf, 0.0), 1), "psm": psm,
            "readable": bool(normalise(a_txt)) and a_conf >= ART_CONF_MIN}


def cluster_members(regions) -> dict[str, list]:
    """-> cluster id -> its member regions, in id order."""
    out: dict[str, list] = {}
    for r in regions:
        cid = r.meta.get("text_cluster_id")
        if cid:
            out.setdefault(cid, []).append(r)
    return dict(sorted(out.items()))


def cluster_boxes(regions) -> list[tuple[str, tuple[float, float, float, float]]]:
    """-> [(cluster id, (x0, y0, x1, y1) in mm)], the union of each tagged
    cluster's member bounds, in id order."""
    out = []
    for cid, members in cluster_members(regions).items():
        bs = [m.polygon.bounds for m in members]
        out.append((cid, (min(b[0] for b in bs), min(b[1] for b in bs),
                          max(b[2] for b in bs), max(b[3] for b in bs))))
    return out


# The thread sits on the compensated outline, up to a fabric's pull past the
# artwork edge; the member mask on the RENDER side is grown by this so a
# column's rails are inside it. The art side is grown by the anti-alias
# halo only.
# One millimetre on both sides: enough to keep a keyline around letters
# that are enclosed-background BODIES (Becker), where the members are the
# white holes and the letter a person reads is the black ring around them.
RENDER_MASK_GROW_MM = 1.0
ART_MASK_GROW_MM = 1.0


def _mask_outside(img: np.ndarray, polys, to_px, grow_px: float) -> np.ndarray:
    """`img` with everything outside the union of `polys` (each mapped
    through `to_px`, grown by `grow_px`) painted the image's own border
    colour, so OCR sees the cluster's ink and not what shares its box —
    Fremont's banner under HOTEL FREMON read as "DMZYY" until this."""
    h, w = img.shape[:2]
    mask = np.zeros((h, w), np.uint8)
    for poly in polys:
        for ring in [poly.exterior]:
            pts = np.array([to_px(x, y) for x, y in ring.coords], np.int32)
            cv2.fillPoly(mask, [pts], 255)
    if grow_px > 0:
        k = int(round(grow_px)) * 2 + 1
        mask = cv2.dilate(mask, np.ones((k, k), np.uint8))
    border = np.concatenate([img[0, :], img[-1, :], img[:, 0], img[:, -1]]).reshape(-1, img.shape[2]) \
        if img.ndim == 3 else np.concatenate([img[0, :], img[-1, :], img[:, 0], img[:, -1]])
    fill = np.median(border, axis=0)
    out = img.copy()
    out[mask == 0] = fill
    return out


def art_crop(p: Prep, box_mm, pad_mm: float = CROP_PAD_MM, members=None) -> np.ndarray:
    """The prepped artwork inside `box_mm`, as BGR for OpenCV. With
    `members` (polygons in mm), everything outside them is painted away."""
    cx, cy, ppm = _plan_frame(p)
    h, w = p.rgb.shape[:2]
    x0 = max(0, int((box_mm[0] - pad_mm) * ppm + cx)); x1 = min(w, int(round((box_mm[2] + pad_mm) * ppm + cx)))
    y0 = max(0, int((box_mm[1] - pad_mm) * ppm + cy)); y1 = min(h, int(round((box_mm[3] + pad_mm) * ppm + cy)))
    crop = cv2.cvtColor(np.ascontiguousarray(p.rgb[y0:y1, x0:x1]), cv2.COLOR_RGB2BGR)
    if members:
        crop = _mask_outside(crop, members,
                             lambda x, y: (int(round(x * ppm + cx - x0)), int(round(y * ppm + cy - y0))),
                             ART_MASK_GROW_MM * ppm)
    return crop


def render_to_px(design: dict, px_per_mm: float = RENDER_PX_PER_MM, pad_mm: float = RENDER_PAD_MM):
    """-> f(x_mm, y_mm) -> (px, py) into `render_design(design, px_per_mm)`.

    The render's frame is the stitch bounds in 0.1 mm units plus its pad;
    the design is y-UP (the adapter's one flip), so a plan's y-down mm maps
    through `-y`. Mirrors `render_design.to_px` exactly.
    """
    box = _bounds(design.get("stitches") or [])
    if box is None:
        return lambda x, y: (0, 0)
    x0, _x1, _y0, y1 = box

    def f(x_mm: float, y_mm: float) -> tuple[int, int]:
        xu, yu = x_mm * UNITS_PER_MM, -y_mm * UNITS_PER_MM
        return (int(round(((xu - x0) / UNITS_PER_MM + pad_mm) * px_per_mm)),
                int(round(((y1 - yu) / UNITS_PER_MM + pad_mm) * px_per_mm)))
    return f


def render_crop(img: np.ndarray, design: dict, box_mm, px_per_mm: float = RENDER_PX_PER_MM,
                pad_mm: float = CROP_PAD_MM, members=None) -> np.ndarray:
    to_px = render_to_px(design, px_per_mm)
    ax, ay = to_px(box_mm[0] - pad_mm, box_mm[1] - pad_mm)
    bx, by = to_px(box_mm[2] + pad_mm, box_mm[3] + pad_mm)
    h, w = img.shape[:2]
    # Clamp each edge into the image BEFORE ordering them: a box that lies
    # wholly outside the render used to leave a negative end index, which
    # Python reads from the far side, and the crop wrapped onto real thread.
    x0, x1 = sorted((min(max(ax, 0), w), min(max(bx, 0), w)))
    y0, y1 = sorted((min(max(ay, 0), h), min(max(by, 0), h)))
    crop = img[y0:y1, x0:x1]
    if members and crop.size:
        def local(x, y):
            px, py = to_px(x, y)
            return px - x0, py - y0
        crop = _mask_outside(crop, members, local, RENDER_MASK_GROW_MM * px_per_mm)
    return crop


def measure(p: Prep, result, plan, px_per_mm: float = RENDER_PX_PER_MM,
            dump: Path | None = None, name: str = "design") -> dict:
    design = plan_to_design(plan)
    img = render_design(design, px_per_mm=px_per_mm)
    rows = []
    members = cluster_members(result.regions)
    clusters = cluster_boxes(result.regions)
    _cx, _cy, art_ppm = _plan_frame(p)
    if clusters:
        for cid, box in clusters:
            polys = [m.polygon for m in members[cid]]
            enclosed = all(m.meta.get("enclosed_background") for m in members[cid])
            a_img = art_crop(p, box, members=polys)
            r_img = render_crop(img, design, box, px_per_mm, members=polys)
            read = read_pair([a_img, art_crop(p, box)],
                             [r_img, render_crop(img, design, box, px_per_mm)], art_ppm, px_per_mm)
            rows.append({"cluster": cid, "height_mm": round(box[3] - box[1], 2),
                         "enclosed": enclosed, **read,
                         "similarity": similarity(read["art_text"], read["render_text"])
                         if read["readable"] else None})
            if dump is not None:
                cv2.imwrite(str(dump / f"{name}_{cid}_art.png"), prepare_for_ocr(a_img))
                cv2.imwrite(str(dump / f"{name}_{cid}_render.png"), prepare_for_ocr(r_img))
    else:
        cx, cy, ppm = _plan_frame(p)
        x0, y0, x1, y1 = p.art_bbox
        box = ((x0 - cx) / ppm, (y0 - cy) / ppm, (x1 - cx) / ppm, (y1 - cy) / ppm)
        a_img, r_img = art_crop(p, box, 0.0), render_crop(img, design, box, px_per_mm, 0.0)
        read = read_pair([a_img], [r_img], art_ppm, px_per_mm)
        rows.append({"cluster": "(whole design)", "height_mm": round(box[3] - box[1], 2),
                     "enclosed": False, **read,
                     "similarity": similarity(read["art_text"], read["render_text"])
                     if read["readable"] else None})
        if dump is not None:
            cv2.imwrite(str(dump / f"{name}_whole_art.png"), prepare_for_ocr(a_img))
            cv2.imwrite(str(dump / f"{name}_whole_render.png"), prepare_for_ocr(r_img))
    scored = [r for r in rows if r["similarity"] is not None]
    weight = sum(len(normalise(r["art_text"])) for r in scored)
    legibility = (sum(r["similarity"] * len(normalise(r["art_text"])) for r in scored) / weight
                  if weight else None)
    conf_drop = (sum((r["art_conf"] - r["render_conf"]) * len(normalise(r["art_text"])) for r in scored) / weight
                 if weight else None)
    render_readable = sum(1 for r in rows
                          if normalise(r["render_text"]) and r["render_conf"] >= RENDER_CONF_MIN)
    return {"clusters": len(clusters), "readable_on_art": len(scored),
            "render_readable": render_readable,
            "legibility": None if legibility is None else round(legibility, 3),
            "confidence_drop": None if conf_drop is None else round(conf_drop, 1),
            "rows": rows}


def run(art: Path, width_mm: float, garment: str, forced_class: str | None = None,
        dump: Path | None = None, flag: str | None = None) -> dict:
    extra = dict([parse_flag(flag)]) if flag else {}
    cfg = PipelineConfig(target_width_mm=width_mm, garment_id=garment, forced_class=forced_class, **extra)
    gen = build_generation(str(art), cfg)
    result = finish_generation(gen.fork(), cfg)
    plan = plan_stitches(result, cfg)
    out = measure(gen.p, result, plan, dump=dump, name=art.stem)
    out.update({"fixture": str(art), "width_mm": width_mm, "garment": garment,
                "design_class": result.design_class})
    return out


def _print(name: str, r: dict) -> None:
    leg = "  n/a" if r["legibility"] is None else f"{r['legibility']:5.2f}"
    drop = "  n/a" if r["confidence_drop"] is None else f"{r['confidence_drop']:+5.1f}"
    print(f"  {name:12} {r['design_class']:12} clusters {r['clusters']:3d} art readable {r['readable_on_art']:3d} "
          f"render readable {r['render_readable']:3d}  legibility {leg}  confidence drop {drop}")
    for row in r["rows"]:
        sim = "  n/a" if row["similarity"] is None else f"{row['similarity']:5.2f}"
        tag = " enclosed" if row.get("enclosed") else ""
        print(f"      {row['cluster'][:16]:16} {row['height_mm']:5.1f} mm  art {normalise(row['art_text'])[:20]:20} "
              f"({row['art_conf']:4.0f})  render {normalise(row['render_text'])[:20]:20} ({row['render_conf']:4.0f})  "
              f"{sim}  psm {row['psm']}{tag}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("fixture", nargs="?")
    ap.add_argument("--width", type=float, default=80.0)
    ap.add_argument("--garment", default="left_chest")
    ap.add_argument("--forced-class", default=None, dest="forced_class")
    ap.add_argument("--corpus", action="store_true")
    ap.add_argument("--dump", type=Path, default=None, help="write the OCR crops here")
    ap.add_argument("--flag", default=None, help="PipelineConfig field to turn on, NAME or NAME=VALUE")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    if a.flag:
        try:
            parse_flag(a.flag)
        except ValueError as e:
            ap.error(str(e))
    if not tesseract_available():
        print("tesseract binary not on PATH — nothing measured (CI installs tesseract-ocr)")
        return 2
    if not a.corpus and not a.fixture:
        ap.error("a fixture or --corpus")
    if a.dump is not None:
        a.dump.mkdir(parents=True, exist_ok=True)
    if a.corpus:
        cases = corpus_cases()
    else:
        art = Path(a.fixture)
        if not art.exists():
            art = ROOT / "testdata" / a.fixture
        cases = [(art.stem, art, a.width, a.garment)]
    results = []
    for name, art, w, g in cases:
        r = run(art, w, g, a.forced_class, a.dump, a.flag)
        results.append(r)
        _print(name, r)
    if a.json:
        print(json.dumps(results, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
