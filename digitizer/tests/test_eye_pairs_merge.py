"""Merging parallel --render lanes: first lane wins, disagreement refuses.
Synthetic lanes only; no digitize, no real logo."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.eye_pairs import merge as m  # noqa: E402


def _lane(root: Path, feats: dict, designs: dict[str, str], renders: dict[str, bytes]) -> Path:
    root.mkdir(parents=True)
    (root / "designs").mkdir()
    (root / "renders").mkdir()
    (root / "features.json").write_text(json.dumps(feats), encoding="utf-8")
    for name, body in designs.items():
        (root / "designs" / name).write_text(body, encoding="utf-8")
    for name, body in renders.items():
        (root / "renders" / name).write_bytes(body)
    return root


def _two_lanes(tmp_path: Path, base_in_lane2: str = '{"stitches": [1]}'):
    lane1 = _lane(tmp_path / "lane1",
                  {"__sources__": {"fx_a": "aaa"},
                   "fx_a": {"base": {"stitches": 10, "wall_s": 1.0},
                            "per_stroke": {"stitches": 11, "wall_s": 1.0}}},
                  {"fx_a__base.json": '{"stitches": [1]}', "fx_a__per_stroke.json": '{"stitches": [2]}'},
                  {"fx_a__base.jpg": b"B", "fx_a__per_stroke.jpg": b"P", "fx_a__art.png": b"A"})
    lane2 = _lane(tmp_path / "lane2",
                  {"__sources__": {"fx_a": "aaa", "fx_b": "bbb"},
                   "fx_a": {"base": {"stitches": 10, "wall_s": 2.0},
                            "ref_0827": {"stitches": 5, "design_only": True}},
                   "fx_b": {"base": {"stitches": 20}, "wide_columns": {"error": "boom"}}},
                  {"fx_a__base.json": base_in_lane2, "fx_a__ref_0827.json": '{"stitches": [3]}',
                   "fx_b__base.json": '{"stitches": [4]}'},
                  {"fx_a__base.jpg": b"B", "fx_a__ref_0827.jpg": b"R", "fx_b__base.jpg": b"Q",
                   "fx_b__art.png": b"Z"})
    return lane1, lane2


def test_rows_are_unioned_and_the_first_lane_wins(tmp_path):
    lane1, lane2 = _two_lanes(tmp_path)
    n = m.merge_lanes(tmp_path / "out", [lane1, lane2])
    feats = json.loads((tmp_path / "out" / "features.json").read_text(encoding="utf-8"))
    assert feats["__sources__"] == {"fx_a": "aaa", "fx_b": "bbb"}
    assert set(feats["fx_a"]) == {"base", "per_stroke", "ref_0827"}
    assert feats["fx_a"]["base"]["wall_s"] == 1.0          # lane1 listed first
    assert feats["fx_b"]["wide_columns"] == {"error": "boom"}   # errors travel
    assert n == {"fixtures": 2, "arm_runs": 5, "renders": 6, "designs": 4}
    assert sorted(p.name for p in (tmp_path / "out" / "renders").iterdir()) == [
        "fx_a__art.png", "fx_a__base.jpg", "fx_a__per_stroke.jpg", "fx_a__ref_0827.jpg",
        "fx_b__art.png", "fx_b__base.jpg"]
    assert (tmp_path / "out" / "designs" / "fx_a__base.json").read_text() == '{"stitches": [1]}'


def test_order_decides_which_lane_wins(tmp_path):
    lane1, lane2 = _two_lanes(tmp_path)
    m.merge_lanes(tmp_path / "out", [lane2, lane1])
    feats = json.loads((tmp_path / "out" / "features.json").read_text(encoding="utf-8"))
    assert feats["fx_a"]["base"]["wall_s"] == 2.0


def test_a_base_digitized_to_two_designs_is_refused(tmp_path):
    lane1, lane2 = _two_lanes(tmp_path, base_in_lane2='{"stitches": [1, 1]}')
    with pytest.raises(SystemExit, match=r"REFUSED: designs/fx_a__base\.json differs"):
        m.merge_lanes(tmp_path / "out", [lane1, lane2])


def test_a_fixture_rendered_from_two_source_images_is_refused(tmp_path):
    lane1, lane2 = _two_lanes(tmp_path)
    feats = json.loads((lane2 / "features.json").read_text(encoding="utf-8"))
    feats["__sources__"]["fx_a"] = "changed"
    (lane2 / "features.json").write_text(json.dumps(feats), encoding="utf-8")
    with pytest.raises(SystemExit, match="REFUSED: fx_a was rendered from different source"):
        m.merge_lanes(tmp_path / "out", [lane1, lane2])


def test_a_differing_render_is_noted_not_refused(tmp_path, capsys):
    lane1, lane2 = _two_lanes(tmp_path)
    (lane2 / "renders" / "fx_a__base.jpg").write_bytes(b"B2")
    notes = []
    m.merge_lanes(tmp_path / "out", [lane1, lane2], say=notes.append)
    assert notes == [f"note: renders/fx_a__base.jpg differs between {lane1} and {lane2}; keeping the first"]
    assert (tmp_path / "out" / "renders" / "fx_a__base.jpg").read_bytes() == b"B"


def test_a_directory_without_features_is_not_a_lane(tmp_path):
    lane1, _ = _two_lanes(tmp_path)
    (tmp_path / "empty").mkdir()
    with pytest.raises(SystemExit, match="not a --render lane"):
        m.merge_lanes(tmp_path / "out", [lane1, tmp_path / "empty"])


def test_cli_prints_the_totals(tmp_path, capsys):
    lane1, lane2 = _two_lanes(tmp_path)
    assert m.main([str(tmp_path / "out"), str(lane1), str(lane2)]) == 0
    assert "2 fixtures, 5 arm-runs, 6 renders, 4 designs" in capsys.readouterr().out
