"""tools/flag_sweep.py: the one OFF-vs-ON sweep a flip's evidence comes from.

No digitizing here (the tool's smoke run is in the PR body): the population is
pinned to the tripwire's list and the scorecard's fixtures, the arms to the
requests they hand `pro_pair.digitize`, the figures to a DST written in the
test, and `main` is driven with `sweep_one` replaced so the report, the exit
code and the picture gate are checked without a minute per run.
"""
from __future__ import annotations

import json

import pytest

from tools import flag_sweep as fs
from tools import tripwire as tw
from tools.corpus_scorecard import FIXTURES


def test_population_is_every_tripwire_placement_then_every_fixture():
    pop = fs.population()
    tripwire = [r["slug"] for r in pop if r["kind"] == "tripwire"]
    corpus = [r["slug"] for r in pop if r["kind"] == "corpus"]
    assert tripwire == tw.committed_jobs()
    assert len(tripwire) == 18          # 2026-11-18: the nightly's list, not a subset
    assert corpus == ["corpus:" + f for f in FIXTURES]
    assert len(corpus) == 26
    assert [r["kind"] for r in pop] == ["tripwire"] * 18 + ["corpus"] * 26


def test_both_placements_of_one_artwork_are_in():
    """The miss that made this tool: #1656 moved mfab_hat AND mfab_lc."""
    slugs = {r["slug"] for r in fs.population()}
    assert {"mfab_hat", "mfab_lc"} <= slugs


def test_tripwire_rows_carry_the_pro_width_and_garment_the_nightly_uses():
    from tools.pro_baseline import JOBS
    for r in fs.population(corpus=False):
        garment, width, *_ = JOBS[r["slug"]]
        assert (r["garment"], r["width_mm"]) == (garment, float(width))


def test_corpus_rows_use_the_studio_request():
    from tools.fremont_triage import KENT_WIDTH_MM
    for r in fs.population(tripwire=False):
        assert (r["garment"], r["width_mm"]) == ("hat_front", float(KENT_WIDTH_MM))


def test_only_filters_by_slug_or_fixture_name():
    assert [r["slug"] for r in fs.population(only=["mfab_lc"])] == ["mfab_lc"]
    assert [r["slug"] for r in fs.population(only=["logo_alpha.png"])] == ["corpus:logo_alpha.png"]


def test_arms_set_the_flag_and_lay_context_over_both():
    a = fs.arms("speck_prune", {"extra.x": 1})
    assert a["off"] == {"extra.x": 1, "speck_prune": False}
    assert a["on"] == {"extra.x": 1, "speck_prune": True}
    v = fs.arms("satin_push_keeps_gaps", {}, on=0.5, off=None)
    assert v["off"]["satin_push_keeps_gaps"] is None and v["on"]["satin_push_keeps_gaps"] == 0.5


def test_the_arm_dicts_are_a_config_the_studio_parser_accepts():
    from tools import pro_pair
    for arm in fs.arms("speck_prune", {}).values():
        cfg = pro_pair.config(81.0, "hat_front", arm)
        assert cfg.speck_prune is arm["speck_prune"]


def _write(path, rows):
    import pystitch
    pat = pystitch.EmbPattern()
    for x, y, c in rows:
        pat.add_stitch_absolute(c, x, y)
    pat.add_command(pystitch.END)
    pystitch.write_dst(pat, str(path))


def test_measure_dst_counts_and_the_md5_follows_the_stitches(tmp_path):
    import pystitch
    S, J, T, C = pystitch.STITCH, pystitch.JUMP, pystitch.TRIM, pystitch.COLOR_CHANGE
    a, b, c = tmp_path / "a.dst", tmp_path / "b.dst", tmp_path / "c.dst"
    _write(a, [(0, 0, S), (10, 0, S), (10, 0, T), (100, 0, J), (110, 0, S), (110, 0, C), (110, 10, S)])
    _write(b, [(0, 0, S), (10, 0, S), (10, 0, T), (100, 0, J), (110, 0, S), (110, 0, C), (110, 10, S)])
    _write(c, [(0, 0, S), (10, 0, S), (10, 0, T), (100, 0, J), (110, 0, S), (110, 0, C), (110, 20, S)])
    ma, mb, mc = (fs.measure_dst(p) for p in (a, b, c))
    assert ma == mb and ma["md5"] != mc["md5"]
    assert ma["trims"] >= 1 and ma["jumps"] >= 1 and ma["colours"] == 2
    assert ma["stitches"] >= 4 and ma["needle_up_mm"] > 0


def _fig(md5, stitches=100, nu=10.0):
    return {"md5": md5, "stitches": stitches, "trims": 2, "jumps": 3, "needle_up_mm": nu, "colours": 2}


def _doc(rows):
    return {"flag": "f", "on": True, "off": False, "sets": {}, "rows": rows}


def test_table_says_moved_and_the_deltas_and_lists_errors():
    rows = [
        {"slug": "mfab_lc", "kind": "tripwire", "off": _fig("a" * 32), "on": _fig("b" * 32, 90, 12.5), "moved": True},
        {"slug": "mfab_hat", "kind": "tripwire", "off": _fig("c" * 32), "on": _fig("c" * 32), "moved": False},
        {"slug": "corpus:x.png", "kind": "corpus", "error": "SystemExit: gone"},
    ]
    md = fs.table(_doc(rows))
    assert "**1 moved**" in md and "1 unchanged" in md and "1 errored" in md
    assert "| mfab_lc | yes |" in md and "100 -> 90 (-10)" in md and "10.0 -> 12.5 (+2.5)" in md
    assert "| mfab_hat | no |" in md
    assert "| corpus:x.png | ERROR |" in md


def test_main_writes_json_and_markdown_and_pictures_only_for_movers(tmp_path, monkeypatch):
    pop = [{"slug": "mfab_hat", "kind": "tripwire", "spec": "x", "width_mm": 1.0, "garment": "hat_front"},
           {"slug": "mfab_lc", "kind": "tripwire", "spec": "x", "width_mm": 1.0, "garment": "left_chest"}]
    monkeypatch.setattr(fs, "population", lambda *a, **k: pop)
    monkeypatch.setattr(tw, "materialise", lambda *a, **k: None)

    def fake(row, flag, arm_extra, out):
        moved = row["slug"] == "mfab_lc"
        return {"slug": row["slug"], "kind": "tripwire", "width_mm": 1.0, "garment": "x", "secs": 0.0,
                "off": _fig("a" * 32), "on": _fig("b" * 32 if moved else "a" * 32), "moved": moved,
                "_art_path": "art.png"}
    monkeypatch.setattr(fs, "sweep_one", fake)
    pics = []
    monkeypatch.setattr(fs, "picture", lambda row, out: pics.append(row["slug"]))
    rc = fs.main(["--flag", "speck_prune", "--set", "extra.k=2", "--pictures", "--out", str(tmp_path)])
    assert rc == 0 and pics == ["mfab_lc"]
    doc = json.loads((tmp_path / "sweep.json").read_text(encoding="utf-8"))
    assert doc["moved"] == ["mfab_lc"] and doc["sets"] == {"extra.k": 2} and doc["errors"] == []
    assert all("_art_path" not in r for r in doc["rows"])
    assert "**1 moved**" in (tmp_path / "sweep.md").read_text(encoding="utf-8")


def test_a_run_that_cannot_digitize_is_a_row_not_a_crash(tmp_path, monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("no")
    monkeypatch.setattr(fs, "run_arm", boom)
    monkeypatch.setattr(fs, "_resolve_art", lambda row, s: tmp_path / "a.png")
    r = fs.sweep_one({"slug": "s", "kind": "corpus", "width_mm": 1.0, "garment": "hat_front"},
                     "f", fs.arms("f", {}), tmp_path)
    assert r["error"].startswith("RuntimeError") and "moved" not in r


def test_the_tool_never_writes_a_pro_render():
    """It draws our stitches only: no pro DST is read by this module."""
    src = fs.__file__
    text = open(src, encoding="utf-8").read()
    assert "pro_dst" not in text and "JOBS[s][3]" not in text
