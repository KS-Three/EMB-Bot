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
     read the pro's EST as nothing). A word with no thread near it is
     reported with its note and scores 0, never dropped.
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
     crop. The artwork's own crop is read the same way as the CEILING: a word
     tesseract cannot read off the art (Becker's 146 px logo) says nothing
     about the thread, and is shown as such.

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
geometry (`--no-ocr` asks for that). Kent's Windows box has none: run the
READ on the WSL scorecard box (COOKBOOK "The WSL scorecard box") and the
DIGITIZE wherever you like -- `--digitize` writes OUR design to `--cache`,
`--read` reads it. Pro files and Kent's art are gitignored third-party
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
BASELINE_DRAWS = 500
BASELINE_SEED = 7
WORDS_FILE = DIGITIZER / "testdata" / "word_legibility_words.json"

#: job -> where the art and the pro's file live. "testdata:" is committed,
#: "kent:" is the gitignored `scratch_kent/` folder (EMB_SCRATCH_KENT).
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
    each word's letters. Words with no `cc` (one-letter) are left out of both."""
    use = [r for r in rows if r.get("cc") is not None]
    w = sum(len(norm(r["text"])) for r in use)
    if not w:
        return {"cc": None, "raw": None, "words": 0}
    return {"cc": round(sum(r["cc"] * len(norm(r["text"])) for r in use) / w, 3),
            "raw": round(sum(r["raw"] * len(norm(r["text"])) for r in use) / w, 3),
            "words": len(use)}


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
    root = kent_root()
    if root is None or not (root / rel).exists():
        raise SystemExit(f"{rel!r} not found: it is a gitignored third-party file. Set EMB_SCRATCH_KENT to "
                         f"the folder that holds 'Embroidery Files/' and 'proseal.jpg'.")
    return root / rel


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
                thread_mm: float | None = None) -> np.ndarray | None:
    """BGR crop of the word's box (grown by `CROP_PAD_FRAC` of its height)
    from `design` with its height scaled by `s`; None when no thread falls in
    it."""
    from digitizer_core import stitchviz
    thread_mm = stitchviz.THREAD_MM if thread_mm is None else thread_mm
    x0, y0, x1, y1 = box
    h = y1 - y0
    sub = window_scaled(design, box, s, WINDOW_FRAC * h + 1.0)
    pad = CROP_PAD_FRAC * h
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

def colour_masks(design: dict, ground, px_per_mm: float, max_dist: float = 48.0) -> list[np.ndarray]:
    """One thread mask per spool colour of `design` that is not the ground's
    own (blocks within `max_dist` RGB of one another are one spool): each is
    `glyph_read.thread_ink` of only those blocks, thresholded, on the render
    grid. A pro's DST carries no colours, so it is one mask."""
    from digitizer_core.glyph_read import ink_blocks, thread_ink
    keep = ink_blocks(design, np.asarray(ground, float))
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
        out.append(thread_ink({**design, "stitches": recs}, np.asarray(ground, float), px_per_mm)[0] >= 0.5)
    return out


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


def find_word(masks: list[np.ndarray], exp_box: tuple, px_per_mm: float, art_word: np.ndarray | None = None,
              trace: list | None = None):
    """The word's own thread, found in the file. `exp_box` (u0, v0, u1, v1 in
    grid px) is where the artwork says the word should be, and it is only a
    SEED: the pro sews EST, 1895 and EAT STAY PLAY bigger, bolder and a few
    millimetres off the art, so a box taken from the art would cut them or
    miss them. In every spool colour's thread the letters are fused by a
    growing dilation (`FUSE_MM`), and every fused piece within reach of the
    seed whose size is plausible for the word (`SIZE_RATIO`, `HEIGHT_RATIO`)
    is a candidate; the word is the candidate whose shape and place are
    nearest the art's (|ln aspect ratio|, plus half the |ln| of its width and
    of its height against the art's, plus the distance of its centre in word
    widths, plus 1.5 x (1 - `shape_sim` to the art's own word mask)), and its
    box is the bounding box of its own thread.
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
            if win.sum() < 4:
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
                cost = (abs(math.log((bw / bh) / (ew / eh)))
                        + 0.5 * (abs(math.log(bw / ew)) + abs(math.log(bh / eh)))
                        + math.hypot(cx - ecx, (cy - ecy) * 0.5) / ew)
                if art_word is not None:
                    cost += 1.5 * (1.0 - shape_sim(win[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
                                                   & (lab[ys.min():ys.max() + 1, xs.min():xs.max() + 1] == k),
                                                   art_word))
                if trace is not None:
                    trace.append((round(cost, 2), fuse, wx0 + int(xs.min()), wy0 + int(ys.min()), bw, bh))
                if cost < best_cost:
                    best_cost = cost
                    best = (wx0 + int(xs.min()), wy0 + int(ys.min()), wx0 + int(xs.max()) + 1, wy0 + int(ys.max()) + 1)
    if best is None:
        return None, ("no word-sized thread near the word" if seen else "no thread near the word"), None
    return best, "", round(best_cost, 2)


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


def read_job(job: str, ours: dict, pro: dict, words: list[dict], rgb: np.ndarray, alpha: np.ndarray,
             use_ocr: bool = True, dump: Path | None = None, heights=HEIGHTS_MM,
             ours_width_mm: float | None = None) -> dict:
    """Score every pinned word of `job` in both designs. `ours_width_mm`: the
    width OUR design was digitized at; with it our file is registered exactly
    (`exact_registration`), without it by the same fit as the pro's. -> the
    job's rows, per file and height, and its figures."""
    from digitizer_core.glyph_read import P, PAD_MM, _bbox, ground_colour, soft_ink, thread_ink
    from tools.glyph_legibility import register
    G = ground_colour(rgb, alpha)
    soft_all, _ = soft_ink(rgb, alpha, G)
    sb = _bbox(soft_all)
    ocr_ok = use_ocr and tesseract_available()
    rows: list[dict] = []
    ceilings: dict[str, dict] = {}
    for fname, design in (("ours", ours), ("pro", pro)):
        design = drop_travel(design)
        thread, (dx0, dy1) = thread_ink(design, G, P)
        design = drop_ground_blocks(design, G)
        reg = (exact_registration(sb, ours_width_mm, dx0, dy1) if fname == "ours" and ours_width_mm
               else register(soft_all, thread))
        masks = colour_masks(design, G, P)
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
            box_px, why, cost = find_word(masks, gbox, P, sub[ys.min():ys.max() + 1, xs.min():xs.max() + 1])
            if box_px is None:
                rows.append({**row, "note": why})
                continue
            if cost > LOC_MAX_COST:
                # the thread found is not clearly this word: reading it would score the locator,
                # not the lettering, so the word is NOT scored in this file (n is reported)
                rows.append({**row, "loc_cost": cost, "note": f"not located: best match costs {cost} (> {LOC_MAX_COST})"})
                continue
            u0, v0, u1, v1 = box_px
            # grid px -> the Design's mm (y up): the inverse of `thread_ink`'s frame
            box_mm = (u0 / P + dx0 - PAD_MM, dy1 + PAD_MM - v1 / P,
                      u1 / P + dx0 - PAD_MM, dy1 + PAD_MM - v0 / P)
            h_mm = box_mm[3] - box_mm[1]
            row.update(located=True, loc_cost=cost, height_mm=round(h_mm, 2), width_mm=round(box_mm[2] - box_mm[0], 2),
                       expected_mm=[round((gbox[2] - gbox[0]) / P, 2), round((gbox[3] - gbox[1]) / P, 2)])
            sizes = [("native", 1.0)] + [(f"{h:g}mm", h / h_mm) for h in heights]
            for label, s in sizes:
                r = {**row, "size": label}
                if s > 1.0 + 1e-6:
                    # a stitch layout scaled UP keeps its row pitch and opens gaps no engine would sew
                    rows.append({**r, "read": None, "note": f"skipped: the word is {h_mm:.1f} mm, enlarging invents gaps"})
                    continue
                img = render_word(design, box_mm, s, G)
                if dump is not None and img is not None:
                    dump.mkdir(parents=True, exist_ok=True)
                    cv2.imwrite(str(dump / f"{job}_{fname}_{norm(text)}_{label}.png"), img)
                if img is None:
                    rows.append({**r, "read": "", "conf": 0.0, **chance_corrected("", text), "note": "no thread"})
                    continue
                if not ocr_ok:
                    rows.append({**r, "read": None})
                    continue
                txt, conf = read_crop(img, RENDER_PPM)
                rows.append({**r, "read": norm(txt), "conf": conf, **chance_corrected(txt, text)})
            if fname == "ours" and ocr_ok:       # the artwork's own crop: the reader's ceiling
                a_ppm = P / max(reg.a, 1e-6)
                pad = CROP_PAD_FRAC * (tight[3] - tight[1])
                ax0, ay0 = int(max(0, tight[0] - pad)), int(max(0, tight[1] - pad))
                ax1, ay1 = int(tight[2] + pad), int(tight[3] + pad)
                bgr = cv2.cvtColor(np.clip(rgb[ay0:ay1, ax0:ax1], 0, 255).astype(np.uint8), cv2.COLOR_RGB2BGR)
                txt, conf = read_crop(bgr, a_ppm)
                ceilings[text] = {"read": norm(txt), "conf": conf, **chance_corrected(txt, text)}
    out = {"job": job, "ocr": "ok" if ocr_ok else "OCR UNAVAILABLE", "rows": rows, "art_ceiling": ceilings,
           "figures": {}}
    if ocr_ok:
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
    a = ap.parse_args(argv)
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
                           not a.no_ocr, a.dump, ours_width_mm=cached["width_mm"])
            results.append(res)
            print(table(res))
        if a.json:
            a.json.write_text(json.dumps(results, indent=1), encoding="utf-8")
        return 0
    ap.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
