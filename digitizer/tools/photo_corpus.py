#!/usr/bin/env python
"""The cross-genre Commons corpus and its side-by-side scorecard.

Kent, 2026-10-27, after the 18-genre photo census: "it's as if this digitize
was only building tools to improve the photos we had on hand. This digitizer
needs to be building tools that help and improve ALL photos." Asked what he
wants to look at to judge a photo PR: "Sxs comparison w/ an Artifact that I
can say better or worse." Spec: docs/superpowers/specs/2026-10-27-photo-corpus-sxs-design.md.

Four commands, run from `digitizer/` as `python -m tools.photo_corpus ...`:

    fetch                      testdata/photo/corpus/corpus.json -> <slug>.jpg + manifest.json
                               (Commons API by title; the LIVE licence is re-read and a row
                               whose licence left the allowed set is refused, not downloaded)
    capture --label L [--base REF | --tree DIR]
                               every row digitized with the Studio's own request (80 mm,
                               left_chest) in its own process, cwd = the tree under test, so
                               `--base origin/main` runs the merge-base's digitizer_core;
                               writes corpus_runs/L/<slug>.json|.png|.row.json + run.json
    sxs --before DIR --after DIR
                               one self-contained HTML: source thumbnail, before render, after
                               render, the numbers under both, better / same / worse buttons;
                               "Export verdicts" downloads the JSON `tally` files
    tally VERDICTS.json        copies the verdicts under docs/scoreboards/photo-corpus/ and
                               appends one tally line per before/after pair

All numbers are instrument readings, not quality claims (ROADMAP gate 4). The
verdict column is Kent's. Nothing downloaded or rendered is ever committed:
this repo is public.
"""
from __future__ import annotations

import json
from pathlib import Path

DIGITIZER = Path(__file__).resolve().parent.parent
TESTDATA = DIGITIZER / "testdata"
CORPUS_DIR = TESTDATA / "photo" / "corpus"
CORPUS_JSON = CORPUS_DIR / "corpus.json"
RUNS_DIR = DIGITIZER / "corpus_runs"
SCOREBOARD_DIR = DIGITIZER.parent / "docs" / "scoreboards" / "photo-corpus"

#: The fixed line every page and tally carries.
GATE4_LINE = ("All numbers are instrument readings, not quality claims (ROADMAP gate 4). "
              "The verdict column is Kent's.")

#: Commons `LicenseShortName` substrings a public repo may list (lower-cased match).
OK_LICENCES = ("cc0", "public domain", "pd", "cc by 4.0", "cc by 3.0", "cc by 2.0",
               "cc by-sa 4.0", "cc by-sa 3.0", "cc by-sa 2.0")

ROW_KEYS = ("slug", "kind", "genre", "title", "page", "author", "licence")


def licence_ok(short_name: str) -> bool:
    """Lower-cased substring match against OK_LICENCES; empty is never ok."""
    s = (short_name or "").lower()
    return bool(s) and any(k in s for k in OK_LICENCES)


def load_corpus(path: Path = CORPUS_JSON) -> list[dict]:
    """The committed rows. Raises ValueError on a missing key or a repeated slug."""
    rows = json.loads(Path(path).read_text(encoding="utf-8"))
    seen: set[str] = set()
    for r in rows:
        missing = [k for k in ROW_KEYS if k not in r]
        if missing:
            raise ValueError(f"corpus row {r.get('slug')!r} lacks {missing}")
        if r["slug"] in seen:
            raise ValueError(f"corpus slug repeated: {r['slug']!r}")
        seen.add(r["slug"])
    return rows
