"""`cfg.enclosed_white_skip_transparent` OFF vs ON, per job: which enclosed
areas stop sewing, and what that does to stitches, trims and colour blocks.

    python -m tools.transparent_white_ab --out DIR corpus SLUG [SLUG ...]
           (--corpus-run RUN --photos DIR: stored configs and art)
    python -m tools.transparent_white_ab --out DIR pro SLUG [SLUG ...]
           (`pro_baseline.JOBS`, the Studio request at the pro's size)

Stages 0-4 run once; `finish_generation` runs on two forks, OFF and ON. When
the two forks sew the same regions in the same threads and layers, the plan
is the same by construction (the flag is read nowhere else), so stage 5-7 is
skipped and the row says `identical`. Otherwise both arms are planned, their
designs written to `DIR/<slug>.off.json` / `.on.json`, and the row lists every
area that stopped sewing: its kind, area, whether it is itself lettering (a
hollow letter body, Becker's), and the thread it sewed in.

`--full SLUG` plans both arms even when the forks agree, to check that claim.
Writes `DIR/<kind>.json` (one row per job). Instrument only: no quality claim
(ROADMAP gate 4).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path


def _sha(design: dict) -> str:
    return hashlib.sha256(json.dumps([[s["x"], s["y"], s["type"]] for s in design["stitches"]])
                          .encode()).hexdigest()


def _sewn(result) -> dict:
    return {r.shape_id: (bool(r.meta.get("stitched")), r.meta.get("sew_enclosed_white"),
                         int(r.thread_index), int(r.meta.get("layer", -1)))
            for r in result.regions}


def run_one(slug: str, art: Path, cfg_off, cfg_on, out: Path, full: bool) -> dict:
    from digitizer_core.adapter import plan_to_design
    from digitizer_core.enclosed_white import _is_letter
    from digitizer_core.pipeline import build_generation, finish_generation, plan_stitches
    from digitizer_service.app import _decode
    data = art.read_bytes()
    pixels = _decode(data)
    t0 = time.time()
    gen = build_generation(pixels, cfg_off, exif_source=data)
    has_alpha = bool(pixels.ndim == 3 and pixels.shape[2] == 4 and (pixels[:, :, 3] < 255).any())
    r_off = finish_generation(gen.fork(), cfg_off)
    r_on = finish_generation(gen.fork(), cfg_on)
    s_off, s_on = _sewn(r_off), _sewn(r_on)
    row = {"slug": slug, "art": art.name, "alpha": has_alpha, "bg_from_alpha": bool(gen.p.bg_from_alpha),
           "enclosed": sum(1 for r in r_off.regions if r.meta.get("enclosed_background")),
           "sewn_white_off": sum(1 for r in r_off.regions if r.meta.get("sew_enclosed_white")),
           "sewn_white_on": sum(1 for r in r_on.regions if r.meta.get("sew_enclosed_white"))}
    by_id = {r.shape_id: r for r in r_off.regions}
    dropped = []
    for sid, (st, kind, t, _layer) in s_off.items():
        if kind and not (s_on.get(sid) or (False, None))[1]:
            r = by_id[sid]
            dropped.append({"shape_id": sid, "kind": kind, "area_mm2": round(r.polygon.area, 2),
                            "is_letter": _is_letter(r, cfg_off), "thread": t,
                            "colour_unknown": bool(r.meta.get("enclosed_colour_unknown")),
                            "stitched_off": st, "stitched_on": s_on[sid][0]})
    row["dropped"] = sorted(dropped, key=lambda d: -d["area_mm2"])
    row["dropped_mm2"] = round(sum(d["area_mm2"] for d in dropped), 1)
    row["forks_agree"] = s_off == s_on
    if row["forks_agree"] and not full:
        row["verdict"] = "identical"
        row["secs"] = round(time.time() - t0, 1)
        return row
    for arm, res, cfg in (("off", r_off, cfg_off), ("on", r_on, cfg_on)):
        plan = plan_stitches(res, cfg)
        design = plan_to_design(plan, name=slug)
        (out / f"{slug}.{arm}.json").write_text(json.dumps({"design": design, "_meta": {
            "config_sent": {"enclosed_white_skip_transparent": arm == "on"}}}), encoding="utf-8")
        row[arm] = {"stitches": plan.stats.stitch_count, "trims": plan.stats.trims,
                    "colour_changes": plan.stats.color_changes, "jumps": plan.stats.jumps,
                    "colours": len(design.get("colors") or []), "sha": _sha(design)[:16]}
    row["verdict"] = "identical" if row["off"]["sha"] == row["on"]["sha"] else "moves"
    row["secs"] = round(time.time() - t0, 1)
    return row


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--corpus-run", type=Path)
    ap.add_argument("--photos", type=Path)
    ap.add_argument("--full", action="append", default=[])
    ap.add_argument("kind", choices=("corpus", "pro"))
    ap.add_argument("slugs", nargs="+")
    a = ap.parse_args(argv)
    from digitizer_core import PipelineConfig
    from digitizer_service.app import _parse_config
    a.out.mkdir(parents=True, exist_ok=True)
    path = a.out / f"{a.kind}.json"
    rows = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    for slug in a.slugs:
        if a.kind == "corpus":
            stored = json.loads((a.corpus_run / f"{slug}.json").read_text(encoding="utf-8"))
            sent = stored["_meta"]["config_sent"]
            art = next(p for p in a.photos.glob(f"{slug}.*") if p.suffix.lower() != ".json")
            cfg_off = PipelineConfig(**_parse_config(json.dumps(sent)))
            cfg_on = PipelineConfig(**_parse_config(json.dumps({**sent, "enclosed_white_skip_transparent": True})))
        else:
            from tools import pro_baseline as pb
            from tools import pro_pair
            garment, width, art_spec, *_ = pb.JOBS[slug]
            art = pb.resolve(art_spec)
            cfg_off = pro_pair.config(width, garment)
            cfg_on = pro_pair.config(width, garment, {"enclosed_white_skip_transparent": True})
        try:
            row = run_one(slug, Path(art), cfg_off, cfg_on, a.out, slug in a.full)
            if a.kind == "corpus" and "off" in row:
                row["off_equals_stored"] = row["off"]["sha"] == _sha(stored["design"])[:16]
        except Exception as e:  # noqa: BLE001 - a row, not a crash
            row = {"slug": slug, "error": f"{type(e).__name__}: {e}"[:300]}
        rows[slug] = row
        path.write_text(json.dumps(rows, indent=1), encoding="utf-8")
        print(slug, json.dumps({k: v for k, v in row.items() if k != "dropped"}), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
