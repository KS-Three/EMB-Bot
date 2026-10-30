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


# ---- wave 3 sheet (2026-10-26) -----------------------------------------------------------------

def test_wave_three_flags_are_on_the_sheet_and_off_on_main():
    from digitizer_core import PipelineConfig
    prs = {f: fsr.FLAGS[f]["pr"] for f in fsr.WAVE3}
    assert prs == {"lettering_columns_apex_cut": 1088,
                   "monoline_script_satin": 1063, "fill_section_travel": 1091}
    cfg = PipelineConfig()
    for f in fsr.WAVE3:
        assert fsr.FLAGS[f]["metric"] in fsr.METRICS, f
        assert fsr.FLAGS[f].get("fixtures"), f
        if "extra" in fsr.FLAGS[f]["sets"]:   # a cfg.extra key, not a field
            assert fsr.FLAGS[f]["sets"]["extra"] == {f: True}, f
            assert not (cfg.extra or {}).get(f)
        else:
            assert getattr(cfg, f) is False, f
    # the white switches are ruled through the MFab-art gate, not on this sheet; the bay
    # mouth left it when #1112 flipped it (and `sew_enclosed_white`) ON, 2026-10-26
    for f in ("silhouette_underfill", "sew_enclosed_white", "enclosed_white_keyline",
              "silhouette_underfill_panels", "small_text_bay_mouth"):
        assert f not in fsr.WAVE3
    assert cfg.small_text_bay_mouth is True and "small_text_bay_mouth" in fsr.FLAGS
    # ... and the two Kent flipped from this sheet, 2026-10-26, and the two from wave 5,
    # 2026-10-27: off the list, rows kept, ON
    for f in ("outline_loop_mitre", "fine_bars_satin", "text_cluster_part_touching",
              "lettering_columns_italic_lean"):
        assert f not in fsr.WAVE3 and f in fsr.FLAGS and getattr(cfg, f) is True, f
    # ... and the four the white-keyline recipe took to every job, 2026-10-27
    # (Kent: "Every job (Recommended)"): off the list, rows kept, ON
    for f in ("silhouette_underfill_rim", "keyline_fold_slivers", "skip_covered_shapes",
              "absorb_fragments"):
        assert f not in fsr.WAVE3 and f in fsr.FLAGS and getattr(cfg, f) is True, f


def test_every_flag_has_a_kind():
    for f in fsr.FLAGS:
        assert fsr.flag_kind(f) in ("LAYOUT", "FABRIC"), f
    for f in ("fill_turn_slant", "fill_underlay_cross", "tie_in_off", "satin_underlay_short_columns"):
        assert fsr.flag_kind(f) == "FABRIC"
    assert all(fsr.flag_kind(f) == "LAYOUT" for f in fsr.WAVE3)


def test_bridge_is_a_wave_three_fixture():
    for f in ("outline_loop_mitre", "fine_bars_satin", "silhouette_underfill_rim", "fill_section_travel"):
        assert {"bridge_hat", "bridge_lc"} <= set(fsr.flag_fixtures(f, None)), f


def test_an_extra_key_rides_the_parsed_config_for_one_digitize_only():
    import json

    import importlib
    svc = importlib.import_module("digitizer_service.app")
    from tools import pro_pair as pp
    raw = json.dumps(pp.request(92.5, "hat_front"))
    before = svc._parse_config
    with fsr.config_extra({"fill_section_travel": True}):
        kw = svc._parse_config(raw)
        assert kw["extra"]["fill_section_travel"] is True
    assert svc._parse_config is before
    assert "fill_section_travel" not in (svc._parse_config(raw).get("extra") or {})
    with fsr.config_extra(None):
        assert svc._parse_config is before
    # the request a cell sends never carries `extra` (the service refuses it)
    assert fsr.arm_sets("fill_section_travel") == {"extra": {"fill_section_travel": True}}


def test_counts_read_colour_changes_and_the_sheet_shows_them():
    import pystitch
    S, C, T = pystitch.STITCH, pystitch.COLOR_CHANGE, pystitch.TRIM
    c = fsr.counts([(0, 0, S), (1, 0, S), (1, 0, T), (1, 0, C), (2, 0, S)])
    assert c == {"stitches": 3, "trims": 1, "colours": 1}
    assert fsr._fmt({**c, "about": "x"}) == "3 st / 1 tr / 1 cc / x"
    assert fsr._fmt({"stitches": 3, "trims": 1, "about": "x"}) == "3 st / 1 tr / x"


def test_the_page_groups_rows_by_flag_under_its_kind(tmp_path):
    rows = _rows(tmp_path)
    page = fsr.html(rows)
    heads = re.findall(r"<h2 class='group' id='[a-z_]+'><code>([a-z_]+)</code>", page)
    assert heads == ["fill_underlay_cross", "tie_in_off"]
    assert page.count("<span class='kind fabric'>FABRIC</span>") == 2
    head = fsr.flag_header("tie_in_off", [r for r in rows if r["flag"] == "tie_in_off"])
    assert "becker_hat_small</td><td colspan='8'>not run" in head
    assert "mfab_hat</td><td>engine abc1234</td><td>101 st &middot; 3 tr &middot; - cc</td>" in head


# ---- wave 5 sheet (2026-10-27) -----------------------------------------------------------------

def test_wave_five_rows_are_layout_flags_each_asked_or_labelled():
    from digitizer_core import PipelineConfig
    cfg = PipelineConfig()
    asked = [f for f, s in fsr.W5.items() if s["ask"]]
    assert asked == ["lettering_columns_italic_lean", "fill_section_travel",
                     "bean_ink_outlined_letters", "text_cluster_part_touching"]
    # ruled ON from renders on 2026-10-26 and flipped by #1121: shown, not asked again
    for f in ("outline_loop_mitre", "fine_bars_satin"):
        assert not fsr.W5[f]["ask"] and "ruled ON" in fsr.W5[f]["label"], f
    # the detection pass on fa3150de: the trio's DST is OFF's byte for byte on all ten white jobs
    # off MFab, so the three keyline switches act nowhere a render could show; their one row is
    # the trio's, shown, and none of the three is asked
    assert not fsr.W5["keyline_trio"]["ask"] and "byte for byte" in fsr.W5["keyline_trio"]["label"]
    for f in ("keyline_fold_slivers", "skip_covered_shapes", "absorb_fragments"):
        assert f not in fsr.W5, f
    for f, s in fsr.W5.items():
        assert f in fsr.FLAGS and fsr.flag_kind(f) == "LAYOUT", f
        assert s["ask"] or s.get("label"), f          # a row shown and not asked says why
    # Kent's rulings on the four, 2026-10-27: bean ink with part_touching "Both ON
    # (Recommended)", italic lean "Flip ON (Recommended)", fill_section_travel "Hold OFF
    # (Recommended)"
    ruled_on = {"bean_ink_outlined_letters", "text_cluster_part_touching",
                "lettering_columns_italic_lean"}
    for f in asked:
        if "extra" in fsr.FLAGS[f]["sets"]:            # a cfg.extra key: held, still OFF
            assert f not in ruled_on and not (cfg.extra or {}).get(f), f
        else:
            assert getattr(cfg, f) is (f in ruled_on), f
    # off the sheet, by the brief: ruled, held for fabric, or already ON (script_strokes: ruled
    # ON 2026-10-26, its flip in flight)
    for f in ("sew_enclosed_white_fields_fill", "cut_every_jump", "pull_comp_by_stroke",
              "pro_measured_values", "fill_turn_slant", "small_text_bay_mouth", "script_strokes"):
        assert f not in fsr.W5, f


def test_wave_five_part_touching_asks_beside_bean_ink():
    # #1128: alone, the LC's newly tagged N sews hollow (bean on its keyline); the third cell
    # adds bean ink, and the hat (bean ink does not move its plan) gets none
    assert fsr.arm_sets("bean_ink_outlined_letters") == {"bean_ink_outlined_letters": True}
    assert fsr.also_arm("text_cluster_part_touching", "mfab_lc") == \
        "text_cluster_part_touching__bean_ink"
    assert fsr.also_arm("text_cluster_part_touching", "mfab_hat") is None
    assert fsr.arm_sets("text_cluster_part_touching__bean_ink") == {
        "text_cluster_part_touching": True, "bean_ink_outlined_letters": True}
    assert fsr.off_arm("bean_ink_outlined_letters") == fsr.off_arm("text_cluster_part_touching") == "off"


def test_wave_five_keyline_rows_diff_against_the_shipped_engine():
    # white sews by default (#1112) and the recipe fires by itself on MFab (#1115), the three
    # keyline switches inside it (#1122): OFF is bare `off`, not a hand-built base
    for f in ("keyline_fold_slivers", "skip_covered_shapes", "absorb_fragments", "keyline_trio",
              "fill_section_travel", "lettering_columns_italic_lean"):
        assert fsr.off_arm(f) == "off", f
    assert fsr.arm_sets("absorb_fragments") == {"extra": {"absorb_fragments": True}}
    trio = fsr.arm_sets("keyline_trio")
    assert trio == {"keyline_fold_slivers": True, "skip_covered_shapes": True,
                    "extra": {"absorb_fragments": True}}
    # MFab-type art has all three through the gate since #1122: an MFab cell is OFF byte for
    # byte, so every keyline row reads the jobs off MFab
    for f in ("keyline_fold_slivers", "skip_covered_shapes", "absorb_fragments", "keyline_trio"):
        fx = fsr.flag_fixtures(f, None)
        assert fx and not any(s.startswith("mfab") for s in fx), f
        assert set(fx) <= set(fsr.KEYLINE_OFF_MFAB), f
        assert fsr.also_arm(f, fx[0]) is None, f


def test_wave_five_fixtures_are_the_briefs():
    fst = fsr.flag_fixtures("fill_section_travel", None)
    assert fst[0] == "hotel_fremont_hat"
    assert {"becker_hat_large", "mfab_hat", "precision_drone", "gaulke_roofing_hat"} <= set(fst)  # #1091's hats


def test_gate_three_reads_bare_thread_at_the_instruments_band():
    off = {"bare_mm": {"0.20": 1.00, "0.25": 0.40, "0.30": 0.0}}
    same = {"bare_mm": dict(off["bare_mm"])}
    overlap = {"bare_mm": {"0.20": 1.20, "0.25": 0.40, "0.30": 0.0}}
    real = {"bare_mm": {"0.20": 1.50, "0.25": 0.90, "0.30": 0.2}}
    less = {"bare_mm": {"0.20": 0.10, "0.25": 0.0, "0.30": 0.0}}
    assert fsr.bare_rise(off, same)["rises"] == []
    assert fsr.bare_rise(off, overlap)["rises"] == ["0.20"]
    assert fsr.bare_rise(off, real)["rises"] == ["0.20", "0.25", "0.30"]
    assert fsr.bare_rise({}, real) is None                        # a cell from before the instrument

    def rows(*ons):
        return [{"bare": fsr.bare_rise(off, on)} for on in ons]
    assert fsr.gate3_verdict(rows(same, less)) == "clear"
    assert fsr.gate3_verdict(rows(same, real)) == "gate 3"
    assert fsr.gate3_verdict(rows(overlap)).startswith("gate 3 (at 0.20 mm only")
    assert fsr.gate3_verdict([{"bare": None}]) == "n/a"
    # a third cell that rises trips the row too
    assert fsr.gate3_verdict([{"bare": fsr.bare_rise(off, same),
                               "bare_also": fsr.bare_rise(off, real)}]) == "gate 3"


def test_an_asked_flag_that_raises_bare_thread_is_not_asked():
    sheet = {"outline_loop_mitre": {"ask": True}, "monoline_script_satin": {"ask": False, "label": "HELD"}}
    off = {"bare_mm": {"0.20": 0.0, "0.25": 0.0, "0.30": 0.0}}
    up = {"bare_mm": {"0.20": 0.5, "0.25": 0.5, "0.30": 0.5}}
    clear = [{"bare": fsr.bare_rise(off, off)}]
    assert fsr.ask_status("outline_loop_mitre", clear, sheet)[0] == "ask"
    assert fsr.ask_status("outline_loop_mitre", [{"bare": fsr.bare_rise(off, up)}], sheet)[0] == "gate3"
    cls, text = fsr.ask_status("monoline_script_satin", clear, sheet)
    assert cls == "shown" and "HELD" in text
    assert fsr.ask_status("tie_in_off", clear, sheet) == ("", "")


def _plan(runs):
    from types import SimpleNamespace as NS
    return NS(blocks=[NS(runs=[NS(kind=k, points=pts, jump=False, trim=False, shape_id=f"s{i}")
                               for i, (k, pts) in enumerate(runs)])])


def test_bare_bands_read_a_travel_leg_by_its_clearance():
    from digitizer_core import stitches
    laid = (stitches.FILL, [(0.0, 0.0), (10.0, 0.0)])
    far = _plan([laid, (stitches.TRAVEL, [(10.0, 1.0), (0.0, 1.0)])])
    near = _plan([laid, (stitches.TRAVEL, [(10.0, 0.22), (0.0, 0.22)])])
    on = _plan([laid, (stitches.TRAVEL, [(10.0, 0.0), (0.0, 0.0)])])
    # the walk-in leg from the fill's end to the travel's start is a leg too: 1.0 / 0.22 mm long
    b = fsr.bare_by_band(far)
    assert all(10.0 <= v <= 11.2 for v in b.values()), b
    b = fsr.bare_by_band(near)                  # 0.22 mm off: bare only at the half-thread band
    assert b["0.20"] > 9.5 and b["0.25"] < 0.2 and b["0.30"] < 0.2, b
    assert fsr.bare_by_band(on) == {"0.20": 0.0, "0.25": 0.0, "0.30": 0.0}


def _cell(root, slug, arm, engine, dst=b"DST", sets=None):
    import json
    d = root / slug / arm
    d.mkdir(parents=True)
    (d / "ours.dst").write_bytes(dst)
    (d / "stats.json").write_text(json.dumps({"engine": engine, "sets": sets or {}}))
    return d


def test_adopt_takes_an_old_on_cell_only_where_off_did_not_move(tmp_path):
    old, new = tmp_path / "old", tmp_path / "new"
    sets = fsr.arm_sets("lettering_columns_italic_lean")
    _cell(old, "proseal_hat", "lettering_columns_italic_lean", "aaa", b"ON", sets)
    _cell(old, "proseal_hat", "off__aaa", "aaa", b"OFF1")
    _cell(new, "proseal_hat", "off__bbb", "bbb", b"OFF2")
    r = fsr.adopt(old, new, "lettering_columns_italic_lean", "proseal_hat", "bbb")
    assert "OFF moved" in r and not (new / "proseal_hat" / "lettering_columns_italic_lean").exists()
    (new / "proseal_hat" / "off__bbb" / "ours.dst").write_bytes(b"OFF1")
    r = fsr.adopt(old, new, "lettering_columns_italic_lean", "proseal_hat", "bbb")
    assert "adopted" in r and (new / "proseal_hat" / "lettering_columns_italic_lean").exists()
    assert (new / "proseal_hat" / "off__aaa").exists()          # the OFF it was diffed against


def test_adopt_refuses_a_cell_built_for_another_row_definition(tmp_path):
    old, new = tmp_path / "old", tmp_path / "new"
    # wave 3's keyline cell carried the hand-built d2 base; the row now has none
    _cell(old, "mfab_hat", "keyline_fold_slivers", "aaa", b"ON",
          {"silhouette_underfill": True, "keyline_fold_slivers": True})
    _cell(old, "mfab_hat", "off__aaa", "aaa", b"OFF")
    _cell(new, "mfab_hat", "off__bbb", "bbb", b"OFF")
    assert "not the row's" in fsr.adopt(old, new, "keyline_fold_slivers", "mfab_hat", "bbb")


def test_a_shown_row_is_copied_as_it_is_with_its_engine(tmp_path):
    old, new = tmp_path / "old", tmp_path / "new"
    _cell(old, "tires_hat_3d", "monoline_script_satin", "aaa", b"ON")
    _cell(old, "tires_hat_3d", "off__aaa", "aaa", b"OFF")
    assert "adopted from aaa" in fsr.adopt(old, new, "monoline_script_satin", "tires_hat_3d", None)
    assert fsr._engine_note({"engine": "aaa", "stale": "aaa"}) == "engine aaa: not current base"
    assert "byte for byte" in fsr._engine_note({"engine": "aaa", "base_bytes": "aaa"})


def test_the_artifact_page_is_a_fragment_with_theme_tokens(tmp_path):
    rows = _rows(tmp_path)
    page, _ = fsr.inline_html(rows, tmp_path, "2026-10-27", sheet=fsr.W5, fragment=True)
    assert page.lstrip().startswith("<title>Flip sheet 2026-10-27</title>")
    for tag in ("<!doctype", "<html", "<head", "<body"):
        assert tag not in page.lower(), tag
    assert "claude:viewport-fit-sides" in page
    assert "prefers-color-scheme:dark" in page and ":root[data-theme='dark']" in page
    assert "body{" in page and "background:var(--bg)" in page
    whole = fsr.html(rows)
    assert whole.startswith("<!doctype html>") and "viewport-fit=cover" in whole


def test_the_pros_tiles_live_apart_and_the_local_page_keeps_them(tmp_path):
    """Kent 2026-10-27, "Stop new ones, keep old (Recommended)": the pro's tiles
    are written outside docs/. The inlined page (local) still shows all of
    them; the markdown names them without a link into the gitignored folder."""
    rows = _rows(tmp_path)
    pro_dir = tmp_path / "pro"
    pro_dir.mkdir()
    for r in rows:
        for name in (r.get("images") or {}).values():
            if fsr.is_pro_image(name):
                (tmp_path / name).rename(pro_dir / name)
    assert sorted(p.name for p in pro_dir.iterdir()) == [
        "fill_underlay_cross__mfab_hat__pro.jpg", "fill_underlay_cross__mfab_hat__pro_xray.jpg",
        "tie_in_off__mfab_hat__pro.jpg"]
    page, _ = fsr.inline_html(rows, tmp_path, "2026-10-27", pro_dir=pro_dir)
    assert len(_imgs(page)) == 11 and all(s.startswith("data:image/jpeg;base64,") for s in _imgs(page))
    md = fsr.markdown(rows, tmp_path / "renders", tmp_path / "doc.md")
    assert "__pro" not in md and "pro (local only)" in md and "__off.jpg)" in md
    assert fsr.image_file("a__b__pro.jpg", tmp_path, pro_dir) == pro_dir / "a__b__pro.jpg"
    assert fsr.image_file("a__b__where.jpg", tmp_path, pro_dir) == tmp_path / "a__b__where.jpg"
    assert fsr.image_file("a__b__pro.jpg", tmp_path) == tmp_path / "a__b__pro.jpg"


# ---- defects 4/6 (2026-10-30) ------------------------------------------------------------------

def test_fill_section_cuts_first_row_is_off_on_main_and_covers_every_pair():
    from digitizer_core import PipelineConfig
    from tools import border_census as bc
    spec = fsr.FLAGS["fill_section_cuts_first"]
    assert spec["metric"] in fsr.METRICS
    assert spec["sets"]["extra"] == {"fill_section_cuts_first": True}
    assert not PipelineConfig().extra.get("fill_section_cuts_first")
    # the OFF arm is the shared rembg pin, and ON carries the same pin
    assert fsr.off_arm("fill_section_cuts_first") == "rembg900__off"
    assert (spec["sets"]["photo_prep_background_removal_timeout_s"]
            == spec["base"]["photo_prep_background_removal_timeout_s"])
    assert set(spec["fixtures"]) == {r[0] for r in [*bc.PAIRS, *fsr.EXTRA_PAIRS]}


def test_inpiece_cuts_reads_the_dst_on_both_sides(monkeypatch):
    from tools import sequence_pro as sp
    monkeypatch.setattr(sp, "read_file", lambda path: {"total": {"trims": 13.0, "inter_trims": 7.0}})
    assert fsr.inpiece_cuts(None, None, {"dst": "any.dst"}) == "6 / 13"
