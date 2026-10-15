"""Counter census: the smallest source counter of every text line, beside that
line's win or loss under the true-size switch (2026-10-15, measure only).

The true-size flip (#955) is replacing its cap-height guard with a
COUNTER-WIDTH guard: the switch acts on a line only if the line's smallest
counter is at least 0.5 mm across (scaled by thread weight / 40; a line with
no counter passes). This reads that quantity over the 17-design corpus of
`tools/small_lettering_compare.py` and Fremont's Hat at 65 / 72 / 81 / 92.5 mm,
so the value can be checked before it is built.

Per design, two digitizes, the way the corpus cells run them: `main` (switch
off) and `switch` (`small_text_true_size` + `small_text_keep_stray_lines`, as
#955 will ship it). Per text line of the SWITCH run (a text cluster that
`small_text._core` reads as one line of three or more letters):

- cap: the median member height (mm);
- min counter: the smallest inscribed width (mm) of any hole in the line's
  members, rasterised at `PPM` px/mm. The switch's restore step retraces
  lines under its 3.0 mm cap from the source raster, so for small lettering
  these ARE the source counters; taller lines keep the tracer's holes.
  None: no counter;
- tier: how many members sewed as bean letters under the switch;
- changed: whether any member's stitches differ from main (per-shape digest);
- verdict: on Fremont, whose words `glyph_legibility` reads, WIN / LOSS / TIE
  from that word's OCR glyphs recovered, then legibility (+-0.02); elsewhere
  "unchanged" or "changed (no reader)".

    python -m tools.counter_census --design fremont_hat65 --out DIR
    python -m tools.counter_census --table --out DIR        # from saved rows

No engine change, no flag flipped (ROADMAP gate 1: the 0.5 mm is a candidate).
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import cv2  # noqa: E402
import numpy as np  # noqa: E402

PPM = 40.0                       # raster for a hole's inscribed width
MIN_HOLE_MM2 = 0.003             # a hole smaller than this is tracer dust
GUARD_MM = 0.5                   # the candidate the flip lane will build
SWITCH = {"small_text_true_size": True, "small_text_keep_stray_lines": True}
EXTRA_HATS = {"fremont_hat65": 65.0, "fremont_hat72": 72.0}
FREMONT_HATS = ("fremont_hat65", "fremont_hat72", "fremont_hat81", "fremont_hat925")
FREMONT_WORDS = ("est", "1895", "the", "tagline")


def inscribed_width_mm(ring) -> float:
    """Twice the largest distance from inside the ring to its edge, in mm."""
    pts = np.asarray(ring.coords, np.float64)[:, :2]
    x0, y0 = pts.min(axis=0) - 0.1
    w = int(np.ceil((pts[:, 0].max() - x0 + 0.1) * PPM)) + 2
    h = int(np.ceil((pts[:, 1].max() - y0 + 0.1) * PPM)) + 2
    m = np.zeros((h, w), np.uint8)
    cv2.fillPoly(m, [np.round((pts - [x0, y0]) * PPM).astype(np.int32)], 1)
    if not m.any():
        return 0.0
    d = cv2.distanceTransform(m, cv2.DIST_L2, 5)
    return round(2.0 * float(d.max()) / PPM, 3)


def lines_of(regions) -> list[dict]:
    """Every text line in `regions`: cap, smallest counter, member ids."""
    from shapely.geometry import Polygon
    from digitizer_core.small_text import _core, _height
    clusters: dict[str, list] = {}
    for r in regions:
        cid = r.meta.get("text_cluster_id")
        if cid:
            clusters.setdefault(cid, []).append(r)
    out = []
    for cid in sorted(clusters):
        line = _core(clusters[cid])
        if len(line) < 3:
            continue
        widths = []
        for r in line:
            geoms = [r.polygon] if r.polygon.geom_type == "Polygon" else list(getattr(r.polygon, "geoms", []))
            for g in geoms:
                for hole in g.interiors:
                    if Polygon(hole).area >= MIN_HOLE_MM2:
                        widths.append(inscribed_width_mm(hole))
        b = np.array([r.polygon.bounds for r in line])
        out.append({"cluster": cid, "members": [r.shape_id for r in line], "n": len(line),
                    "cap_mm": round(float(np.median([_height(r) for r in line])), 3),
                    "min_counter_mm": min(widths) if widths else None, "counters": len(widths),
                    "bean": sum(1 for r in line if r.meta.get("bean_letter_spines")),
                    "box_mm": [round(float(v), 2) for v in (b[:, 0].min(), b[:, 1].min(), b[:, 2].max(), b[:, 3].max())]})
    return out


def _run(name: str, overrides: dict, scratch: Path) -> dict:
    """One digitize of a corpus design (or an extra Fremont Hat width)."""
    from tools import small_lettering_compare as slc
    from tools import fremont_triage as ft
    if name in EXTRA_HATS:
        return ft.run_arm(name, EXTRA_HATS[name], None, preflight=False, overrides=overrides)
    spec = slc.corpus_designs()[name]
    if spec["kind"] == "logo":
        return slc._digitize(spec["path"], {**spec["cfg"], **overrides})
    if spec["kind"] == "hat":
        return ft.run_arm(name, spec["width_mm"], None, preflight=False, overrides=overrides)
    run, _extra = slc._digitize_small_print(spec, overrides, scratch)
    return run


def _fremont_words(run: dict) -> dict:
    """Fremont's four words: box (design mm), OCR recovered / read, legibility."""
    from digitizer_core.adapter import plan_to_design
    from tools import fremont_triage as ft
    from tools import glyph_legibility as gl
    design = run.get("design") or plan_to_design(run["plan"], name="x")
    words, _d, _r = gl.read_case("fremont", design, use_ocr=True, words=list(FREMONT_WORDS))
    p = run["gen"].p
    out = {}
    for w in words:
        s = w.summary()
        o = s.get("ocr") if isinstance(s.get("ocr"), dict) else {}
        out[w.name] = {"box_mm": [round(float(v), 2) for v in ft.roi_mm(p, ft.ROIS[w.name])],
                       "ocr": [o.get("recovered"), o.get("read_on_source")],
                       "legibility": round(float(s["legibility"]), 3) if s.get("legibility") is not None else None}
    return out


def _verdict(m: dict, s: dict) -> str:
    mo, so = m["ocr"][0] or 0, s["ocr"][0] or 0
    if so != mo:
        return "WIN" if so > mo else "LOSS"
    ml, sl = m["legibility"], s["legibility"]
    if ml is None or sl is None or abs(sl - ml) < 0.02:
        return "TIE"
    return "WIN" if sl > ml else "LOSS"


def census_design(name: str, out: Path) -> dict:
    from tools.hairline_logo_bill import shape_digests
    t = time.time()
    scratch = out / "_scratch"
    main = _run(name, {}, scratch)
    sw = _run(name, dict(SWITCH), scratch)
    dm, ds = shape_digests(main["plan"]), shape_digests(sw["plan"])
    rows = lines_of(sw["result"].regions)
    words = None
    if name.startswith("fremont_hat"):
        words = {"main": _fremont_words(main), "switch": _fremont_words(sw)}
    for row in rows:
        row["changed"] = any(dm.get(i) != ds.get(i) for i in row["members"])
        row["word"] = None
        row["verdict"] = "changed (no reader)" if row["changed"] else "unchanged"
        if words:
            x0, y0, x1, y1 = row["box_mm"]
            cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
            hits = [w for w, v in words["switch"].items()
                    if v["box_mm"][0] <= cx <= v["box_mm"][2] and v["box_mm"][1] <= cy <= v["box_mm"][3]]
            if hits:
                w = hits[0]
                row["word"] = w
                row["main"], row["switch"] = words["main"][w], words["switch"][w]
                row["verdict"] = _verdict(words["main"][w], words["switch"][w])
    rec = {"design": name, "lines": rows, "secs": round(time.time() - t),
           "stitches": [main["plan"].stats.stitch_count, sw["plan"].stats.stitch_count]}
    out.mkdir(parents=True, exist_ok=True)
    (out / f"census_{name}.json").write_text(json.dumps(rec, indent=1, default=str))
    for r in rows:
        print(f"{name:22s} {r['cluster']:16s} n={r['n']:2d} cap={r['cap_mm']:.2f} "
              f"min_counter={r['min_counter_mm']} counters={r['counters']} bean={r['bean']} "
              f"{r['word'] or '-':8s} {r['verdict']}", flush=True)
    print(f"{name}: {len(rows)} lines, {rec['secs']} s", flush=True)
    return rec


def table(out: Path) -> str:
    recs = [json.loads(p.read_text()) for p in sorted(out.glob("census_*.json"))]
    lines = ["| design | line | letters | cap mm | min counter mm | counters | bean | word | verdict | guard 0.5 |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    for rec in recs:
        for r in rec["lines"]:
            mc = r["min_counter_mm"]
            guard = "pass (no counter)" if mc is None else ("pass" if mc >= GUARD_MM else "HOLD")
            lines.append(f"| {rec['design']} | {r['cluster']} | {r['n']} | {r['cap_mm']:.2f} | "
                         f"{'-' if mc is None else f'{mc:.2f}'} | {r['counters']} | {r['bean']} | "
                         f"{r.get('word') or '-'} | {r['verdict']} | {guard} |")
    return "\n".join(lines)


def designs() -> list[str]:
    from tools import small_lettering_compare as slc
    return list(slc.corpus_designs()) + list(EXTRA_HATS)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--design", help="one design: a corpus design or fremont_hat65 / fremont_hat72")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--table", action="store_true")
    ap.add_argument("--out", default=str(ROOT.parent / "docs" / "renders" / "counter-census-2026-10-15"))
    a = ap.parse_args(argv)
    out = Path(a.out)
    if a.list:
        print("\n".join(designs()))
        return 0
    if a.table:
        print(table(out))
        return 0
    if not a.design or a.design not in designs():
        raise SystemExit(f"--design in {designs()}")
    census_design(a.design, out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
