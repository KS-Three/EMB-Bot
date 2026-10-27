#!/usr/bin/env python
"""Where a render of the professional's stitch file goes: never under docs/.

**Kent's ruling, 2026-10-27, verbatim: "Stop new ones, keep old
(Recommended)".** The repo is PUBLIC, and docs/ already held about 210 images
drawn from the pro's files (flip-sheet `__pro.jpg` tiles, `off_on_pro` crops,
`pro_pair` sheets). Those stay where they are. A NEW one is written to `ROOT`,
gitignored and local only. Our own tiles may still go to docs/.

`digitizer/tests/test_no_new_pro_renders.py` holds the line: it fails on any
committed image under docs/ that `marks_pro` flags and that is not in today's
list (`tests/pro_renders_allowlist.txt`). The rule reads names only,
never pixels. A composite whose name says nothing of the pro (`pro_pair`'s
`sheet_whole.png`, `bay_census`'s `<slug>.png`) is invisible to it, which is
why the tools that compose one write it here by default.

    .venv/Scripts/python -m tools.pro_renders            # list today's flagged images
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path, PurePosixPath

REPO = Path(__file__).resolve().parents[2]
ROOT = REPO / "pro_renders"     # gitignored (root .gitignore)
DOCS = "docs"
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".bmp", ".tif", ".tiff"}
_SPLIT = re.compile(r"[^a-z0-9]+")
#: a word that marks the pro: `pro` (`__pro`, `_pro`, `-pro`, `off_on_pro`,
#: `pro_pair_<slug>/`), `pro925` (the pro at 92.5 mm), `professional`. Not
#: `proseal` (a customer), `repro`, `promoted`.
_PRO_WORD = re.compile(r"pro\d*|professional")


def out_dir(name: str) -> Path:
    """`ROOT / name`: the default folder for a tool's pro renders."""
    return ROOT / name


def refuse_docs(path) -> Path:
    """`path`, or SystemExit when it lies under docs/ (a pro render's folder)."""
    p = Path(path).resolve()
    docs = (REPO / DOCS).resolve()
    if p == docs or docs in p.parents:
        raise SystemExit(f"{path}: a render of the pro's file never goes under docs/ "
                         "(Kent 2026-10-27: \"Stop new ones, keep old (Recommended)\")")
    return Path(path)


def marks_pro(path) -> bool:
    """True when any word of `path` -- each folder and the file's stem, split
    on anything not a letter or digit -- is a pro word (`_PRO_WORD`)."""
    p = PurePosixPath(str(path).replace("\\", "/"))
    parts = [*p.parent.parts, p.stem]
    return any(_PRO_WORD.fullmatch(w) for part in parts for w in _SPLIT.split(part.lower()) if w)


def committed_images(repo: Path = REPO) -> list[str] | None:
    """Every committed image under docs/, repo-relative with `/`; None outside
    a git checkout."""
    proc = subprocess.run(["git", "ls-files", "-z", "--", DOCS], cwd=repo, capture_output=True, text=True)
    if proc.returncode != 0:
        return None
    return sorted(f for f in proc.stdout.split("\0") if f and PurePosixPath(f).suffix.lower() in IMAGE_EXTS)


def flagged(files: list[str]) -> list[str]:
    """`files` whose path below docs/ marks the pro (the `docs` folder itself
    is not read)."""
    return [f for f in files if marks_pro(PurePosixPath(f).relative_to(DOCS))]


def main() -> int:
    files = committed_images()
    if files is None:
        print("not a git checkout")
        return 2
    for f in flagged(files):
        print(f)
    return 0


if __name__ == "__main__":
    sys.exit(main())
