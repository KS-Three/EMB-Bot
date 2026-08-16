"""Prep the 15 designs that have REAL customer artwork, in both lanes.

Lane `recon` is exactly what `prep_all.py` has always done: artwork
reconstructed from the pro's own stitches. Lane `real` feeds the engine the
artwork the customer actually sent (see `real_art.py`).

Same designs, same pro files, same engine, same config — the ONLY difference is
the image handed to stage 1. So `score(recon) - score(real)` per design is a
direct measurement of how much the reconstructed-art corpus has been flattering
the engine, replacing the +10-18 point estimate in
`pro-parity-program-2026-08-14.md` §2 that was extrapolated from a single
design.

Run:
    PRO_PARITY_ROOT="G:/My Drive/EMB-Bot/Embroidery Files" \
    PRO_PARITY_OUT=<somewhere> python digitizer/tools/pro_parity/prep_both.py

Then score each lane:
    python digitizer/tools/pro_parity/scorecard.py <OUT>/real/*
    python digitizer/tools/pro_parity/scorecard.py <OUT>/recon/*

Paths below are relative to PRO_PARITY_ROOT and are the LOCAL Google Drive
copies, verified byte-identical (md5, 110/110 files) to the `Embroidery
Files.zip` the earlier corpus was built from. The macOS-colon folder names the
zip carries (`To a T:Becker Beanies`) appear as `_` on Windows.
"""
import json
import os
import shutil
import sys
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import prep_all
import real_art

ROOT = Path(os.environ.get("PRO_PARITY_ROOT", r"G:/My Drive/EMB-Bot/Embroidery Files"))
prep_all.ROOT = ROOT

# Resolved in main(), not at import: `DESIGNS` is worth importing from other
# probes (which garment each design is, which artwork goes with which stitch
# file) and a module-level `os.environ[...]` made that a KeyError.
OUT = None


def _out():
    global OUT
    if OUT is None:
        OUT = Path(os.environ["PRO_PARITY_OUT"])
    return OUT

# (slug, pro stitch file, customer artwork, garment_id).
# PES where it exists (it carries thread colours); DST where that is all the job
# has.
#
# The GARMENT comes from the pro's own filename convention, per Kent
# (2026-08-15): `hat` is a Richardson 112 — a structured, foam-backed cap front;
# `beanie` is a knit winter hat; `LC` is a left chest; Hotel Fremont's second
# file is a twill patch. Every parity run before this one passed no garment at
# all, so `fabrics.py` fell back to `pique_knit` (a polo left chest) for cap
# fronts and beanies alike — see docs/pro-parity-real-art-2026-08-15.md §5b.
#
# `bridge_hat` / `bridge_lc` are NEW — the Bridge Bar job arrived with the
# artwork on 2026-08-15 and was never in the 23-design corpus.
DESIGNS = [
    ("becker_hat_large",    "Becker Marine/Becker Hat & Polo Large/beckers logo hat.PES",
                            "Becker Marine/Becker Marine Logo.png", "hat_front"),
    ("becker_lc_large",     "Becker Marine/Becker Hat & Polo Large/beckers logolc.PES",
                            "Becker Marine/Becker Marine Logo.png", "left_chest"),
    ("becker_hat_small",    "Becker Marine/Becker Hat & Polo Small/Becker Hat Small/beckers logo hat 2 A.PES",
                            "Becker Marine/Becker Marine Logo.png", "hat_front"),
    ("becker_chest_small",  "Becker Marine/Becker Hat & Polo Small/Becker Chest Small/beckers logo LC 2 A.PES",
                            "Becker Marine/Becker Marine Logo.png", "left_chest"),
    ("becker_beanie",       "To a T_Becker Beanies/beckers logo hat 2 A a.PES",
                            "Becker Marine/Becker Marine Logo.png", "beanie"),
    ("gaulke_roofing_hat",  "Gaulke Roofing/c golke logo hat.DST",
                            "Gaulke Roofing/Gaulke Roofing Logo.png", "hat_front"),
    ("gaulke_roofing_lc",   "Gaulke Roofing/c golke logo LC.DST",
                            "Gaulke Roofing/Gaulke Roofing Logo.png", "left_chest"),
    ("hotel_fremont_hat",   "Hotel Fremont/Hotel Hat/HOTEL FREMONT HAT.PES",
                            "Hotel Fremont/Hotel Fremont Logo.webp", "hat_front"),
    ("hotel_fremont_patch", "Hotel Fremont/Hotel Patch/HOTEL FREMONT .PES",
                            "Hotel Fremont/Hotel Fremont Logo.webp", "patch"),
    ("mfab_hat",            "MFAB/Mfab Hat & Polo/mf4b logo hat.PES",
                            "MFAB/MFab Logo.png", "hat_front"),
    ("mfab_lc",             "MFAB/Mfab Hat & Polo/mf4b logo lc.PES",
                            "MFAB/MFab Logo.png", "left_chest"),
    ("precision_drone",     "Precision Drone/PRECISION DRON HAT 2.PES",
                            "Precision Drone/Precision Thermal Drone Logo.png", "hat_front"),
    ("tires_hat_3d",        "TIRES/fwdyourdigitizingorderisreadytireslogo (1)/TIRES HAT 3D.PES",
                            "TIRES/Tires Logo.png", "hat_front"),
    ("bridge_hat",          "Bridge Bar/Bridge Bar Embroidery Files/BRIDGE LOGO HAT.PES",
                            "Bridge Bar/Bridge Bar Logo.jpg", "hat_front"),
    ("bridge_lc",           "Bridge Bar/Bridge Bar Embroidery Files/BRIDGE LOGO LC.PES",
                            "Bridge Bar/Bridge Bar Logo.jpg", "left_chest"),
]

# Set PRO_PARITY_GARMENT=0 to reproduce the pre-2026-08-15 behaviour (no garment
# passed, so every design digitizes as pique_knit).
USE_GARMENT = os.environ.get("PRO_PARITY_GARMENT", "1") != "0"

PRO_FILES = ("pro_stitches.csv", "pro_blocks.json", "pro_render.png")


def prep_one(slug, stitch_rel, art_rel, garment_id):
    entry = {"slug": slug, "source": stitch_rel, "art": art_rel,
             "garment_id": garment_id if USE_GARMENT else None}
    path = prep_all.find_file(stitch_rel)
    if path is None:
        raise FileNotFoundError(stitch_rel)
    entry["file"] = str(path)

    blocks, breaks, threads, bounds, jumps, trims = prep_all.decode(path)
    assert all(len(b) == len(k) for b, k in zip(blocks, breaks))
    cvs = prep_all.Canvas(bounds)
    width_mm = bounds[2] - bounds[0]

    out = _out()
    recon = out / "recon" / slug
    real = out / "real" / slug
    for d in (recon, real):
        d.mkdir(parents=True, exist_ok=True)

    # --- pro side: identical in both lanes ---------------------------------
    meas, flags = prep_all.reconstruct(blocks, threads, cvs,
                                       recon / "art.png", recon / "art_meta.json")
    (recon / "pro_blocks.json").write_text(
        json.dumps(prep_all.block_summary(blocks, threads, meas), indent=1))
    with open(recon / "pro_stitches.csv", "w") as f:
        f.write("block,run,trim,jump,x_mm,y_mm\n")
        for i, runs in enumerate(blocks):
            for ri, (r, kind) in enumerate(zip(runs, breaks[i])):
                t = 1 if kind in ("trim", "color") else 0
                j = 1 if kind == "jump" else 0
                for k, (x, y) in enumerate(r):
                    f.write(f"{i},{ri},{t if k == 0 else 0},"
                            f"{j if k == 0 else 0},{x:.2f},{y:.2f}\n")
    prep_all.render(blocks, threads, flags, recon / "pro_render.png", bounds=bounds)
    for n in PRO_FILES:
        shutil.copyfile(recon / n, real / n)

    entry["pro"] = {
        "stitches": sum(len(p) for runs in blocks for p in runs),
        "blocks": len(blocks),
        "runs": sum(len(runs) for runs in blocks),
        "jumps": jumps, "trims": trims,
        "width_mm": round(width_mm, 1),
        "height_mm": round(bounds[3] - bounds[1], 1),
    }

    # --- real artwork ------------------------------------------------------
    art_src = prep_all.find_file(art_rel)
    if art_src is None:
        raise FileNotFoundError(art_rel)
    info = real_art.prepare(art_src, real / "art.png")
    info["dpi_vs_design"] = real_art.dpi(info["ink_bbox_px"][0], width_mm)
    entry["art_prep"] = info

    # --- engine, once per lane --------------------------------------------
    for lane, d in (("recon", recon), ("real", real)):
        res, plan, ours_blocks, ours_threads = prep_all.run_ours(
            d / "art.png", width_mm, d,
            garment_id=garment_id if USE_GARMENT else None)
        entry[lane] = {
            "stitches": sum(len(r) for runs in ours_blocks for r in runs),
            "blocks": len(ours_blocks),
            "regions": len(res.regions),
            **prep_all.machine_meta(d),
            "warnings": [w["code"] for w in res.warnings],
        }
        allpts = [p for runs in ours_blocks for r in runs for p in r]
        if allpts:
            bb = (min(p[0] for p in allpts), min(p[1] for p in allpts),
                  max(p[0] for p in allpts), max(p[1] for p in allpts))
            prep_all.render(ours_blocks, ours_threads, None,
                            d / "ours_render.png", bounds=bb)
    entry["ok"] = True
    return entry


def main():
    want = set(a for a in sys.argv[1:] if not a.startswith("-"))
    targets = [d for d in DESIGNS if not want or d[0] in want]
    manifest = []
    print(f"garment_id: {'FROM FILENAME' if USE_GARMENT else 'None (pique_knit for everything)'}")
    for slug, stitch_rel, art_rel, garment_id in targets:
        t0 = time.time()
        try:
            entry = prep_one(slug, stitch_rel, art_rel, garment_id)
        except Exception as e:
            entry = {"slug": slug, "source": stitch_rel, "art": art_rel, "ok": False,
                     "error": f"{type(e).__name__}: {e}",
                     "trace": traceback.format_exc()[-800:]}
        entry["seconds"] = round(time.time() - t0, 1)
        manifest.append(entry)
        if entry["ok"]:
            print(f"[{slug}] {str(entry['garment_id']):10s} pro {entry['pro']['stitches']:6d} st | "
                  f"recon {entry['recon']['stitches']:6d} | real {entry['real']['stitches']:6d} | "
                  f"art {entry['art_prep']['dpi_vs_design']:6.1f} dpi "
                  f"({entry['seconds']}s)", flush=True)
        else:
            print(f"[{slug}] FAILED {entry['error']} ({entry['seconds']}s)", flush=True)

    # scorecard.py reads manifest.json from the PARENT of each design dir, so
    # both lanes need their own copy.
    for lane in ("recon", "real"):
        p = _out() / lane / "manifest.json"
        old = {e["slug"]: e for e in (json.loads(p.read_text()) if p.exists() else [])}
        old.update({e["slug"]: e for e in manifest})
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps([old[s] for s, _, _, _ in DESIGNS if s in old], indent=1))
    print(f"\n{sum(1 for e in manifest if e['ok'])}/{len(manifest)} designs prepped, both lanes")


if __name__ == "__main__":
    main()
