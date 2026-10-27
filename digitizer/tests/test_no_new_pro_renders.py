# digitizer/tests/test_no_new_pro_renders.py
"""No NEW render of the professional's stitch files under docs/.

Kent's ruling, 2026-10-27, verbatim: "Stop new ones, keep old (Recommended)".
This repo is PUBLIC. docs/ already holds about 210 images drawn from the pro's
files, and they stay; `tests/pro_renders_allowlist.txt` lists exactly those,
generated once from main 8341d1f7. Any other committed image under docs/ whose
path marks the pro (`tools.pro_renders.marks_pro`) fails here. Write it to
`pro_renders/` (gitignored) instead: the render tools default there.

Cheap on purpose: `git ls-files` and names, no image is opened.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from tools import pro_renders as pr

ALLOWLIST = Path(__file__).with_name("pro_renders_allowlist.txt")


def _allowed() -> set[str]:
    lines = ALLOWLIST.read_text(encoding="utf-8").splitlines()
    return {s for s in (x.strip() for x in lines) if s and not s.startswith("#")}


def test_no_new_pro_render_under_docs():
    files = pr.committed_images()
    if files is None:
        pytest.skip("not a git checkout: the committed-image inventory is unavailable")
    assert files, "no committed image under docs/: the inventory broke"
    new = sorted(set(pr.flagged(files)) - _allowed())
    assert not new, (
        f"{len(new)} new image(s) under docs/ marked as drawn from the pro's file: {new}. "
        "Kent 2026-10-27: \"Stop new ones, keep old (Recommended)\". Write pro renders to "
        "pro_renders/ (gitignored, `tools.pro_renders.out_dir`). A file the rule flags that is "
        "NOT drawn from a pro file: rename it so no folder or word in its name is `pro`.")


@pytest.mark.parametrize("path", [
    "renders/flip-sheet-2026-10-23/tie_in_off__mfab_hat__pro.jpg",
    "renders/flip-sheet-2026-10-23/tie_in_off__mfab_hat__pro_xray.jpg",
    "renders/keyline-loop-chain-2026-10-26/mfab_hat_off_on_pro.jpg",
    "renders/x/pro-crop.png",
    "renders/x/ours_vs_PRO.png",
    "renders/border-by-size-2026-10-23/pro_pair_mfab_hat_S127f7bff/sheet_whole.png",
    "renders/outer-rail-pitch-2026-10-06/zoom_pro925_HOTE.png",
    "renders/x/professional_crop.png",
])
def test_the_rule_marks_the_pro(path):
    assert pr.marks_pro(path)


@pytest.mark.parametrize("path", [
    "renders/flip-sheet-2026-10-27/lettering_columns_italic_lean__proseal_hat__off.jpg",
    "renders/blend-pullcomp-2026-09-04/repro_frame_seam_zoom_artwork.jpg",
    "renders/area-weighted-promotions-2026-09-16/promoted_drone_0.jpg",
    "renders/x/approach_process.png",
    "renders/x/mfab_hat_off_on.jpg",
])
def test_the_rule_leaves_other_words(path):
    assert not pr.marks_pro(path)


def test_the_docs_folder_itself_is_not_read():
    assert pr.flagged(["docs/renders/a/off.jpg", "docs/renders/a/b_pro.jpg"]) == ["docs/renders/a/b_pro.jpg"]


def test_every_listed_file_is_one_the_rule_flags():
    """The list holds today's flagged images and nothing else: an entry the
    rule would not flag is a hole someone could hide a pro render behind."""
    stray = sorted(f for f in _allowed() if not pr.marks_pro(Path(f).relative_to("docs").as_posix()))
    assert not stray, stray


def test_render_tools_default_outside_docs():
    """Every tool whose default used to put a pro panel under docs/ now
    defaults to `pro_renders/`."""
    from tools import border_census, flip_eight_proof, flip_sheet_renders, lane_census
    docs = (pr.REPO / "docs").resolve()
    for where in (flip_sheet_renders.DEFAULT_PRO_RENDERS, flip_eight_proof.DEFAULT_OUT,
                  border_census.OUT_CROPS, lane_census.OUT_RENDERS):
        where = Path(where).resolve()
        assert docs not in where.parents, where
        assert pr.ROOT.resolve() in where.parents, where


def test_a_pro_folder_under_docs_is_refused():
    with pytest.raises(SystemExit, match="never goes under docs/"):
        pr.refuse_docs(pr.REPO / "docs" / "renders" / "flip-sheet-x")
    assert pr.refuse_docs(pr.out_dir("flip-sheet-x")) == pr.out_dir("flip-sheet-x")


def test_the_flip_sheet_names_its_pro_folder_after_its_renders():
    from tools import flip_sheet_renders as fsr
    a = fsr.parse_args(["report", "--renders", "../docs/renders/flip-sheet-2026-10-27"])
    assert a.pro_renders is None          # report_cmd resolves it: pro_renders/flip-sheet-2026-10-27
    assert fsr.DEFAULT_PRO_RENDERS == pr.out_dir(fsr.DEFAULT_RENDERS.name)
