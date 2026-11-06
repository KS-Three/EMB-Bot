"""Outline fonts digitized on demand (`digitizer_core.outline_fonts`).

The registry ships UNMODIFIED OFL TTFs fetched at a pinned google/fonts
commit (`tools/fetch_outline_fonts.py`); these tests pin that the files on
disk are the ones the registry names, that layout reads the font (size,
kerning, counters), and that the pipeline sews the result through the
Column lane as lettering.
"""
from __future__ import annotations

import hashlib
import json

import pytest

from digitizer_core import PipelineConfig
from digitizer_core import outline_fonts as of
from digitizer_core.adapter import plan_to_design
from digitizer_core.columns import is_lettering
from digitizer_core.pipeline import plan_stitches

CFG = PipelineConfig(garment_id="left_chest", preflight=False)


# --- registry ---------------------------------------------------------------

def test_registry_files_exist_and_match_their_recorded_hashes():
    reg = json.loads(of.REGISTRY.read_text(encoding="utf-8"))
    assert reg["fonts"], "empty registry"
    for f in reg["fonts"]:
        p = of.FONTS_DIR / f["file"]
        assert p.exists(), f["file"]
        assert hashlib.sha256(p.read_bytes()).hexdigest() == f["sha256"], f["file"]
        lic = of.FONTS_DIR / f["licenseFile"]
        assert lic.exists(), f["licenseFile"]
        assert "SIL OPEN FONT LICENSE" in lic.read_text(encoding="utf-8", errors="replace").upper()


def test_every_font_is_ofl_and_keys_are_unique_slugs():
    fonts = of.list_fonts()
    keys = [f["key"] for f in fonts]
    assert len(keys) == len(set(keys))
    for f in fonts:
        assert f["licenseId"] == "OFL-1.1", f["key"]
        assert f["kind"] == "outline"
        assert f["group"] in {"Sans", "Serif", "Script", "Display"}, f["key"]
        assert f["key"] == f["key"].lower() and " " not in f["key"]


def test_unknown_font_is_a_request_error_not_a_crash():
    with pytest.raises(of.OutlineFontError):
        of.layout_text("no-such-font", "Hi", cap_mm=10)
    with pytest.raises(of.OutlineFontError):
        of.font_path("no-such-font")


def test_coverage_is_the_studio_shape_and_covers_ascii_letters():
    cov = of.coverage("montserrat")
    assert cov and all(isinstance(c, int) or (isinstance(c, list) and len(c) == 2) for c in cov)
    def has(cp):
        return any(c == cp if isinstance(c, int) else c[0] <= cp <= c[1] for c in cov)
    assert all(has(ord(ch)) for ch in "AZaz09")
    assert not has(0x20)  # whitespace is never "coverage"


# --- layout -----------------------------------------------------------------

def test_cap_height_lands_where_asked():
    L = of.layout_text("montserrat-bold", "H", cap_mm=12.0)
    h = L.letters[0].polygon
    assert h.bounds[3] - h.bounds[1] == pytest.approx(12.0, abs=0.15)
    assert L.cap_mm == pytest.approx(12.0, abs=1e-6)


def test_width_mode_lands_the_block_at_the_target_width():
    L = of.layout_text("open-sans", "Fremont", width_mm=76.0)
    assert L.width_mm == pytest.approx(76.0, abs=1e-6)
    xs = [l.polygon.bounds for l in L.letters]
    assert max(b[2] for b in xs) - min(b[0] for b in xs) == pytest.approx(76.0, abs=1e-6)


def test_exactly_one_size_is_required():
    with pytest.raises(of.OutlineFontError):
        of.layout_text("lobster", "a", width_mm=10, cap_mm=10)
    with pytest.raises(of.OutlineFontError):
        of.layout_text("lobster", "a")
    with pytest.raises(of.OutlineFontError):
        of.layout_text("lobster", "a", cap_mm=-1)


def test_counters_become_holes_not_separate_shapes():
    L = of.layout_text("montserrat", "oB", cap_mm=10)
    by = {}
    for l in L.letters:
        by.setdefault(l.char, []).append(l.polygon)
    assert len(by["o"]) == 1 and len(by["o"][0].interiors) == 1
    assert len(by["B"]) == 1 and len(by["B"][0].interiors) == 2
    for polys in by.values():
        for p in polys:
            assert p.is_valid


def test_kerning_pulls_av_closer_than_the_bare_advances():
    """EB Garamond kerns A-V by -140 units via GPOS class pairs; the gap
    between the two glyphs' ink must be narrower than with an unkerned pair
    of the same letters (A-A has no kern there)."""
    kern = of._kerner("eb-garamond")
    assert kern.get("A", "V") < 0
    L = of.layout_text("eb-garamond", "AV", cap_mm=10)
    a, v = (l.polygon for l in L.letters)
    gap_av = v.bounds[0] - a.bounds[2]
    L2 = of.layout_text("eb-garamond", "AA", cap_mm=10)
    a1, a2 = (l.polygon for l in L2.letters)
    gap_aa = a2.bounds[0] - a1.bounds[2]
    assert gap_av < gap_aa - 0.2


def test_letter_spacing_widens_the_block():
    tight = of.layout_text("poppins", "ABC", cap_mm=10)
    loose = of.layout_text("poppins", "ABC", cap_mm=10, letter_spacing_mm=2.0)
    assert loose.width_mm == pytest.approx(tight.width_mm + 4.0, abs=1e-6)


def test_two_lines_stack_downward_in_pipeline_space():
    L = of.layout_text("roboto", "AB\nCD", cap_mm=8)
    top = [l for l in L.letters if l.line == 0]
    bottom = [l for l in L.letters if l.line == 1]
    assert top and bottom
    # y grows DOWN in pipeline space: the second line sits below the first
    assert min(l.polygon.bounds[1] for l in bottom) > max(l.polygon.bounds[3] for l in top) - 0.5


def test_lines_justify_against_the_widest():
    def centres(align):
        L = of.layout_text("roboto", "WIDE LINE\nI", cap_mm=8, align=align)
        short = [l.polygon for l in L.letters if l.line == 1]
        long_ = [l.polygon for l in L.letters if l.line == 0]
        cx = lambda ps: (min(p.bounds[0] for p in ps) + max(p.bounds[2] for p in ps)) / 2  # noqa: E731
        return cx(short) - cx(long_), min(p.bounds[0] for p in short) - min(p.bounds[0] for p in long_)
    c_off, _ = centres("center")
    _, l_off = centres("left")
    r_off, _ = centres("right")
    # Justified on ADVANCE widths, as a typesetter does, so the ink can sit a
    # side bearing (well under 1 mm at cap 8) off the geometric centre.
    assert abs(c_off) < 1.0          # centred under the long line
    assert abs(l_off) < 1.0          # flush left with it
    assert r_off > 5                 # pushed to the right end
    with pytest.raises(of.OutlineFontError):
        of.layout_text("roboto", "a", cap_mm=8, align="justify")


def test_characters_the_font_lacks_are_reported_not_fatal():
    L = of.layout_text("bebas-neue", "A中B", cap_mm=10)
    assert L.unsupported == ["中"]
    assert [l.char for l in L.letters] == ["A", "B"]
    with pytest.raises(of.OutlineFontError):
        of.layout_text("bebas-neue", "中", cap_mm=10)


def test_text_limits_are_enforced():
    with pytest.raises(of.OutlineFontError):
        of.layout_text("anton", "x" * (of.MAX_TEXT_CHARS + 1), cap_mm=10)
    with pytest.raises(of.OutlineFontError):
        of.layout_text("anton", "\n".join("a" * (of.MAX_LINES + 1)), cap_mm=10)


# --- pipeline ---------------------------------------------------------------

def test_result_regions_are_lettering_the_column_lane_takes():
    result, layout = of.build_text_result("montserrat-bold", "Fab", CFG, cap_mm=10, thread_rgb=[0, 0, 0])
    assert len(result.regions) == 3
    assert all(is_lettering(r, CFG) for r in result.regions)
    assert all(r.meta["tier"] == "auto" for r in result.regions)
    assert all(r.shape_id for r in result.regions)
    assert result.segmenter == "outline_font" and result.px_per_mm is None
    assert [r.meta["glyph"] for r in sorted(result.regions, key=lambda r: r.polygon.bounds[0])] == ["F", "a", "b"]


def test_thread_rgb_snaps_and_thread_index_is_bounded():
    result, _ = of.build_text_result("anton", "A", CFG, cap_mm=10, thread_rgb=[200, 0, 0])
    assert result.palette[0]["number"] and result.palette[0]["rgb"] != [0, 0, 0]
    with pytest.raises(of.OutlineFontError):
        of.build_text_result("anton", "A", CFG, cap_mm=10, thread_index=10 ** 6)
    with pytest.raises(of.OutlineFontError):
        of.build_text_result("anton", "A", CFG, cap_mm=10, thread_index=0, thread_rgb=[0, 0, 0])


def test_the_plan_sews_satin_columns_and_is_deterministic():
    result, _ = of.build_text_result("bebas-neue", "FAB", CFG, cap_mm=8)
    plan = plan_stitches(result, CFG)
    design = plan_to_design(plan)
    kinds = {r["kind"] for r in design["runs"]}
    assert "satin" in kinds
    assert plan.stats.stitch_count > 200
    stitched = sum(1 for s in design["stitches"] if s["type"] == "stitch")
    assert stitched == plan.stats.stitch_count
    # identical input, identical bytes
    result2, _ = of.build_text_result("bebas-neue", "FAB", CFG, cap_mm=8)
    design2 = plan_to_design(plan_stitches(result2, CFG))
    assert json.dumps(design, sort_keys=True) == json.dumps(design2, sort_keys=True)


def test_lettering_words_tagger_runs_on_regions_alone():
    cfg = PipelineConfig(garment_id="left_chest", preflight=False, lettering_words=True)
    result, _ = of.build_text_result("poppins-bold", "WORD", cfg, cap_mm=10)
    assert all(is_lettering(r, cfg) for r in result.regions)
    assert all(r.meta.get("word_id") for r in result.regions)
