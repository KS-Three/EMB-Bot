"""`tools.bench_free_digitizers`: the figure path runs on tiny SYNTHETIC DSTs written here.

No third-party stitch file is read or committed: both machine files are generated
below with pystitch (a tatami block and a satin-ish zig-zag block, a trim between
them). The check is that the seven figures come out of the same reader the
tripwire uses, that the competitor's own counts / box are right, that the table
carries no raw agreement, and that a manifest's claims are compared with what
the reader counts.
"""
from __future__ import annotations

import pytest

pystitch = pytest.importorskip("pystitch")

from tools import bench_free_digitizers as bench  # noqa: E402


def _write(path, rows, shift=0.0):
    """A tatami block (long rows 0.4 mm apart), a TRIM, then a zig-zag column."""
    p = pystitch.EmbPattern()
    y = 0.0
    for i in range(30):
        xs = (0.0, 20.0) if i % 2 == 0 else (20.0, 0.0)
        for x in xs:
            p.add_stitch_absolute(pystitch.STITCH, (x + shift) * 10, y * 10)
        y += 0.4
    p.add_stitch_absolute(pystitch.TRIM, 0, 0)
    p.add_stitch_absolute(pystitch.JUMP, 30 * 10, 0)
    for k in range(rows):
        p.add_stitch_absolute(pystitch.STITCH, (30 + (k % 2) * 3) * 10, k * 0.4 * 10)
    p.add_stitch_absolute(pystitch.END, 0, 0)
    pystitch.write_dst(p, str(path))


def test_longest_side_uses_the_ink_box_aspect():
    assert bench.longest_side_mm(100.0, (50, 100)) == 100.0          # wider than tall
    assert bench.longest_side_mm(100.0, (200, 100)) == 200.0         # taller than wide
    assert bench.longest_side_mm(61.0, (100, 99)) == pytest.approx(61.62, abs=0.01)


def test_figures_from_synthetic_dsts(tmp_path):
    comp, pro = tmp_path / "comp.dst", tmp_path / "pro.dst"
    _write(comp, 20)
    _write(pro, 40, shift=0.5)
    r = bench.competitor_figures(comp, pro, tmp_path / "score", "synthetic")
    assert r["own"]["stitches"] == 60 + 20          # 30 rows x 2 ends + the zig-zag
    assert r["own"]["trims"] == 1
    assert r["own"]["width_mm"] > 20 and r["own"]["height_mm"] > 10
    v = r["values"]
    assert {"stitches", "trims", "hops", "needle_up_mm"} <= set(v)
    assert v["hops"] >= 1 and v["needle_up_mm"] > 0
    assert r["pro"]["stitches"] == 100
    # the kappa half either ran (chance-corrected, with its chance floor) or says why not
    assert ("sttype_kappa" in v and r["chance"] is not None) or "kappa_error" in v
    # nothing raw leaks into a figure (ROADMAP gate 4)
    assert not any("raw" in k or "agreement" in k for k in v)


def test_table_and_manifest_check(tmp_path):
    comp, pro = tmp_path / "comp.dst", tmp_path / "pro.dst"
    _write(comp, 20)
    _write(pro, 40)
    r = bench.competitor_figures(comp, pro, tmp_path / "score", "synthetic")
    r["ours"] = dict(r["values"])
    r["size_ratio"] = 1.0
    r["manifest_check"] = bench.manifest_check({"stitch_count": 70, "trims": "1"}, r["own"])
    assert r["manifest_check"]["stitches"] == {"stated": 70.0, "read": 80, "diff": 10.0}
    assert r["manifest_check"]["trims"]["diff"] == 0
    md = bench.table({"engine": "synth", "date": "2026-11-04", "jobs": {"synthetic": r}, "missing": ["other"]})
    assert "| synthetic |" in md and "other" in md
    assert "raw" not in md.lower() and "agreement" not in md.lower()


def test_manifest_loading_is_forgiving(tmp_path):
    assert bench.load_manifest(tmp_path) == {}
    (tmp_path / "manifest.json").write_text("not json", encoding="utf-8")
    assert bench.load_manifest(tmp_path) == {}
    (tmp_path / "manifest.json").write_text('{"jobs": {"a": {"stitch_count": 5}}, "x": 1}', encoding="utf-8")
    assert bench.load_manifest(tmp_path) == {"a": {"stitch_count": 5}}


def test_reports_match_one_engine_not_its_arms(tmp_path):
    for n in ("report-nuizu-2026-11-04.json", "report-nuizu-satin-auto-2026-11-04.json",
              "report-nuizu-2026-11-05.json", "report-nuizu-2026-11-04.md"):
        (tmp_path / n).write_text("{}", encoding="utf-8")
    got = [p.name for p in bench._reports(tmp_path, "nuizu")]
    assert got == ["report-nuizu-2026-11-04.json", "report-nuizu-2026-11-05.json"]
    assert [p.name for p in bench._reports(tmp_path, "nuizu-satin-auto")] == ["report-nuizu-satin-auto-2026-11-04.json"]
