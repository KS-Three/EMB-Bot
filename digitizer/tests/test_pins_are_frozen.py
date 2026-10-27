"""A default flip should cost only the goldens that DELIBERATELY ride the defaults.

#1112's first CI round failed 128 tests; 79 were one moved flat-lane golden copied as
a literal into 16 files, and #1057 spent 86 commits re-pinning OFF tests that had
landed meanwhile under the pre-flip defaults. Two rules end that, and this file
holds both:

1. An md5 pin of the engine's output is built on a FROZEN engine: a dated snapshot
   of `PipelineConfig`'s declared defaults, `tests/engine_2026_10_27.json`, spread
   with `conftest.frozen_cfg(...)` / `ENGINE_2026_10_27`, so a later flip cannot
   move it. The flat golden is the exception on purpose: it is DERIVED from
   `testdata/flat_lane_golden.json` (`conftest.FLAT_GOLDEN_MD5`), and the tests that
   compare the shipped engine to it ride the defaults, so a flip that recaptures
   the golden moves them in one place.
2. A snapshot must name every `PipelineConfig` field. A flag that ships as a new
   field defaulting True (a flip) would otherwise reach every test that spreads a
   snapshot made before it existed, silently moving their pins.

**What a failure here means.**
- "unfrozen md5 pin": the test file pins a 32-hex digest of an engine run and
  builds its config from the live defaults. Spread `frozen_cfg(...)`. If the pin is
  ABOUT the current default (a golden the flip is meant to move), say so with a
  `# pin-rides-defaults: <why>` line in the file, or an entry in `RIDES_DEFAULTS`
  below with the reason.
- "snapshot lacks / names stale fields": add the new field to
  `tests/engine_*.json` with the value the engine had BEFORE the flip that made it
  default-on (False / None for a flag built OFF; the OLD default for a field a
  flip changed), or drop a removed field.

Truncated pins (`digest[:8]`, tuples) are not seen here: `tools.ci_repin RUN_ID`
re-pins a red md5 of either kind from a CI run, and the repin is the fix, not a
hand edit.

Roll the snapshot forward with a NEW dated file after a flip wave
(`engine_<date>.json`, built from `dataclasses.fields`, never `asdict`), point new
pins at it, and leave the old pins on theirs.
"""
from __future__ import annotations

import dataclasses
import re
from pathlib import Path

import pytest

from digitizer_core import PipelineConfig
from digitizer_core.config import SMALL_TEXT_TRUE_SIZE
from tests.conftest import (ENGINE_2026_10_27, FLAT_GOLDEN_MD5, frozen_cfg,
                            read_engine_snapshot)

TESTS = Path(__file__).resolve().parent

#: Test files whose md5 pin is ABOUT the current default, or does not read
#: `PipelineConfig` defaults at all. Each entry is a ruling, not a convenience.
RIDES_DEFAULTS = {
    # --- the pin never passes through PipelineConfig's defaults ------------------------
    "test_column_ends.py": "pins `columns.lettering_columns_shape` on glyph polygons with explicit kwargs",
    "test_column_inside_stagger.py": "pins the Column lane's runs on polygons with explicit kwargs",
    "test_column_small_bold.py": "pins the Column lane's runs on polygons with explicit kwargs",
    "test_fill_section_travel.py": "pins `stitch_shape` on a shapely polygon with explicit arguments",
    "test_fur_fill.py": "pins `stitch_shape` on shapely polygons with explicit arguments",
    "test_small_text_reach_edges.py": "pins `enlarge_small_text` with explicit KW; the flag is its own argument",
    "test_underfill_rim.py": "pins `test_silhouette_underfill._sew`, which freezes the 2026-10-23 flips itself",
    # --- sew-out cards: their configs are composed in tools/sewout_card_*.py -----------
    "test_sewout_card_bayhold_edgecap.py": "pins the card tool's stream; its arms are built in the tool",
    "test_sewout_card_lettering_arms.py": "pins the card tool's stream; its arms are built in the tool",
    # --- owned by a live lane: whichever PR lands second adapts ------------------------
    "test_column_apex_cut.py": "live lane (apex cut / apex walk)",
    "test_keyline_loop_chain.py": "live lane (keyline_loop_chain)",
    "test_script_strokes.py": "live lane (script_strokes)",
    "test_small_text_grow_away.py": "the grow_away lane's own OFF/ON arms (flipped by #1127)",
}

_MD5 = re.compile(r"""["'][0-9a-f]{32}["']""")
#: the file builds a config or runs a pipeline stage: a pin there can follow a default
_RUNS_ENGINE = re.compile(r"\b(?:PipelineConfig|cfg|digitize|run_stages|plan_stitches)\(")
#: a frozen engine: a dated snapshot, or one of the older dicts of flags pinned off
_FROZEN = re.compile(
    r"\b(?:frozen_cfg|ENGINE_20\d\d_\d\d_\d\d|PRE_FLIP|FLIP_20\d\d_\d\d_\d\d|whitebg_pre_flip)\b"
    r"|\b\w+_OFF\b")
_MARKED = re.compile(r"#[ \t]*pin-rides-defaults:[ \t]*\S")


def unfrozen_pins(sources: dict[str, str], allow=RIDES_DEFAULTS) -> list[str]:
    """Names of the test files that pin an md5 of an engine run and spread no
    frozen dict, minus the ones that said why they ride the defaults."""
    return sorted(name for name, text in sources.items()
                  if name not in allow
                  and _MD5.search(text) and _RUNS_ENGINE.search(text)
                  and not _FROZEN.search(text) and not _MARKED.search(text))


def _sources() -> dict[str, str]:
    return {p.name: p.read_text(encoding="utf-8") for p in sorted(TESTS.glob("test_*.py"))
            if p.name != Path(__file__).name}


# --- rule 1: an md5 pin spreads a frozen dict -----------------------------------------

def test_no_md5_pin_rides_the_live_defaults_unannounced():
    bad = unfrozen_pins(_sources())
    assert not bad, (
        f"unfrozen md5 pin in {bad}: the file pins a 32-hex digest of an engine run and builds its "
        "config from the live defaults, so the next default flip moves it. Build the config with "
        "`tests.conftest.frozen_cfg(...)` (or spread `ENGINE_2026_10_27`). A pin that is ABOUT "
        "the current default says so with a `# pin-rides-defaults: <why>` line, or an entry in "
        "RIDES_DEFAULTS in tests/test_pins_are_frozen.py.")


def test_the_scanner_catches_an_unfrozen_sample():
    digest = "a" * 32
    unfrozen = f'cfg = PipelineConfig(target_width_mm=80.0)\nassert md5(run(cfg)) == "{digest}"\n'
    frozen = unfrozen.replace("PipelineConfig(", "frozen_cfg(")
    dated = unfrozen.replace("PipelineConfig(target_width_mm=80.0)", "PipelineConfig(**ENGINE_2026_10_27)")
    older = unfrozen.replace("PipelineConfig(", "PipelineConfig(**PRE_FLIP, ")
    marked = unfrozen + "# pin-rides-defaults: the golden a flip is meant to move\n"
    unmarked_comment = unfrozen + "# pin-rides-defaults:\n"
    no_engine = f'assert md5(lane(poly, a=1)) == "{digest}"\n'
    sources = {"test_a.py": unfrozen, "test_b.py": frozen, "test_c.py": dated, "test_d.py": older,
               "test_e.py": marked, "test_f.py": unfrozen, "test_g.py": no_engine,
               "test_h.py": unmarked_comment}
    assert unfrozen_pins(sources, allow={"test_f.py": "ruled"}) == ["test_a.py", "test_h.py"]


def test_a_derived_golden_is_not_a_literal_pin():
    # the flat-lane md5s come from the golden file, so a file using them carries no digest
    text = "from .conftest import FLAT_GOLDEN_MD5\nassert md5(digitize(x, PipelineConfig())) == FLAT_GOLDEN_MD5['a']\n"
    assert unfrozen_pins({"test_x.py": text}, allow={}) == []
    assert set(FLAT_GOLDEN_MD5) == {"logo_alpha.png", "logo_whitebg.png", "ribbon_curve.png"}
    assert all(re.fullmatch(r"[0-9a-f]{32}", v) for v in FLAT_GOLDEN_MD5.values())


def test_the_allow_list_names_real_reasons():
    assert all(len(why.split()) >= 3 for why in RIDES_DEFAULTS.values())


# --- rule 2: a snapshot names every field ---------------------------------------------

def _snapshot_files() -> list[Path]:
    return sorted(TESTS.glob("engine_20*_*_*.json"))


def test_there_is_a_dated_snapshot():
    assert [p.name for p in _snapshot_files()], "tests/engine_<date>.json is gone"


@pytest.mark.parametrize("path", _snapshot_files(), ids=lambda p: p.name)
def test_a_snapshot_names_every_pipeline_config_field(path):
    snap = set(read_engine_snapshot(path.name))
    fields = {f.name for f in dataclasses.fields(PipelineConfig)}
    missing, stale = sorted(fields - snap), sorted(snap - fields)
    assert not missing and not stale, (
        f"{path.name} lacks {missing} and names stale {stale}. A field that is not in the snapshot "
        "takes its LIVE default in every test that spreads it, which is how a flip moves a frozen "
        "pin. Add each missing field with the value the engine had BEFORE the flip that made it "
        "default-on (False / None for a flag built OFF; the OLD default for a field a flip "
        "changed); drop the stale ones.")


@pytest.mark.parametrize("path", _snapshot_files(), ids=lambda p: p.name)
def test_a_snapshot_stores_declared_not_filled_values(path):
    """`asdict(PipelineConfig())` records the seven fields `small_text_true_size` fills at
    construction; spread back, they would survive a `setattr(small_text_true_size=False)`
    that is meant to clear them (tests, `flagcost.py`, `parity_config(**extra)`)."""
    snap = read_engine_snapshot(path.name)
    assert {k: snap[k] for k in SMALL_TEXT_TRUE_SIZE} == {k: None for k in SMALL_TEXT_TRUE_SIZE}


def test_frozen_cfg_fills_and_clears_the_true_size_fields_like_a_live_config():
    # Not compared to the live PipelineConfig: that follows every flip, this must not.
    frozen = frozen_cfg()
    assert frozen.small_text_true_size is True
    assert frozen._true_size_filled == tuple(SMALL_TEXT_TRUE_SIZE)
    assert {k: getattr(frozen, k) for k in SMALL_TEXT_TRUE_SIZE} == SMALL_TEXT_TRUE_SIZE
    frozen.small_text_true_size = False
    assert all(getattr(frozen, k) is None for k in SMALL_TEXT_TRUE_SIZE)
    off = frozen_cfg(small_text_true_size=False)
    assert off._true_size_filled == () and all(getattr(off, k) is None for k in SMALL_TEXT_TRUE_SIZE)


def test_a_spread_hands_each_config_its_own_containers_and_a_tuple():
    a, b = frozen_cfg(), frozen_cfg()
    assert a.extra is not b.extra and a.shape_overrides is not b.shape_overrides
    assert isinstance(a.tonal_split_veto_mm, tuple)
    assert "extra" not in ENGINE_2026_10_27 and "tonal_split_veto_mm" in ENGINE_2026_10_27
