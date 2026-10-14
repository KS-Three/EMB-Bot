"""Fur regions on the streamline tier: the gate's census and the bill (2026-10-13).

    python -m tools.fur_regions_census run    [--fixtures a,b] [--force]
    python -m tools.fur_regions_census table
    python -m tools.fur_regions_census render --fixture photo/owl_kent.jpg@studio

`cfg.hair_regions_directional` (default OFF, `digitizer_core/fur_regions.py`)
sends a region the hair gate reads as FUR to the `streamline` tier. This
tool answers three questions per fixture, 80 mm / left_chest, 40 wt:

1. **What the gate reads** (`census`): per stitched auto-tier region, its
   area, the ridge-test strands inside it, strand mm per mm2, and the verdict.
   The table reports the densest region of at least `FUR_MIN_AREA_MM2`, so a
   reader can see how far every fixture sits from the threshold.
2. **Whether anything moved**: stages 0-4 run ONCE (`build_generation`), then
   `finish_generation` + `plan_stitches` with the flag OFF and ON, and the
   two stitch streams are compared by md5 (x, y, kind, jump, trim, thread).
3. **The bill, where it moved**: stitches, trims, colour changes, thread
   laid, thread over bare fabric by #895's corrected reader
   (`tools.hairline_travel.measure_plan`, flights excluded), preflight's
   DENSITY_STACKED finding and stacked-coverage area, and bare artwork
   (`ARTWORK_UNCOVERED`'s metrics from `run_preflight` with the image).

A fixture spec is `path[@route]`: `file` (default; `corpus_scorecard`'s
MATRIX[0]), `studio` (the Studio's photo signals, as #876's trial ran it)
or `classical` (`forced_class=photo_subject`, `photo_prep=False`).

Writes `rows.json` and `table.md` under docs/renders/claude-hair-region-
directional-fill/; render strips go there too, their lossless parts to
digitizer/.cache/fur-regions/. Every number is a property of the FILE, not of
cloth (ROADMAP gate 1).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import time
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from digitizer_core import PipelineConfig, fur_regions, stitchviz  # noqa: E402
from digitizer_core.adapter import UNITS_PER_MM, plan_to_design  # noqa: E402
from digitizer_core.pipeline import build_generation, finish_generation, plan_stitches  # noqa: E402
from digitizer_core.preflight import run_preflight  # noqa: E402
from tools import corpus_scorecard as sc  # noqa: E402
from tools._console import utf8_console  # noqa: E402
from tools.hairline_travel import measure_plan  # noqa: E402

TESTDATA = sc.TESTDATA
OUT_DIR = ROOT.parent / "docs" / "renders" / "claude-hair-region-directional-fill"
PARTS = ROOT / ".cache" / "fur-regions"
ROUTES = {
    "file": dict(sc.MATRIX[0]),
    "studio": {"target_width_mm": 80.0, "detect_photographic": True, "faces_route_flat": True},
    "classical": {"target_width_mm": 80.0, "forced_class": "photo_subject", "photo_prep": False},
}
# The scorecard's 26 (the nine logos among them), plus the one real fur photo
# by the Studio's route and by the photo lane's.
DEFAULT = [*sc.FIXTURES, "photo/owl_kent.jpg@studio", "photo/owl_kent.jpg@classical"]
RENDER_PX_PER_MM = 6.0
ZOOM_PX_PER_MM = 16.0
MAX_JPEG_BYTES = 290_000


def split(spec: str) -> tuple[str, str]:
    path, _, route = spec.partition("@")
    return path, route or "file"


def cfgs(route: str) -> tuple[PipelineConfig, PipelineConfig]:
    base = ROUTES[route]
    return (PipelineConfig(**base, hair_regions_directional=False),
            PipelineConfig(**base, hair_regions_directional=True))


def plan_md5(plan) -> str:
    coords = [[round(x, 4), round(y, 4), r.kind, r.jump, r.trim, b.thread_index]
              for b, r in plan.iter_runs() for x, y in r.points]
    return hashlib.md5(json.dumps(coords).encode()).hexdigest()


def bill(result, plan, cfg, image) -> dict:
    st = plan.stats
    thread_mm = sum(math.dist(a, c) for b in plan.blocks for r in b.runs
                    for a, c in zip(r.points, r.points[1:]))
    travel = measure_plan(plan, with_legacy=False)
    pf = run_preflight(result, plan, cfg, image=image)
    m = pf["metrics"]
    dens = [f for f in pf["findings"] if f["code"] == "DENSITY_STACKED"]
    return {
        "stitches": st.stitch_count, "trims": st.trims, "color_changes": st.color_changes,
        "thread_m": round(thread_mm / 1000.0, 2),
        "thread_bare_mm": travel["thread_bare_mm"], "flight_bare_mm": travel["flight_bare_mm"],
        "density_stacked": ([{k: f.get(k) for k in ("severity", "over_warn_mm2", "over_block_mm2",
                                                      "peak_units", "patches")} for f in dens]
                            or None),
        "coverage_over_warn_mm2": m.get("coverage_over_warn_mm2"),
        "coverage_over_block_mm2": m.get("coverage_over_block_mm2"),
        "uncovered_total_mm2": m.get("uncovered_total_mm2"),
        "uncovered_wanted_mm2": m.get("uncovered_wanted_mm2"),
        "grade": pf.get("grade"),
    }


def run_one(spec: str, keep: dict | None = None) -> dict:
    path, route = split(spec)
    image = TESTDATA / path
    off_cfg, on_cfg = cfgs(route)
    t0 = time.perf_counter()
    gen = build_generation(image, off_cfg)
    t1 = time.perf_counter()
    res_off = finish_generation(gen.fork(), off_cfg)
    res_on = finish_generation(gen.fork(), on_cfg)
    t2 = time.perf_counter()
    read = res_on.hair_fur_read
    plan_off = plan_stitches(res_off, off_cfg)
    plan_on = plan_stitches(res_on, on_cfg)
    t3 = time.perf_counter()
    m_off, m_on = plan_md5(plan_off), plan_md5(plan_on)
    big = {s: v for s, v in (read or {}).items() if v["area_mm2"] >= fur_regions.FUR_MIN_AREA_MM2}
    densest = max(big.items(), key=lambda kv: kv[1]["density"], default=None)
    row = {
        "fixture": path, "route": route, "class": res_on.design_class,
        "min_density": fur_regions.FUR_MIN_STRAND_DENSITY,
        "gate_ran": read is not None, "regions_read": len(read or {}),
        "fur_ids": list(res_on.hair_fur_ids or ()),
        "densest": (None if densest is None else {"id": densest[0], **densest[1]}),
        # Only the regions the area floor lets the gate judge: the rest are
        # not fur by construction, and listing them all made the file huge.
        "read": (None if read is None else big),
        "md5_off": m_off, "md5_on": m_on, "identical": m_off == m_on,
        "seconds": {"stages0_4": round(t1 - t0, 1), "finish_x2_with_gate": round(t2 - t1, 1),
                    "plan_x2": round(t3 - t2, 1)},
    }
    if m_off != m_on:
        row["off"] = bill(res_off, plan_off, off_cfg, image)
        row["on"] = bill(res_on, plan_on, on_cfg, image)
    if keep is not None:
        keep.update(res_off=res_off, res_on=res_on, plan_off=plan_off, plan_on=plan_on)
    return row


def _load(out: Path) -> dict:
    f = out / "rows.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}


def cmd_run(args) -> int:
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    specs = args.fixtures.split(",") if args.fixtures else list(DEFAULT)
    for spec in specs:
        rows = _load(out)
        if spec in rows and "error" not in rows[spec] and not args.force:
            print(f"{spec}: cached")
            continue
        try:
            rows[spec] = run_one(spec)
        except Exception as exc:  # noqa: BLE001 -- one bad fixture must not sink the run
            rows[spec] = {"fixture": spec, "error": f"{type(exc).__name__}: {exc}"}
        r = rows[spec]
        if "error" in r:
            print(f"{spec}: ERROR {r['error']}", flush=True)
        else:
            d = r["densest"]
            print(f"{spec}: class {r['class']} fur {len(r['fur_ids'])} identical {r['identical']} "
                  f"densest {None if d is None else (d['density'], d['strands'], d['area_mm2'])} "
                  f"{r['seconds']}", flush=True)
        (out / "rows.json").write_text(json.dumps(rows, indent=1) + "\n", encoding="utf-8")
    return 0


def markdown(rows: dict) -> str:
    ok = {k: r for k, r in rows.items() if "error" not in r}
    lines = [
        f"Gate: area >= {fur_regions.FUR_MIN_AREA_MM2:g} mm2, >= {fur_regions.FUR_MIN_STRANDS} strands, "
        "strand mm per mm2 at the row's own `min density`. 80 mm, 40 wt.", "",
        "| fixture | route | class | gate ran | regions read | min density | fur | densest region >= area floor "
        "(id, mm/mm2, strands, mm2) | OFF vs ON |",
        "|---|---|---|---|---|---|---|---|---|"]
    for k, r in ok.items():
        d = r["densest"]
        dd = "-" if d is None else f"{d['id']} {d['density']:.3f} / {d['strands']} / {d['area_mm2']:.0f}"
        lines.append(f"| {r['fixture']} | {r['route']} | {r['class']} | {'yes' if r['gate_ran'] else 'no'} "
                     f"| {r['regions_read']} | {r.get('min_density', 0.25):g} | {len(r['fur_ids'])} | {dd} | "
                     f"{'identical' if r['identical'] else '**moved**'} |")
    moved = {k: r for k, r in ok.items() if not r["identical"]}
    if moved:
        keys = ["stitches", "trims", "color_changes", "thread_m", "thread_bare_mm", "flight_bare_mm",
                "coverage_over_warn_mm2", "coverage_over_block_mm2", "uncovered_total_mm2",
                "uncovered_wanted_mm2", "grade"]
        lines += ["", "### The bill where it moved (OFF -> ON)", "",
                  "| fixture | " + " | ".join(keys) + " | DENSITY_STACKED |",
                  "|---|" + "---|" * (len(keys) + 1)]
        for k, r in moved.items():
            cells = [f"{r['off'][x]} -> {r['on'][x]}" for x in keys]
            ds = f"{r['off']['density_stacked']} -> {r['on']['density_stacked']}"
            lines.append(f"| {k} | " + " | ".join(cells) + f" | {ds} |")
    bad = {k: r["error"] for k, r in rows.items() if "error" in r}
    if bad:
        lines += ["", "### Errors", ""] + [f"- {k}: {e}" for k, e in bad.items()]
    return "\n".join(lines) + "\n"


def cmd_table(args) -> int:
    out = Path(args.out)
    text = markdown(_load(out))
    (out / "table.md").write_text(text, encoding="utf-8")
    print(text)
    return 0


def _write_jpeg(path: Path, img) -> None:
    q = 85
    while True:
        ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, q])
        if len(buf) <= MAX_JPEG_BYTES or (q <= 60 and img.shape[1] < 400):
            break
        if q > 60:
            q -= 8
        else:
            img = cv2.resize(img, (img.shape[1] * 4 // 5, img.shape[0] * 4 // 5),
                             interpolation=cv2.INTER_AREA)
    path.write_bytes(buf.tobytes())


def _panel(img, label: str):
    band = np.full((30, img.shape[1], 3), 255, np.uint8)
    cv2.putText(band, label, (6, 21), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (30, 30, 30), 1, cv2.LINE_AA)
    return np.vstack([band, img])


def _side_by_side(tiles):
    h = max(t.shape[0] for t in tiles)
    padded = [np.vstack([t, np.full((h - t.shape[0], t.shape[1], 3), 255, np.uint8)]) for t in tiles]
    sep = np.full((h, 8, 3), 255, np.uint8)
    out = []
    for t in padded:
        out += [t, sep]
    return np.hstack(out[:-1])


def _crop(design, box_mm, px_per_mm):
    """`box_mm` = (x0, y0, x1, y1) in plan mm (y down) -> that window of the
    render at `px_per_mm`, the same window for every arm."""
    img = stitchviz.render_design(design, px_per_mm=px_per_mm)
    _size, to_px = stitchviz._frame(design.get("stitches") or [], px_per_mm, 2.0)
    a = to_px({"x": box_mm[0] * UNITS_PER_MM, "y": -box_mm[1] * UNITS_PER_MM})
    b = to_px({"x": box_mm[2] * UNITS_PER_MM, "y": -box_mm[3] * UNITS_PER_MM})
    x0, x1 = sorted((int(a[0]), int(b[0])))
    y0, y1 = sorted((int(a[1]), int(b[1])))
    return img[max(y0, 0):max(y1, 1), max(x0, 0):max(x1, 1)]


def cmd_render(args) -> int:
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    PARTS.mkdir(parents=True, exist_ok=True)
    keep: dict = {}
    row = run_one(args.fixture, keep)
    path, route = split(args.fixture)
    stem = Path(path).stem + ("" if route == "file" else f"_{route}")
    d_off = plan_to_design(keep["plan_off"], name=f"{stem} OFF")
    d_on = plan_to_design(keep["plan_on"], name=f"{stem} ON")
    tiles = []
    for d, label in ((d_off, "OFF (today)"), (d_on, "hair_regions_directional ON")):
        img = stitchviz.render_design(d, px_per_mm=RENDER_PX_PER_MM)
        cv2.imwrite(str(PARTS / f"{stem}_{label[:3].strip()}.png"), img)
        tiles.append(_panel(img, label))
    _write_jpeg(out / f"{stem}_off_on.jpg", _side_by_side(tiles))
    written = [f"{stem}_off_on.jpg"]
    # Zoom: the fur regions' box when the gate found any, else the region
    # it read densest (so a negative shows where the gate looked hardest).
    ids = row["fur_ids"] or ([row["densest"]["id"]] if row["densest"] else [])
    polys = [r.polygon for r in keep["res_on"].regions if r.shape_id in ids]
    if polys:
        x0 = min(p.bounds[0] for p in polys) - 2
        y0 = min(p.bounds[1] for p in polys) - 2
        x1 = max(p.bounds[2] for p in polys) + 2
        y1 = max(p.bounds[3] for p in polys) + 2
        zt = [_panel(_crop(d, (x0, y0, x1, y1), ZOOM_PX_PER_MM), f"{label}, {ZOOM_PX_PER_MM:g} px/mm")
              for d, label in ((d_off, "OFF"), (d_on, "ON"))]
        _write_jpeg(out / f"{stem}_off_on_zoom.jpg", _side_by_side(zt))
        written.append(f"{stem}_off_on_zoom.jpg")
    print(json.dumps({"fixture": args.fixture, "fur_ids": row["fur_ids"], "identical": row["identical"],
                      "zoom_ids": ids, "written": written}))
    return 0


def main(argv=None) -> int:
    utf8_console()
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", default=str(OUT_DIR))
    ap.add_argument("--min-density", type=float, default=None,
                    help="override fur_regions.FUR_MIN_STRAND_DENSITY for this run (a looser candidate)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--fixtures", default="")
    r.add_argument("--force", action="store_true")
    r.set_defaults(fn=cmd_run)
    t = sub.add_parser("table")
    t.set_defaults(fn=cmd_table)
    d = sub.add_parser("render")
    d.add_argument("--fixture", default="photo/owl_kent.jpg@studio")
    d.set_defaults(fn=cmd_render)
    args = ap.parse_args(argv)
    if args.min_density is not None:
        fur_regions.FUR_MIN_STRAND_DENSITY = args.min_density
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
