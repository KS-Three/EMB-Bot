#!/usr/bin/env python
"""Does stage-1.25 photograph detection still earn its keep over stage 0's
texture gate? (MASTER_SCOPE defect 15, census 2026-11-06)

Defect 15: an UNDECLARED photograph got neither depth sequencing nor the
palette bind because `config.is_photographic` fell back to stage 0's class,
and stage 0's colour statistics could not tell `owl_kent.jpg` from two
gradient logos. Two things changed since the defect was written:

  * `cfg.stage0_texture_gate` (ON since 2026-10-28, PR #1178) routes grainy
    opaque artwork to a photo class on `texture_frac`, so for a row it
    catches `is_photographic` is True from the CLASS with no detection at all;
  * the Studio sends `detect_photographic=true` AND `faces_route_flat=true` on
    every job (app/src/lib/digitizer.js), so a face hit routes FLAT and keeps
    the photographic machinery OFF — detection's one remaining way to ADD a
    photograph is EXIF, or a face on a job that opted out of the flat route.

This tool replays `/classify`'s block (stage 0, stage 1 prep, stage 1.25 —
`digitizer_service/app.py::classify_art`) on every row, never a full
digitize, and prints the four cells the defect's closure turns on:

    photo class by stage 0  x  a detection signal fired

over the repo's committed fixtures and the 39-row Commons corpus
(`testdata/photo/corpus/corpus.json`; images fetched by
`python -m tools.photo_corpus fetch`, gitignored, never committed).

**Every number is an instrument reading, not a quality claim** (ROADMAP gate
4). Nothing here moves a threshold (gate 2) or flips a flag (gate 3).

    cd digitizer && .venv/Scripts/python -m tools.photo_detect_census             # the table + the 2x2
    .venv/Scripts/python -m tools.photo_detect_census --json OUT.json          # + the committed summary
    .venv/Scripts/python -m tools.photo_detect_census --digitize SLUG [SLUG..] # full run at 80 mm, both arms

On Linux the interpreter is `.venv/bin/python` (CLAUDE.md).
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from digitizer_core import photo_signals as ps                       # noqa: E402
from digitizer_core import stage0_classify as s0                    # noqa: E402
from digitizer_core.config import PHOTO_CLASSES, PipelineConfig, is_photographic  # noqa: E402
from digitizer_core.stage1_prep import prep                          # noqa: E402
from tools.stage0_photo_gate import (                               # noqa: E402
    CORPUS_JSON, PHOTOGRAPHED_GRAPHICS, TESTDATA, corpus_items,
)

#: The committed artwork this census reads, with what each IS by hand.
#: `photo` = a real photograph; `logo` = graphic art. The 14 logos are the
#: false-positive population `tests/test_photo_detection.py::LOGOS` pins at 0;
#: `drone_render`, `summit_badge` and the thermal badge are the three logos
#: `config.is_photographic`'s docstring names as reading MORE photographic
#: than the owl on stage 0's old primary gate.
FIXTURES: dict[str, str] = {
    "photo/owl_kent.jpg": "photo",
    "photo/drone_render.png": "logo",
    "photo/summit_badge.png": "logo",
    "photo/logo_drone_thermal_badge.png": "logo",
    "becker_marine_logo.png": "logo", "logo_script_tires.png": "logo",
    "logo_whitebg.png": "logo", "logo_alpha.png": "logo", "ribbon_curve.png": "logo",
    "bg_uncertain.png": "logo", "photo/enthusiast_logo.png": "logo",
    "photo/logo_hotel_fremont.webp": "logo", "photo/logo_bridge_bar.jpg": "logo",
    "photo/logo_gaulke_roofing.png": "logo", "photo/logo_golden_tee.jpg": "logo",
    "photo/screenshot_phone_ui_golke.jpg": "logo",
}

#: The committed logos: the 14 `tests/test_photo_detection.py::LOGOS` pins
#: plus the thermal badge. The false-positive count over them must be 0.
LOGOS = tuple(k for k, v in FIXTURES.items() if v == "logo")
assert len(LOGOS) == 15, LOGOS

SUMMARY_JSON = TESTDATA / "photo" / "photo_detect_census_2026-11-06.json"


def _slug(path: Path) -> str:
    path = Path(path)
    if path.parent == TESTDATA:
        return path.name
    if path.parent == TESTDATA / "photo":
        return f"photo/{path.name}"
    return path.stem


def studio_cfg(**kw) -> PipelineConfig:
    """What the Studio sends on every job that matters here: detection on,
    a face routes flat (app/src/lib/digitizer.js ~L206-217), 80 mm."""
    kw.setdefault("target_width_mm", 80.0)
    kw.setdefault("detect_photographic", True)
    kw.setdefault("faces_route_flat", True)
    return PipelineConfig(**kw)


def read_row(path: Path, *, kind: str, genre: str | None, cfg: PipelineConfig | None = None) -> dict:
    """`/classify` replayed on one file: stage 0 under both arms of the
    texture gate, stage 1 prep, stage 1.25 with BOTH signals read
    (`faces_always`, so a face is counted even when EXIF fired first)."""
    cfg = cfg or studio_cfg()
    path = Path(path)
    on = s0.classify(str(path), cfg)
    off = s0.classify(str(path), dataclasses.replace(cfg, stage0_texture_gate=False))
    p = prep(str(path), cfg, design_class=on.class_)
    t0 = time.perf_counter()
    sig = ps.detect(str(path), rgb=p.rgb, cfg=cfg, faces_always=True)
    detect_ms = round((time.perf_counter() - t0) * 1000, 1)
    detected = sig.is_photograph is True
    # The verdict `is_photographic()` reaches with detection OFF (class only)
    # and ON (`apply_detection` folds a hit into the caller's config).
    base = PipelineConfig(target_width_mm=cfg.target_width_mm)
    off_verdict = is_photographic(base, on.class_)
    on_verdict = is_photographic(ps.apply_detection(base, detected), on.class_)
    # What a STUDIO job actually gets: a face hit under faces_route_flat
    # re-classifies "flat" with the caller's config untouched
    # (pipeline.build_generation, FACE_ROUTED_FLAT), so the photographic
    # machinery stays OFF for it.
    face_routed_flat = bool(detected and cfg.faces_route_flat and sig.faces)
    if face_routed_flat:
        studio_class, studio_verdict = "flat", False
    else:
        studio_class, studio_verdict = on.class_, on_verdict
    return {
        "slug": _slug(path), "kind": kind, "genre": genre,
        "class_on": on.class_, "conf_on": round(float(on.confidence), 3),
        "class_off": off.class_,
        "photo_class": on.class_ in PHOTO_CLASSES,
        "texture_frac": round(float(on.signals["texture_frac"]), 4),
        "cutout": bool(on.signals["cutout_alpha"]),
        "exif_camera": sig.exif_camera,
        "faces": sig.faces, "face_reason": sig.face_reason,
        "signal": sig.signal,                     # "exif" | "face" | None
        "detected": detected,
        "is_photographic_off": bool(off_verdict),
        "is_photographic_on": bool(on_verdict),
        "face_routed_flat": face_routed_flat,
        "studio_class": studio_class,
        "studio_is_photographic": bool(studio_verdict),
        "detect_ms": detect_ms,
    }


def corpus_rows(corpus_json: Path = CORPUS_JSON) -> list[tuple[Path, str, str]]:
    """(path, kind, genre) for every corpus row whose image is present. A
    `logo` row whose MEDIUM is a photograph (`stage0_photo_gate.PHOTOGRAPHED_GRAPHICS`)
    is relabelled `photo-of-logo`, as that tool does."""
    paths, kinds = corpus_items(corpus_json)
    genres = {r["slug"]: r["genre"] for r in json.loads(corpus_json.read_text(encoding="utf-8"))} \
        if corpus_json.exists() else {}
    return [(p, kinds.get(p.stem, "fixture"), genres.get(p.stem)) for p in paths]


def census(include_corpus: bool = True, corpus_json: Path = CORPUS_JSON) -> list[dict]:
    items = [(TESTDATA / rel, k, None) for rel, k in FIXTURES.items() if (TESTDATA / rel).exists()]
    if include_corpus:
        items += corpus_rows(corpus_json)
    out = []
    for path, kind, genre in items:
        try:
            out.append(read_row(path, kind=kind, genre=genre))
        except Exception as exc:                                       # noqa: BLE001
            out.append({"slug": _slug(path), "kind": kind, "genre": genre,
                        "error": f"{type(exc).__name__}: {exc}"[:200]})
    return out


def two_by_two(rows: list[dict], kinds=("photo",)) -> dict:
    """The four cells over rows of the given kinds, plus the lists behind the
    two cells the verdict turns on."""
    sel = [r for r in rows if r.get("kind") in kinds and "error" not in r]
    cells = {"photo_class&detected": 0, "photo_class&silent": 0,
             "other_class&detected": 0, "other_class&silent": 0}
    for r in sel:
        a = "photo_class" if r["photo_class"] else "other_class"
        b = "detected" if r["detected"] else "silent"
        cells[f"{a}&{b}"] += 1
    return {
        "n": len(sel), "cells": cells,
        # detection's only possible gain over the gate: a non-photo class a
        # signal still catches
        "detection_rescues": sorted(r["slug"] for r in sel if not r["photo_class"] and r["detected"]),
        # the defect's remaining population: no photo class AND no signal
        "escapes": sorted(r["slug"] for r in sel if not r["is_photographic_on"]),
        # what a Studio job (faces_route_flat) actually gets
        "studio_not_photographic": sorted(r["slug"] for r in sel if not r["studio_is_photographic"]),
        "face_routed_flat": sorted(r["slug"] for r in sel if r["face_routed_flat"]),
        # the gate's own gain: photo class ON that was not a photo class OFF
        "gate_rescues": sorted(r["slug"] for r in sel
                               if r["photo_class"] and r["class_off"] not in PHOTO_CLASSES),
    }


def kappa(rows: list[dict], predicate: str) -> dict:
    """Cohen's kappa of one yes/no reading (`photo_class`, `detected` or
    `studio_is_photographic`) against the hand label, over the rows labelled
    `photo` or `logo` — the photographed graphics sit in neither population.
    ROADMAP gate 4: the chance-corrected figure, never the raw share."""
    sel = [r for r in rows if r.get("kind") in ("photo", "logo") and "error" not in r]
    n = len(sel)
    if not n:
        return {"n": 0, "kappa": None}
    tp = sum(1 for r in sel if r["kind"] == "photo" and r[predicate])
    fn = sum(1 for r in sel if r["kind"] == "photo" and not r[predicate])
    fp = sum(1 for r in sel if r["kind"] == "logo" and r[predicate])
    tn = n - tp - fn - fp
    po = (tp + tn) / n
    pe = ((tp + fp) * (tp + fn) + (fn + tn) * (fp + tn)) / (n * n)
    k = None if pe == 1.0 else (po - pe) / (1.0 - pe)
    return {"n": n, "tp": tp, "fn": fn, "fp": fp, "tn": tn,
            "kappa": None if k is None else round(k, 3)}


def summary(rows: list[dict]) -> dict:
    logos = [r for r in rows if r.get("kind") == "logo" and "error" not in r]
    return {
        "date": "2026-11-06",
        "rows": rows,
        "kappa": {name: kappa(rows, name)
                  for name in ("photo_class", "detected", "studio_is_photographic")},
        "photos": two_by_two(rows, ("photo",)),
        "photo_of_logo": two_by_two(rows, ("photo-of-logo",)),
        "logos": {
            "n": len(logos),
            "false_positives": sorted(r["slug"] for r in logos if r["detected"]),
            "photo_class": sorted(r["slug"] for r in logos if r["photo_class"]),
        },
        "errors": sorted(r["slug"] for r in rows if "error" in r),
    }


# --- the full-run arm: duplicate cones and re-snap escapes ----------------------

def digitize_both(path: Path, width_mm: float = 80.0) -> dict:
    """One row digitized twice at `width_mm`: as the Studio sends it
    (detection on, face routes flat, nothing declared) and with
    `is_photographic=True` forced. Per arm: the class, the verdict the run
    carried, duplicate cones (a cone number sewn in more than one block —
    `cone_revisits.revisits`), and the re-snap's ADDED / outside-palette
    cones probed the way `tools/resnap_escape.py` probes them."""
    from digitizer_core import pipeline as pl
    from digitizer_core.pipeline import plan_stitches, run_stages
    from tools.cone_revisits import revisits

    real = pl.revalidate_threads

    def one(cfg: PipelineConfig) -> dict:
        seen: dict = {}

        def probe(regions, p, cfg_, **kw):
            seen["entry"] = {r.thread_index for r in regions
                             if not r.meta.get("enclosed_background")}
            seen["palette"] = set(kw.get("palette_indices") or ())
            return real(regions, p, cfg_, **kw)

        pl.revalidate_threads = probe
        t0 = time.perf_counter()
        try:
            res = run_stages(str(path), cfg)
        finally:
            pl.revalidate_threads = real
        plan = plan_stitches(res, cfg)
        end = {r.thread_index for r in res.regions}
        added = end - seen.get("entry", set())
        outside = (end - seen["palette"]) if seen.get("palette") else set()
        dups = revisits(plan, res)
        return {
            "class": res.design_class,
            "detected_photographic": bool(res.detected_photographic),
            "is_photographic": bool(is_photographic(
                ps.apply_detection(cfg, res.detected_photographic), res.design_class)),
            "blocks": len(plan.palette),
            "distinct_cones": len({str(e["number"]) for e in plan.palette}),
            "duplicate_cones": len(dups),
            "duplicate_routes": sorted({d["route"] for d in dups}),
            "resnap_added": len(added), "resnap_outside_palette": len(outside),
            "wall_s": round(time.perf_counter() - t0, 1),
        }

    return {
        "slug": _slug(path), "width_mm": width_mm,
        "studio": one(studio_cfg(target_width_mm=width_mm)),
        "forced_photo": one(studio_cfg(target_width_mm=width_mm, is_photographic=True)),
    }


# --- printing -------------------------------------------------------------------

def print_table(rows: list[dict]) -> None:
    print("# photo detection census — readings, not claims. cfg: detect_photographic=True, "
          "faces_route_flat=True (the Studio's), 80 mm; class_off = stage0_texture_gate=False")
    hdr = (f"{'slug':<34} {'kind':<13} {'genre':<16} {'class_on':<14} {'class_off':<14} "
           f"{'tex':>6} {'signal':<7} {'faces':>5} {'isP off':>7} {'isP on':>6} {'studio':<14}")
    print(hdr)
    print("-" * len(hdr))
    for r in rows:
        if "error" in r:
            print(f"{r['slug'][:34]:<34} {r['kind']:<13} ERROR {r['error']}")
            continue
        studio = r["studio_class"] + ("" if r["studio_is_photographic"] else " (no P)")
        print(f"{r['slug'][:34]:<34} {r['kind']:<13} {str(r['genre'] or '-')[:16]:<16} "
              f"{r['class_on']:<14} {r['class_off']:<14} {r['texture_frac']:6.3f} "
              f"{str(r['signal'] or '-'):<7} {str(r['faces'] if r['faces'] is not None else 'n/a'):>5} "
              f"{str(r['is_photographic_off']):>7} {str(r['is_photographic_on']):>6} {studio:<14}")


def print_2x2(label: str, t: dict) -> None:
    c = t["cells"]
    print(f"\n# {label} (n {t['n']}): photo class by stage 0  x  a detection signal fired")
    print(f"#                  detected   silent")
    print(f"#   photo class   {c['photo_class&detected']:>8}   {c['photo_class&silent']:>6}")
    print(f"#   other class   {c['other_class&detected']:>8}   {c['other_class&silent']:>6}")
    print(f"#   detection rescues (other class, signal fired): {t['detection_rescues'] or 'none'}")
    print(f"#   escapes (is_photographic False with detection ON): {t['escapes'] or 'none'}")
    print(f"#   studio job NOT photographic (faces_route_flat): {t['studio_not_photographic'] or 'none'}")
    print(f"#   face routed flat: {t['face_routed_flat'] or 'none'}")
    print(f"#   gate rescues (photo class only with the texture gate ON): {t['gate_rescues'] or 'none'}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m tools.photo_detect_census",
                                 description=__doc__.split("\n\n")[0])
    ap.add_argument("--corpus", type=Path, default=CORPUS_JSON)
    ap.add_argument("--fixtures-only", action="store_true")
    ap.add_argument("--json", type=Path, default=None, help="write the summary JSON here")
    ap.add_argument("--digitize", nargs="+", default=None,
                    help="corpus slugs or testdata-relative paths: full run at 80 mm, both arms")
    ap.add_argument("--width-mm", type=float, default=80.0)
    a = ap.parse_args(argv)

    if a.digitize:
        out = []
        for name in a.digitize:
            p = TESTDATA / name
            if not p.exists():
                for ext in (".png", ".jpg"):
                    q = a.corpus.parent / f"{name}{ext}"
                    if q.exists():
                        p = q
                        break
            if not p.exists():
                print(f"{name}: no such file under testdata/ or the corpus folder", file=sys.stderr)
                continue
            r = digitize_both(p, a.width_mm)
            out.append(r)
            for arm in ("studio", "forced_photo"):
                d = r[arm]
                print(f"{r['slug'][:30]:<30} {arm:<13} class {d['class']:<14} isP {str(d['is_photographic']):<5} "
                      f"blocks {d['blocks']:>3} distinct {d['distinct_cones']:>3} dup {d['duplicate_cones']:>2} "
                      f"{','.join(d['duplicate_routes']) or '-':<16} resnap +{d['resnap_added']} "
                      f"outside {d['resnap_outside_palette']}  {d['wall_s']}s", flush=True)
        if a.json:
            a.json.write_text(json.dumps(out, indent=1), encoding="utf-8")
        return 0

    rows = census(include_corpus=not a.fixtures_only, corpus_json=a.corpus)
    s = summary(rows)
    print_table(rows)
    print_2x2("real photographs", s["photos"])
    print_2x2("photographed graphics (photo-of-logo)", s["photo_of_logo"])
    lg = s["logos"]
    print(f"\n# logos (n {lg['n']}): false positives (a signal fired) {len(lg['false_positives'])} "
          f"{lg['false_positives'] or ''}; photo class by stage 0: {lg['photo_class'] or 'none'}")
    print("# kappa against the hand label over photo + logo rows (gate 4: chance-corrected):")
    for name, k in s["kappa"].items():
        print(f"#   {name:<24} kappa {k['kappa']}  (n {k['n']}, tp {k.get('tp')} fn {k.get('fn')} "
              f"fp {k.get('fp')} tn {k.get('tn')})")
    if s["errors"]:
        print(f"# errors: {s['errors']}")
    if a.json:
        a.json.write_text(json.dumps(s, indent=1), encoding="utf-8")
        print(f"\n# summary -> {a.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
