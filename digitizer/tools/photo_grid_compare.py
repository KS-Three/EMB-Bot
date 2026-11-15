"""`photo_work_grid` OFF against ON, one design at a time.

Built 2026-11-14 for Kent's ruling on `cfg.photo_work_grid` (MFab's small
line under a white slab at some sizes; memory `mfab-photo-route-2026-11-04`).

    # one digitize: a JSON line on stdout, the design saved for the sheets
    python -m tools.photo_grid_compare run NAME ART WIDTH_MM GARMENT off|on OUTDIR
    # art | OFF | ON | pro for every width of NAME found in OUTDIR
    python -m tools.photo_grid_compare sheet NAME ART OUTDIR [PRO] [--band Y0 Y1]
    # stage 0 only: which designs take the photo lane
    python -m tools.photo_grid_compare classify WIDTH GARMENT ART [ART ...]

Each run goes through `tools.pro_pair` (the Studio's request, the service's
parser). It records the design class, the working grid, the regions and how
many of them are text-tagged (`text_candidate`), stitches, trims, wall and
CPU seconds, and preflight's grade, score and finding codes. `--band` is the
sheet's zoom row, as fractions of the design's height (default 0.5-0.9:
MFab's "AND WELDING LLC").
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import cv2
import numpy as np

DIGITIZER = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(DIGITIZER))

PX = 8.0           # sheet px per mm
ZOOM = 2.5         # the zoom row's scale over PX


def run(name: str, art: str, width: float, garment: str, arm: str, outdir: Path) -> dict:
    from digitizer_core.adapter import plan_to_design
    from digitizer_core.pipeline import build_generation, finish_generation, plan_stitches
    from digitizer_core.preflight import run_preflight
    from digitizer_service.app import _decode
    from tools import pro_pair

    cfg = pro_pair.config(width, garment, {"photo_work_grid": arm == "on"})
    data = Path(art).read_bytes()
    c0, t0 = time.process_time(), time.perf_counter()
    gen = build_generation(_decode(data), cfg, exif_source=data)
    result = finish_generation(gen.fork(), cfg)
    plan = plan_stitches(result, cfg)
    secs, cpu = time.perf_counter() - t0, time.process_time() - c0
    try:
        pf = run_preflight(result, plan, cfg)
    except Exception as e:  # noqa: BLE001 -- a broken preflight is a finding
        pf = {"grade": None, "score": None, "findings": [], "error": str(e)[:200]}
    design = plan_to_design(plan, name=f"{name}_{width}_{arm}")
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / f"{name}_{width}_{arm}.design.json").write_text(json.dumps(design), encoding="utf-8")
    tagged = [r for r in result.regions if (r.meta or {}).get("text_candidate")]
    return {"name": name, "width": width, "garment": garment, "arm": arm,
            "class": gen.classification_class, "px_per_mm": round(float(gen.p.px_per_mm), 2),
            "regions": len(result.regions), "text_tagged": len(tagged),
            "stitches": plan.stats.stitch_count, "trims": plan.stats.trims,
            "secs": round(secs, 1), "cpu": round(cpu, 1),
            "grade": pf.get("grade"), "score": pf.get("score"),
            "findings": sorted({f.get("code") for f in (pf.get("findings") or []) if isinstance(f, dict)})}


def _render(design: dict, px: float) -> np.ndarray:
    from digitizer_core.stitchviz import render_design
    return render_design(design, px_per_mm=px, pad_mm=1.0)


def _label(img: np.ndarray, text: str) -> np.ndarray:
    bar = np.full((24, img.shape[1], 3), 255, np.uint8)
    cv2.putText(bar, text[:140], (4, 17), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (0, 0, 0), 1, cv2.LINE_AA)
    return np.vstack([bar, img])


def _fit(img: np.ndarray, w: int, h: int) -> np.ndarray:
    s = min(w / img.shape[1], h / img.shape[0])
    im = cv2.resize(img, (max(1, int(img.shape[1] * s)), max(1, int(img.shape[0] * s))),
                    interpolation=cv2.INTER_AREA)
    out = np.full((h, w, 3), 255, np.uint8)
    out[:im.shape[0], :im.shape[1]] = im
    return out


def _art(path: str) -> np.ndarray:
    im = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    if im.ndim == 3 and im.shape[2] == 4:
        a = im[..., 3:4].astype(np.float32) / 255.0
        im = (im[..., :3].astype(np.float32) * a + 255.0 * (1 - a)).astype(np.uint8)
    elif im.ndim == 2:
        im = cv2.cvtColor(im, cv2.COLOR_GRAY2BGR)
    return im


def sheet(name: str, art: str, outdir: Path, pro: str | None, band=(0.5, 0.9)) -> list[Path]:
    rows = {}
    for line in (outdir / "runs.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("{"):
            r = json.loads(line)
            if r["name"] == name:
                rows[(r["width"], r["arm"])] = r
    pro_img = None
    if pro:
        from tools import pro_baseline as pb
        from tools.eye_pairs.filearm import design_from_file
        pro_img = _render(design_from_file(pb.resolve(pro)), PX)
    art_img = _art(art)
    out = []
    for width in sorted({w for w, _a in rows}):
        off, on = rows.get((width, "off")), rows.get((width, "on"))
        if not off or not on:
            continue
        imgs = {a: _render(json.loads((outdir / f"{name}_{width}_{a}.design.json").read_text(encoding="utf-8")), PX)
                for a in ("off", "on")}
        W = max(i.shape[1] for i in imgs.values())
        H = max(i.shape[0] for i in imgs.values())
        panels = [_label(_fit(art_img, W, H), "art"),
                  *[_label(_fit(imgs[a], W, H),
                           f"{a.upper()} {r['class']} {r['px_per_mm']} px/mm, {r['text_tagged']} tagged, "
                           f"{r['stitches']} st, {r['trims']} trims, {r['secs']} s, grade {r['grade']}")
                    for a, r in (("off", off), ("on", on))]]
        if pro_img is not None:
            panels.append(_label(_fit(pro_img, W, H), "pro (its own size)"))
        top = np.hstack([np.pad(p, ((0, 0), (0, 6), (0, 0)), constant_values=60) for p in panels])
        zooms = []
        for p in panels:
            body = p[24:]
            y0, y1 = int(band[0] * body.shape[0]), int(band[1] * body.shape[0])
            z = body[y0:y1]
            z = cv2.resize(z, (int(z.shape[1] * ZOOM), int(z.shape[0] * ZOOM)), interpolation=cv2.INTER_CUBIC)
            zooms.append(np.pad(z, ((0, 0), (0, int(6 * ZOOM)), (0, 0)), constant_values=60))
        zrow = np.hstack(zooms)
        zrow = cv2.resize(zrow, (top.shape[1], int(zrow.shape[0] * top.shape[1] / zrow.shape[1])))
        title = np.full((30, top.shape[1], 3), 255, np.uint8)
        cv2.putText(title, f"{name} at {width} mm ({off['garment']}): photo_work_grid OFF | ON",
                    (6, 21), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 0, 0), 1, cv2.LINE_AA)
        path = outdir / "sheets" / f"{name}_{width}_off_on_pro.png"
        path.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(path), np.vstack([title, top, zrow]))
        out.append(path)
    return out


def classify_many(width: float, garment: str, arts: list[str]) -> list[dict]:
    from digitizer_core.pipeline import classify
    from digitizer_service.app import _decode
    from tools import pro_pair
    cfg = pro_pair.config(width, garment, {})
    out = []
    for a in arts:
        try:
            c = classify(_decode(Path(a).read_bytes()), cfg)
            out.append({"art": a, "class": c.class_})
        except Exception as e:  # noqa: BLE001
            out.append({"art": a, "class": None, "error": str(e)[:120]})
    return out


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    cmd = argv.pop(0)
    if cmd == "run":
        name, art, width, garment, arm, outdir = argv
        print(json.dumps(run(name, art, float(width), garment, arm, Path(outdir))), flush=True)
        return 0
    if cmd == "sheet":
        band = (0.5, 0.9)
        if "--band" in argv:
            i = argv.index("--band")
            band = (float(argv[i + 1]), float(argv[i + 2]))
            argv = argv[:i] + argv[i + 3:]
        name, art, outdir, *pro = argv
        for p in sheet(name, art, Path(outdir), pro[0] if pro else None, band):
            print(p)
        return 0
    if cmd == "classify":
        width, garment, *arts = argv
        for r in classify_many(float(width), garment, arts):
            print(json.dumps(r), flush=True)
        return 0
    raise SystemExit(f"unknown command {cmd}")


if __name__ == "__main__":
    raise SystemExit(main())
