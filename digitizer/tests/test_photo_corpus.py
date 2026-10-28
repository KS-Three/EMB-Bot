"""tools/photo_corpus.py -- the cross-genre Commons corpus and its side-by-side
scorecard (Kent, 2026-10-27: "This digitizer needs to be building tools that
help and improve ALL photos"; spec docs/superpowers/specs/2026-10-27-photo-corpus-sxs-design.md).

No network and no pipeline here: `fetch` takes an injected API callable,
`capture` runs a stub worker, `sxs` reads tiny synthetic runs. Digitizing the
real corpus is hours of work and belongs to the tool's own CLI.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from tools import photo_corpus as pc


# ------------------------------------------------------------------ Task 1: the list
def test_corpus_rows_are_complete_unique_and_licence_clean():
    rows = pc.load_corpus()
    assert len(rows) >= 18
    assert len({r["slug"] for r in rows}) == len(rows)
    for r in rows:
        assert set(r) >= {"slug", "kind", "genre", "title", "page", "author", "licence"}
        assert r["kind"] in {"photo", "logo"}
        assert r["title"].startswith("File:")
        assert pc.licence_ok(r["licence"]), r["slug"]


def test_no_image_is_tracked_under_the_corpus_dir():
    out = subprocess.run(["git", "ls-files", str(pc.CORPUS_DIR)], capture_output=True, text=True,
                         cwd=pc.DIGITIZER).stdout
    names = {Path(p).name for p in out.split()}
    assert names <= {"corpus.json", "README.md"}


def test_licence_ok_is_a_lowercase_substring_match():
    assert pc.licence_ok("CC BY-SA 4.0")
    assert pc.licence_ok("Public domain")
    assert not pc.licence_ok("CC BY-NC 2.0")
    assert not pc.licence_ok("")


def test_load_corpus_rejects_duplicate_slugs(tmp_path):
    p = tmp_path / "c.json"
    row = {"slug": "a", "kind": "photo", "genre": "g", "title": "File:x.jpg", "page": "u",
           "author": "me", "licence": "cc0"}
    p.write_text(json.dumps([row, row]), encoding="utf-8")
    with pytest.raises(ValueError):
        pc.load_corpus(p)
