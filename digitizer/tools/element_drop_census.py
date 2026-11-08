"""Does ARTWORK_ELEMENT_DROPPED fire where an element really left the design?

Digitizes each image with the Studio's own request (`tools.fremont_triage.
studio_request` at --width on --garment, the census's 80 mm left chest by
default), runs preflight on the result, and prints one row per image: stage-0
class, the grade with and without the new finding, the finding's severity and
area, its causes, and the pipeline warnings it was read from. Written for the
2026-11-01 PR that added the finding, against the 21 Commons logo rows of
`docs/logo-style-census-2026-10-27.md` (items 3-4 name the losses) and the
committed fixtures. Numbers only; nothing here is a quality claim, and nothing
is sewn.

Since 2026-11-07 each row also scores the same plan with
`cfg.dropped_element_v2` OFF and ON (one digitize, preflight twice), so the
table reads the finding OFF and ON side by side.

    python -m tools.element_drop_census IMG [IMG ...] [--out DIR] [--width 80]
                                        [--garment left_chest] [--garment-rgb 235,232,223]
    python -m tools.element_drop_census --table DIR     # re-print a finished run

One digitize at a time: on Kent's laptop take a CPU slot first
(`docs/superpowers/plans/2026-10-27-director-handoff.md` §5). Each row's full
output (warnings, preflight, timings) lands in `--out/<slug>.json`; a row that
already has one is re-printed, not re-run.
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = Path(tempfile.gettempdir()) / "embwt" / "element_drop_census"
FINDING = "ARTWORK_ELEMENT_DROPPED"
READ_FROM = ("SHAPE_NOT_STITCHED", "SHAPES_LEFT_UNSEWN", "DROPPED_SMALL_SHAPES",
             "COLOR_CAP_APPLIED", "THREAD_RESNAPPED_AFTER_DRIFT")


def _config(width: float, garment: str, garment_rgb: tuple[int, int, int]) -> dict:
    from tools.fremont_triage import studio_request
    req = studio_request(width)
    req["target_width_mm"] = float(width)
    req["garment_id"] = garment
    req["garment_rgb"] = list(garment_rgb)
    return req


def run_one(image: Path, out: Path, req: dict) -> dict:
    """Digitize one image the way the Studio would and score it -> the row."""
    from digitizer_core.config import PipelineConfig
    from digitizer_core.pipeline import build_generation, finish_generation, plan_stitches
    from digitizer_core.preflight import _DEDUCT, run_preflight
    from digitizer_service.app import _decode, _parse_config

    t0 = time.time()
    data = image.read_bytes()
    cfg = PipelineConfig(**_parse_config(json.dumps(req)))
    pixels = _decode(data)
    gen = build_generation(pixels, cfg, exif_source=data)
    result = finish_generation(gen.fork(), cfg)
    plan = plan_stitches(result, cfg)
    pf = run_preflight(result, plan, dataclasses.replace(cfg, dropped_element_v2=False), image=pixels)
    cfg_v2 = dataclasses.replace(cfg, dropped_element_v2=True)
    pf_v2 = run_preflight(result, plan, cfg_v2, image=pixels)
    wall = round(time.time() - t0, 1)

    without = [f for f in pf["findings"] if f["code"] != FINDING]
    score_wo = max(0, 100 - sum(_DEDUCT.get(f["severity"], 0) for f in without))
    grade_wo = ("A" if score_wo >= 90 else "B" if score_wo >= 75 else
                "C" if score_wo >= 60 else "D" if score_wo >= 40 else "F")
    hit = next((f for f in pf["findings"] if f["code"] == FINDING), None)
    row = {
        "slug": image.stem, "image": str(image), "wall_s": wall,
        "class": gen.classification_class,
        "stitches": sum(b.stitch_count for b in plan.blocks),
        "regions": len(result.regions),
        "artwork_mm2": round(sum(float(r.area_mm2 or 0.0) for r in result.regions), 1),
        "grade_without": f"{grade_wo} {score_wo}",
        "grade_with": f"{pf['grade']} {pf['score']}",
        "finding": hit,
        "metrics": {k: v for k, v in pf["metrics"].items() if k.startswith("element_")},
        "grade_v2": f"{pf_v2['grade']} {pf_v2['score']}",
        "finding_v2": next((f for f in pf_v2["findings"] if f["code"] == FINDING), None),
        "metrics_v2": {k: v for k, v in pf_v2["metrics"].items() if k.startswith("element_")},
        "read_from": [{k: v for k, v in w.items() if k != "message" and k != "pieces"}
                      for w in plan.warnings if w.get("code") in READ_FROM],
        "findings": [(f["code"], f["severity"]) for f in pf["findings"]],
        "request": req,
    }
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{image.stem}.json").write_text(json.dumps(row, indent=1), encoding="utf-8")
    return row


def _verdict(f: dict | None) -> str:
    """'warn 85.5 (unsewn_enclosed 2)' or '-'."""
    if not f:
        return "-"
    causes = ", ".join(f"{k} {v}" for k, v in f["extra"]["causes"].items() if v)
    return f"{f['severity']} {f['extra']['total_mm2']} ({causes})"


def table(rows: list[dict]) -> str:
    head = ("| image | class | grade without / OFF / v2 ON | OFF: finding mm2 (causes) | "
            "v2 ON: finding mm2 (causes) | transparent holes skipped | read from | s |\n"
            "|---|---|---|---|---|---|---|---|")
    lines = [head]
    for r in rows:
        codes = ", ".join(sorted({w["code"] for w in r.get("read_from", [])})) or "-"
        m2 = r.get("metrics_v2") or {}
        skipped = (f"{m2['element_drop_transparent_count']} / "
                   f"{m2['element_drop_transparent_mm2']}"
                   if "element_drop_transparent_count" in m2 else "-")
        lines.append(
            f"| {r['slug']} | {r.get('class')} | {r['grade_without']} / {r['grade_with']} / "
            f"{r.get('grade_v2', '-')} | {_verdict(r.get('finding'))} | "
            f"{_verdict(r.get('finding_v2'))} | {skipped} | {codes} | {r.get('wall_s')} |")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m tools.element_drop_census",
                                 description=__doc__.split("\n\n")[0])
    ap.add_argument("images", nargs="*", type=Path)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--width", type=float, default=80.0)
    ap.add_argument("--garment", default="left_chest")
    ap.add_argument("--garment-rgb", default="235,232,223")
    ap.add_argument("--table", type=Path, help="re-print the table of a finished run dir")
    a = ap.parse_args(argv)

    if a.table:
        rows = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(a.table.glob("*.json"))]
        print(table(rows))
        return 0
    if not a.images:
        ap.error("give at least one image, or --table DIR")
    rgb = tuple(int(v) for v in a.garment_rgb.split(","))
    req = _config(a.width, a.garment, rgb)
    rows = []
    for img in a.images:
        done = a.out / f"{img.stem}.json"
        if done.exists():
            rows.append(json.loads(done.read_text(encoding="utf-8")))
            print(f"[{img.stem}] kept", flush=True)
            continue
        print(f"[{img.stem}] digitizing ...", flush=True)
        try:
            row = run_one(img, a.out, req)
        except Exception as exc:  # one bad row must not lose the run
            row = {"slug": img.stem, "image": str(img), "error": repr(exc),
                   "grade_without": "-", "grade_with": "-", "finding": None}
            a.out.mkdir(parents=True, exist_ok=True)
            (a.out / f"{img.stem}.json").write_text(json.dumps(row, indent=1), encoding="utf-8")
        rows.append(row)
        f = row.get("finding")
        verdict = "no finding" if not f else (
            f"{f['severity']} {f['extra']['total_mm2']} mm2 ({f['extra']['frac']:.1%})")
        print(f"[{img.stem}] {row.get('class')} {row['grade_without']} -> "
              f"{row['grade_with']} {verdict} {row.get('wall_s')} s", flush=True)
    print()
    print(table(rows))
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(ROOT))
    raise SystemExit(main())
