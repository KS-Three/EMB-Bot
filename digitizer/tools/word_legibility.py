#!/usr/bin/env python
"""Can a stranger READ each word of the sewn lettering, ours beside the pro's?

I3 of the lettering lane. `tools/legibility.py` OCRs whole text clusters of
OUR render against the artwork (an edit distance, no chance floor, no pro) and
`tools/glyph_legibility.py` reads thread GLYPH by glyph against the source
shape. Neither answers the question a lettering PR needs a number for, and
neither puts the pro's file beside ours: *at the size this word is really
worn, does tesseract read the word the artwork spells?* This does, for one
job at a time, and prints ours and the pro's side by side so a PR can carry
a legibility figure next to its render.

What it does, per job (art + the pro's stitch file for the same art):

  1. Digitize the art the way the Studio asks (`tools.pro_pair.digitize`:
     the service's own parser, today's defaults) -> OUR design. The pro's
     file is read by pystitch through `glyph_legibility.design_from_pes`.
     Both go through ONE reader and ONE renderer
     (`digitizer_core.stitchviz.render_design`, the repo's thread renderer).
  2. Word boxes are PINNED in `testdata/word_legibility_words.json`: the
     known text of each word and its box as fractions of the artwork's INK
     box. They were proposed by the tagger (`--propose`: `glyph_read.
     word_boxes`) and named by hand against the art. Text and numbers only;
     no artwork is stored.
  3. EACH FILE IS LOCATED IN ITS OWN FRAME. The artwork's ink is registered
     to that file's thread (`glyph_legibility.register`: a per-axis scale and
     a translation fitted to the file), and the registered box is only a
     SEED: `find_word` takes the spool colour with most thread in it, fuses
     its letters with a growing dilation, and the word is that fused piece's
     own bounding box in the file. A fixed box would cut the pro's EST, 1895
     and EAT STAY PLAY, which it sews bolder and wider than the art draws
     them (the first version, a correlation shift, latched onto the rope and
     read the pro's EST as nothing). Three more stages when that finds
     nothing clearly the word (2026-10-25): the same search over every run
     of consecutive letters rather than fused pieces, with the thin joins that
     weld a letter to a rope cut first (Fremont's pro STAY, PLAY, 1895;
     ProSeal's SPRAY FOAM beside its +); the same search over what SHOWS of
     each spool (`visible_masks`: MFab's pro sews a black bed under white
     satin and black letters, and the black spool alone has them welded to
     the bed); and, last, the art's own place when the thread there LOOKS like
     the art's word (`appearance_sim`, `ACCEPT_SIM`): the row says
     `loc: registered`. A word none of these finds is `n/loc` and left OUT of
     the figure, never scored 0 (that would score the locator).
     Thread the colour of the ground is dropped where it lies on bare cloth
     and kept where it lies on other thread (`keep_visible_ground`): MFab's
     white letters on a black bed are thread.
  4. SIMULATED SEWN HEIGHT. The stitches around the word are cut out, scaled
     about the word's centre so the word's ink is exactly 4 / 7 / 12 mm tall
     (`HEIGHTS_MM`), and drawn at 20 px/mm with the filament kept at its
     real 0.4 mm, on the artwork's own ground colour (thread the colour of
     the ground vanishes, as on cloth). It answers "if THIS stitch layout
     were worn at H mm, would the thread still read"; it is NOT a digitize at
     that size (the engine would build a 4 mm word differently, so the
     number is the geometry's, not the product's at 4 mm), and not a sew-out
     (ROADMAP gate 1: no pull, no push, no nap). SHRINK ONLY: a layout scaled
     UP keeps its row pitch and opens gaps no engine would sew, so a word
     already smaller than H is not read at H (its row says so). Shrinking is
     the physical direction: the strokes narrow, the 0.4 mm filament does
     not, and counters close as they do on a small sewn word. The word's
     NATIVE size is read too, because that is what the job really is.
  5. Tesseract (psm 7, the repo's three preprocessing variants, the most
     confident reading wins -- chosen WITHOUT looking at the truth) reads the
     crop, in two VIEWS (2026-10-25): WIDE, every stitch of every neighbour in
     reach (the only crop before today), and TIGHT, only the thread within
     `CROP_NEIGHBOUR_MM` of the word's own box. A black bar a millimetre from
     the pro's STAY sets Otsu's threshold above STAY's orange and the word is
     read as nothing; and BECKER's black letters in a grey outline binarise
     apart only beside the next line's grey, so a tight view alone reads it
     worse. The most confident of the six readings wins, the wide view on a
     tie (`view` on the row). The artwork's own crop is read the same way as
     the CEILING: a word tesseract cannot read off the art (Becker's 146 px
     logo) says nothing about the thread, and is shown as such.

  6. THE FINER NUMBER, `reach` (2026-10-25). `cc` is 1.00 for any word that
     reads, so it cannot show a word getting better. At the size the word is
     really sewn, its crop is shown at smaller and smaller sizes (area-averaged
     down in half-octave steps to 3 px tall: the word seen from farther and
     farther), read at every step, and `reach` is the area under `cc`
     against the log of the size, in OCTAVES: how many times the word can be
     halved, the distance doubled, and still be read. It moves with the size a
     word is sewn at (a small word re-set bigger gains) and with how well its
     letters hold together as the picture shrinks (`floor_px`, the smallest
     height it is still read at, is the size-free part). It is built from
     `cc`, so it is chance-corrected, and it does not saturate where `cc`
     does: it is zero for a word not read at native and the whole ladder's
     height for one read all the way down. Not a distance in metres: no
     viewer, no sew-out (ROADMAP gate 1). The art's own crop gets the same
     ladder, as the ceiling.

THE NUMBER (ROADMAP gate 4: no quality claim on a raw agreement number).
Per word, `raw` is the character-level similarity of the reading R to the
known text T (`difflib` ratio, 2M/(|R|+|T|) over the A-Z0-9 letters). Raw
moves with the mix of words and with how many letters a word has, so it is
printed only BESIDE the headline. The headline, `cc`, is the same similarity
corrected for chance:

    cc = (raw - base) / (1 - base),    base = E[ratio(R, shuffle(T))]

where `shuffle(T)` is a random permutation of T's own letters (500 draws, a
fixed seed). `base` is what a reader gets by saying the right letters in a
random order, so `cc` is 0 for a reading that is no better than that (an
empty reading is exactly 0) and 1 for the word itself. Kappa was the other
candidate: a character-level confusion matrix over a few hundred letters has
cells of one or two, and `cc` needs no cell to be filled. A job's figure is
the mean of its words' `cc` weighted by the word's letters; the word is the
unit (a job is 5-14 words), the n is printed with it, and no interval is
claimed from n that small.

Environment. Needs the `tesseract` binary for the numbers; a box without it
skips the OCR step with a message and still writes the crops and the
geometry (`--no-ocr` asks for that). Kent's Windows box has tesseract 5.4.0
(under Program Files, on the bash PATH; CI's is 5.3.4, so a figure
quoted from here says which). Every crop of a job is read in a few
list-of-images tesseract runs (`read_crops`), not one process per crop: a
process start costs 5 s on a loaded laptop, and a job is 40-400 crops.
`--digitize` writes OUR design to `--cache`, `--read` reads it; `--no-ladder`
leaves out the `reach` reads (about two thirds of them). Pro files and Kent's art are gitignored third-party
files: `EMB_SCRATCH_KENT` names the folder holding `Embroidery Files/` and
`proseal.jpg` (default: the first `scratch_kent/` above this checkout).

    python -m tools.word_legibility --list
    python -m tools.word_legibility --digitize fremont,becker,mfab,proseal --cache DIR
    python -m tools.word_legibility --propose mfab --cache DIR      # tagger word boxes, art overlay
    python -m tools.word_legibility --read fremont,becker,mfab,proseal --cache DIR [--json OUT] [--dump DIR]
"""
from __future__ import annotations

import argparse
import difflib
import json
import math
import os
import re
import shutil
import sys
from pathlib import Path

import cv2
import numpy as np

DIGITIZER = Path(__file__).resolve().parent.parent
if str(DIGITIZER) not in sys.path:
    sys.path.insert(0, str(DIGITIZER))

HEIGHTS_MM = (4.0, 7.0, 12.0)    # simulated sewn word heights; "native" is read as well
RENDER_PPM = 20.0                # px per mm of the simulated render
CROP_PAD_FRAC = 0.25             # OCR crop margin, as a share of the word's height
WINDOW_FRAC = 0.8                # stitches within this many word heights of the box are drawn
CROP_NEIGHBOUR_MM = 0.5          # the TIGHT view of a word: only the thread within this far of its own box. A bar 1 mm
                                 # from STAY is not STAY, and its black sets Otsu's threshold above STAY's orange; but a
                                 # wide view can read what a tight one cannot (BECKER's black letters in a grey outline
                                 # binarise apart only beside the next line's grey), so the reader gets both views
BASELINE_DRAWS = 500
BASELINE_SEED = 7
WORDS_FILE = DIGITIZER / "testdata" / "word_legibility_words.json"

#: job -> where the art and the pro's file live. "testdata:" is committed,
#: "kent:" is the gitignored `scratch_kent/` folder (EMB_SCRATCH_KENT),
#: "path:" absolute. `main` adds every job `tools.pro_intake` registered.
JOBS: dict[str, dict] = {
    "fremont": {"art": "testdata:photo/logo_hotel_fremont.webp", "garment": "hat_front",
                "pro": "kent:Embroidery Files/Hotel Fremont/Hotel Hat/HOTEL FREMONT HAT.PES"},
    "becker": {"art": "testdata:becker_marine_logo.png", "garment": "hat_front",
               "pro": "testdata:reference/becker_hat_polo_large_beckers_logo_hat.pes"},
    "mfab": {"art": "testdata:art/logo_mfab_hat.png", "garment": "hat_front",
             "pro": "kent:Embroidery Files/MFAB/Mfab Hat & Polo/mf4b logo hat.PES"},
    "proseal": {"art": "kent:proseal.jpg", "garment": "hat_front",
                "pro": "kent:Embroidery Files/Proseal/PROSEALHAT.DST"},
}


# --- the number --------------------------------------------------------------

def norm(text: str) -> str:
    """Upper-case letters and digits only (the repo's `legibility.normalise`)."""
    return re.sub(r"[^A-Z0-9]", "", (text or "").upper())


def raw_sim(read: str, truth: str) -> float:
    """Character-level similarity of two normalised strings: difflib's
    2M/(|a|+|b|). 0 when either is empty."""
    if not read or not truth:
        return 0.0
    return difflib.SequenceMatcher(None, read, truth, autojunk=False).ratio()


def shuffle_baseline(read: str, truth: str, draws: int = BASELINE_DRAWS,
                     seed: int = BASELINE_SEED) -> float:
    """E[ratio(read, p)] over random permutations p of `truth`'s own letters:
    what saying the right letters in a random order earns."""
    if not read or not truth:
        return 0.0
    rng = np.random.default_rng(seed)
    chars = np.array(list(truth))
    tot = 0.0
    for _ in range(draws):
        tot += raw_sim(read, "".join(rng.permutation(chars)))
    return tot / draws


def chance_corrected(read: str, truth: str) -> dict:
    """-> {"raw", "base", "cc"} for a reading against the known text. `cc` is
    None when the baseline is 1 (a one-letter word, or one letter repeated:
    every shuffle IS the word, so there is nothing to correct against)."""
    r, t = norm(read), norm(truth)
    raw = raw_sim(r, t)
    base = shuffle_baseline(r, t)
    cc = None if base >= 1.0 - 1e-9 else (raw - base) / (1.0 - base)
    return {"raw": round(raw, 3), "base": round(base, 3), "cc": None if cc is None else round(cc, 3)}


def job_figure(rows: list[dict]) -> dict:
    """The job's number: `cc` and `raw` averaged over its words, weighted by
    each word's letters. Words with no `cc` (one-letter) are left out of both.
    `reach` (octaves, the finer number) is averaged the same way over the
    words that have one."""
    use = [r for r in rows if r.get("cc") is not None]
    w = sum(len(norm(r["text"])) for r in use)
    if not w:
        return {"cc": None, "raw": None, "words": 0, "reach": None}
    deep = [r for r in use if r.get("reach") is not None]
    wr = sum(len(norm(r["text"])) for r in deep)
    return {"cc": round(sum(r["cc"] * len(norm(r["text"])) for r in use) / w, 3),
            "raw": round(sum(r["raw"] * len(norm(r["text"])) for r in use) / w, 3),
            "words": len(use),
            "reach": round(sum(r["reach"] * len(norm(r["text"])) for r in deep) / wr, 3) if wr else None}


BLIND_CC = 0.5     # a reading at or above this is a reading of the word


def blind_words(rows: list[dict], ceilings: dict) -> dict[str, str]:
    """The words this reader cannot judge: those whose chance-corrected
    reading, in the art's own crop AND in every file's thread at its native
    size, stays under `BLIND_CC`. The art's word is the best a reader can do
    with the word (BECKER reads 0.00 off the art and 1.00 off the pro's
    thread, so a thread reading counts); when nothing reads, 0.00 against
    0.06 is two guesses, not two lettering qualities (MFab's outlined AND
    WELDING LLC: the art, ours and the pro's thread all read under 0.2). The
    board leaves them out and says so. -> {word: why}."""
    out = {}
    for t in {r["text"] for r in rows}:
        ccs = {f: next((r.get("cc") for r in rows if r["file"] == f and r["text"] == t and r.get("size") == "native"), None)
               for f in ("ours", "pro")}
        art = (ceilings.get(t) or {}).get("cc")
        seen = [v for v in (*ccs.values(), art) if v is not None]
        if seen and max(seen) < BLIND_CC:
            out[t] = (f"the reader reads neither the art nor either file's thread (cc art "
                      f"{'-' if art is None else format(art, '+.2f')}, ours {'-' if ccs['ours'] is None else format(ccs['ours'], '+.2f')}, "
                      f"pro {'-' if ccs['pro'] is None else format(ccs['pro'], '+.2f')})")
    return out


# --- files -------------------------------------------------------------------

def tesseract_available() -> bool:
    return shutil.which("tesseract") is not None


def kent_root() -> Path | None:
    env = os.environ.get("EMB_SCRATCH_KENT")
    if env:
        return Path(env)
    for p in (DIGITIZER, *DIGITIZER.parents):
        if (p / "scratch_kent").is_dir():
            return p / "scratch_kent"
    return None


def resolve(spec: str) -> Path:
    kind, _sep, rel = spec.partition(":")
    if kind == "testdata":
        return DIGITIZER / "testdata" / rel
    if kind == "path":
        return Path(rel)
    root = kent_root()
    if root is None or not (root / rel).exists():
        raise SystemExit(f"{rel!r} not found: it is a gitignored third-party file. Set EMB_SCRATCH_KENT to "
                         f"the folder that holds 'Embroidery Files/' and 'proseal.jpg'.")
    return root / rel


def registered_jobs() -> dict[str, dict]:
    """The pairs `tools.pro_intake` registered (its gitignored registry beside
    the job folders), in JOBS' shape; the pro's PES when the pair has one (a
    DST draws one black block)."""
    from tools.pro_intake import pair_record, registered_pairs
    out = {}
    for slug, pro, art, gid in registered_pairs():
        pes = pair_record(slug)["pes"]
        out[slug] = {"art": f"path:{art}", "garment": gid or "hat_front", "pro": f"path:{pes or pro}"}
    return out


def pinned_words(job: str) -> list[dict]:
    data = json.loads(WORDS_FILE.read_text(encoding="utf-8"))
    return data["jobs"].get(job, {}).get("words", [])


def pro_width_mm(path: Path) -> float:
    import pystitch
    x0, _y0, x1, _y1 = pystitch.read(str(path)).extents()
    return round((x1 - x0) / 10.0, 1)


# --- window, scale, render ----------------------------------------------------

TRAVEL_MM = 9.0     # a stitch longer than this is travel, not thread a word is made of


def drop_travel(design: dict, max_mm: float = TRAVEL_MM) -> dict:
    """`design` with every stitch longer than `max_mm` made a jump. A few
    pro files carry travel runs sewn as 12 mm stitches (Fremont's: three,
    drawn as a black diagonal through FREMONT's R, welding it to the border
    for any word finder, and across the crop for a reader); the machine cuts
    or buries them, and the renderer draws them as thread. Ours has none."""
    out, prev = [], None
    lim = max_mm * 10.0
    for rec in design.get("stitches") or []:
        k = rec.get("type")
        if k == "stitch" and prev is not None and math.hypot(rec["x"] - prev[0], rec["y"] - prev[1]) > lim:
            rec = {**rec, "type": "jump"}
        out.append(rec)
        prev = (rec["x"], rec["y"]) if rec.get("type") == "stitch" else None
    return {**design, "stitches": out}


def drop_ground_blocks(design: dict, ground) -> dict:
    """`design` with every colour block that is the ground's own colour turned
    into jumps (thread the colour of the cloth is not seen on it; the engine
    sews the background shapes, and they would draw as grey stripes across
    every word). The same filter `glyph_read.thread_ink` applies."""
    from digitizer_core.glyph_read import ink_blocks
    keep = ink_blocks(design, np.asarray(ground, float))
    ci, out = 0, []
    for rec in design.get("stitches") or []:
        k = rec.get("type")
        if k == "color":
            ci += 1
        elif k == "stitch" and not keep[min(ci, len(keep) - 1)]:
            rec = {**rec, "type": "jump"}
        out.append(rec)
    return {**design, "stitches": out}


def keep_visible_ground(design: dict, ground, px_per_mm: float, dist: float | None = None):
    """`drop_ground_blocks`, minus the stitches that are SEEN. Thread the
    colour of the ground vanishes on bare cloth, and that is all
    `drop_ground_blocks` knows: MFab's pro sews its AND WELDING LLC in white
    thread (240) over a black bed, on art whose ground is white (254), and it
    dropped every letter with the cloth. Here a ground-coloured stitch is
    kept when the thread already sewn lies under it (most of the stitch
    falls on coverage drawn from every stitch before it), and made a jump
    when it lies on bare cloth. -> (design, keep): per colour block, does any
    of it show (`colour_masks(keep=)`)."""
    from digitizer_core import stitchviz
    from digitizer_core.glyph_read import GROUND_DIST
    dist = GROUND_DIST if dist is None else dist
    g = np.asarray(ground, float)
    cols = design.get("colors") or [{"r": 0, "g": 0, "b": 0}]
    is_ground = [float(np.linalg.norm(np.array([c["r"], c["g"], c["b"]], float) - g)) <= dist for c in cols]
    recs = design.get("stitches") or []
    b = stitchviz._bounds(recs)
    if b is None:
        return design, [not x for x in is_ground]
    x0, x1, y0, y1 = b
    k = px_per_mm / stitchviz.UNITS_PER_MM
    cover = np.zeros((int((y1 - y0) * k) + 4, int((x1 - x0) * k) + 4), np.uint8)
    thick = max(1, int(round(stitchviz.THREAD_MM * px_per_mm)))
    ci, pos, shown = 0, None, [False] * len(cols)
    out = []
    for rec in recs:
        t = rec.get("type")
        if t == "color":
            ci += 1
            out.append(rec)
            continue
        if t not in ("stitch", "jump"):
            out.append(rec)
            continue
        pt = (int(round((rec["x"] - x0) * k)), int(round((rec["y"] - y0) * k)))
        i = min(ci, len(cols) - 1)
        if t == "stitch" and pos is not None:
            if not is_ground[i]:
                cv2.line(cover, pos, pt, 255, thick)
                shown[i] = True
            else:
                pts = [(pos[0] + (pt[0] - pos[0]) * f, pos[1] + (pt[1] - pos[1]) * f) for f in (0.0, 0.25, 0.5, 0.75, 1.0)]
                on = sum(1 for (px, py) in pts if cover[min(max(int(round(py)), 0), cover.shape[0] - 1),
                                                       min(max(int(round(px)), 0), cover.shape[1] - 1)])
                if on >= 4:
                    cv2.line(cover, pos, pt, 255, thick)
                    shown[i] = True
                    rec = {**rec, "g": True}           # ground-coloured thread that shows (`ground_in_box`)
                else:
                    rec = {**rec, "type": "jump"}
        pos = pt
        out.append(rec)
    return {**design, "stitches": out}, [(not is_ground[i]) or shown[i] for i in range(len(cols))]


def ground_in_box(design: dict, box: tuple, margin_mm: float = 0.0) -> dict:
    """`design` from `keep_visible_ground`, with the ground-coloured thread it
    kept (stitches marked `g`) shown only inside `box` (x0, y0, x1, y1 mm, y
    up) grown by `margin_mm`, and made a jump elsewhere. White thread over a
    black bed IS a letter when it lies in the word's own box (MFab's pro);
    outside it, it is a border or a satin edge beside the word, which a
    reader looking at the word's crop was never asked to see (Fremont's pro
    white rope over its black ring, along the bottom of every small word)."""
    x0, y0, x1, y1 = (v * 10.0 for v in box)
    m = margin_mm * 10.0
    out = []
    for rec in design.get("stitches") or []:
        if rec.get("g") and not (x0 - m <= rec["x"] <= x1 + m and y0 - m <= rec["y"] <= y1 + m):
            rec = {**rec, "type": "jump"}
        out.append(rec)
    return {**design, "stitches": out}


def window_scaled(design: dict, box: tuple, s: float, margin_mm: float) -> dict:
    """The part of `design` within `margin_mm` of `box` (x0, y0, x1, y1 in mm,
    y UP, the Design's own frame), scaled by `s` about the box's centre. The
    filament is NOT scaled: that is the render's, at its real width. A stitch
    whose predecessor fell outside the window starts a fresh thread (a jump to
    itself), so no line is drawn across the window's edge. Colour records are
    kept so the colour index stays in step."""
    x0, y0, x1, y1 = (v * 10.0 for v in box)          # design units are 0.1 mm
    m = margin_mm * 10.0
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    out, gap = [], True
    for rec in design.get("stitches") or []:
        k = rec.get("type")
        if k == "color":
            out.append(rec)
            gap = True
            continue
        if k not in ("stitch", "jump"):
            gap = True
            continue
        inside = x0 - m <= rec["x"] <= x1 + m and y0 - m <= rec["y"] <= y1 + m
        if not inside or k == "jump":
            gap = True
            continue
        p = {"x": (rec["x"] - cx) * s + cx, "y": (rec["y"] - cy) * s + cy}
        if gap:
            out.append({**p, "type": "jump"})
            gap = False
        out.append({**p, "type": "stitch"})
    return {"stitches": out, "colors": design.get("colors") or [{"r": 0, "g": 0, "b": 0}]}


def render_word(design: dict, box: tuple, s: float, ground_rgb, ppm: float = RENDER_PPM,
                thread_mm: float | None = None, margin_mm: float | None = None,
                pad_frac: float = CROP_PAD_FRAC) -> np.ndarray | None:
    """BGR crop of the word's box (grown by `CROP_PAD_FRAC` of its height)
    from `design` with its height scaled by `s`; None when no thread falls in
    it. The stitches drawn are those within `margin_mm` of the box (default
    `WINDOW_FRAC` of its height and a mm: everything the crop can show)."""
    from digitizer_core import stitchviz
    thread_mm = stitchviz.THREAD_MM if thread_mm is None else thread_mm
    x0, y0, x1, y1 = box
    h = y1 - y0
    sub = window_scaled(design, box, s, WINDOW_FRAC * h + 1.0 if margin_mm is None else margin_mm)
    pad = pad_frac * h
    frame_pad = 2.0 + pad * s          # the render's own margin must hold the whole crop
    frame = stitchviz._frame(sub["stitches"], ppm, frame_pad)
    if frame is None:
        return None
    bgr = (int(ground_rgb[2]), int(ground_rgb[1]), int(ground_rgb[0]))
    img = stitchviz.render_design(sub, px_per_mm=ppm, fabric_bgr=bgr, pad_mm=frame_pad, thread_mm=thread_mm)
    _hw, to_px = frame
    cx, cy = (x0 + x1) / 2.0 * 10.0, (y0 + y1) / 2.0 * 10.0
    hw, hh = ((x1 - x0) / 2.0 + pad) * 10.0 * s, ((y1 - y0) / 2.0 + pad) * 10.0 * s
    ax, ay = to_px({"x": cx - hw, "y": cy + hh})
    bx, by = to_px({"x": cx + hw, "y": cy - hh})
    H, W = img.shape[:2]
    ax, bx = sorted((min(max(ax, 0), W), min(max(bx, 0), W)))
    ay, by = sorted((min(max(ay, 0), H), min(max(by, 0), H)))
    if bx - ax < 4 or by - ay < 4:
        return None
    return img[ay:by, ax:bx]


# --- locating a word in a file's own frame -----------------------------------

def colour_masks(design: dict, ground, px_per_mm: float, max_dist: float = 48.0, keep=None) -> list[np.ndarray]:
    """One thread mask per spool colour of `design` that is not the ground's
    own (blocks within `max_dist` RGB of one another are one spool): each is
    `glyph_read.thread_ink` of only those blocks, thresholded, on the render
    grid. A pro's DST carries no colours, so it is one mask. `keep` (per
    colour block, from `keep_visible_ground`) says which blocks show, in
    place of the colour test, so white thread sewn over black is a spool."""
    from digitizer_core.glyph_read import ink_blocks, thread_ink
    custom = keep is not None
    keep = ink_blocks(design, np.asarray(ground, float)) if keep is None else keep
    cols = design.get("colors") or [{"r": 0, "g": 0, "b": 0}]
    groups: list[tuple[np.ndarray, list[int]]] = []
    for i, c in enumerate(cols):
        if not keep[min(i, len(keep) - 1)]:
            continue
        v = np.array([c["r"], c["g"], c["b"]], float)
        for gv, members in groups:
            if np.linalg.norm(gv - v) <= max_dist:
                members.append(i)
                break
        else:
            groups.append((v, [i]))
    out = []
    for _gv, members in groups:
        ci, recs = 0, []
        for rec in design.get("stitches") or []:
            k = rec.get("type")
            if k == "color":
                ci += 1
            elif k == "stitch" and min(ci, len(cols) - 1) not in members:
                rec = {**rec, "type": "jump"}
            recs.append(rec)
        out.append(_flat_ink({**design, "stitches": recs}, len(keep), px_per_mm) if custom
                   else thread_ink({**design, "stitches": recs}, np.asarray(ground, float), px_per_mm)[0] >= 0.5)
    return out


def visible_masks(design: dict, keep, ground, px_per_mm: float, max_dist: float = 48.0) -> list[np.ndarray]:
    """One mask per spool colour of what is SEEN of it: the design drawn flat in
    its own colours on a cloth no thread is the colour of, and each spool's
    mask is the pixels that are thread of that colour. `colour_masks` draws a
    spool's stitches alone, so thread that is covered still counts: MFab's pro
    sews a black bed under the whole badge and white satin and black letters
    over it, and in the black spool's mask the letters are welded to the bed
    that no eye sees them welded to. Here the white satin is in the way, as it
    is in the picture."""
    from digitizer_core import stitchviz
    from digitizer_core.glyph_read import PAD_MM
    cols = design.get("colors") or [{"r": 0, "g": 0, "b": 0}]
    rgb = [np.array([c["r"], c["g"], c["b"]], float) for c in cols]
    groups: list[tuple[np.ndarray, list[int]]] = []
    for i, v in enumerate(rgb):
        if not keep[min(i, len(keep) - 1)]:
            continue
        for gv, members in groups:
            if np.linalg.norm(gv - v) <= max_dist:
                members.append(i)
                break
        else:
            groups.append((v, [i]))
    if not groups:
        return []
    cloth = max(((255, 0, 255), (0, 255, 0), (0, 255, 255), (255, 255, 0), (0, 0, 255)),
                key=lambda c: min(float(np.linalg.norm(np.array(c, float) - v)) for v in rgb))
    img = stitchviz.render_design(design, px_per_mm=px_per_mm, fabric_bgr=cloth[::-1], pad_mm=PAD_MM, lit=False)
    px = img[..., ::-1].astype(np.float32)
    covered = np.linalg.norm(px - np.array(cloth, np.float32), axis=2) > 60.0
    return [covered & (np.linalg.norm(px - gv.astype(np.float32), axis=2) <= max_dist) for gv, _m in groups]


def _flat_ink(design: dict, n_blocks: int, px_per_mm: float) -> np.ndarray:
    """`glyph_read.thread_ink`'s render of EVERY stitch the design has left
    (it filters blocks by colour, and here the caller already chose them):
    flat, black on white, thresholded, on the same grid."""
    from digitizer_core import stitchviz
    from digitizer_core.glyph_read import PAD_MM
    black = {"stitches": design["stitches"], "colors": [{"r": 0, "g": 0, "b": 0}] * max(1, n_blocks)}
    img = stitchviz.render_design(black, px_per_mm=px_per_mm, fabric_bgr=(255, 255, 255), pad_mm=PAD_MM, lit=False)
    return (1.0 - img.mean(axis=2) / 255.0) >= 0.5


FUSE_MM = (0.3, 0.45, 0.6, 0.8, 1.0, 1.3, 1.6, 2.0)   # letter-fusing dilations tried
SIZE_RATIO = (0.6, 2.0)         # a word's width, in the expected width, that is still "the word"
HEIGHT_RATIO = (0.5, 2.6)       # and its height
REACH_X, REACH_Y = 0.8, 1.5     # how far past the seed box (in its width / height) the word may sit
LOC_MAX_COST = 2.0              # a word whose best candidate costs more than this is not scored in that file
REACH_MM = 2.0                  # ... plus this


def shape_sim(cand: np.ndarray, art: np.ndarray, size: tuple = (96, 32)) -> float:
    """Correlation of two word masks once each is stretched to `size` and
    blurred: how alike the layout of ink is, whatever the stroke weight or the
    scale (the pro's letters are bolder and bigger than the art's). A strip of
    rope against a word of letters reads near 0; the word against its own art
    reads high. In [-1, 1]."""
    def prep(m):
        g = cv2.resize(m.astype(np.float32), size, interpolation=cv2.INTER_AREA)
        return cv2.GaussianBlur(g, (0, 0), 2.0)
    a, b = prep(cand), prep(art)
    a, b = a - a.mean(), b - b.mean()
    d = float(np.sqrt((a * a).sum() * (b * b).sum()))
    return 0.0 if d < 1e-9 else float((a * b).sum() / d)


PEEL_MM = 0.35          # a join thinner than twice this (a run of thread between a letter and a rope) is cut
RUN_GAP = 1.2           # letters of one word are at most this many word heights apart
INNER_GAP = 0.4         # a piece this close to a run, on its line, is part of it
RUN_DUST_MM = 0.25      # a piece smaller than this across is not a letter


def _pieces(win: np.ndarray, lab0: np.ndarray, big: list, box0: tuple, ew: float, eh: float, px_per_mm: float):
    """The letter-sized pieces of thread in a window: every connected piece of
    it that is not as big as a rope, and, from each piece that IS (a letter
    sewn to a rope by a thin run of thread, the pro's STAY and PLAY on
    Fremont), what is left of it after `PEEL_MM` of opening cuts the thin
    joins. -> [(x0, y0, x1, y1, mask)] in the window's own pixels."""
    wx0, wy0 = box0
    out = []

    def add(mask):
        n, lab, st, _c = cv2.connectedComponentsWithStats(mask.astype(np.uint8), connectivity=8)
        for k in range(1, n):
            x, y, w, h, a = (int(v) for v in st[k])
            if max(w, h) < RUN_DUST_MM * px_per_mm or w > SIZE_RATIO[1] * ew or h > HEIGHT_RATIO[1] * eh:
                continue
            out.append((x, y, x + w, y + h, (lab[y:y + h, x:x + w] == k)))

    add(win)
    r = max(1, int(round(PEEL_MM * px_per_mm)))
    ker = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))
    H, W = win.shape
    for k in big:
        comp = (lab0[wy0:wy0 + H, wx0:wx0 + W] == k).astype(np.uint8)
        if comp.sum() < 4:
            continue
        core = cv2.morphologyEx(comp, cv2.MORPH_OPEN, ker)
        if not core.any():
            continue
        n, lab = cv2.connectedComponents(core)
        for j in range(1, n):
            piece = cv2.dilate((lab == j).astype(np.uint8), ker) & comp         # the letter, its edge given back
            add(piece.astype(bool))
    return out


def _run_candidates(pieces, ew: float, eh: float, px_per_mm: float):
    """Every run of consecutive pieces along a line (by x, each within
    `RUN_GAP` word heights of the last and sharing its height) whose size is
    plausible for the word: what a word IS, a few letters side by side,
    without asking how far a dilation must grow to weld them. A fused piece
    cannot tell a word from the word and the mark beside it (ProSeal's
    SPRAY FOAM, then the + that is as far from FOAM as FOAM's own space);
    a run can end where the word does. A run that leaves out a piece within
    `INNER_GAP` of itself on its own line is part of a longer run and is not a
    candidate (AT is not EAT). -> [(x0, y0, x1, y1, [piece, ...])]."""
    order = sorted(pieces, key=lambda t: t[0])
    gap = max(RUN_GAP * eh, 2.5 * px_per_mm)
    inner = max(INNER_GAP * eh, 0.8 * px_per_mm)

    def closed(box, run):
        bx0, by0, bx1, by1 = box
        for a in order:
            if any(a is r for r in run):
                continue
            if min(by1, a[3]) - max(by0, a[1]) < 0.4 * min(by1 - by0, a[3] - a[1]):
                continue
            if max(a[0] - bx1, bx0 - a[2]) <= inner:
                return False
        return True

    def plausible(x0, y0, x1, y1):
        return SIZE_RATIO[0] <= (x1 - x0) / ew and HEIGHT_RATIO[0] <= (y1 - y0) / eh <= HEIGHT_RATIO[1]

    out = []
    for i in range(len(order)):
        x0, y0, x1, y1 = order[i][:4]
        run = [order[i]]
        if plausible(x0, y0, x1, y1) and closed((x0, y0, x1, y1), run):
            out.append((x0, y0, x1, y1, list(run)))
        for j in range(i + 1, len(order)):
            a = order[j]
            if a[0] - x1 > gap:
                break
            if min(y1, a[3]) - max(y0, a[1]) < 0.4 * min(y1 - y0, a[3] - a[1]):
                continue
            x0, y0, x1, y1 = min(x0, a[0]), min(y0, a[1]), max(x1, a[2]), max(y1, a[3])
            if x1 - x0 > SIZE_RATIO[1] * ew:
                break
            run.append(a)
            if plausible(x0, y0, x1, y1) and closed((x0, y0, x1, y1), run):
                out.append((x0, y0, x1, y1, list(run)))
    return out


SIZE_WEIGHT = 0.25      # the pro re-sets small words 2-2.5x bigger (the small-text floor): size is a hint, not a charge


def _place_cost(bw, bh, cx, cy, ew, eh, ecx, ecy) -> float:
    """What a candidate piece costs for not being where and what the art's
    word is: |ln| of its aspect ratio against the art's, `SIZE_WEIGHT` of the
    |ln| of its scale (the geometric mean of its width and height ratios),
    and its centre's distance from the art's in word widths (y at half)."""
    return (abs(math.log((bw / bh) / (ew / eh)))
            + SIZE_WEIGHT * abs(0.5 * (math.log(bw / ew) + math.log(bh / eh)))
            + math.hypot(cx - ecx, (cy - ecy) * 0.5) / ew)


def find_word(masks: list[np.ndarray], exp_box: tuple, px_per_mm: float, art_word: np.ndarray | None = None,
              trace: list | None = None, runs: bool = True):
    """The word's own thread, found in the file. `exp_box` (u0, v0, u1, v1 in
    grid px) is where the artwork says the word should be, and it is only a
    SEED: the pro sews EST, 1895 and EAT STAY PLAY bigger, bolder and a few
    millimetres off the art, so a box taken from the art would cut them or
    miss them. In every spool colour's thread the letters are fused by a
    growing dilation (`FUSE_MM`), and every fused piece within reach of the
    seed whose size is plausible for the word (`SIZE_RATIO`, `HEIGHT_RATIO`)
    is a candidate; the word is the candidate whose shape and place are
    nearest the art's (`_place_cost`, plus 1.5 x (1 - `shape_sim` to the art's
    own word mask)), and its
    box is the bounding box of its own thread. `runs` adds a second kind of
    candidate beside the fused pieces: every run of consecutive letter pieces
    (`_run_candidates`), with the thin joins that weld a letter to a rope cut
    first (`_pieces`), costed the same way.
    -> (box, note, cost): the box in grid px and the winning cost, or
    (None, why, None)."""
    u0, v0, u1, v1 = (float(v) for v in exp_box)
    ew, eh = max(1.0, u1 - u0), max(1.0, v1 - v0)
    ecx, ecy = (u0 + u1) / 2.0, (v0 + v1) / 2.0
    rx, ry = REACH_X * ew + REACH_MM * px_per_mm, REACH_Y * eh + REACH_MM * px_per_mm
    best, best_cost, seen = None, 1e9, False
    for m in masks:
        H, W = m.shape
        wx0, wy0 = int(max(0, u0 - rx)), int(max(0, v0 - ry))
        wx1, wy1 = int(min(W, u1 + rx)), int(min(H, v1 + ry))
        win = m[wy0:wy1, wx0:wx1]
        if win.sum() < 4:
            continue
        seen = True
        # a piece of thread as big as a rope, a rule or a border is not a letter, and a
        # letter may sit a hair from one: drop those BEFORE the letters are fused, or the
        # fusing welds the word to its frame
        n0, lab0, st0, _c = cv2.connectedComponentsWithStats(m.astype(np.uint8), connectivity=8)
        big = [k for k in range(1, n0) if st0[k, cv2.CC_STAT_WIDTH] > SIZE_RATIO[1] * ew
               or st0[k, cv2.CC_STAT_HEIGHT] > HEIGHT_RATIO[1] * eh]
        if big:
            win = win & ~np.isin(lab0[wy0:wy1, wx0:wx1], big)
            if win.sum() < 4 and not runs:      # (with runs, a word sewn INTO a rope is peeled out of it below)
                continue
        for fuse in FUSE_MM:
            r = max(1, int(round(fuse * px_per_mm)))
            dil = cv2.dilate(win.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1)))
            n, lab = cv2.connectedComponents(dil)
            for k in range(1, n):
                ys, xs = np.where((lab == k) & win)
                if not len(xs):
                    continue
                bw, bh = int(xs.max() - xs.min() + 1), int(ys.max() - ys.min() + 1)
                if not (SIZE_RATIO[0] <= bw / ew <= SIZE_RATIO[1] and HEIGHT_RATIO[0] <= bh / eh <= HEIGHT_RATIO[1]):
                    continue
                cx, cy = wx0 + (xs.min() + xs.max()) / 2.0, wy0 + (ys.min() + ys.max()) / 2.0
                cost = _place_cost(bw, bh, cx, cy, ew, eh, ecx, ecy)
                if art_word is not None:
                    cost += 1.5 * (1.0 - shape_sim(win[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
                                                   & (lab[ys.min():ys.max() + 1, xs.min():xs.max() + 1] == k),
                                                   art_word))
                if trace is not None:
                    trace.append((round(cost, 2), fuse, wx0 + int(xs.min()), wy0 + int(ys.min()), bw, bh))
                if cost < best_cost:
                    best_cost = cost
                    best = (wx0 + int(xs.min()), wy0 + int(ys.min()), wx0 + int(xs.max()) + 1, wy0 + int(ys.max()) + 1)
        if not runs:
            continue
        for rx0, ry0, rx1, ry1, run in _run_candidates(_pieces(m[wy0:wy1, wx0:wx1], lab0, big, (wx0, wy0), ew, eh, px_per_mm),
                                                       ew, eh, px_per_mm):
            bw, bh = rx1 - rx0, ry1 - ry0
            cx, cy = wx0 + (rx0 + rx1) / 2.0, wy0 + (ry0 + ry1) / 2.0
            cost = _place_cost(bw, bh, cx, cy, ew, eh, ecx, ecy)
            if cost >= best_cost:
                continue
            if art_word is not None:
                canvas = np.zeros((bh, bw), bool)
                for px0, py0, px1, py1, pm in run:
                    canvas[py0 - ry0:py1 - ry0, px0 - rx0:px1 - rx0] |= pm
                cost += 1.5 * (1.0 - shape_sim(canvas, art_word))
            if trace is not None:
                trace.append((round(cost, 2), "run", wx0 + rx0, wy0 + ry0, bw, bh))
            if cost < best_cost:
                best_cost = cost
                best = (wx0 + rx0, wy0 + ry0, wx0 + rx1, wy0 + ry1)
    if best is None:
        return None, ("no word-sized thread near the word" if seen else "no thread near the word"), None
    return best, "", round(best_cost, 2)


def art_crop(rgb: np.ndarray, tight: tuple, pad_frac: float = CROP_PAD_FRAC) -> np.ndarray:
    """BGR crop of the artwork's word box `tight` (x0, y0, x1, y1 px), grown
    by `pad_frac` of its height as `render_word` grows the thread's."""
    pad = pad_frac * (tight[3] - tight[1])
    ax0, ay0 = int(max(0, tight[0] - pad)), int(max(0, tight[1] - pad))
    ax1, ay1 = int(tight[2] + pad), int(tight[3] + pad)
    return cv2.cvtColor(np.clip(rgb[ay0:ay1, ax0:ax1], 0, 255).astype(np.uint8), cv2.COLOR_RGB2BGR)


ACCEPT_SIM = 0.5         # a registered window whose thread looks this much like the art's own word is the word
SURE_COST = 1.5          # ... and it beats a found piece of thread that costs more than this (a wrong piece costs 1.8-2.0;
                         # the pro's re-set small words cost 1.2-1.5 and look NOTHING like the art's window: sim <= 0.5)


def appearance_sim(a: np.ndarray, b: np.ndarray, size: tuple = (96, 32)) -> float:
    """Correlation of two BGR crops' greys once each is stretched to `size`
    and blurred, signed (a word drawn dark on light against its own negative
    is NOT the word). The crops are of the same word at the same place:
    artwork and thread, cut by the same rule (`CROP_PAD_FRAC` of the word's
    height round it)."""
    def prep(img):
        g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img
        return cv2.GaussianBlur(cv2.resize(g.astype(np.float32), size, interpolation=cv2.INTER_AREA), (0, 0), 1.5)
    x, y = prep(a), prep(b)
    x, y = x - x.mean(), y - y.mean()
    d = float(np.sqrt((x * x).sum() * (y * y).sum()))
    return 0.0 if d < 1e-9 else float((x * y).sum() / d)


# --- the OCR step ---------------------------------------------------------------

def read_crop(img: np.ndarray, px_per_mm: float) -> tuple[str, float]:
    """Tesseract on one word crop: psm 7 (a single line), the repo's three
    preprocessing variants, the most confident reading. The truth is not
    consulted."""
    from digitizer_core import legibility as core
    best = ("", -1.0)
    for blur_mm, thin_mm in core.VARIANTS_MM:
        txt, conf = core.ocr(img, 7, blur_mm * px_per_mm, thin_mm * px_per_mm)
        if norm(txt) and conf > best[1]:
            best = (txt, conf)
    return best[0], round(max(best[1], 0.0), 1)


# --- the OCR step, batched ---------------------------------------------------------

BATCH_WORKERS = 4        # tesseract processes read in parallel
BATCH_MIN = 8            # fewest images worth a process of their own


def _tsv_reads(tsv: str, n: int) -> list[tuple[str, float]]:
    """`n` readings from the TSV of one list-of-images tesseract run: per page
    the words joined by a space and their mean confidence, exactly as
    `legibility.ocr` takes them from `image_to_data` (a page with no word is
    ("", 0.0)). Every page has a row of its own (level 1) whether or not it
    has a word, so the pages are counted, and a run that did not read all `n`
    (an image tesseract could not open, a version that numbers its pages
    another way) raises ValueError rather than hand a reading to the wrong
    crop."""
    words: dict[int, list[tuple[str, float]]] = {}
    pages: set[int] = set()
    for line in tsv.splitlines()[1:]:
        p = line.split("\t")
        if len(p) < 11:
            continue
        try:
            page = int(p[1])
        except ValueError:
            continue
        pages.add(page)
        if p[0] != "5" or len(p) < 12:
            continue
        try:
            conf = int(float(p[10]))                  # pytesseract hands `legibility.ocr` whole numbers
        except ValueError:
            continue
        if p[11].strip() and conf >= 0:
            words.setdefault(page, []).append((p[11], conf))
    if len(pages) != n:
        raise ValueError(f"tesseract returned {len(pages)} pages for {n} images")
    out = []
    for page in sorted(pages):
        w = words.get(page, [])
        out.append((" ".join(t for t, _c in w).strip(), sum(c for _t, c in w) / len(w) if w else 0.0))
    return out


def _tesseract_list(paths: list[Path], work: Path, tag: str) -> list[tuple[str, float]] | None:
    """One tesseract process over `paths` (its list-of-images input: the 5 s
    this laptop spends starting tesseract, and a CI box's 0.2 s, are paid once
    per batch instead of once per crop), psm 7 as `read_crop`, one thread (the
    parallelism is the batches). None when it fails, so the caller can read
    one by one."""
    import subprocess
    lst, base = work / f"{tag}.txt", work / tag
    lst.write_text("\n".join(str(p) for p in paths) + "\n", encoding="utf-8")
    env = {**os.environ, "OMP_THREAD_LIMIT": "1"}
    try:
        subprocess.run([shutil.which("tesseract"), str(lst), str(base), "--psm", "7", "tsv"], env=env,
                       capture_output=True, check=True, timeout=1800)
        return _tsv_reads((work / f"{tag}.tsv").read_text(encoding="utf-8"), len(paths))
    except (OSError, subprocess.SubprocessError, ValueError):
        return None


def read_crops(items: list[tuple[np.ndarray, float]], workers: int = BATCH_WORKERS) -> list[tuple[str, float]]:
    """`read_crop` over many (crop, px per mm) pairs, the same readings from
    far fewer tesseract starts: every crop's preprocessing variants are
    written out and read in a few parallel list-of-images runs, and each crop
    keeps its most confident reading as `read_crop` does. A run that fails
    falls back to `read_crop` for the crops it held."""
    if not items:
        return []
    import tempfile
    from concurrent.futures import ThreadPoolExecutor
    from digitizer_core import legibility as core
    variants = core.VARIANTS_MM
    with tempfile.TemporaryDirectory(prefix="wl_ocr_") as tmp:
        work = Path(tmp)
        paths = []
        for i, (img, ppm) in enumerate(items):
            for j, (blur_mm, thin_mm) in enumerate(variants):
                p = work / f"c{i:05d}_{j}.png"
                cv2.imwrite(str(p), core.prepare_for_ocr(img, blur_mm * ppm, thin_mm * ppm))
                paths.append(p)
        per = max(BATCH_MIN, -(-len(paths) // max(1, workers)))
        chunks = [paths[k:k + per] for k in range(0, len(paths), per)]
        with ThreadPoolExecutor(max_workers=max(1, min(workers, len(chunks)))) as ex:
            got = list(ex.map(lambda a: _tesseract_list(a[1], work, f"b{a[0]}"), enumerate(chunks)))
        reads: list[tuple[str, float] | None] = []
        for chunk, r in zip(chunks, got):
            reads.extend(r if r is not None else [None] * len(chunk))
    out = []
    for i, (img, ppm) in enumerate(items):
        rs = reads[i * len(variants):(i + 1) * len(variants)]
        if any(r is None for r in rs):
            out.append(read_crop(img, ppm))
            continue
        best = ("", -1.0)
        for txt, conf in rs:
            if norm(txt) and conf > best[1]:
                best = (txt, conf)
        out.append((best[0], round(max(best[1], 0.0), 1)))
    return out


# --- the finer number: how far away the word can be seen and still be read --------

LADDER_STEP = 2 ** -0.5     # each rung shows the word this much smaller: two rungs to the octave
LADDER_FLOOR_PX = 3.0       # the last rung: a word this many px tall is a smear, read or not


def ladder_heights(h_px: float, floor: float = LADDER_FLOOR_PX) -> list[float]:
    """The heights (px) a word `h_px` tall is shown at below its own:
    `LADDER_STEP` apart, then the floor. Empty when the word is not above it."""
    out, x = [], h_px * LADDER_STEP
    while x > floor * 1.05:
        out.append(round(x, 2))
        x *= LADDER_STEP
    return out + [floor] if h_px > floor * 1.05 else []


def shrink_crop(img: np.ndarray, f: float) -> np.ndarray:
    """`img` seen from 1/f times as far: area-averaged down to `f` of its size,
    so the thread texture averages away as it does to an eye and the reader's
    own upscale supplies the blur."""
    h, w = img.shape[:2]
    return cv2.resize(img, (max(1, int(round(w * f))), max(1, int(round(h * f)))), interpolation=cv2.INTER_AREA)


def reach_octaves(curve: list[tuple[float, float]]) -> float | None:
    """The area under a word's chance-corrected reading, `cc` (below 0 counts
    0), against the log of the height it is shown at, in OCTAVES: `curve` is
    [(height px, cc), ...] from the word's native height down to the ladder's
    floor, trapezoid between its points. A word read perfectly from native
    down to the floor earns log2(native / floor); one that stops reading at
    half its native height earns 1; a word that is not read at native earns 0
    (it is the number of times the word can be halved in size, i.e. the
    distance doubled, and still be read).
    It moves with every level a word survives, and with a half-read level
    (that is why it does not saturate where `cc` does), and it is built from
    `cc` alone, so it carries the chance correction. None when any `cc` is
    undefined (a one-letter word)."""
    if not curve or any(cc is None for _h, cc in curve):
        return None
    pts = sorted(((math.log2(h), max(cc, 0.0)) for h, cc in curve), reverse=True)
    if len(pts) == 1:
        return 0.0
    return round(sum((a[0] - b[0]) * (a[1] + b[1]) / 2.0 for a, b in zip(pts, pts[1:])), 3)


def floor_px(curve: list[tuple[float, float]], at: float = 0.5) -> float | None:
    """The smallest height (px) the word is still read at: walking down
    `curve` from native, where `cc` first drops below `at`, interpolated in
    log height between the last level at or above it and the first below. The
    lowest height tried (the ladder's floor) when it never drops, None when it
    is below `at` already at native or `cc` is undefined."""
    if not curve or any(cc is None for _h, cc in curve):
        return None
    pts = sorted(curve, reverse=True)
    if pts[0][1] < at:
        return None
    for (h0, c0), (h1, c1) in zip(pts, pts[1:]):
        if c1 < at:
            t = (c0 - at) / max(c0 - c1, 1e-9)
            return round(math.exp(math.log(h0) + t * (math.log(h1) - math.log(h0))), 1)
    return round(pts[-1][0], 1)


# --- one job ---------------------------------------------------------------------

def _ink_frac_box(sb, f):
    return (sb[0] + f[0] * (sb[2] - sb[0]), sb[1] + f[1] * (sb[3] - sb[1]),
            sb[0] + f[2] * (sb[2] - sb[0]), sb[1] + f[3] * (sb[3] - sb[1]))


def exact_registration(sb, width_mm: float, dx0: float, dy1: float):
    """The artwork -> OUR thread grid, with no search. Stage 4 draws the
    plan about the centre of the artwork's ink box, at `width_mm` across it
    (`plan_to_design` only flips y), so the ink box maps onto the design
    around (0, 0) and the grid's frame is `thread_ink`'s (`dx0`, `dy1`). A
    fitted registration of a 146 px logo to our own thread was wrong by half
    a line of Becker's lettering; the pro's file has no such frame and is
    still fitted."""
    from digitizer_core.glyph_read import P, PAD_MM, Registration
    s = width_mm / (sb[2] - sb[0])
    cx, cy = (sb[0] + sb[2]) / 2.0, (sb[1] + sb[3]) / 2.0
    return Registration(ax=P * s, ay=P * s, tx=P * (-cx * s - dx0 + PAD_MM),
                        ty=P * (dy1 + PAD_MM - cy * s), score=1.0)


def _read_ladders(pending, art_pending, ceilings) -> None:
    """Show every NATIVE crop (ours', the pro's and the art's) at each rung of
    its `ladder_heights`, read all the rungs in one batch, and put `ladder`
    [[height px, cc], ...], `reach` (octaves) and `floor_px` on each row (on
    `art_ceiling[text]` for the art). A word is shrunk from its own native
    height, so a word that is small to begin with has fewer rungs to lose:
    that is the size part of how far away a word can be read."""
    jobs = []        # (target, text, native height px, native cc, crop, px/mm)
    for row, img, ppm, text in pending:
        if row.get("size") == "native":
            jobs.append((row, text, float(row["height_mm"]) * ppm, row.get("cc"), img, ppm))
    for text, img, ppm, h_px in art_pending:
        if text in ceilings:
            jobs.append((ceilings[text], text, h_px, ceilings[text].get("cc"), img, ppm))
    items, spans = [], []
    for _t, _text, h_px, _cc, img, ppm in jobs:
        rungs = ladder_heights(h_px)
        spans.append((len(items), rungs))
        items += [(shrink_crop(img, h / h_px), ppm * h / h_px) for h in rungs]
    reads = read_crops(items)
    for (target, text, h_px, cc0, _img, _ppm), (a, rungs) in zip(jobs, spans):
        if not rungs:
            continue
        curve = [(round(h_px, 1), cc0)] + [(h, chance_corrected(t, text)["cc"])
                                         for h, (t, _c) in zip(rungs, reads[a:a + len(rungs)])]
        target.update(ladder=[[h, cc] for h, cc in curve], reach=reach_octaves(curve), floor_px=floor_px(curve))


def locate_overlay(design: dict, ground, boxes) -> np.ndarray:
    """The whole file drawn at the grid's scale with where the artwork says
    each word is (blue, `reg.apply_box` of its art box) and where it was found
    (green; dashed-short in red when the best candidate was refused)."""
    from digitizer_core import stitchviz
    from digitizer_core.glyph_read import P, PAD_MM
    img = stitchviz.render_design(design, px_per_mm=P, fabric_bgr=(int(ground[2]), int(ground[1]), int(ground[0])),
                                  pad_mm=PAD_MM)
    for text, g, f in boxes:
        cv2.rectangle(img, (int(g[0]), int(g[1])), (int(g[2]), int(g[3])), (255, 0, 0), 2)
        if f is not None:
            cv2.rectangle(img, (int(f[0]), int(f[1])), (int(f[2]), int(f[3])), (0, 200, 0), 2)
        cv2.putText(img, text, (int(g[0]), max(12, int(g[1]) - 4)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
    return img


def read_job(job: str, ours: dict, pro: dict, words: list[dict], rgb: np.ndarray, alpha: np.ndarray,
             use_ocr: bool = True, dump: Path | None = None, heights=HEIGHTS_MM,
             ours_width_mm: float | None = None, ladder: bool = True) -> dict:
    """Score every pinned word of `job` in both designs. `ours_width_mm`: the
    width OUR design was digitized at; with it our file is registered exactly
    (`exact_registration`), without it by the same fit as the pro's. `ladder`:
    also shrink each word's NATIVE crop down `ladder_heights` and read it at
    every level (the row's `reach`, `floor_px` and `ladder`, and the art's own
    in `art_ceiling`). -> the job's rows, per file and height, and its figures."""
    from digitizer_core.glyph_read import P, PAD_MM, _bbox, ground_colour, soft_ink, thread_ink
    from tools.glyph_legibility import register
    G = ground_colour(rgb, alpha)
    soft_all, _ = soft_ink(rgb, alpha, G)
    sb = _bbox(soft_all)
    ocr_ok = use_ocr and tesseract_available()
    rows: list[dict] = []
    ceilings: dict[str, dict] = {}
    pending: list[tuple[dict, list, float, str]] = []            # (row, [wide, tight] crops, px/mm, text): read in ONE batch below
    art_pending: list[tuple[str, np.ndarray, float, float]] = []  # (text, art crop, px/mm, word height px)
    for fname, design in (("ours", ours), ("pro", pro)):
        design = drop_travel(design)
        thread, (dx0, dy1) = thread_ink(design, G, P)
        design, keep = keep_visible_ground(design, G, P)
        seen_boxes: list[tuple[str, tuple, tuple | None]] = []     # (text, where the art says, where it was found)
        seen_masks = None                                           # `visible_masks`, drawn when a word needs them
        reg = (exact_registration(sb, ours_width_mm, dx0, dy1) if fname == "ours" and ours_width_mm
               else register(soft_all, thread))
        masks = colour_masks(design, G, P, keep=keep)
        for wd in words:
            text = wd["text"]
            bx = _ink_frac_box(sb, wd["box"])
            x0, y0, x1, y1 = (int(v) for v in bx)
            sub = soft_all[max(0, y0):y1, max(0, x0):x1] >= 0.5
            ys, xs = np.where(sub)
            row = {"file": fname, "text": text, "located": False}
            if not len(xs):
                rows.append({**row, "note": "no ink in the pinned box"})
                continue
            tight = (x0 + xs.min(), y0 + ys.min(), x0 + xs.max() + 1, y0 + ys.max() + 1)
            gbox = reg.apply_box(*tight)
            art_bgr = art_crop(rgb, tight)
            if fname == "ours" and ocr_ok:       # the artwork's own crop: the reader's ceiling
                art_pending.append((text, art_bgr, P / max(reg.a, 1e-6), float(tight[3] - tight[1])))

            def to_mm(b):
                """grid px -> the Design's mm (y up): the inverse of `thread_ink`'s frame"""
                return (b[0] / P + dx0 - PAD_MM, dy1 + PAD_MM - b[3] / P, b[2] / P + dx0 - PAD_MM, dy1 + PAD_MM - b[1] / P)
            art_word = sub[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
            box_px, why, cost = find_word(masks, gbox, P, art_word)
            how = "thread"
            if box_px is None or cost > LOC_MAX_COST:
                # the thread is there but welded to what lies UNDER the lettering (a bed, a border): look at what shows
                if seen_masks is None:
                    seen_masks = visible_masks(design, keep, G, P)
                b2, why2, c2 = find_word(seen_masks, gbox, P, art_word)
                if b2 is not None and (box_px is None or c2 < cost):
                    box_px, why, cost, how = b2, why2, c2, "visible"
            # the art's box against the thread in the same box, neither padded: what the neighbours
            # put in a crop's margin is not what is being compared
            reg_img = render_word(ground_in_box(design, to_mm(gbox)), to_mm(gbox), 1.0, G, pad_frac=0.0,
                                  margin_mm=CROP_NEIGHBOUR_MM)
            reg_sim = None if reg_img is None else round(appearance_sim(art_crop(rgb, tight, 0.0), reg_img), 2)
            found = box_px if box_px is not None and cost <= LOC_MAX_COST else None
            if box_px is None or cost > LOC_MAX_COST or (cost > SURE_COST and reg_sim is not None and reg_sim >= ACCEPT_SIM):
                if reg_sim is not None and reg_sim >= ACCEPT_SIM:
                    # no piece of thread is clearly the word (white letters welded into a black bed by a
                    # keyline a filament wide), but the thread where the artwork put it LOOKS like the
                    # artwork's word: read it there, and say so
                    box_px, cost, how = tuple(int(round(v)) for v in gbox), round(1.0 - reg_sim, 2), "registered"
                    found = box_px
                elif box_px is None:
                    seen_boxes.append((text, gbox, None))
                    rows.append({**row, "note": why, "reg_sim": reg_sim})
                    continue
                else:
                    seen_boxes.append((text, gbox, box_px))
                    # the thread found is not clearly this word: reading it would score the locator,
                    # not the lettering, so the word is NOT scored in this file (n is reported)
                    rows.append({**row, "loc_cost": cost, "reg_sim": reg_sim,
                                 "note": f"not located: best match costs {cost} (> {LOC_MAX_COST})"})
                    continue
            seen_boxes.append((text, gbox, found))
            box_mm = to_mm(box_px)
            h_mm = box_mm[3] - box_mm[1]
            shown = ground_in_box(design, box_mm, 0.05 * h_mm)
            near = CROP_NEIGHBOUR_MM
            row.update(located=True, loc=how, loc_cost=cost, reg_sim=reg_sim, height_mm=round(h_mm, 2),
                       width_mm=round(box_mm[2] - box_mm[0], 2),
                       expected_mm=[round((gbox[2] - gbox[0]) / P, 2), round((gbox[3] - gbox[1]) / P, 2)])
            sizes = [("native", 1.0)] + [(f"{h:g}mm", h / h_mm) for h in heights]
            for label, s in sizes:
                r = {**row, "size": label}
                if s > 1.0 + 1e-6:
                    # a stitch layout scaled UP keeps its row pitch and opens gaps no engine would sew
                    rows.append({**r, "read": None, "note": f"skipped: the word is {h_mm:.1f} mm, enlarging invents gaps"})
                    continue
                img = render_word(shown, box_mm, s, G)                     # the wide view: every neighbour in reach
                if img is None:
                    rows.append({**r, "read": "", "conf": 0.0, **chance_corrected("", text), "note": "no thread"})
                    continue
                if not ocr_ok:
                    rows.append({**r, "read": None})
                    if dump is not None:
                        dump.mkdir(parents=True, exist_ok=True)
                        cv2.imwrite(str(dump / f"{job}_{fname}_{norm(text)}_{label}.png"), img)
                    continue
                tight = render_word(shown, box_mm, s, G, margin_mm=near)    # the tight view: the word's own thread
                rows.append({**r})
                pending.append((rows[-1], [img] + ([tight] if tight is not None else []), RENDER_PPM, text))
        if dump is not None:
            dump.mkdir(parents=True, exist_ok=True)
            cv2.imwrite(str(dump / f"{job}_{fname}_located.png"), locate_overlay(design, G, seen_boxes))
    out = {"job": job, "ocr": "ok" if ocr_ok else "OCR UNAVAILABLE", "rows": rows, "art_ceiling": ceilings,
           "figures": {}, "blind": {}}
    if ocr_ok:
        flat = [(im, ppm) for _r, ims, ppm, _t in pending for im in ims]
        reads = read_crops(flat + [(b, a_ppm) for _t, b, a_ppm, _h in art_pending])
        k, chosen = 0, []
        for row, ims, ppm, text in pending:
            got = reads[k:k + len(ims)]
            k += len(ims)
            # the most confident reading of the views wins, chosen WITHOUT looking at the truth (as the
            # preprocessing variants are); the wide view on a tie, which is the crop every earlier number used
            best = max(range(len(ims)), key=lambda i: (bool(norm(got[i][0])), got[i][1], -i))
            txt, conf = got[best]
            row.update(read=norm(txt), conf=conf, view=("wide", "tight")[best], **chance_corrected(txt, text))
            chosen.append((row, ims[best], ppm, text))
            if dump is not None:
                dump.mkdir(parents=True, exist_ok=True)
                cv2.imwrite(str(dump / f"{job}_{row['file']}_{norm(text)}_{row['size']}.png"), ims[best])
        for (text, _b, _p, _h), (txt, conf) in zip(art_pending, reads[k:]):
            ceilings[text] = {"read": norm(txt), "conf": conf, **chance_corrected(txt, text)}
        if ladder:
            _read_ladders(chosen, art_pending, ceilings)
        out["blind"] = blind_words(rows, ceilings)
        for label in ["native"] + [f"{h:g}mm" for h in heights]:
            by = {f: {r["text"]: r for r in rows if r["file"] == f and r.get("size") == label and "cc" in r}
                  for f in ("ours", "pro")}
            common = set(by["ours"]) & set(by["pro"])
            for f in ("ours", "pro"):
                out["figures"][f"{f}/{label}"] = job_figure(list(by[f].values()))
                out["figures"][f"{f}/{label}/both"] = job_figure([by[f][t] for t in by[f] if t in common])
    return out


# --- the digitize stage ---------------------------------------------------------

def digitize_job(job: str, cache: Path) -> Path:
    from digitizer_core.glyph_read import _bbox, ground_colour, soft_ink, source_from_prep, word_boxes
    from tools import pro_pair
    spec = JOBS[job]
    art, pro = resolve(spec["art"]), resolve(spec["pro"])
    width = pro_width_mm(pro)
    d = pro_pair.digitize(art, width, spec["garment"])
    p = d.gen.p
    rgb, alpha = source_from_prep(p)
    G = ground_colour(rgb, alpha)
    sb = _bbox(soft_ink(rgb, alpha, G)[0])
    x0, y0, x1, y1 = p.art_bbox
    cx, cy, ppm = (x0 + x1) / 2.0, (y0 + y1) / 2.0, float(p.px_per_mm)
    proposed = []
    for key, members, (bx0, by0, bx1, by1), _keeps in word_boxes(d.result.regions, d.cfg):
        px = (bx0 * ppm + cx, by0 * ppm + cy, bx1 * ppm + cx, by1 * ppm + cy)
        frac = [(px[0] - sb[0]) / (sb[2] - sb[0]), (px[1] - sb[1]) / (sb[3] - sb[1]),
                (px[2] - sb[0]) / (sb[2] - sb[0]), (px[3] - sb[1]) / (sb[3] - sb[1])]
        proposed.append({"key": key, "members": len(members), "box": [round(v, 4) for v in frac]})
    cache.mkdir(parents=True, exist_ok=True)
    dest = cache / f"ours_{job}.json"
    dest.write_text(json.dumps({"job": job, "width_mm": width, "garment": spec["garment"],
                                "stitches": d.plan.stats.stitch_count, "trims": d.plan.stats.trims,
                                "design": d.design, "proposed_words": proposed}), encoding="utf-8")
    return dest


def propose(job: str, cache: Path, out_png: Path) -> None:
    from tools.glyph_legibility import load_source
    from digitizer_core.glyph_read import _bbox, ground_colour, soft_ink
    data = json.loads((cache / f"ours_{job}.json").read_text(encoding="utf-8"))
    rgb, alpha = load_source(resolve(JOBS[job]["art"]))
    G = ground_colour(rgb, alpha)
    sb = _bbox(soft_ink(rgb, alpha, G)[0])
    img = cv2.cvtColor(np.clip(rgb, 0, 255).astype(np.uint8), cv2.COLOR_RGB2BGR)
    for i, w in enumerate(data["proposed_words"]):
        b = _ink_frac_box(sb, w["box"])
        cv2.rectangle(img, (int(b[0]), int(b[1])), (int(b[2]), int(b[3])), (0, 0, 255), 2)
        cv2.putText(img, str(i), (int(b[0]) + 3, int(b[1]) + 18), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)
        print(f"{i:3d}  {w['key']:>18}  members {w['members']:3d}  box {w['box']}")
    out_png.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out_png), img)
    print("wrote", out_png)


def load_pro_design(path: Path) -> dict:
    from tools.glyph_legibility import design_from_pes
    return design_from_pes(path)


def table(res: dict) -> str:
    lines = [f"{res['job']}  (ocr: {res['ocr']})"]
    sizes = ["native"] + [f"{h:g}mm" for h in HEIGHTS_MM]
    lines.append(f"  {'word':22} {'art':>5} " + "".join(f" | {s:^17}" for s in sizes))
    lines.append(f"  {'':22} {'cc':>5} " + "".join(f" | {'ours':>8}{'pro':>9}" for _ in sizes) + "   cc, raw in ()")
    texts = []
    for r in res["rows"]:
        if r["text"] not in texts:
            texts.append(r["text"])

    def cell(file, text, size):
        for r in res["rows"]:
            if r["file"] == file and r["text"] == text and r.get("size") == size:
                if r.get("read") is None:
                    return "skip" if str(r.get("note", "")).startswith("skipped") else "-"
                cc = "n/a" if r.get("cc") is None else f"{r['cc']:+.2f}"
                return f"{cc}({r['raw']:.2f})"
        return "n/loc" if any(r["file"] == file and r["text"] == text and "size" not in r for r in res["rows"]) else "?"
    for t in texts:
        c = res["art_ceiling"].get(t)
        cc = "-" if not c or c.get("cc") is None else f"{c['cc']:+.2f}"
        lines.append(f"  {t[:22]:22} {cc:>5} " + "".join(
            f" | {cell('ours', t, s):>8}{cell('pro', t, s):>9}" for s in sizes))
    if any("reach" in r for r in res["rows"]) or any("reach" in c for c in res["art_ceiling"].values()):
        lines.append("")
        lines.append("  FINER, at the size sewn: reach in octaves / the smallest height (px, 20 px/mm render) it is still "
                     "read at (cc >= 0.5); 'r' = read where the art put it, not on a found piece of thread")
        lines.append(f"  {'word':22} {'art':>10} {'ours':>12} {'pro':>12}")

        def fine(file, text):
            r = next((r for r in res["rows"] if r["file"] == file and r["text"] == text and r.get("size") == "native"), None)
            if r is None:
                return "n/loc"
            if r.get("reach") is None:
                return "-"
            fl = r.get("floor_px")
            return f"{r['reach']:.2f}{'r' if r.get('loc') == 'registered' else ''}/{'-' if fl is None else format(fl, '.0f')}"
        for t in texts:
            c = res["art_ceiling"].get(t) or {}
            art = "-" if c.get("reach") is None else f"{c['reach']:.2f}/{'-' if c.get('floor_px') is None else format(c['floor_px'], '.0f')}"
            lines.append(f"  {t[:22]:22} {art:>10} {fine('ours', t):>12} {fine('pro', t):>12}")

        def fig_reach(k):
            v = res["figures"].get(k)
            return "-" if not v or v.get("reach") is None else f"{v['reach']:.2f} n={v['words']}"
        lines.append(f"    JOB reach, both files' words: ours {fig_reach('ours/native/both'):12} pro {fig_reach('pro/native/both')}")
    for t, why in res.get("blind", {}).items():
        lines.append(f"  blind: {t}: {why}")
    if res["figures"]:
        lines.append("  JOB cc (raw), n words; 'both' = the words scored in BOTH files:")

        def fig(k):
            v = res["figures"].get(k)
            return "-" if not v or v["cc"] is None else f"{v['cc']:+.2f} ({v['raw']:.2f}) n={v['words']}"
        for label in sizes:
            lines.append(f"    {label:7} ours {fig(f'ours/{label}'):20} pro {fig(f'pro/{label}'):20}"
                         f" | both: ours {fig(f'ours/{label}/both'):20} pro {fig(f'pro/{label}/both')}")
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--digitize", metavar="JOBS", help="digitize ours, write ours_<job>.json to --cache")
    ap.add_argument("--propose", metavar="JOB", help="print the tagger's word boxes from --cache, write an overlay")
    ap.add_argument("--read", metavar="JOBS")
    ap.add_argument("--cache", type=Path, default=Path("word_legibility_cache"))
    ap.add_argument("--json", type=Path)
    ap.add_argument("--dump", type=Path, help="write every OCR crop here")
    ap.add_argument("--no-ocr", action="store_true")
    ap.add_argument("--no-ladder", action="store_true", help="skip the shrinking ladder (reach): about a third of the reads")
    a = ap.parse_args(argv)
    JOBS.update({j: s for j, s in registered_jobs().items() if j not in JOBS})
    if a.list:
        for j, spec in JOBS.items():
            print(j, spec["garment"], spec["art"], "|", spec["pro"], "|", [w["text"] for w in pinned_words(j)])
        return 0
    if a.digitize:
        for j in a.digitize.split(","):
            print("wrote", digitize_job(j, a.cache))
        return 0
    if a.propose:
        propose(a.propose, a.cache, a.cache / f"propose_{a.propose}.png")
        return 0
    if a.read:
        from tools.glyph_legibility import load_source
        if not tesseract_available() and not a.no_ocr:
            print("tesseract binary not on PATH: reading geometry and crops only, no numbers "
                  "(run on the WSL scorecard box, or CI; --no-ocr silences this)")
        results = []
        for j in a.read.split(","):
            words = pinned_words(j)
            if not words:
                print(f"{j}: no pinned words in {WORDS_FILE.name}; run --propose and pin them")
                continue
            cached = json.loads((a.cache / f"ours_{j}.json").read_text(encoding="utf-8"))
            rgb, alpha = load_source(resolve(JOBS[j]["art"]))
            res = read_job(j, cached["design"], load_pro_design(resolve(JOBS[j]["pro"])), words, rgb, alpha,
                           not a.no_ocr, a.dump, ours_width_mm=cached["width_mm"], ladder=not a.no_ladder)
            results.append(res)
            print(table(res))
        if a.json:
            a.json.write_text(json.dumps(results, indent=1), encoding="utf-8")
        return 0
    ap.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
