# digitizer/tests/test_flip_sheet_renders.py
"""The render flip sheet's inlined page and its per-flag OFF arm.

Kent opens the sheet in the desktop app's file viewer, which cannot resolve a
relative image path: a page that links `flag__fixture__off.jpg` shows broken
boxes. `inline_html` makes ONE file with every picture a data URI. Pinned here:

  1. no `<img>` keeps a file name, every one is a decodable JPEG data URI;
  2. the page is held under its size ceiling by re-encoding smaller, and
     reports the level it needed;
  3. a flag with a `base` (`enclosed_white_keyline` acts only under
     `sew_enclosed_white`) is diffed against ITS OWN OFF, never the bare one.

No engine runs: renders are noise JPEGs written to a tmp directory.
"""
from __future__ import annotations

import base64
import re

import cv2
import numpy as np

from tools import flip_sheet_renders as fsr


def _jpg(path, w=720, h=440, seed=0):
    rng = np.random.default_rng(seed)
    cv2.imwrite(str(path), rng.integers(0, 255, (h, w, 3), dtype=np.uint8), [1, 90])


def _rows(tmp_path):
    rows = []
    for i, flag in enumerate(("fill_underlay_cross", "tie_in_off")):
        row = {"flag": flag, "fixture": "mfab_hat", "width_mm": 104.9, "pr": 1000 + i,
               "about": "x", "sets": {flag: True}, "note": "", "status": "rendered",
               "engine": "abc1234", "diff": 10, "in_window": 8, "box_mm": [0, 0, 18, 11],
               "byte_identical": False, "images": {}}
        for side in ("off", "on", "pro"):
            row[side] = {"stitches": 100 + i, "trims": 3, "about": "7"}
            for key in (side, side + "_xray") if flag == "fill_underlay_cross" else (side,):
                name = f"{flag}__mfab_hat__{key}.jpg"
                _jpg(tmp_path / name, seed=len(name))
                row["images"][key] = name
        _jpg(tmp_path / f"{flag}__mfab_hat__where.jpg", 240, 150)
        row["images"]["where"] = f"{flag}__mfab_hat__where.jpg"
        rows.append(row)
    rows.append({"flag": "tie_in_off", "fixture": "becker_hat_small", "width_mm": 100.0, "pr": 1001,
                 "about": "x", "sets": {}, "note": "", "status": "not run"})
    return rows


def _imgs(page):
    return re.findall(r"<img src='([^']*)'", page)


def test_inline_page_has_no_file_references(tmp_path):
    rows = _rows(tmp_path)
    page, level = fsr.inline_html(rows, tmp_path, "2026-10-24")
    srcs = _imgs(page)
    assert len(srcs) == 11            # 3 + 3 x-ray + where, then 3 + where
    assert all(s.startswith("data:image/jpeg;base64,") for s in srcs)
    assert "2026-10-24" in page and ".jpg'" not in page
    assert level == fsr.INLINE_LEVELS[0]           # the renders as written fit easily
    for s in srcs:
        raw = base64.b64decode(s.split(",", 1)[1])
        assert cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR) is not None


def test_inline_page_is_the_plain_page_with_names_swapped(tmp_path):
    rows = _rows(tmp_path)
    plain = fsr.html(rows)
    inline, _ = fsr.inline_html(rows, tmp_path)
    assert re.sub(r"data:image/jpeg;base64,[A-Za-z0-9+/=]+", "N", inline) == \
        re.sub(r"[\w.]+__[\w.]+\.jpg", "N", plain)


def test_inline_page_shrinks_to_its_ceiling(tmp_path):
    rows = _rows(tmp_path)
    big, lvl0 = fsr.inline_html(rows, tmp_path, max_mb=50)
    ceiling = len(big) / 1024 / 1024 * 0.6
    small, lvl = fsr.inline_html(rows, tmp_path, max_mb=ceiling)
    assert lvl0 == fsr.INLINE_LEVELS[0] and lvl != lvl0
    assert len(small) <= ceiling * 1024 * 1024
    # a ceiling nothing meets still returns a page, at the smallest level
    page, lvl_min = fsr.inline_html(rows, tmp_path, max_mb=0.001)
    assert lvl_min == fsr.INLINE_LEVELS[-1] and _imgs(page)


def test_summary_table_lists_every_row(tmp_path):
    table = fsr.summary_table(_rows(tmp_path))
    assert table.count("<tr>") == 1 + 3
    assert "not run" in table and "100 st / 3 tr / 7" in table


def test_a_flag_with_a_base_has_its_own_off_arm():
    assert fsr.off_arm("enclosed_white_keyline") == "enclosed_white_keyline__off"
    assert fsr.off_arm("lettering_columns_inside_stagger") == "off"
    assert fsr.arm_sets("enclosed_white_keyline__off") == {"sew_enclosed_white": True}
    assert fsr.arm_sets("off") == {}
    assert fsr.arm_sets("enclosed_white_keyline")["enclosed_white_keyline"] is True
    # the keyline's ON arm carries its base, so ON differs from OFF by the flag alone
    spec = fsr.FLAGS["enclosed_white_keyline"]
    assert {k: v for k, v in spec["sets"].items() if k not in spec["base"]} == {"enclosed_white_keyline": True}
    assert fsr.is_off("off") and fsr.is_off("enclosed_white_keyline__off")
    assert not fsr.is_off("enclosed_white_keyline")


def test_off_cells_are_cached_per_engine_and_on_cells_are_not(tmp_path):
    off = fsr.cell_dir(tmp_path, "mfab_hat", "enclosed_white_keyline__off", "abc")
    assert off.name == "enclosed_white_keyline__off__abc"
    assert fsr.cell_dir(tmp_path, "mfab_hat", "off", "abc").name == "off__abc"
    assert fsr.cell_dir(tmp_path, "mfab_hat", "enclosed_white_keyline", "abc").name == "enclosed_white_keyline"


def test_wave_one_flags_are_on_the_sheet():
    prs = {f: s["pr"] for f, s in fsr.FLAGS.items()}
    assert prs["lettering_columns_inside_stagger"] == 1058
    assert prs["enclosed_white_keyline"] == 1059
    assert prs["text_cluster_wide_letters"] == 1060
    for f in prs:
        assert fsr.FLAGS[f]["metric"] in fsr.METRICS, f


def test_white_under_1mm_counts_white_thread_only():
    # x/y are tenths of a mm: 10 units = 1 mm
    design = {"colors": [{"r": 255, "g": 255, "b": 255}, {"r": 0, "g": 0, "b": 0}],
              "stitches": [{"type": "stitch", "x": 0, "y": 0}, {"type": "stitch", "x": 5, "y": 0},
                           {"type": "stitch", "x": 40, "y": 0}, {"type": "color"},
                           {"type": "stitch", "x": 0, "y": 0}, {"type": "stitch", "x": 2, "y": 0}]}
    assert fsr.white_under_1mm(None, None, {"design": design}) == "3 (1 under 1 mm)"
    assert fsr.white_under_1mm(None, None, {"design": None}).startswith("n/a")


def test_tagged_reads_the_cells_stats_and_the_pro_has_none():
    assert fsr.tagged(None, None, {"stats": {"tagged": 16}}) == "16"
    assert fsr.tagged(None, None, {"runs": None}).startswith("n/a")


def test_wave_two_flags_are_on_the_sheet():
    prs = {f: s["pr"] for f, s in fsr.FLAGS.items()}
    assert prs["monoline_script_satin"] == 1063
    assert prs["silhouette_underfill"] == 1064
    assert prs["border_from_outline"] == 1065
    assert prs["small_text_cap_reach_edges"] == 1066
    for f in prs:
        assert fsr.FLAGS[f]["metric"] in fsr.METRICS, f


def test_flags_with_one_base_share_one_off_arm():
    # Kent flipped sew_enclosed_white and the keyline 2026-10-24: both wave-2 white flags
    # are diffed against that one OFF, digitized once per fixture
    assert fsr.off_arm("border_from_outline") == fsr.off_arm("silhouette_underfill") == "white_sewn__off"
    assert fsr.arm_sets("white_sewn__off") == {"sew_enclosed_white": True, "enclosed_white_keyline": True}
    # the reach flag acts only under #1029's re-set: its OFF is that set, without the flag
    off = fsr.arm_sets(fsr.off_arm("small_text_cap_reach_edges"))
    assert off == fsr.FLAGS["small_text_set"]["sets"] and "small_text_cap_reach_edges" not in off
    for f, spec in fsr.FLAGS.items():
        if spec.get("base"):
            # ON differs from its OFF: a key the base lacks, or (a flag already ON by
            # default, its OFF pinned False -- the 2026-10-26 rows) a value it changes
            missing = object()
            extra = {k: v for k, v in spec["sets"].items() if spec["base"].get(k, missing) != v}
            assert extra and fsr.arm_sets(fsr.off_arm(f)) == spec["base"], f
    assert fsr.off_arm("wave3_flips") == fsr.off_arm("small_text_bay_mouth") == "wave3_off__off"


def test_a_flag_with_fixtures_runs_only_on_them():
    assert fsr.flag_fixtures("monoline_script_satin", None) == ["tires_hat_3d"]
    assert fsr.flag_fixtures("monoline_script_satin", ["mfab_hat"]) == []
    assert fsr.flag_fixtures("tie_in_off", None) == [s for s, _ in fsr.FIXTURES]
    assert fsr.flag_fixtures("tie_in_off", ["mfab_hat"]) == ["mfab_hat"]


def test_sub_1mm_counts_short_stitches_and_resets_at_a_cut():
    import pystitch
    S, T = pystitch.STITCH, pystitch.TRIM
    stream = [(0, 0, S), (0.5, 0, S), (3, 0, S), (3, 0, T), (3.2, 0, S), (3.4, 0, S)]
    assert fsr.sub_1mm(stream, None, None) == 2


def test_a_row_with_a_third_cell():
    # d2 | d2 + panels | d2 + panels + mitre | pro (#1094): the third cell is its own arm,
    # cached like ON (never per engine), its sets the row's ON plus what it adds
    assert fsr.also_arm("silhouette_underfill_panels") == "silhouette_underfill_panels__mitre"
    assert fsr.also_arm("tie_in_off") is None
    sets = fsr.arm_sets("silhouette_underfill_panels__mitre")
    on = fsr.FLAGS["silhouette_underfill_panels"]["sets"]
    assert {k: v for k, v in sets.items() if k not in on} == {"outline_loop_mitre": True}
    assert not fsr.is_off("silhouette_underfill_panels__mitre")
    row = {"on": {"stitches": 1, "trims": 2, "about": "x"}, "also": {"stitches": 3, "trims": 4, "about": "y"},
           "also_label": "ON + MITRE"}
    assert fsr._sides(row) == ("off", "on", "also", "pro")
    assert fsr._fmt_on(row).endswith("ON + MITRE: 3 st / 4 tr / y")
    assert fsr._sides({"on": {}}) == ("off", "on", "pro")
