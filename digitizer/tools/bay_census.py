#!/usr/bin/env python
"""bay_census: is each bay of a small sewn letter OPEN, ours beside the
professional's? The census behind `small_text.BAY_MOUTH_MM` and the proof
sheet of `cfg.small_text_bay_mouth` (W3-02, 2026-10-25; ON since 2026-10-26).

WHY. The re-set (`small_text_cap_letter_gap_mm`) grows Fremont's EST 1895 to
the pro's ~4 mm bold satin, and its widening sews three bays shut: E reads
B, S reads 8, 5 reads 3. The professional's same letters are NOT wider -- on
the hat ours are wider than his (S 1.06, 5 1.07 of his w/h aspect) and still
shut -- so widening was measured and dropped. What he keeps is a MOUTH: his
terminals stop short of the stroke they curl toward.

HOW, one reader on both machine files, each in its own frame:
- the file's letters are `tools/small_text_columns.pieces` (per colour
  block, needle-down stitches drawn 0.4 mm wide at 20 px/mm, opened by
  0.55 mm) in a line's band; a piece wider than one letter (the pro's 895
  sews joined) is split at its column-sum minima into as many letters as the
  line's text gives it by width;
- each letter's MOUTHS are `small_text.bay_mouths` on that thread raster:
  every pocket of ground inside the letter's 0.8 mm closing at least 0.15 mm
  from the thread, and the widest clear passage from it to the outside (0 =
  enclosed, so an 8's counters read 0 by design);
- aspect is the letter's sewn width over height, thread included; OCR is
  `glyph_legibility._ocr_char` on the letter alone (psm 10, no language
  model), a second reader.

The pro's files are read out of the committed `Embroidery Files.zip`. Ours
are digitized at the pro's width through `tools.pro_pair.digitize` with the
re-set made explicit (#1057's values), OFF and ON, and cached as DST.

  python -m tools.bay_census --census                       # the pro's E/S/5 mouths -> BAY_MOUTH_MM
  python -m tools.bay_census digitize --cache DIR [SLUG ...]  # ours, off and on arms
  python -m tools.bay_census --cache DIR --table [--crops OUT]

A mouth here is read on the thread raster of a machine file: a picture of
the file, not of cloth. Whether 0.50 mm stays open on a cap is a sew-out
question (ROADMAP gate 1).
"""
from __future__ import annotations

import argparse
import functools
import hashlib
import json
import sys
import tempfile
import zipfile
from pathlib import Path

import numpy as np

DIGITIZER = Path(__file__).resolve().parent.parent
if str(DIGITIZER) not in sys.path:
    sys.path.insert(0, str(DIGITIZER))

ZIP = DIGITIZER.parent / "Embroidery Files.zip"
#: the re-set as #1057 makes it the default (Kent 2026-10-23); None until then
#: The re-set, with the switch itself pinned OFF in the request: the "on" arm
#: turns it on at the call (`functools.partial` below), so OFF stays the
#: pre-flip re-set now that the default is ON (2026-10-26).
RESET = {"small_text_cap_mm": 4.0, "small_text_cap_max_width_scale": 1.05,
         "small_text_cap_min_stroke_mm": 0.85, "small_text_cap_letter_gap_mm": 0.25,
         "small_text_cap_bold_scale": 1.45, "lettering_columns_small_bold": True,
         "small_text_bay_mouth": False}
ARMS = ("off", "on")
#: letters whose mouths set the target: the three Fremont shut
MOUTH_GLYPHS = "ES5"
def _ocr_pull_mm() -> float:
    """The OCR's second read takes back the pull the engine added to these
    letters, a side, the way `glyph_legibility --pull-mm` does
    (`glyph_read.pull_erode`): `lettering_columns_small_bold` pulls a
    `columns.SMALL_BOLD_PULL_FRAC` share of the stroke, here the re-set's
    0.85 mm floor. A way of reading the file as if the cloth had pulled, not
    a measurement of any cloth."""
    from digitizer_core.columns import SMALL_BOLD_PULL_FRAC
    return round(SMALL_BOLD_PULL_FRAC * RESET["small_text_cap_min_stroke_mm"], 4)

#: slug -> its pro DST in the zip, its line (own-frame band y0, y1, x0, x1 mm
#: and colour block, picked from `small_text_columns --pieces`), the line's
#: letters, and our line's band in OUR file (both arms; checked by count)
LINES = {
    "hotel_fremont_hat": {
        "pro": "Embroidery Files/Hotel Fremont/Hotel Hat/HOTEL FREMONT HAT.DST",
        "pro_band": (11.0, 16.5, 30.0, 64.0), "pro_block": 8, "text": "EST1895",
        "ours_band": (12.0, 17.5, 28.0, 68.0)},
    "hotel_fremont_patch": {
        "pro": "Embroidery Files/Hotel Fremont/Hotel Patch/HOTEL FREMONT .DST",
        "pro_band": (10.0, 15.0, 30.0, 62.0), "pro_block": 8, "text": "EST1895",
        "ours_band": (11.5, 17.2, 29.0, 66.0)},
    "proseal_hat": {
        "pro": "Embroidery Files/Proseal/PROSEALHAT.DST",
        "pro_band": (58.0, 64.0, 0.0, 45.0), "pro_block": 0, "text": "SPRAYFOAM",
        "ours_band": (58.5, 64.0, 0.0, 45.0)},
    "proseal_beanie": {
        "pro": "Embroidery Files/Proseal/PROSEALHAT BEANI.DST",
        "pro_band": (49.0, 55.0, 0.0, 40.0), "pro_block": 1, "text": "SPRAYFOAM",
        "ours_band": (52.5, 58.0, 0.0, 42.0)},
    "precision_drone": {
        "pro": "Embroidery Files/Precision Drone/PRECISION DRON HAT 2.DST",
        "pro_band": (53.0, 59.0, 10.0, 52.0), "pro_block": 1, "text": "ANDDRONE",
        "ours_band": (55.0, 59.6, 10.0, 52.0)},
}
#: the census's lines: every E, S and 5 of the pro's small lines (Drone's AND
#: DRONE has none)
CENSUS = ("hotel_fremont_hat", "hotel_fremont_patch", "proseal_hat", "proseal_beanie")


# ------------------------------------------------------------------ reading
def pro_blocks(slug: str):
    """The pro's DST for `slug`, out of the committed zip, as
    `small_text_columns.read_blocks` reads it."""
    from tools import small_text_columns as stc
    with zipfile.ZipFile(ZIP) as z:
        data = z.read(LINES[slug]["pro"])
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "pro.dst"
        path.write_bytes(data)
        return stc.read_blocks(path)


def allot(widths: list[float], n: int) -> list[int] | None:
    """How many of `n` letters each piece holds, by width (largest
    remainder, one at least): the pro's 895 sews as one piece. None when
    there are more pieces than letters."""
    if not widths or len(widths) > n:
        return None
    tot = sum(widths)
    raw = [w / tot * n for w in widths]
    k = [max(1, int(r)) for r in raw]
    while sum(k) < n:
        i = max(range(len(k)), key=lambda i: raw[i] - k[i])
        k[i] += 1
    while sum(k) > n:
        i = max((i for i in range(len(k)) if k[i] > 1), key=lambda i: k[i] - raw[i])
        k[i] -= 1
    return k


def split(mask: np.ndarray, k: int) -> list[np.ndarray]:
    """A piece's mask split into `k` letters at the column-sum minimum near
    each even share of its width."""
    if k == 1:
        return [mask]
    prof = mask.sum(0).astype(float)
    w = mask.shape[1]
    cuts = [0]
    for j in range(1, k):
        lo, hi = int((j - 0.35) * w / k), int((j + 0.35) * w / k)
        cuts.append(lo + int(np.argmin(prof[lo:hi])))
    cuts.append(w)
    return [mask[:, a:b] for a, b in zip(cuts, cuts[1:])]


def _tight(m: np.ndarray) -> np.ndarray:
    ys, xs = np.nonzero(m)
    return m[ys.min():ys.max() + 1, xs.min():xs.max() + 1]


def read_glyph(mask: np.ndarray, ocr: bool = True) -> dict:
    """One letter's numbers off its thread raster (module docstring)."""
    from digitizer_core.small_text import bay_mouths
    from tools import small_text_columns as stc
    m = _tight(mask.astype(bool))
    h, w = m.shape
    row = {"w_mm": round(w / stc.PPM, 2), "h_mm": round(h / stc.PPM, 2), "aspect": round(w / h, 3),
           "mouths": [p["mouth_mm"] for p in bay_mouths(m, stc.PPM)]}
    if ocr:
        from digitizer_core.glyph_read import pull_erode
        from tools import glyph_legibility as gl
        ok = gl.tesseract_available()
        row["ocr"] = gl._ocr_char(m, stc.PPM)[0] if ok else None
        pulled = pull_erode(np.pad(m, 4), _ocr_pull_mm(), stc.THREAD_MM, stc.PPM, None, "none")
        row["ocr_pulled"] = gl._ocr_char(pulled, stc.PPM)[0] if ok and pulled.any() else None
    return row


def read_line(blocks, band, text: str, block=None, ocr: bool = True) -> dict:
    """Every letter of one line: pieces in `band` (own frame, mm), split to
    `text`'s count. -> {"letters": [row + "char"], "masks": [...]} or
    {"unread": why}."""
    from tools import small_text_columns as stc
    y0, y1, x0, x1 = band
    sel = sorted((p for p in stc.pieces(blocks)
                  if y0 <= (p["y0"] + p["y1"]) / 2 <= y1 and x0 <= (p["x0"] + p["x1"]) / 2 <= x1
                  and (block is None or p["block"] == block)), key=lambda p: p["x0"])
    ks = allot([p["x1"] - p["x0"] for p in sel], len(text))
    if ks is None:
        return {"unread": f"{len(sel)} pieces for {len(text)} letters"}
    letters, masks, ci = [], [], 0
    for p, k in zip(sel, ks):
        for sub in split(p["mask"], k):
            if not sub.any():
                return {"unread": "an empty split"}
            row = read_glyph(sub, ocr)
            row["char"] = text[ci]
            ci += 1
            letters.append(row)
            masks.append(_tight(sub))
    return {"letters": letters, "masks": masks, "blocks": sorted({int(p["block"]) for p in sel})}


def census(ocr: bool = False) -> dict:
    """The pro's E/S/5 mouths over `CENSUS`, each file in its own frame."""
    mouths, rows = [], {}
    for slug in CENSUS:
        spec = LINES[slug]
        got = read_line(pro_blocks(slug), spec["pro_band"], spec["text"], spec["pro_block"], ocr)
        rows[slug] = got.get("letters") or got
        for g in got.get("letters", []):
            if g["char"] in MOUTH_GLYPHS:
                mouths.extend(g["mouths"])
    mouths.sort()
    return {"n": len(mouths), "mouths": mouths,
            "min": mouths[0] if mouths else None, "max": mouths[-1] if mouths else None,
            "median": round(float(np.median(mouths)), 3) if mouths else None, "lines": rows}


# ------------------------------------------------------------------ ours
def digitize(slug: str, cache: Path, arms=ARMS) -> None:
    """Ours for `slug` at the pro's width, the re-set explicit: `off`, and
    `on` with the switch driven by `functools.partial` on
    `small_text.enlarge_small_text` (the pipeline imports it at the call).
    Writes <cache>/<slug>/<arm>.dst and <arm>.json (the growth's rows)."""
    from digitizer_core import small_text
    from digitizer_core.export import plan_to_pattern
    from digitizer_service import formats
    from tools import border_census as bc
    from tools import pro_pair as pp
    from tools import small_text_floor_census as stf
    pairs = {r[0]: r for r in bc.PAIRS + stf.EXTRA_PAIRS}
    pro, art = bc.find_pair(*pairs[slug][:3])
    if art is None:
        raise SystemExit(f"{slug}: no art (it lives on Kent's box only)")
    width = pp.pro_counts(pro)["width_mm"]
    real = small_text.enlarge_small_text
    out = cache / slug
    out.mkdir(parents=True, exist_ok=True)
    for arm in arms:
        rows: list = []
        grow = functools.partial(real, bay_mouth=True) if arm == "on" else real

        def spy(*a, grow=grow, rows=rows, **k):
            got = grow(*a, **k)
            rows.extend(got)
            return got
        small_text.enlarge_small_text = spy
        try:
            d = pp.digitize(art, width, pairs[slug][3], extra=dict(RESET))
        finally:
            small_text.enlarge_small_text = real
        (out / f"{arm}.dst").write_bytes(formats.write(plan_to_pattern(d.plan), "dst"))
        (out / f"{arm}.json").write_text(json.dumps({"width_mm": width, "secs": round(d.secs),
                                                     "stitches": d.plan.stats.stitch_count,
                                                     "trims": d.plan.stats.trims, "growth": rows},
                                                    indent=1, default=str))
        print(f"{slug} {arm}: {d.plan.stats.stitch_count} st, {round(d.secs)} s", flush=True)


def compare(cache: Path, slugs=None, ocr: bool = True) -> dict:
    """OFF, ON and the pro, letter by letter, for every cached slug."""
    from tools import small_text_columns as stc
    out = {}
    for slug in slugs or LINES:
        spec = LINES[slug]
        if not (cache / slug / "off.dst").exists():
            continue
        row = {"pro": read_line(pro_blocks(slug), spec["pro_band"], spec["text"], spec["pro_block"], ocr)}
        for arm in ARMS:
            path = cache / slug / f"{arm}.dst"
            if path.exists():
                row[arm] = read_line(stc.read_blocks(path), spec["ours_band"], spec["text"], None, ocr)
                row[arm]["md5"] = hashlib.md5(path.read_bytes()).hexdigest()
        out[slug] = row
    return out


def _fmt(ms) -> str:
    return ", ".join(f"{m:.2f}" for m in ms) or "-"


def table(rows: dict) -> str:
    """Markdown: per letter, mouths and aspect OFF | ON | pro, and the OCR
    as drawn and pulled (`_ocr_pull_mm`)."""
    out = ["| job | letter | mouths mm OFF | ON | pro | aspect OFF / ON / pro | OCR OFF / ON / pro | "
           f"OCR pulled {_ocr_pull_mm()} mm OFF / ON / pro |",
           "|---|---|---|---|---|---|---|---|"]
    for slug, row in rows.items():
        sides = [row.get(a, {"unread": "not digitized"}) for a in ("off", "on", "pro")]
        if any("unread" in s for s in sides):
            out.append(f"| {slug} | n/read: " + "; ".join(f"{a} {s['unread']}" for a, s in zip(("off", "on", "pro"), sides)
                                                          if "unread" in s) + " | | | | | | |")
            continue
        for k, ch in enumerate(LINES[slug]["text"]):
            g = [s["letters"][k] for s in sides]
            out.append(f"| {slug} | {ch} | {_fmt(g[0]['mouths'])} | {_fmt(g[1]['mouths'])} | {_fmt(g[2]['mouths'])} | "
                       f"{g[0]['aspect']:.3f} / {g[1]['aspect']:.3f} / {g[2]['aspect']:.3f} | "
                       f"{g[0].get('ocr') or '?'} / {g[1].get('ocr') or '?'} / {g[2].get('ocr') or '?'} | "
                       f"{g[0].get('ocr_pulled') or '?'} / {g[1].get('ocr_pulled') or '?'} / "
                       f"{g[2].get('ocr_pulled') or '?'} |")
    return "\n".join(out)


def crops(rows: dict, cache: Path, out: Path) -> list[Path]:
    """`<slug>.png`: the line OFF | ON | pro, each file's own band drawn by
    `small_text_columns.render_band` (needle-down stitches 0.4 mm wide, the
    line's own colour blocks dark, every other block pale). `rows` is
    `compare`'s."""
    import cv2
    from tools import small_text_columns as stc
    out.mkdir(parents=True, exist_ok=True)
    written = []
    for slug, row in rows.items():
        spec = LINES[slug]
        if not all("letters" in row.get(k, {}) for k in ("off", "on", "pro")):
            continue
        panels = []
        for arm, key, blocks, band in (
                ("OFF (re-set, #1057 values)", "off", stc.read_blocks(cache / slug / "off.dst"), spec["ours_band"]),
                ("ON (small_text_bay_mouth)", "on", stc.read_blocks(cache / slug / "on.dst"), spec["ours_band"]),
                ("PRO", "pro", pro_blocks(slug), spec["pro_band"])):
            img = stc.render_band(blocks, band, keep=set(row[key].get("blocks", [])), ppm=40.0, pad_mm=0.3)
            bar = np.full((40, img.shape[1], 3), 255, np.uint8)
            cv2.putText(bar, f"{slug}  {arm}", (6, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2, cv2.LINE_AA)
            panels.append(np.vstack([bar, img]))
        w = max(p.shape[1] for p in panels)
        sheet = np.vstack([np.pad(p, ((0, 12), (0, w - p.shape[1]), (0, 0)), constant_values=255) for p in panels])
        path = out / f"{slug}.png"
        cv2.imwrite(str(path), sheet)
        written.append(path)
    return written


def main(argv=None) -> int:
    from tools._console import utf8_console
    utf8_console()
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "digitize":
        ap = argparse.ArgumentParser(prog="bay_census digitize")
        ap.add_argument("--cache", type=Path, required=True)
        ap.add_argument("--arm", action="append", choices=ARMS)
        ap.add_argument("slugs", nargs="*")
        a = ap.parse_args(argv[1:])
        for slug in a.slugs or list(LINES):
            digitize(slug, a.cache, tuple(a.arm or ARMS))
        return 0
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--census", action="store_true", help="the pro's E/S/5 mouths (the BAY_MOUTH_MM census)")
    ap.add_argument("--cache", type=Path, help="ours, from `digitize`")
    ap.add_argument("--table", action="store_true")
    ap.add_argument("--json", type=Path)
    ap.add_argument("--crops", type=Path)
    ap.add_argument("--no-ocr", action="store_true")
    a = ap.parse_args(argv)
    if a.census:
        c = census()
        print(json.dumps({k: v for k, v in c.items() if k != "lines"}))
    if a.cache:
        rows = compare(a.cache, ocr=not a.no_ocr)
        if a.table:
            print(table(rows))
        if a.json:
            a.json.write_text(json.dumps({s: {k: {kk: vv for kk, vv in v.items() if kk != "masks"}
                                                for k, v in r.items()} for s, r in rows.items()}, indent=1))
        if a.crops:
            for p in crops(rows, a.cache, a.crops):
                print(p)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
