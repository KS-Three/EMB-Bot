"""Build the 2026-11-14 photo subject-recall kit (pre-registration:
`subject-recall-preregistration.md` beside this file).

    cd digitizer
    python ../docs/defect-marks-2026-11-14/build_kit.py [--root DIGITIZER] [--corpus-dir DIR] [--only SLUG] [--kit-only]

The 15 photos of the pre-registration's table (every Commons-corpus photo row
Kent had not graded, plus the walkthrough's toadstool) are copied (gitignored)
to `<root>/eye_pairs_out/defect-marks-1114-art/` with a `corpus.json` of photo
rows, digitized one process at a time through `photo_corpus.capture` with THIS
tree's own Studio request (80 mm, left_chest) into
`<root>/corpus_runs/subject-1114-<sha8>/`, and turned into the marking page by
`defect_marks.build_kit` at `<root>/eye_pairs_out/defect-marks-1114/` (items
`P_<slug>`). `--root` defaults to this tree's `digitizer/`; the sitting's kit
was built into the live checkout's so it outlives the lane. Nothing here
changes the request, the reader or the page.
Serve: `python -m tools.defect_marks serve --kit eye_pairs_out/defect-marks-1114 --port 8739`.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

DIGITIZER = Path(__file__).resolve().parents[2] / "digitizer"
sys.path.insert(0, str(DIGITIZER))

from tools import defect_marks as dm  # noqa: E402
from tools import photo_corpus as pc  # noqa: E402

#: The pre-registration's table, in its order: every corpus photo row not
#: graded on 2026-11-10 (bw_street, night_neon, architecture, landscape_lake).
CORPUS_SLUGS = ("food_plate", "vintage_sepia", "fireworks", "snow_highkey", "flower_macro", "dark_dog",
                "underwater_reef", "watercolor", "pencil_sketch", "stained_glass", "group_people",
                "sports_action", "night_skyline", "oil_painting")
TOADSTOOL = ("toadstool_dof_meadow", DIGITIZER / "testdata" / "photo" / "photo_dof_meadow.png")


def stage_art(art: Path, corpus_dir: Path) -> list[dict]:
    """Copy the 15 photos as `<slug>.<ext>` and write their photo rows."""
    art.mkdir(parents=True, exist_ok=True)
    corpus = {r["slug"]: r for r in json.loads((corpus_dir / "corpus.json").read_text(encoding="utf-8"))}
    rows = []
    for slug in CORPUS_SLUGS:
        src = pc.photo_path(corpus_dir, slug)
        if src is None:
            raise SystemExit(f"{slug}: no image under {corpus_dir} (run `python -m tools.photo_corpus fetch`)")
        shutil.copyfile(src, art / f"{slug}{src.suffix}")
        rows.append({**corpus[slug], "kind": "photo"})
    slug, src = TOADSTOOL
    shutil.copyfile(src, art / f"{slug}{src.suffix}")
    rows.append({"slug": slug, "kind": "photo", "genre": "toadstool dof meadow",
                 "title": "photo_dof_meadow.png (repo fixture, build walkthrough 2026-11-13 section 4)"})
    (art / "corpus.json").write_text(json.dumps(rows, indent=1), encoding="utf-8")
    return rows


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, default=DIGITIZER, help="where eye_pairs_out/ and corpus_runs/ go")
    ap.add_argument("--corpus-dir", type=Path, default=pc.CORPUS_DIR, help="the fetched Commons corpus images")
    ap.add_argument("--only", action="append", default=[])
    ap.add_argument("--kit-only", action="store_true", help="skip the capture, rebuild the page")
    a = ap.parse_args(argv)
    art = a.root / "eye_pairs_out" / "defect-marks-1114-art"
    kit_dir = a.root / "eye_pairs_out" / "defect-marks-1114"
    rows = stage_art(art, a.corpus_dir)
    sha = pc._head_sha(DIGITIZER)
    run = a.root / "corpus_runs" / f"subject-1114-{sha[:8]}"
    if not a.kit_only:
        todo = [r for r in rows if not a.only or r["slug"] in a.only]
        res = pc.capture(todo, art, DIGITIZER, run, sha, procs=1)
        for slug, r in res["rows"].items():
            print(slug, r.get("state"), r.get("stitch_count") or (r.get("stats") or {}).get("stitch_count"),
                  flush=True)
    kit = dm.build_kit(kit_dir, run, None, photos=art)
    print("kit", kit["kit_sha256"][:12], "items", [it["id"] for it in kit["items"]], "skipped", kit["skipped"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
