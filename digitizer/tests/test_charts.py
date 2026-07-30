"""Thread charts, and the cross-language guard that keeps them honest.

Studio stores a thread-brand preference and sends its id straight to
`/digitize`. If the Python generator and `tools/build-threads.mjs` ever disagree
about what a brand is called or how many colors it has, that preference stops
resolving — or worse, resolves to a chart with different contents than the one
the browser is showing. Two parsers in two languages over the same files is
exactly the kind of duplication that drifts silently, so it is asserted rather
than trusted.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
import pytest

from digitizer_core.gpl import parse_gpl
from digitizer_core.threads import (
    CHART,
    DEFAULT_BRAND,
    Chart,
    brand_index,
    load_chart,
    rgb_to_lab,
)

REPO = Path(__file__).resolve().parents[2]
BROWSER_INDEX = REPO / "app" / "src" / "lib" / "threadBrandsIndex.js"


def _browser_brands() -> list[dict]:
    """Parse THREAD_BRAND_INDEX out of the generated JS module."""
    text = BROWSER_INDEX.read_text(encoding="utf-8")
    m = re.search(r"THREAD_BRAND_INDEX\s*=\s*(\[.*?\]);", text, re.S)
    assert m, f"could not find THREAD_BRAND_INDEX in {BROWSER_INDEX}"
    return json.loads(m.group(1))


@pytest.mark.skipif(not BROWSER_INDEX.is_file(), reason="browser bundle not present")
def test_brand_ids_match_the_browser_exactly():
    ours = {b["id"] for b in brand_index()}
    theirs = {b["id"] for b in _browser_brands()}

    assert ours == theirs, (
        f"only in Python: {sorted(ours - theirs)}; only in browser: {sorted(theirs - ours)}"
    )


@pytest.mark.skipif(not BROWSER_INDEX.is_file(), reason="browser bundle not present")
def test_brand_colour_counts_match_the_browser():
    """Same ids with different contents would be worse than a missing brand."""
    ours = {b["id"]: b["count"] for b in brand_index()}
    for b in _browser_brands():
        assert ours[b["id"]] == b["count"], (
            f"{b['id']}: python parsed {ours[b['id']]}, browser parsed {b['count']}"
        )


def test_policy_excluded_brands_are_absent():
    """No charts from companies selling embroidery software or machines."""
    ids = {b["id"] for b in brand_index()}
    for banned in ("brother-country", "brother-embroidery", "janome",
                   "viking-palette", "floriani-polyester", "hemingworth", "ral"):
        assert banned not in ids, f"{banned} violates the thread-chart policy"


def test_default_chart_is_isacord_and_is_what_goldens_pin():
    assert CHART.id == DEFAULT_BRAND == "isacord"
    assert len(CHART) == 398
    assert CHART[0].number == "0003"


def test_unknown_brand_raises_rather_than_substituting():
    """Silently falling back to Isacord would put the wrong catalog numbers on
    an operator's worksheet, which is the defect the brand parameter exists to
    prevent."""
    with pytest.raises(KeyError):
        load_chart("not-a-real-brand")


def test_every_shipped_brand_loads_and_is_well_formed():
    for entry in brand_index():
        chart = load_chart(entry["id"])
        assert isinstance(chart, Chart)
        assert len(chart) == entry["count"]
        assert chart.lab.shape == (len(chart), 3)
        for t in chart:
            assert t.name, f"{entry['id']} has a nameless thread"
            assert all(0 <= v <= 255 for v in t.rgb)


def test_load_chart_is_cached():
    assert load_chart("polyneon") is load_chart("polyneon")


def test_each_chart_matches_its_own_colors_to_itself():
    """The nearest thread to a thread's own RGB is that thread (or an exact
    duplicate of it) — a chart that fails this has a Lab conversion bug."""
    for brand in ("isacord", "polyneon", "madeira-rayon"):
        chart = load_chart(brand)
        for t in list(chart)[::17]:                  # every 17th, for speed
            j = chart.nearest_index(rgb_to_lab(np.array([t.rgb], np.float64))[0])
            assert chart[j].rgb == t.rgb, f"{brand}: {t.number} matched {chart[j].number}"


def test_parser_handles_the_shapes_gpl_files_actually_take():
    text = "\n".join([
        "GIMP Palette",
        "Name: Test",
        "Columns: 4",
        "# RGB Value\tColor Name Number",
        "255 255 255\t\tWhite\t0015",
        "0 0 0\tBlack With Spaces\t9999",
        "12 34 56\tNo Code Here",
        "999 0 0\tOut Of Range\t1",
        "not a line at all",
    ])
    entries = parse_gpl(text)

    assert entries == [
        ("0015", "White", (255, 255, 255)),
        ("9999", "Black With Spaces", (0, 0, 0)),
        ("", "No Code Here", (12, 34, 56)),
    ]
