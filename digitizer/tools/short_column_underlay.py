#!/usr/bin/env python
"""`cfg.satin_underlay_short_columns` OFF against ON against the pro, on the
three paired jobs: bare satin columns counted, and the underlay rendered.

    .venv/Scripts/python -m tools.short_column_underlay --out DIR
        [--fixtures fremont,becker,mfab] [--pro-root DIR]

Per fixture it digitizes the customer's art the way the Studio asks for it
(`tools.pro_pair.digitize`, the pro's own width and garment) with the flag
OFF and ON, writes both plans to DST through the service's writer, and reads
all three files -- ours OFF, ours ON, the pro's -- with ONE instrument,
`tools.pro_satin_underlay` (columns by length and width band, each bare or
carrying a centre run / edge run / zigzag). The plan's own run kinds give a
second count that needs no classifier: a SATIN run is bare by kind when no
UNDERLAY run of its shape was sewn since that shape's previous SATIN run.

Plans are pickled beside the DSTs (`<slug>_<arm>.plan.pkl`) so a render
tweak does not re-digitize (ten minutes an arm on Fremont).

Renders: the preview and the eye-pairs sheets draw underlay UNDER the top
thread, so underlay is invisible present or absent. Here every UNDERLAY run
is drawn OVER the top thread in red (an x-ray, not a sew-out picture), for
the whole design at 20 px/mm and for the two lettering shapes with the most
bare columns OFF at 40 px/mm, OFF | ON | pro on the same box (the pro's
underlay is the reader's classification drawn red; his file has no kinds).
"""
from __future__ import annotations

import argparse
import json
import os
import pickle
import sys
import time
from pathlib import Path

DIGITIZER = Path(__file__).resolve().parent.parent
if str(DIGITIZER) not in sys.path:
    sys.path.insert(0, str(DIGITIZER))

FLAG = "satin_underlay_short_columns"
TESTDATA = DIGITIZER / "testdata"
PRO_ROOT = Path(os.environ.get("PRO_PARITY_ROOT", r"G:/My Drive/EMB-Bot/Embroidery Files"))

# slug -> (art, width mm, garment, pro DST relative to the pro root). Widths
# are the pro's own (`docs/settings-vs-pro-2026-10-21.md`, "Ours").
FIXTURES = {
    "fremont": (TESTDATA / "photo" / "logo_hotel_fremont.webp", 92.5, "hat_front",
                "Hotel Fremont/Hotel Hat/HOTEL FREMONT HAT.DST"),
    "becker": (TESTDATA / "becker_marine_logo.png", 76.5, "hat_front",
               "Becker Marine/Becker Hat & Polo Small/Becker Hat Small/beckers logo hat 2 A.DST"),
    "mfab": (PRO_ROOT / "MFAB" / "MFab Logo.png", 104.9, "hat_front",
             "MFAB/Mfab Hat & Polo/mf4b logo hat.DST"),
}
UNDERLAY_BGR = (40, 40, 230)        # satin underlay (the subject)
FILL_UNDERLAY_BGR = (60, 170, 240)  # fill underlay, for context


def bare_by_kind(plan) -> dict:
    """SATIN runs with and without an UNDERLAY run of their shape since the
    shape's previous SATIN run, in the same block. `short` is a satin run
    whose own points span under 5 mm (the audit's 'short column')."""
    from digitizer_core import stitches
    tot = bare = short = short_bare = 0
    for b in plan.blocks:
        seen: set[str] = set()
        for r in b.runs:
            if r.kind == stitches.UNDERLAY:
                seen.add(r.shape_id)
            elif r.kind == stitches.SATIN:
                xs = [p[0] for p in r.points]
                ys = [p[1] for p in r.points]
                is_short = max(max(xs) - min(xs), max(ys) - min(ys)) < 5.0
                tot += 1
                short += is_short
                if r.shape_id not in seen:
                    bare += 1
                    short_bare += is_short
                seen.discard(r.shape_id)
    return {"satin_runs": tot, "bare": bare, "bare_pct": round(100 * bare / tot, 1) if tot else None,
            "short": short, "short_bare": short_bare,
            "short_bare_pct": round(100 * short_bare / short, 1) if short else None}


def by_instrument(path: Path) -> dict:
    from tools import pro_satin_underlay as psu
    rows = psu.read_columns(psu.blocks_from_file(path))
    n = len(rows)
    short = [r for r in rows if r["length"] < 5.0]
    return {"columns": n, "bare": sum(r["bare"] for r in rows),
            "bare_pct": round(100 * sum(r["bare"] for r in rows) / n, 1) if n else None,
            "short": len(short), "short_bare": sum(r["bare"] for r in short),
            "short_bare_pct": round(100 * sum(r["bare"] for r in short) / len(short), 1) if short else None,
            "table": psu.table(rows)}


def xray(plan, ppm: float, pad_mm: float = 2.0):
    """-> (BGR image with UNDERLAY runs drawn over the top thread, to_px)."""
    import cv2
    from digitizer_core import stitchviz
    from digitizer_core.adapter import plan_to_design
    design = plan_to_design(plan)
    img = stitchviz.render_design(design, ppm, pad_mm=pad_mm)
    frame = stitchviz._frame(design["stitches"], ppm, pad_mm)
    if frame is None:
        return img, None, design
    _, to_px = frame
    st = design["stitches"]
    w = max(1, int(round(0.12 * ppm)))
    satin_shapes = {r["shape"] for r in design.get("runs", []) if r["kind"] == "satin"}
    for run in design.get("runs", []):
        if run["kind"] != "underlay":
            continue
        # red under a satin shape (the subject), orange under a fill
        colour = UNDERLAY_BGR if run["shape"] in satin_shapes else FILL_UNDERLAY_BGR
        pts = [to_px(st[i]) for i in range(run["i0"], run["i1"] + 1) if st[i].get("type") == "stitch"]
        for a, b in zip(pts, pts[1:]):
            cv2.line(img, a, b, colour, w, cv2.LINE_AA)
    return img, to_px, design


def pro_xray(path: Path, ppm: float, pad_mm: float = 2.0):
    """The pro's file rendered like ours, every stitch the reader counted as
    underlay under a satin column drawn over the top thread in red. The
    file has no run kinds; red here is `tools.pro_satin_underlay`'s reading
    (the same one the counts in the PR body rest on), not a tag."""
    import cv2
    import pystitch
    from digitizer_core import stitchviz
    from digitizer_core.adapter import pattern_to_design, _u
    from tools import pro_satin_underlay as psu
    from tools.pro_parity import prep_all
    pat = pystitch.read(str(path))
    design = pattern_to_design(pat, name=path.stem, fallback_colors=list(prep_all.GREYS))
    img = stitchviz.render_design(design, ppm, pad_mm=pad_mm)
    frame = stitchviz._frame(design["stitches"], ppm, pad_mm)
    _, to_px = frame
    w = max(1, int(round(0.12 * ppm)))
    rows = psu.read_columns(psu.blocks_from_file(path), keep_segs=True)
    for r in rows:
        if r["bare"]:
            continue
        for (pa, pb) in r["under_segs"]:
            ax, ay = _u(pa[0], pa[1])
            bx, by = _u(pb[0], pb[1])
            cv2.line(img, to_px({"x": ax, "y": ay}), to_px({"x": bx, "y": by}), UNDERLAY_BGR, w, cv2.LINE_AA)
    return img, to_px, design


def rel_box(design: dict, to_px, px_box):
    """A pixel box as fractions of the design's own stitch extents."""
    from digitizer_core import stitchviz
    x0, x1, y0, y1 = stitchviz._bounds(design["stitches"])
    px0, py0 = to_px({"x": x0, "y": y1})
    px1, py1 = to_px({"x": x1, "y": y0})
    fw, fh = float(px1 - px0), float(py1 - py0)
    bx0, by0, bx1, by1 = px_box
    return ((bx0 - px0) / fw, (by0 - py0) / fh, (bx1 - px0) / fw, (by1 - py0) / fh)


def px_box_from_rel(design: dict, to_px, rel):
    from digitizer_core import stitchviz
    x0, x1, y0, y1 = stitchviz._bounds(design["stitches"])
    px0, py0 = to_px({"x": x0, "y": y1})
    px1, py1 = to_px({"x": x1, "y": y0})
    fw, fh = float(px1 - px0), float(py1 - py0)
    return (int(px0 + rel[0] * fw), int(py0 + rel[1] * fh), int(px0 + rel[2] * fw), int(py0 + rel[3] * fh))


def _crop(img, box):
    x0, y0, x1, y1 = (max(0, box[0]), max(0, box[1]), min(img.shape[1], box[2]), min(img.shape[0], box[3]))
    return img[y0:y1, x0:x1].copy()


def shape_px_box(design: dict, to_px, shape_id: str, pad_px: int):
    st = design["stitches"]
    xs, ys = [], []
    for run in design.get("runs", []):
        if run["shape"] != shape_id:
            continue
        for i in range(run["i0"], run["i1"] + 1):
            if st[i].get("type") == "stitch":
                x, y = to_px(st[i])
                xs.append(x)
                ys.append(y)
    if not xs:
        return None
    return (min(xs) - pad_px, min(ys) - pad_px, max(xs) + pad_px, max(ys) + pad_px)


def bare_shapes_off(plan, prefer: set[str] | None = None) -> list[tuple[str, int]]:
    """shape_id -> bare-by-kind satin runs, most first; shapes in `prefer`
    (the lettering) ahead of the rest."""
    from digitizer_core import stitches
    count: dict[str, int] = {}
    for b in plan.blocks:
        seen: set[str] = set()
        for r in b.runs:
            if r.kind == stitches.UNDERLAY:
                seen.add(r.shape_id)
            elif r.kind == stitches.SATIN:
                if r.shape_id not in seen:
                    count[r.shape_id] = count.get(r.shape_id, 0) + 1
                seen.discard(r.shape_id)
    prefer = prefer or set()
    return sorted(count.items(), key=lambda kv: (kv[0] not in prefer, -kv[1]))


def lettering_shapes(result) -> set[str]:
    out = set()
    for r in result.regions:
        m = getattr(r, "meta", {}) or {}
        if m.get("text_candidate") or m.get("text_cluster_id") is not None or m.get("lettering_group") is not None:
            out.add(r.shape_id)
    return out


def _label(img, text):
    import cv2
    im = img.copy()
    cv2.rectangle(im, (0, 0), (im.shape[1], 30), (255, 255, 255), -1)
    cv2.putText(im, text, (6, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2, cv2.LINE_AA)
    return im


def _row(tiles):
    import cv2
    import numpy as np
    h = max(t.shape[0] for t in tiles)
    pad = lambda im: cv2.copyMakeBorder(im, 0, h - im.shape[0], 0, 0, cv2.BORDER_CONSTANT, value=(255, 255, 255))
    gap = np.full((h, 12, 3), 255, np.uint8)
    out = []
    for t in tiles:
        if out:
            out.append(gap)
        out.append(pad(t))
    return np.concatenate(out, axis=1)


def run_fixture(slug: str, out: Path, pro_root: Path, ppm_crop: float = 40.0) -> dict:
    import cv2
    from digitizer_core.export import write_dst
    from tools.pro_pair import digitize

    art, width, garment, pro_rel = FIXTURES[slug]
    if not art.exists():
        return {"fixture": slug, "skipped": f"art missing: {art}"}
    res: dict = {"fixture": slug, "art": art.name, "width_mm": width, "garment": garment}
    plans = {}
    letters: set[str] = set()
    for arm, extra in (("off", {}), ("on", {FLAG: True})):
        t = time.time()
        cache = out / f"{slug}_{arm}.plan.pkl"
        if cache.exists():
            plans[arm], letters = pickle.loads(cache.read_bytes())
            d = None
        else:
            d = digitize(art, width, garment, extra)
            plans[arm] = d.plan
            letters = lettering_shapes(d.result)
            cache.write_bytes(pickle.dumps((d.plan, letters)))
        dst = write_dst(plans[arm], out / f"{slug}_{arm}.dst", f"{slug[:8]} {arm}".upper())
        res[arm] = {"secs": round(time.time() - t, 1), "stitches": plans[arm].stats.stitch_count,
                    "trims": plans[arm].stats.trims, "by_kind": bare_by_kind(plans[arm]),
                    "by_instrument": by_instrument(dst)}
    pro = pro_root / pro_rel
    if pro.exists():
        res["pro"] = {"file": pro.name, "by_instrument": by_instrument(pro)}
    else:
        res["pro"] = {"file": str(pro), "missing": True}

    # renders: OFF | ON | pro, the pro's underlay as the reader counts it
    pro_ok = pro.exists()
    full = {arm: xray(plans[arm], 20.0) for arm in ("off", "on")}
    panels = [_label(full["off"][0], f"{slug} {width} mm {garment} OFF  (satin underlay red, fill underlay orange)"),
              _label(full["on"][0], f"{slug} ON ({FLAG})")]
    if pro_ok:
        pro_full = pro_xray(pro, 20.0)
        panels.append(_label(pro_full[0], f"pro {pro.name}  (underlay as read)"))
    cv2.imwrite(str(out / f"{slug}_xray_off_on_pro_20pxmm.png"), _row(panels))
    # the two lettering shapes with the most bare columns OFF, same crop on
    # all three: ours by the shape's stitch box, the pro's by that box as a
    # fraction of the design's extents (no registration -- the same logo at
    # the same width, so a fraction lands on the same letter, give or take)
    picks = [sid for sid, _n in bare_shapes_off(plans["off"], letters) if sid][:2]
    res["crops"] = []
    arms = {arm: xray(plans[arm], ppm_crop) for arm in ("off", "on")}
    pro_crop = pro_xray(pro, ppm_crop) if pro_ok else None
    for k, sid in enumerate(picks, start=1):
        box = shape_px_box(arms["off"][2], arms["off"][1], sid, int(2.0 * ppm_crop))
        if box is None:
            continue
        rel = rel_box(arms["off"][2], arms["off"][1], box)
        tiles = [_label(_crop(arms["off"][0], box), f"{sid} OFF"),
                 _label(_crop(arms["on"][0], px_box_from_rel(arms["on"][2], arms["on"][1], rel)), f"{sid} ON")]
        if pro_crop is not None:
            tiles.append(_label(_crop(pro_crop[0], px_box_from_rel(pro_crop[2], pro_crop[1], rel)), "pro, same box"))
        p = out / f"{slug}_letter{k}_{sid}_off_on_pro_40pxmm.png"
        cv2.imwrite(str(p), _row(tiles))
        res["crops"].append(p.name)
    return res


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", required=True)
    ap.add_argument("--fixtures", default="fremont,becker,mfab")
    ap.add_argument("--pro-root", default=str(PRO_ROOT))
    a = ap.parse_args(argv)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    results = []
    for slug in a.fixtures.split(","):
        r = run_fixture(slug.strip(), out, Path(a.pro_root))
        results.append(r)
        brief = {k: v for k, v in r.items() if k not in ("off", "on", "pro")}
        for arm in ("off", "on", "pro"):
            if arm in r and isinstance(r[arm], dict):
                bi = r[arm].get("by_instrument", {})
                brief[arm] = {k: bi.get(k) for k in ("columns", "bare_pct", "short", "short_bare_pct")}
                if "by_kind" in r[arm]:
                    brief[arm]["kind_bare_pct"] = r[arm]["by_kind"]["bare_pct"]
                    brief[arm]["kind_short_bare_pct"] = r[arm]["by_kind"]["short_bare_pct"]
                    brief[arm]["stitches"] = r[arm]["stitches"]
        print(json.dumps(brief))
        sys.stdout.flush()
    (out / "results.json").write_text(json.dumps(results, indent=1, default=str), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
