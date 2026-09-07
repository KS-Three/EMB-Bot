"""The two engines must make the SAME physical choice on the same garment.

`digitizer_core/fabrics.py` opens by saying so: *"a straight port of the
browser engine's `src/fabrics.js`. Same ids, same values, deliberately. …
When a sew-out moves a number, move it in both places."* Nothing checked it,
and it was not true.

## What the unchecked copy cost, measured 2026-09-07

Corpus law 26 (`docs/corpus-laws-round3-2026-08-01.md`, ruled **shipped
2026-08-05**) moved `fill_underlay` from `edge_lattice` to `edge_run` on the
two knit presets: under a fill the professional corpus runs a walk, and a
sparse-grid tatami underlay is **7 cases in 507**. It landed in Python. It
never landed in `src/fabrics.js`.

`pique_knit` is **Left Chest** and `jersey_tee` is **Beanie** and **Sleeve** —
three of the ten garments, including the commonest placement there is. On
those, for a month, the browser engine ran `edgeRun().concat(lattice(90))`
where the Python engine ran `edgeRun()`: a whole extra crosshatch pass under
every knit fill, worth **+1.4% to +5.7% stitches** (enthusiast_logo 8537 vs
8419, logo_whitebg 12144 vs 11490, logo_script_tires 12628 vs 11952, all at
left_chest). Three shipped Studio lanes read that table — image mode, manual
digitizing and shape presets, all via `generate.js`'s
`EMB.getFabric(EMB.fabricForGarment(garment.id))`.

## Why a test and not just the fix

The fix is two words; the drift is the durable problem. This table is a
BY-HAND PORT across a language boundary, which is the same class
`test_code_wires.py` guards for warning codes and `test_charts.py` for thread
brands — and the worst-behaved instance of it, because the other two lose a
string and this one changes what the machine sews. Nothing imports, nothing
type-checks, and a suite stays green either way.

Read together with those two: `test_code_wires.py` is the codes seam,
`test_charts.py` the thread-brand seam, this the physical-preset seam.

**This file asserts AGREEMENT, never a value.** Which number is right is
gate 1 — sew-out evidence, Kent's call. Whether the two engines say the same
number is not a physical question at all, and is the only thing checked here.
"""
from __future__ import annotations

import pathlib
import re

from digitizer_core.fabrics import FABRICS, GARMENT_FABRIC, DEFAULT_FABRIC_ID

REPO = pathlib.Path(__file__).resolve().parents[2]
FABRICS_JS = REPO / "src" / "fabrics.js"

# camelCase in the browser, snake_case in Python, same physics.
FIELDS = {
    "pullCompMm": "pull_comp_mm",
    "fillUnderlay": "fill_underlay",
    "satinUnderlay": "satin_underlay",
    "densityAdjust": "density_adjust",
    "trimAtMm": "trim_at_mm",
}


def _js_fabrics(src: str) -> dict[str, dict[str, str]]:
    """`FABRICS` object literals from `src/fabrics.js`, values kept as text.

    Text, not floats: `0.90` and `0.9` are the same number and a DIFFERENT
    literal, and the thing being guarded is a hand-copy. Comparing the strings
    is what makes `str(0.90) == "0.9"` on the Python side the assertion's
    problem rather than its blind spot — see `_py_value`.
    """
    m = re.search(r"const FABRICS = \[(.*?)\n  \];", src, re.S)
    assert m, "no `const FABRICS = [...]` in src/fabrics.js"
    out: dict[str, dict[str, str]] = {}
    for block in re.findall(r"\{(.*?)\n    \}", m.group(1), re.S):
        fid = re.search(r'id:\s*"([^"]+)"', block)
        if not fid:
            continue
        entry = {}
        for key in FIELDS:
            v = re.search(rf'{key}:\s*("?[^,\n]*?"?),', block)
            if v:
                entry[key] = v.group(1).strip().strip('"')
        out[fid.group(1)] = entry
    return out


def _js_garment_fabric(src: str) -> dict[str, str]:
    m = re.search(r"const GARMENT_FABRIC = \{(.*?)\n  \};", src, re.S)
    assert m, "no `const GARMENT_FABRIC = {...}` in src/fabrics.js"
    return dict(re.findall(r'(\w+):\s*"([^"]+)"', m.group(1)))


def _norm(v) -> str:
    """One spelling for one physical value, whichever source it came from.

    `densityAdjust: 0.90` in JS and `0.90` in Python are the same number and
    the same literal; `0.9` is the same number and a different one. A test
    that reports that pair as drift cries wolf on the exact field a sew-out is
    most likely to move, so numerics are compared as NUMBERS and everything
    else (the underlay ids, which are what actually drifted) as text.

    Both sides go through here. Normalising only one is how the first cut of
    this file failed: `str(0.90)` is `'0.9'`, the JS text was `'0.90'`, and it
    reported fleece_sweatshirt as divergent when the two engines agree.
    """
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return repr(float(v))
    text = str(v).strip().strip('"')
    try:
        return repr(float(text))
    except ValueError:
        return text


def test_the_parser_is_not_vacuous():
    """A regex that finds nothing passes every comparison below.

    Pin the shapes first — `test_code_wires.py` states the general form of
    this, and `test_stitchviz.py` is the repo's worked example of what
    skipping it costs.
    """
    js = _js_fabrics(FABRICS_JS.read_text(encoding="utf-8"))
    assert len(js) == 7, sorted(js)
    assert js["pique_knit"]["fillUnderlay"] == "edge_run"        # law 26
    assert js["terry_towel"]["densityAdjust"] == "0.85"          # raw text
    assert _norm("0.90") == _norm(0.9) == "0.9"                 # and normalised
    assert _norm("edge_run") == "edge_run"                      # not a number
    assert all(len(v) == len(FIELDS) for v in js.values()), js

    garments = _js_garment_fabric(FABRICS_JS.read_text(encoding="utf-8"))
    assert len(garments) == 10, sorted(garments)
    assert garments["left_chest"] == "pique_knit"


def test_every_fabric_preset_agrees_field_for_field():
    """The whole table, both directions, every physical field.

    A preset present on one side only is as bad as a wrong number: the
    browser's `getFabric` returns `undefined` and `digitize.js` falls through
    to its own `|| "edge_lattice"` default, while Python's `get_fabric` falls
    back to `pique_knit`. Two different silent answers to the same question.
    """
    js = _js_fabrics(FABRICS_JS.read_text(encoding="utf-8"))
    py = {f.id: f for f in FABRICS}
    assert set(js) == set(py), (
        f"only in src/fabrics.js: {sorted(set(js) - set(py))}; "
        f"only in fabrics.py: {sorted(set(py) - set(js))}")

    drift = []
    for fid, fabric in sorted(py.items()):
        for js_field, py_field in FIELDS.items():
            want = _norm(getattr(fabric, py_field))
            got = _norm(js[fid][js_field])
            if want != got:
                drift.append(f"{fid}.{js_field}: browser {got!r} != python {want!r}")
    assert not drift, (
        "the two engines would sew this garment differently:\n  "
        + "\n  ".join(drift))


def test_every_garment_maps_to_the_same_fabric_in_both_engines():
    """`GARMENT_FABRIC` is the second copy, and the one the Studio indexes
    with whatever `project.garmentId` happens to be.

    An id in one map and not the other does not raise on either side — both
    fall back to `pique_knit` — so a garment can quietly lose its preset in
    one engine while the other keeps it.
    """
    js = _js_garment_fabric(FABRICS_JS.read_text(encoding="utf-8"))
    assert js == GARMENT_FABRIC, (
        f"only in src/fabrics.js: {sorted(set(js) - set(GARMENT_FABRIC))}; "
        f"only in fabrics.py: {sorted(set(GARMENT_FABRIC) - set(js))}; "
        f"disagree: {sorted(k for k in set(js) & set(GARMENT_FABRIC) if js[k] != GARMENT_FABRIC[k])}")

    # Both maps must name presets that exist, or the fallback silently swaps
    # the physics for the default.
    ids = {f.id for f in FABRICS}
    assert set(GARMENT_FABRIC.values()) <= ids, sorted(set(GARMENT_FABRIC.values()) - ids)
    assert DEFAULT_FABRIC_ID in ids


def test_the_browser_fallback_default_matches_python_s():
    """Three places spell the default, and they are all `pique_knit` today.

    `fabrics.py` has `DEFAULT_FABRIC_ID`; `src/fabrics.js` writes the literal
    twice, in `fabricForGarment`'s `||` and nowhere else. `digitize.js` holds a
    FOURTH default of a different kind (`fabric.fillUnderlay || "edge_lattice"`,
    used when no fabric is passed at all) — deliberately not asserted here,
    because it answers "no garment chosen", not "this garment".
    """
    src = FABRICS_JS.read_text(encoding="utf-8")
    m = re.search(r'return GARMENT_FABRIC\[garmentId\] \|\| "([a-z_]+)"', src)
    assert m, "src/fabrics.js's fabricForGarment no longer has a literal default"
    assert m.group(1) == DEFAULT_FABRIC_ID, (
        f"browser falls back to {m.group(1)!r}, Python to {DEFAULT_FABRIC_ID!r}")


# --- The second hand-copied physical pair -----------------------------------
#
# `src/digitize.js` names its two spacing constants after the Python ones in
# its own comments ("Tatami row spacing — `machine.FILL_ROW_MM`"), and
# `generate.js` says the Studio passes neither, on purpose, because "the
# engine's own defaults … ARE the Studio's numbers, so a ruling moves them in
# one place." One place inside the Studio — `machine.py` still holds its own
# copy, so a ruling actually has to move them in two, across a language
# boundary, by hand. Identical to the fabric table above, and in sync today;
# guarded now rather than after it drifts, because fill row spacing is the one
# number DOCTRINE calls settled (Kent's ruling 2026-09-03) and the browser
# preview is what a customer judges the file by.

DIGITIZE_JS = REPO / "src" / "digitize.js"


def _js_const(src: str, name: str) -> str:
    m = re.search(rf"^\s*const {name} = ([0-9.]+);", src, re.M)
    assert m, f"no `const {name} = <number>;` in src/digitize.js"
    return m.group(1)


def test_the_two_spacing_constants_agree_across_the_engines():
    """A drift here is invisible and expensive: the browser draws the preview
    the customer approves, the Python engine writes the file the machine sews,
    and row spacing is the single biggest lever on both density and runtime.
    """
    from digitizer_core import machine

    src = DIGITIZE_JS.read_text(encoding="utf-8")
    for js_name, py_name in (("FILL_ROW_MM", "FILL_ROW_MM"),
                             ("SATIN_SPACING_MM", "SATIN_SPACING_MM")):
        want = _norm(getattr(machine, py_name))
        got = _norm(_js_const(src, js_name))
        assert want == got, (
            f"{js_name}: browser {got}, python machine.{py_name} {want} — "
            "the preview and the file would carry different density")

    # And the superseded value must stay superseded rather than creep back as
    # the live one: 0.40 was the pre-2026-09-03 fill row, kept in machine.py
    # only as a named record of what moved.
    assert _norm(machine.FILL_ROW_MM_BEFORE_2026_09_03) != _norm(machine.FILL_ROW_MM)
