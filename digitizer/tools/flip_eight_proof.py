#!/usr/bin/env python
"""flip_eight_proof: BEFORE | AFTER | pro for the 2026-10-23 default flip.

Kent read the flip sheet (`docs/flip-sheet-2026-10-23.md`, PR #1047) and
ruled "flip the eight ON, hold two". This renders what that ruling does to
the three paired jobs the sheet used, as ONE engine change rather than one
flag at a time: BEFORE is today's engine with every flipped flag set back to
its pre-flip value (`BEFORE`, the same dict `tests/conftest.py` pins as
`FLIP_2026_10_23`), AFTER is the engine's plain defaults, pro is the
professional's file for the same job. Counts are read off the DSTs with
`tools.flip_sheet_renders`' readers (one reader, pystitch), the crop is
placed where the two arms differ most, and the whole design is drawn small
beside it so the crop can be found.

    .venv/Scripts/python -m tools.flip_eight_proof [--out DIR]
        [--fixtures hotel_fremont_hat becker_hat_small mfab_hat] [--cache DIR]

Nothing here changes an engine default.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

DIGITIZER = Path(__file__).resolve().parent.parent
if str(DIGITIZER) not in sys.path:
    sys.path.insert(0, str(DIGITIZER))

from tools._console import utf8_console  # noqa: E402
from tools import flip_sheet_renders as fsr  # noqa: E402

#: The pre-flip engine: every value Kent flipped on 2026-10-23, set back.
#: Mirrors `tests/conftest.py`'s FLIP_2026_10_23 (tests/test_flip_eight_proof.py
#: holds the pair). The small-text set is the flip sheet's exact arm.
BEFORE: dict[str, object] = {
    "fill_turn_slant": False,
    "trim_bury_under_later": False,
    "tie_in_off": False,
    "small_solids_satin": False,
    "compact_solids_satin": False,
    "satin_underlay_short_columns": False,
    "fill_underlay_cross": False,
    "small_text_cap_mm": None,
    "small_text_cap_max_width_scale": None,
    "small_text_cap_min_stroke_mm": None,
    "small_text_cap_letter_gap_mm": None,
    "small_text_cap_bold_scale": None,
    "lettering_columns_small_bold": False,
    # PR #1057 (Kent 2026-10-23, same day, by the pro's numbers): the two layout
    # flags and the corner fold, so every site that pins "before the 10-23 flips"
    # pins them too.
    "border_by_size": False,
    "enclosed_alpha_hole_parts": False,
    "lettering_columns_corner_fold": False,
}
HELD_OFF = ("cut_every_jump", "sew_enclosed_white")

#: every picture here has the pro beside ours: local only (Kent 2026-10-27, "Stop new
#: ones, keep old (Recommended)"; `tools.pro_renders`). The 10-23 proof in docs/ stays.
DEFAULT_OUT = fsr.pro_renders.out_dir("flip-eight-2026-10-23")
DEFAULT_CACHE = DIGITIZER / "debug_out" / "flip_eight"
SMALL_PPM = 6.0


def digitize_arm(slug: str, arm: str, cache: Path) -> dict:
    """ours.dst + design.json for one arm; cached per engine commit."""
    from tools import pro_pair as pp
    from digitizer_core.export import write_dst
    sha = fsr.engine_sha()
    out = cache / slug / f"{arm}__{sha}"
    if (out / "design.json").exists():
        return {"dir": out, "sha": sha}
    fx = fsr.fixture_files(slug)
    sets = dict(BEFORE) if arm == "before" else {}
    d = pp.digitize(fx["art"], fx["width_mm"], fx["garment"], sets)
    out.mkdir(parents=True, exist_ok=True)
    write_dst(d.plan, out / "ours.dst")
    (out / "design.json").write_text(json.dumps(d.design), encoding="utf-8")
    (out / "stats.json").write_text(json.dumps(
        {"slug": slug, "arm": arm, "sets": sets, "engine": sha, "secs": round(d.secs, 1),
         "plan_stitches": d.plan.stats.stitch_count, "plan_trims": d.plan.stats.trims}, indent=1),
        encoding="utf-8")
    return {"dir": out, "sha": sha}


def _load(path: Path) -> dict:
    cell = {"dst": path / "ours.dst",
            "design": json.loads((path / "design.json").read_text(encoding="utf-8"))}
    cell["stream"] = fsr.read_stream(cell["dst"])
    return cell


def _small(design: dict, ppm: float = SMALL_PPM):
    from digitizer_core import stitchviz
    return stitchviz.render_design(design, px_per_mm=ppm)


def _hstack(images, gap: int = 12):
    import cv2
    import numpy as np
    h = max(im.shape[0] for im in images)
    w = sum(im.shape[1] for im in images) + gap * (len(images) - 1)
    canvas = np.full((h, w, 3), 255, dtype=np.uint8)
    x = 0
    for im in images:
        if im.ndim == 2:
            im = cv2.cvtColor(im, cv2.COLOR_GRAY2BGR)
        canvas[:im.shape[0], x:x + im.shape[1]] = im[:, :, :3]
        x += im.shape[1] + gap
    return canvas


def one_fixture(slug: str, cache: Path, out: Path) -> dict:
    fx = fsr.fixture_files(slug)
    before = _load(digitize_arm(slug, "before", cache)["dir"])
    after_dir = digitize_arm(slug, "after", cache)
    after = _load(after_dir["dir"])
    pro = fsr.pro_cell(fx)
    row = {"fixture": slug, "width_mm": fx["width_mm"], "engine": after_dir["sha"],
           "pro_file": fx["pro_dst"].name,
           "before": fsr.counts(before["stream"]), "after": fsr.counts(after["stream"]),
           "pro": fsr.counts(pro["stream"])}
    d = fsr.diff_points(fsr.needle_points(before["stream"]), fsr.needle_points(after["stream"]))
    row["diff"] = len(d)
    labels = {"before": f"BEFORE: {row['before']['stitches']} st, {row['before']['trims']} tr",
              "after": f"AFTER: {row['after']['stitches']} st, {row['after']['trims']} tr",
              "pro": f"PRO: {row['pro']['stitches']} st, {row['pro']['trims']} tr"}
    whole = _hstack([fsr._label(_small(before["design"]), labels["before"]),
                     fsr._label(_small(after["design"]), labels["after"]),
                     fsr._label(_small(pro["design_render"]), labels["pro"])])
    name = f"{slug}__whole_before_after_pro.jpg"
    fsr._write(out / name, whole)
    row["images"] = {"whole": name}
    if d:
        box = fsr.best_window(d)
        row["box_mm"] = [round(v, 1) for v in box]
        frame = fsr._design_frame(before["design"])
        pbox = fsr.pro_box(pro["design_render"], frame, box)
        crop = _hstack([fsr._label(fsr.render_crop(before["design"], box), labels["before"]),
                        fsr._label(fsr.render_crop(after["design"], box), labels["after"]),
                        fsr._label(fsr.render_crop(pro["design_render"], pbox), labels["pro"])])
        name = f"{slug}__crop_before_after_pro.jpg"
        fsr._write(out / name, crop)
        row["images"]["crop"] = name
        name = f"{slug}__where.jpg"
        fsr._write(out / name, fsr.where_image(before["design"], box))
        row["images"]["where"] = name
    print(f"{slug}: before {row['before']} after {row['after']} pro {row['pro']} "
          f"({len(d)} points differ)", flush=True)
    return row


def markdown(rows: list[dict]) -> str:
    L = ["# Flip eight 2026-10-23: BEFORE | AFTER | pro", "",
         "Kent's ruling on the flip sheet (PR #1047): flip the eight ON, hold two. BEFORE is "
         "today's engine with the flipped values set back (`tools/flip_eight_proof.py`'s `BEFORE`); "
         "AFTER is the engine's plain defaults; pro is the professional's DST for the same job. "
         "Counts are pystitch records off the DSTs. Held OFF: " + ", ".join(f"`{f}`" for f in HELD_OFF) + ".",
         "", "| fixture | width | engine | BEFORE st / tr | AFTER st / tr | pro st / tr | points moved | pictures |",
         "|---|---|---|---|---|---|---|---|"]
    for r in rows:
        pics = " ".join(f"[{k}]({v})" for k, v in r["images"].items())
        L.append(f"| {r['fixture']} | {r['width_mm']:g} mm | {r['engine']} | "
                 f"{r['before']['stitches']:,} / {r['before']['trims']} | "
                 f"{r['after']['stitches']:,} / {r['after']['trims']} | "
                 f"{r['pro']['stitches']:,} / {r['pro']['trims']} | {r['diff']:,} | {pics} |")
    L += ["", "Regenerate: `python -m tools.flip_eight_proof` from `digitizer/`."]
    return "\n".join(L) + "\n"


def main(argv=None) -> int:
    utf8_console()
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    ap.add_argument("--fixtures", nargs="*", default=[s for s, _ in fsr.FIXTURES])
    a = ap.parse_args(argv)
    a.out.mkdir(parents=True, exist_ok=True)
    rows = [one_fixture(slug, a.cache, a.out) for slug in a.fixtures]
    (a.out / "README.md").write_text(markdown(rows), encoding="utf-8")
    (a.out / "rows.json").write_text(json.dumps(rows, indent=1), encoding="utf-8")
    print(f"wrote {a.out / 'README.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
