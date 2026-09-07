# digitizer/tests/test_flip_sheet.py
"""The flip sheet's arm bookkeeping and its stale-cache guard.

`flip_sheet.py` decides a default, so the two ways it can quietly lie are
worth pinning:

  1. **A combination arm mistaken for a single.** The interaction table asks
     "does this combination behave like the union of its parts?", and it
     answers by comparing against the SINGLES. When `singles` was written as
     "every arm except `off` and `all`", adding any combination arm would have
     put that combination in its own baseline and made the comparison
     meaningless without erroring. It is derived from the flag count now.

  2. **Rows from two different engines in one table.** This actually happened.
     The first pass was cached before `dissolve_phantom_blends` was fixed, the
     fixed arms were re-measured into a second directory, and the published
     sheet drew rows from both — sound, as it turned out (all 26 `off` digests
     match across the two trees, so the flag gate provably holds), but nothing
     in the tool checked. Rows carry their `head` now and `report` says so.

No engine runs here: every assertion is over the arm table or over rows
written to a tmp directory.
"""
from __future__ import annotations

import json

from tools.flip_sheet import ARMS, BARRED, SINGLES, report


def test_singles_are_exactly_the_one_flag_arms():
    """The property the interaction table rests on."""
    assert set(SINGLES) == {a for a, kw in ARMS.items() if len(kw) == 1}
    assert "off" not in SINGLES and "all" not in SINGLES
    for a in SINGLES:
        assert len(ARMS[a]) == 1, a


def test_every_combination_is_made_of_measured_singles():
    """A combination whose flag nothing measures alone cannot be attributed:
    the interaction table would report it as "moves only in combination" for
    a flag that simply has no single-flag row."""
    single_flags = {next(iter(ARMS[a])) for a in SINGLES}
    for arm, kw in ARMS.items():
        if len(kw) <= 1:
            continue
        missing = set(kw) - single_flags
        assert not missing, f"{arm} flips {missing} with no single-flag arm"


def test_barred_flags_are_in_no_arm():
    """`edge_cap` is gate 1 and `chain_links` is gate 3. A sheet that measured
    either would hand Kent a number he is not allowed to act on, and the
    barred list is documentation until something checks it."""
    for arm, kw in ARMS.items():
        for flag in BARRED:
            assert flag not in kw, f"{arm} flips barred flag {flag}"


def _row(tmp, arm, fixture, head, digest="d", score=100, grade="A"):
    (tmp / f"{arm}__{fixture}.json").write_text(json.dumps({
        "arm": arm, "fixture": fixture, "head": head, "digest": digest,
        "stitches": 100, "trims": 1, "blocks": 1, "cones": 1,
        "grade": grade, "score": score,
    }))


def test_report_announces_rows_measured_on_different_trees(tmp_path, capsys):
    _row(tmp_path, "off", "a.png", head="aaaaaaa")
    _row(tmp_path, "halo", "a.png", head="bbbbbbb", digest="e")
    report(tmp_path)
    out = capsys.readouterr().out
    assert "MIXED TREES" in out
    assert "aaaaaaa" in out and "bbbbbbb" in out


def test_report_is_quiet_when_every_row_is_one_tree(tmp_path, capsys):
    """The guard must not cry wolf on the normal case, or it gets ignored."""
    _row(tmp_path, "off", "a.png", head="aaaaaaa")
    _row(tmp_path, "halo", "a.png", head="aaaaaaa", digest="e")
    report(tmp_path)
    out = capsys.readouterr().out
    assert "MIXED TREES" not in out and "PROVENANCE UNKNOWN" not in out


def test_an_unstamped_row_is_UNKNOWN_provenance_not_a_different_tree(tmp_path, capsys):
    """The distinction the banner has to keep. Rows cached before `head`
    existed are not evidence of a second engine — claiming they are would be
    the same over-claim this banner was added to catch."""
    _row(tmp_path, "off", "a.png", head=None)
    _row(tmp_path, "halo", "a.png", head="aaaaaaa", digest="e")
    out = (report(tmp_path), capsys.readouterr().out)[1]
    assert "PROVENANCE UNKNOWN" in out
    assert "MIXED TREES" not in out, "an unstamped row is unknown, not different"
