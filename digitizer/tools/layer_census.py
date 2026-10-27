"""layer_census: where a machine file sews one colour ON another, same reader both sides.

    python -m tools.layer_census                       # every registered pro pair (pro_intake), DST read
    python -m tools.layer_census FILE.dst [--colours PES_OR_PLAN] [--beanie] [--json OUT]

Built 2026-10-26 for W4-06. #1104 found the pro builds Precision Drone's
badge back to front (23 blocks, 8 cones, his dark ground walking under 18
later blocks) where we knock colours out, and named LAYERING plus colour
revisits as the lever. Before building it, this counts where he layers.

One reader, both sides; DST, never PES (the PES only names the threads). Each
file in its own frame. Per colour BLOCK, every needle-down segment is drawn a
thread wide at 10 px/mm, closed 0.6 mm (fill rows and satin crosses become a
body) and opened 0.6 mm (a lone run line drops out, `sequence_pro`'s rule).

- LAYERED cells: a cell 0.5 mm deep inside two blocks of DIFFERENT colours
  (each body eroded half a millimetre, so a seam's underlap is not layering).
  `under_by_colour` says which colour went down first there.
- PIECES: each connected part of a block's body that comes within 1 mm of an
  earlier block of another colour. Its interior (eroded 0.5 mm) is `on` when
  half or more lies on that earlier thread, `off` (knocked out) at a fifth or
  less, else `partial`. `inside` is the most of it any one earlier block's
  OUTLINE (its body, holes closed) holds: 0.9 or more reads as a piece sitting
  inside that block -- a ground's contents. `host` is that block.
- `kappa_inside_rule`: Cohen's kappa of "inside => on" against the labels,
  partials out. The labels are his; the rule is the class the census tests.
- REVISITS: a block whose colour an earlier block already sewed, and how much
  of that colour's earlier body the blocks in between covered (a revisit made
  to sew ON something is layering; one with nothing between is not).
- A beanie's knockdown (block 0 holding 0.95 of the design) is no ground: it
  is left out of every count.
- `compare(ours, pro)`: per OUR piece, our label beside his at the same
  place, the two designs aligned box to box; kappa over the pairs.

It reads; it does not judge. Measured with it 2026-10-26
(`docs/layering-census-2026-10-26.md`), 28 of his DSTs: every piece that sits
inside an earlier colour's outline is sewn ON that colour (162 of 162); the
rule is already built as `silhouette_underfill`, and no layering or colour
order reaches our between-piece cuts -- 80 of 176 cross the very ground the
pieces sit on, which sews first in any back-to-front build.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

DIGITIZER = Path(__file__).resolve().parent.parent
if str(DIGITIZER) not in sys.path:
    sys.path.insert(0, str(DIGITIZER))

from tools import sequence_pro as sp  # noqa: E402

PPM = 10.0            # px per mm
THREAD_MM = 0.4       # machine.COVERAGE_THREAD_W_MM
CLOSE_MM = 0.6        # fill rows and satin crosses close into a body ...
OPEN_MM = 0.6         # ... and a lone run line opens away (sequence_pro's OPEN_MM)
DEEP_MM = 0.5         # a cell is "under" only this far inside both bodies: seam underlap is not layering
PIECE_MIN_MM2 = 1.0
INTERIOR_MIN_MM2 = 0.5
CONTAIN = 0.9         # a piece lies inside an earlier block's outline (holes closed)
ON = 0.5              # its interior lies on earlier other-colour thread this much: sewn ON it
OFF = 0.2             # ... this little: knocked out of it
TOUCH_MM = 1.0        # a piece meets an earlier block within this
KNOCKDOWN_FILLED = 0.95


def _disk(mm):
    import cv2
    k = max(1, int(round(mm * PPM)))
    return cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))


def bodies(path):
    """-> (sequence_pro.read(path), [bool raster per block], [moves per block]):
    every needle-down segment drawn a thread wide, closed, then opened."""
    import cv2
    import numpy as np
    f = sp.read(path)
    x0, y0, x1, y1 = f["extents"]
    ox, oy = x0 - 2, y0 - 2
    w = int((x1 - x0 + 4) * PPM) + 2
    h = int((y1 - y0 + 4) * PPM) + 2
    lw = max(1, int(round(THREAD_MM * PPM)))

    def px(p):
        return int(round((p[0] - ox) * PPM)), int(round((p[1] - oy) * PPM))

    out, mvs = [], []
    for b in f["blocks"]:
        mv = sp.moves(b)
        mvs.append(mv)
        im = np.zeros((h, w), np.uint8)
        for a, c in zip(mv, mv[1:]):
            if not c["up"]:
                cv2.line(im, px(a["p"]), px(c["p"]), 1, lw)
        im = cv2.morphologyEx(im, cv2.MORPH_CLOSE, _disk(CLOSE_MM))
        im = cv2.morphologyEx(im, cv2.MORPH_OPEN, _disk(OPEN_MM))
        out.append(im.astype(bool))
    return f, out, mvs


def _outline(m):
    """The block's body with every hole closed (a 1 mm closing first, so
    a fill's row gaps do not count as holes)."""
    import cv2
    import numpy as np
    m8 = cv2.morphologyEx(m.astype(np.uint8), cv2.MORPH_CLOSE, _disk(1.0))
    cs, _ = cv2.findContours(m8, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    out = np.zeros_like(m8)
    cv2.drawContours(out, cs, -1, 1, -1)
    return out.astype(bool)


def _trims(mv) -> int:
    n, prev = 0, False
    for m in mv:
        if m["trim"] and not prev:
            n += 1
        prev = m["trim"]
    return n


def kappa(pairs) -> float | None:
    """Cohen's kappa over (rater a, rater b) boolean pairs; None when chance
    agreement is total (one rater constant on both labels)."""
    n = len(pairs)
    if not n:
        return None
    po = sum(1 for a, b in pairs if a == b) / n
    pa = sum(1 for a, _ in pairs if a) / n
    pb = sum(1 for _, b in pairs if b) / n
    pe = pa * pb + (1 - pa) * (1 - pb)
    if pe >= 1 - 1e-12:
        return None
    return (po - pe) / (1 - pe)


def read(path, colours=None, beanie: bool = False, keep: bool = False) -> dict:
    """One machine file -> its layering, per block and per piece (module docstring).
    `keep`: also return the rasters `compare` needs (not JSON-able)."""
    import cv2
    import numpy as np
    f, fps, mvs = bodies(path)
    nb = len(fps)
    named = colours is not None and len(colours) == nb
    colours = list(colours) if named else [f"block {i + 1}" for i in range(nb)]
    cell = 1.0 / PPM ** 2
    union = np.zeros_like(fps[0])
    for m in fps:
        union |= m
    area = float(union.sum() * cell)
    outl = [_outline(m) for m in fps]
    filled = [float(o.sum() * cell / area) for o in outl]
    # a beanie's knockdown: block 0 under the whole design, garment colour
    kd = {0} if beanie and nb > 1 and filled[0] >= KNOCKDOWN_FILLED else set()
    er = _disk(2 * DEEP_MM)
    deep = [cv2.erode(m.astype(np.uint8), er).astype(bool) for m in fps]
    first = np.full(union.shape, -1, np.int32)
    layered = np.zeros_like(union)
    under = {}
    for i, m in enumerate(deep):
        if i in kd:
            continue
        hit = m & (first >= 0)
        for bi in (np.unique(first[hit]) if hit.any() else []):
            if colours[bi] == colours[i]:
                continue
            sel = hit & (first == bi) & ~layered
            under[colours[bi]] = under.get(colours[bi], 0.0) + float(sel.sum() * cell)
            layered |= sel
        first[m & (first < 0)] = i
    blk_area = [float(m.sum() * cell) for m in fps]
    col_area: dict[str, float] = {}
    for i, c in enumerate(colours):
        if i not in kd:
            col_area[c] = col_area.get(c, 0.0) + blk_area[i]
    pieces = []
    touch = _disk(2 * TOUCH_MM)
    for j in range(nb):
        others = [i for i in range(j) if colours[i] != colours[j] and i not in kd]
        if j in kd or not others:
            continue
        below = np.zeros_like(union)
        for i in others:
            below |= fps[i]
        n, lab, stats, _c = cv2.connectedComponentsWithStats(fps[j].astype(np.uint8), connectivity=8)
        for k in range(1, n):
            a = float(stats[k, cv2.CC_STAT_AREA] * cell)
            if a < PIECE_MIN_MM2:
                continue
            P = lab == k
            if not (cv2.dilate(P.astype(np.uint8), touch).astype(bool) & below).any():
                continue
            Pi = cv2.erode(P.astype(np.uint8), er).astype(bool)
            if Pi.sum() * cell < INTERIOR_MIN_MM2:
                continue
            on = float((Pi & below).sum() / Pi.sum())
            inside, host = 0.0, None
            for i in others:
                v = float((P & outl[i]).sum() / P.sum())
                if v > inside:
                    inside, host = v, i
            pieces.append(dict(block=j, colour=colours[j], area=round(a, 2), on=round(on, 3),
                               inside=round(inside, 3), host=host,
                               host_colour=None if host is None else colours[host],
                               label="on" if on >= ON else ("off" if on <= OFF else "partial")))
            if keep:
                pieces[-1]["_cells"] = np.nonzero(Pi)
    rev = []
    for j in range(nb):
        prev = [i for i in range(j) if colours[i] == colours[j] and i not in kd]
        if not prev or j in kd:
            continue
        mine = np.zeros_like(union)
        for i in prev:
            mine |= deep[i]
        over = sum(int((deep[x] & mine).sum()) for x in range(prev[-1] + 1, j))
        rev.append(dict(block=j, colour=colours[j], after=prev[-1], covered_between_mm2=round(over * cell, 1)))
    judged = [p for p in pieces if p["label"] != "partial"]
    k = kappa([(p["inside"] >= CONTAIN, p["label"] == "on") for p in judged])
    extra = dict(_layered=layered, _extents=f["extents"]) if keep else {}
    return dict(file=Path(path).name, named=named, area_mm2=round(area, 1), **extra,
                blocks=nb - len(kd), cones=len({c for i, c in enumerate(colours) if i not in kd}),
                knockdown=bool(kd), trims=sum(_trims(mv) for i, mv in enumerate(mvs) if i not in kd),
                layered_mm2=round(float(layered.sum() * cell), 1),
                layered_share=round(float(layered.sum()) / max(1, int(union.sum())), 3),
                under_by_colour={c: round(v, 1) for c, v in under.items()},
                colour_area={c: round(v, 1) for c, v in col_area.items()},
                pieces=pieces, kappa_inside_rule=None if k is None else round(k, 3), revisits=rev,
                block_rows=[dict(block=i, colour=colours[i], area_mm2=round(blk_area[i], 1),
                                 trims=_trims(mvs[i]), outline_share=round(filled[i], 3), knockdown=i in kd)
                            for i in range(nb)])


def compare(ours, pro) -> dict:
    """Per OUR piece, its label beside the pro's at the same place: our
    interior cells carried into his frame box to box (both designs' stitch
    extents, `tools/pro_layers`' alignment; a 1-2 mm residual is normal) and
    read on his cells where one colour lies deep on another. `ours`, `pro`:
    `read(..., keep=True)` results. -> {"rows", "kappa", "n"}, partials out."""
    import numpy as np
    ox0, oy0, ox1, oy1 = ours["_extents"]
    px0, py0, px1, py1 = pro["_extents"]
    sx, sy = (px1 - px0) / (ox1 - ox0), (py1 - py0) / (oy1 - oy0)
    lay = pro["_layered"]
    h, w = lay.shape
    rows = []
    for p in ours["pieces"]:
        r, c = p["_cells"]
        x = (c / PPM + ox0 - 2 - ox0) * sx + px0
        y = (r / PPM + oy0 - 2 - oy0) * sy + py0
        pc = np.clip(np.round((x - (px0 - 2)) * PPM).astype(int), 0, w - 1)
        pr = np.clip(np.round((y - (py0 - 2)) * PPM).astype(int), 0, h - 1)
        share = float(lay[pr, pc].mean()) if len(pr) else 0.0
        mine = float(ours["_layered"][r, c].mean()) if len(r) else 0.0
        lab = lambda s: "on" if s >= ON else ("off" if s <= OFF else "partial")  # noqa: E731
        rows.append(dict(block=p["block"], area=p["area"], inside=p["inside"], ours_share=round(mine, 3),
                         ours=lab(mine), pro_share=round(share, 3), pro=lab(share)))
    pairs = [(q["ours"] == "on", q["pro"] == "on") for q in rows if "partial" not in (q["ours"], q["pro"])]
    k = kappa(pairs)
    return {"rows": rows, "n": len(pairs), "kappa": None if k is None else round(k, 3),
            "agree": sum(1 for a, b in pairs if a == b)}


def counts(r: dict) -> dict:
    """{inside|outside: {on, off, partial}} pieces of one reading."""
    out = {"inside": {"on": 0, "off": 0, "partial": 0}, "outside": {"on": 0, "off": 0, "partial": 0}}
    for p in r["pieces"]:
        out["inside" if p["inside"] >= CONTAIN else "outside"][p["label"]] += 1
    return out


def colours_of(path) -> list[str] | None:
    """Block colours: a PES's thread list, or a pickled StitchPlan's palette."""
    path = Path(path)
    if path.suffix.lower() == ".pes":
        import pystitch
        return [t.hex_color() for t in pystitch.read(str(path)).threadlist]
    if path.suffix.lower() in (".pkl", ".pickle"):
        import pickle
        plan = pickle.loads(path.read_bytes())
        return ["#%02x%02x%02x" % tuple(c["rgb"]) for c in plan.palette]
    return None


def registered() -> list[tuple[str, Path, Path | None, bool]]:
    """(slug, DST, PES or None, beanie) for every registered pro pair; the
    `Test Files` job (a third-party sample folder) is not his."""
    from tools import pro_intake as pi
    reg = pi.load_registry()
    out = []
    for job_name, job in reg["jobs"].items():
        if job_name == "Test Files":
            continue
        for p in job["pairs"]:
            dst = pi.resolve(p["dst"], reg)
            pes = pi.resolve(p.get("pes"), reg)
            beanie = (p.get("garment_id") or "").upper() == "BEANIE"
            out.append((p["slug"], dst, pes if pes is not None and Path(pes).exists() else None, beanie))
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("files", nargs="*")
    ap.add_argument("--colours", action="append", default=[],
                    help="per FILE, in order: a PES or a pickled plan whose palette names the blocks")
    ap.add_argument("--beanie", action="store_true", help="the FILES are beanies (block 0 may be a knockdown)")
    ap.add_argument("--json", default=None)
    a = ap.parse_args(argv)
    if a.files:
        jobs = [(Path(f).stem, Path(f), Path(a.colours[i]) if i < len(a.colours) else None, a.beanie)
                for i, f in enumerate(a.files)]
    else:
        jobs = registered()
    rows = []
    for slug, dst, cols, beanie in jobs:
        r = read(dst, colours_of(cols) if cols else None, beanie=beanie)
        r["slug"] = slug
        rows.append(r)
        c = counts(r)
        print(f"{slug:34s} blocks {r['blocks']:2d} cones {r['cones']:2d}{' +kd' if r['knockdown'] else '    '} "
              f"trims {r['trims']:3d} layered {r['layered_mm2']:7.1f} mm2 ({r['layered_share']:.2f})  "
              f"inside on/off/partial {c['inside']['on']}/{c['inside']['off']}/{c['inside']['partial']}  "
              f"outside {c['outside']['on']}/{c['outside']['off']}/{c['outside']['partial']}  "
              f"kappa(inside rule) {r['kappa_inside_rule']}", flush=True)
    if len(rows) > 1:
        pairs = [(p["inside"] >= CONTAIN, p["label"] == "on") for r in rows for p in r["pieces"]
                 if p["label"] != "partial"]
        k = kappa(pairs)
        print(f"all: {len(pairs)} judged pieces, kappa(inside rule) {None if k is None else round(k, 3)}")
    if a.json:
        Path(a.json).write_text(json.dumps(rows, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
