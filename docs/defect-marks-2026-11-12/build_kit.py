"""Build the 2026-11-12 letter-reader replication kit (pre-registration:
`letter-reader-replication-preregistration.md` beside this file).

    cd digitizer
    python ../docs/defect-marks-2026-11-12/build_kit.py [--only lt_<slug>] [--kit-only]

The nine public-domain lettering logos of `testdata/art/commons_lettering/`
are copied (gitignored) to `eye_pairs_out/defect-marks-1112-art/` as
`<slug>.png` with a `corpus.json` of logo rows, digitized one process at a
time through `photo_corpus.capture` with the tree's own Studio request (80 mm,
left_chest) into `corpus_runs/lettering-1112-<sha8>/`, and turned into the
marking page by `defect_marks.build_kit` at `eye_pairs_out/defect-marks-1112/`
(items `C_lt_<slug>`). Nothing here changes the request, the reader or the page.
Serve: `python -m tools.defect_marks serve --kit eye_pairs_out/defect-marks-1112 --port 8738`.
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

SRC = DIGITIZER / "testdata" / "art" / "commons_lettering"
# item slug -> committed file, the order and names of the pre-registration's table
ITEMS = {
    "lt_bukit_asam": "bukit_asam_logo_cmyk_01.png",
    "lt_but_seriously": "but_seriously_logo.png",
    "lt_hed_p_e": "hed_p_e_logo.png",
    "lt_jakarta": "jakarta_logo.png",
    "lt_k_line": "k_line_logo.png",
    "lt_ahora": "logo_ahora.png",
    "lt_dot_music": "music_logo.png",
    "lt_n_sync": "n_sync_logo.png",
    "lt_and_pizza": "pizza_logo.png",
}
ART = DIGITIZER / "eye_pairs_out" / "defect-marks-1112-art"
KIT = DIGITIZER / "eye_pairs_out" / "defect-marks-1112"


def stage_art() -> list[dict]:
    """Copy the nine files as `<slug>.png` and write the logo rows."""
    ART.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((SRC / "manifest.json").read_text(encoding="utf-8"))
    rows = []
    for slug, fname in ITEMS.items():
        shutil.copyfile(SRC / fname, ART / f"{slug}.png")
        m = manifest[fname]
        rows.append({"slug": slug, "kind": "logo", "genre": slug, "title": m["title"], "page": m["page"],
                     "author": m["author"], "licence": m["licence"]})
    (ART / "corpus.json").write_text(json.dumps(rows, indent=1), encoding="utf-8")
    return rows


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", action="append", default=[])
    ap.add_argument("--kit-only", action="store_true", help="skip the capture, rebuild the page")
    a = ap.parse_args(argv)
    rows = stage_art()
    sha = pc._head_sha(DIGITIZER)
    run = pc.RUNS_DIR / f"lettering-1112-{sha[:8]}"
    if not a.kit_only:
        todo = [r for r in rows if not a.only or r["slug"] in a.only]
        res = pc.capture(todo, ART, DIGITIZER, run, sha, procs=1)
        for slug, r in res["rows"].items():
            print(slug, r.get("state"), r.get("stitch_count") or (r.get("stats") or {}).get("stitch_count"),
                  flush=True)
    kit = dm.build_kit(KIT, run, None, photos=ART)
    print("kit", kit["kit_sha256"][:12], "items", [it["id"] for it in kit["items"]], "skipped", kit["skipped"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
