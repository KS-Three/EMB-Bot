"""Hairline line route on the GRADIENT lane, as a supplement (2026-10-14).

    python -m tools.hairline_lines_gradient drawn [--image hair_strands]
    python -m tools.hairline_lines_gradient owl --arm off|region|base|supp
    python -m tools.hairline_lines_gradient logos [--only tires,drone]
    python -m tools.hairline_lines_gradient table
    python -m tools.hairline_lines_gradient render

Measures `cfg.hairline_lines_gradient` (default OFF), #915's proposal: the
Studio sends `owl_kent.jpg` down `gradient`, where the line route
(`cfg.hairline_from_lines`, #882) never runs. With the flag on, the region
tier runs there exactly as before and the line route ADDS the strands it laid
nothing near (`stage6_hairline_lines.supplements` / `supplement_zone`).

Arms (`ARMS`): `off`; `region` (`cfg.hairline`); `base` (`hairline`,
`hairline_from_lines`, `hairline_lines_strand_test`: inert on `gradient`, so
its plan must be md5-identical to `region`'s); `supp` (`base` plus the new
flag). Route: #915's `studio` (`detect_photographic`, `faces_route_flat`, no
forced class), 40 wt, work grid 8.

- `drawn`: `hair_strands` / `hair_fine` at 80 mm, stages once, four plans.
- `owl`: `owl_kent` at 127 mm, ONE plan per process (a plan is minutes on a
  shared laptop). Run `off` and `region` first: bare fabric is read against
  them.
- `logos`: the nine corpus logos (`tools.thin_strokes.corpus_cases`, the
  byte-duplicate run once) at their own widths and garments, `max_colors` 6
  (what the Studio sends), Studio flags. Stages once, `base` and `supp`
  planned; md5 equal or the row lists what moved.

Rows go to `debug_out/hairline_lines_gradient/*.json`; `table` writes
`table.md` and `table.json` beside the renders. Bare fabric is preflight's
uncovered-artwork instrument (`hairline_renders.bare_cells`, as #915 read
it). Every number is a property of the FILE, not of cloth (ROADMAP gate 1).
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from digitizer_core import PipelineConfig, preflight  # noqa: E402
from digitizer_core import stage6_hairline_lines as L  # noqa: E402
from digitizer_core.adapter import plan_to_design  # noqa: E402
from digitizer_core.pipeline import plan_stitches, run_stages  # noqa: E402
from tools import hair_reach as hr  # noqa: E402
from tools.hairline_renders import bare_cells, bare_new_mm2  # noqa: E402
from tools.thin_strokes import STUDIO_MAX_COLORS, corpus_cases  # noqa: E402

DEBUG = ROOT / "debug_out" / "hairline_lines_gradient"
OUT = ROOT.parent / "docs" / "renders" / "claude-hairline-lines-gradient"
BASE = dict(hairline=True, hairline_from_lines=True, hairline_lines_strand_test=True)
ARMS = {"off": {}, "region": {"hairline": True}, "base": BASE,
        "supp": dict(BASE, hairline_lines_gradient=True)}
LABELS = {"off": "OFF", "region": "hairline ON (regions)",
          "base": "+ from_lines + strand test (inert on gradient)",
          "supp": "+ hairline_lines_gradient (supplement)"}
OWL_WIDTH = 127.0


def cfg_for(arm: str, width: float, **extra) -> PipelineConfig:
    return PipelineConfig(target_width_mm=width, work_px_per_mm=8.0, thread_wt=40,
                          **hr.STUDIO, **ARMS[arm], **extra)


def plan_md5(plan) -> str:
    """`tests/test_hairline_lines._md5`'s digest: every point, kind, jump, trim."""
    import hashlib
    coords = [[round(x, 4), round(y, 4), r.kind, r.jump, r.trim]
              for _, r in plan.iter_runs() for x, y in r.points]
    return hashlib.md5(json.dumps(coords).encode()).hexdigest()


def tier_warnings(plan) -> tuple[dict | None, dict | None]:
    """(region tier's HAIRLINE_TIER_SEWN, the supplement's), either None."""
    ws = [w for w in plan.warnings if w["code"] == "HAIRLINE_TIER_SEWN"]
    sup = next((w for w in ws if w.get("source") == "lines_gradient"), None)
    reg = next((w for w in ws if "source" not in w), None)
    return reg, sup


def measure(plan, image: str, sp) -> dict:
    st = plan.stats
    reg, sup = tier_warnings(plan)
    runs = [r for b in plan.blocks for r in b.runs if r.shape_id == L.SHAPE_ID
            and r.kind == "run"]
    return {
        "md5": plan_md5(plan), "stitches": st.stitch_count, "trims": st.trims,
        "color_changes": st.color_changes, "under_1mm": hr._short(plan),
        "thread_m": round(sum(math.dist(a, c) for b in plan.blocks for r in b.runs
                              for a, c in zip(r.points, r.points[1:])) / 1000.0, 2),
        "region": ({k: reg.get(k) for k in ("shapes", "strands", "dropped")} if reg else None),
        "supplement": ({k: sup.get(k) for k in ("strands", "dropped", "found", "refused_no_ridge",
                                                "refused_bar", "refused_region",
                                                "refused_own_tone", "sewn_by_polarity")}
                       if sup else None),
        "supp_strand_mm": round(sum(math.dist(a, c) for r in runs
                                    for a, c in zip(r.points, r.points[1:])), 1),
        "zones": hr.run_zone_counts(image, runs, sp) if runs and sp is not None else None,
    }


def _bare(plan, result, path, cfg):
    p = preflight.prep(path, cfg, design_class=result.design_class)
    return bare_cells(plan, result, p)


def _save_bare(name: str, bare) -> None:
    np.savez_compressed(DEBUG / f"{name}_bare.npz", grid=bare[0], origin=np.array(bare[1]),
                        cell=bare[2])


def _load_bare(name: str):
    f = DEBUG / f"{name}_bare.npz"
    if not f.exists():
        return None
    z = np.load(f)
    return z["grid"], tuple(z["origin"]), float(z["cell"])


def _bare_fields(row: dict, stem: str, arm: str, bare) -> None:
    row["bare_mm2"] = round(float(bare[0].sum()) * bare[2] ** 2, 2)
    if arm in ("off", "region"):
        _save_bare(f"{stem}_{arm}", bare)
    for ref in ("off", "region"):
        # An arm run in parallel with `off` / `region` waits for its read.
        t0 = time.time()
        while (arm not in ("off", "region") and _load_bare(f"{stem}_{ref}") is None
               and time.time() - t0 < 1800):
            time.sleep(15)
        base = bare if ref == arm else _load_bare(f"{stem}_{ref}")
        if base is not None:
            row[f"bare_new_vs_{ref}_mm2"] = round(bare_new_mm2(bare, base), 2)


def _save_design(plan, stem: str, arm: str) -> None:
    (DEBUG / f"{stem}_{arm}_design.json").write_text(
        json.dumps(plan_to_design(plan, name=f"{stem} {arm}")), encoding="utf-8")


def _write(row: dict, name: str) -> dict:
    (DEBUG / f"{name}.json").write_text(json.dumps(row, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(row), flush=True)
    return row


# ------------------------------------------------------------------- commands

def cmd_owl(arm: str) -> dict:
    """One plan of owl_kent on the Studio route. Stages per process."""
    path, stem = hr.IMAGES["owl_kent"], f"owl_kent_w{OWL_WIDTH:g}"
    cfg = cfg_for(arm, OWL_WIDTH)
    t0 = time.time()
    result = run_stages(path, cfg)
    plan = plan_stitches(result, cfg)
    row = {"image": "owl_kent", "width_mm": OWL_WIDTH, "arm": arm,
           "design_class": result.design_class,
           **measure(plan, "owl_kent", result.source_pixels)}
    _bare_fields(row, stem, arm, _bare(plan, result, path, cfg))
    _save_design(plan, stem, arm)
    if arm == "supp":
        (DEBUG / f"{stem}_{arm}_strands.json").write_text(json.dumps(
            [{"rgb": list(b.rgb), "points": [list(p) for p in r.points]}
             for b in plan.blocks for r in b.runs
             if r.shape_id == L.SHAPE_ID and r.kind == "run"]), encoding="utf-8")
    row["seconds"] = round(time.time() - t0)
    return _write(row, f"{stem}_{arm}")


def cmd_drawn(images) -> int:
    """The drawn hair fixtures, 80 mm: stages once, four plans."""
    for image in images:
        path, stem = hr.IMAGES[image], f"{image}_w{hr.DRAWN_WIDTH:g}"
        result = run_stages(path, cfg_for("off", hr.DRAWN_WIDTH))
        for arm in ARMS:
            t0 = time.time()
            cfg = cfg_for(arm, hr.DRAWN_WIDTH)
            plan = plan_stitches(result, cfg)
            row = {"image": image, "width_mm": hr.DRAWN_WIDTH, "arm": arm,
                   "design_class": result.design_class,
                   **measure(plan, image, result.source_pixels)}
            _bare_fields(row, stem, arm, _bare(plan, result, path, cfg))
            _save_design(plan, stem, arm)
            row["seconds"] = round(time.time() - t0)
            _write(row, f"{stem}_{arm}")
    return 0


def cmd_logos(only) -> int:
    """The nine logos: `base` vs `supp`, from one `run_stages` each."""
    for name, path, width, garment in corpus_cases():
        if only and name not in only:
            continue
        t0 = time.time()
        kw = dict(garment_id=garment, max_colors=STUDIO_MAX_COLORS)
        result = run_stages(path, cfg_for("base", width, **kw))
        plans = {arm: plan_stitches(result, cfg_for(arm, width, **kw)) for arm in ("base", "supp")}
        row = {"logo": name, "file": path.name, "width_mm": width, "garment": garment,
               "design_class": result.design_class,
               "supplement_runs": L.supplements(cfg_for("supp", width, **kw),
                                                result.design_class)}
        for arm, plan in plans.items():
            row[arm] = measure(plan, name, result.source_pixels)
        row["identical"] = row["base"]["md5"] == row["supp"]["md5"]
        if not row["identical"]:
            cfg = cfg_for("base", width, **kw)
            b0 = _bare(plans["base"], result, path, cfg)
            b1 = _bare(plans["supp"], result, path, cfg)
            row["bare_new_vs_base_mm2"] = round(bare_new_mm2(b1, b0), 2)
        row["seconds"] = round(time.time() - t0)
        _write(row, f"logo_{name}")
    return 0


# --------------------------------------------------------------------- tables

def _rows(prefix: str) -> list[dict]:
    return [json.loads(f.read_text(encoding="utf-8")) for f in sorted(DEBUG.glob(f"{prefix}*.json"))
            if not f.name.endswith(("_design.json", "_strands.json"))]


def _sup(r, k, default="-"):
    return (r.get("supplement") or {}).get(k, default)


def _sum(d):
    return sum(d.values()) if isinstance(d, dict) else d


def plan_table(rows: list[dict]) -> str:
    out = ["| image | arm | region strands | supplement strands | refused: region covers it | "
           "refused: own tone | bristle-box strands | stitches | trims | colour chg | thread m | "
           "< 1 mm | bare new vs OFF mm2 | bare new vs region mm2 | md5 |",
           "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    order = {a: i for i, a in enumerate(ARMS)}
    for r in sorted(rows, key=lambda r: (r["image"], order[r["arm"]])):
        z = (r.get("zones") or {}).get("bristles", {}).get("n", "-") if r.get("zones") else "-"
        out.append(
            f"| {r['image']} {r['width_mm']:g} mm | {LABELS[r['arm']]} | "
            f"{(r.get('region') or {}).get('strands', '-')} | {_sup(r, 'strands')} | "
            f"{_sum(_sup(r, 'refused_region'))} | {_sum(_sup(r, 'refused_own_tone'))} | {z} | {r['stitches']:,} | {r['trims']} | "
            f"{r['color_changes']} | {r['thread_m']} | {r['under_1mm']} | "
            f"{r.get('bare_new_vs_off_mm2', '-')} | {r.get('bare_new_vs_region_mm2', '-')} | "
            f"`{r['md5'][:8]}` |")
    return "\n".join(out)


def logo_table(rows: list[dict]) -> str:
    out = ["| logo | width / garment | class | supplement runs? | base md5 | supp md5 | identical | "
           "strands added | trims base / supp | bare new vs base mm2 |",
           "|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        b, s = r["base"], r["supp"]
        out.append(
            f"| {r['logo']} | {r['width_mm']:g} mm / {r['garment']} | {r['design_class']} | "
            f"{'yes' if r['supplement_runs'] else 'no'} | `{b['md5'][:8]}` | `{s['md5'][:8]}` | "
            f"{'yes' if r['identical'] else 'NO'} | {_sup(s, 'strands', 0)} | "
            f"{b['trims']} / {s['trims']} | {r.get('bare_new_vs_base_mm2', '-')} |")
    return "\n".join(out)


def cmd_table(out: Path) -> int:
    out.mkdir(parents=True, exist_ok=True)
    plans = [r for r in _rows("") if "arm" in r]
    logos = _rows("logo_")
    text = ("PLANS (Studio route, 40 wt, grid 8)\n\n" + plan_table(plans)
            + "\n\nNINE LOGOS (base = hairline + from_lines + strand test; supp = + the flag)\n\n"
            + logo_table(logos) + "\n")
    (out / "table.md").write_text(text, encoding="utf-8")
    (out / "table.json").write_text(json.dumps({"plans": plans, "logos": logos}, indent=1) + "\n",
                                    encoding="utf-8")
    print(text)
    return 0


# -------------------------------------------------------------------- renders

def _label(img, text: str):
    band = np.full((34, img.shape[1], 3), 255, np.uint8)
    cv2.putText(band, text[:48], (6, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (30, 30, 30), 2,
                cv2.LINE_AA)
    return np.vstack([band, img])


def _strip(tiles):
    hh = min(t.shape[0] for t in tiles)
    ww = min(t.shape[1] for t in tiles)
    sep = np.full((hh, 8, 3), 255, np.uint8)
    row = []
    for t in tiles:
        row += [t[:hh, :ww], sep]
    return np.hstack(row[:-1])


def supplement_map(out: Path) -> None:
    """owl_kent: the strands the supplement sews (dark red / light cyan) and
    the ones it refused because a region-tier shape covers them (yellow),
    over the raster the route read; the bristle box in green."""
    result = run_stages(hr.IMAGES["owl_kent"], cfg_for("off", OWL_WIDTH))
    sp = result.source_pixels
    k = 2
    big = cv2.resize(cv2.cvtColor(sp.rgb, cv2.COLOR_RGB2BGR), None, fx=k, fy=k,
                     interpolation=cv2.INTER_NEAREST)
    big = (0.55 * big + 0.45 * 255).astype(np.uint8)
    saved = json.loads((DEBUG / f"owl_kent_w{OWL_WIDTH:g}_supp_strands.json")
                       .read_text(encoding="utf-8"))
    for s in saved:
        q = np.array([sp.to_px(x, y) for x, y in s["points"]]) * k
        r, g, b = s["rgb"]
        cv2.polylines(big, [np.round(q).astype(np.int32)], False,
                      (230, 160, 0) if 0.2126 * r + 0.7152 * g + 0.0722 * b > 128
                      else (0, 0, 230), 2, cv2.LINE_AA)
    h, w = big.shape[:2]
    x0, y0, x1, y1 = hr.ZONES["owl_kent"]["bristles"]
    cv2.rectangle(big, (int(x0 * w), int(y0 * h)), (int(x1 * w), int(y1 * h)), (0, 150, 0), 2)
    hr.write_jpeg(out / "owl_kent_supplement_strands.jpg", big)


def cmd_render(out: Path) -> int:
    """region | supp strips over owl_kent's bristle box at 16 px/mm, and over
    each drawn fixture whole at 8 px/mm, from the saved designs."""
    from digitizer_core import machine, stitchviz
    out.mkdir(parents=True, exist_ok=True)
    stem = f"owl_kent_w{OWL_WIDTH:g}"
    have = [a for a in ("region", "supp") if (DEBUG / f"{stem}_{a}_design.json").exists()]
    if have:
        result = run_stages(hr.IMAGES["owl_kent"], cfg_for("off", OWL_WIDTH))
        sp = result.source_pixels
        h, w = sp.rgb.shape[:2]
        x0, y0, x1, y1 = hr.ZONES["owl_kent"]["bristles"]
        a, b = sp.to_mm(x0 * w, y0 * h), sp.to_mm(x1 * w, y1 * h)
        tiles = [_label(hr.beak_crop("owl_kent", json.loads(
            (DEBUG / f"{stem}_{arm}_design.json").read_text(encoding="utf-8")),
            (a[0], a[1], b[0], b[1]), 16.0, 40), f"BEFORE: {LABELS[arm]}" if arm == "region"
            else f"AFTER: {LABELS[arm]}") for arm in have]
        hr.write_jpeg(out / "owl_kent_bristles_before_after_16pxmm.jpg", _strip(tiles))
    for image in hr.DRAWN:
        s = f"{image}_w{hr.DRAWN_WIDTH:g}"
        tiles = []
        for arm, tag in (("region", "BEFORE"), ("supp", "AFTER")):
            f = DEBUG / f"{s}_{arm}_design.json"
            if f.exists():
                img = stitchviz.render_design(json.loads(f.read_text(encoding="utf-8")),
                                              px_per_mm=8.0,
                                              thread_mm=machine.thread_profile(40).width_mm)
                tiles.append(_label(img, f"{tag}: {LABELS[arm]}"))
        if tiles:
            hr.write_jpeg(out / f"{image}_before_after_8pxmm.jpg", _strip(tiles))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("drawn")
    d.add_argument("--image", choices=list(hr.DRAWN), action="append")
    o = sub.add_parser("owl")
    o.add_argument("--arm", choices=list(ARMS), required=True)
    g = sub.add_parser("logos")
    g.add_argument("--only", default="")
    for name in ("table", "render", "map"):
        p = sub.add_parser(name)
        p.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args(argv)
    DEBUG.mkdir(parents=True, exist_ok=True)
    if args.cmd == "drawn":
        return cmd_drawn(args.image or list(hr.DRAWN))
    if args.cmd == "owl":
        cmd_owl(args.arm)
        return 0
    if args.cmd == "logos":
        return cmd_logos({s for s in args.only.split(",") if s})
    if args.cmd == "render":
        return cmd_render(args.out)
    if args.cmd == "map":
        args.out.mkdir(parents=True, exist_ok=True)
        supplement_map(args.out)
        return 0
    return cmd_table(args.out)


if __name__ == "__main__":
    raise SystemExit(main())
