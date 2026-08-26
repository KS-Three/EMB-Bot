"""Stage-agnostic — `digitizer_core.stitchviz`, the thread render.

Why it exists: the acceptance sheet showed `pystitch.write_svg`'s vector
proof, and Kent, looking at a sheet of them on 2026-08-24, said it was hard
to picture how any of it became an embroidered product. He was right. A
hairline polyline cannot show whether twelve spools read as a face, because
thread has width, overlaps, and covers cloth. These pin the geometry of the
render and the one number it produces.
"""
from __future__ import annotations

import re

import numpy as np
import pytest

from digitizer_core.stitchviz import (
    COVERAGE_PX_PER_MM,
    FABRIC_BGR,
    THREAD_MM,
    UNITS_PER_MM,
    coverage,
    render_design,
    render_png_bytes,
)


def _design(stitches, colors=None):
    return {"stitches": stitches, "colors": colors or [{"r": 10, "g": 20, "b": 200}]}


def _run(x0, y0, x1, y1, n=40):
    """A straight run of `n` stitches, in 0.1 mm design units (y up)."""
    return [{"x": int(x0 + (x1 - x0) * i / (n - 1)),
             "y": int(y0 + (y1 - y0) * i / (n - 1)),
             "type": "stitch"} for i in range(n)]


def test_an_empty_design_renders_bare_cloth_rather_than_raising():
    """A plan that emitted nothing is a real outcome (stage 7's never-drop
    ladder can still hand back an empty design), and the sheet has to draw
    a cell for it."""
    img = render_design(_design([]))
    assert img.ndim == 3 and img.shape[2] == 3
    assert np.all(img.reshape(-1, 3) == np.array(FABRIC_BGR))


def test_the_render_is_scaled_and_oriented_like_the_design():
    """Design units are 0.1 mm with y UP; the image is pixels with y DOWN.
    A run that climbs in design space must descend in the image, or every
    render is vertically mirrored and nobody notices until a sew-out."""
    d = _design(_run(0, 0, 0, 200))          # 20 mm straight up
    px_per_mm, pad = 10.0, 2.0
    img = render_design(d, px_per_mm=px_per_mm, pad_mm=pad)

    # 20 mm of travel plus 2 mm padding each side, at 10 px/mm.
    assert img.shape[0] == int((200 / UNITS_PER_MM + 2 * pad) * px_per_mm)
    ys = np.where(np.any(np.any(img != np.array(FABRIC_BGR), axis=2), axis=1))[0]
    # Thread occupies the middle band, not the padding — allowing for the
    # round cap, which deliberately extends half a filament past the last
    # stitch because that is what the end of a stitch looks like.
    cap = THREAD_MM * px_per_mm / 2.0 + 1.0
    assert ys.min() >= pad * px_per_mm - cap
    assert ys.max() <= img.shape[0] - pad * px_per_mm + cap


def test_thread_is_drawn_at_its_real_width():
    """The whole point of the render: a filament, not a hairline.

    The measured footprint is WIDER than the nominal filament and that is
    not a bug — anti-aliasing puts a partial fringe either side, so a
    nominal 4 px thread touches about 7 px. The fringe is why `coverage`
    reads the difference between two backgrounds instead of counting
    non-fabric pixels: counted flat, that fringe would inflate every sparse
    design by roughly a third.
    """
    d = _design(_run(0, 0, 0, 200))
    img = render_design(d, px_per_mm=10.0)
    mid = img[img.shape[0] // 2]
    nominal = THREAD_MM * 10.0
    touched = np.where(np.any(mid != np.array(FABRIC_BGR), axis=1))[0]
    assert nominal <= len(touched) <= nominal + 4, "fringe should be a fringe"

    # The SOLID part — pixels more thread than cloth — stays near nominal.
    dist = np.linalg.norm(mid.astype(int) - np.array(FABRIC_BGR), axis=1)
    solid = np.where(dist > dist.max() / 2.0)[0]
    assert len(solid) == pytest.approx(nominal, abs=2.0)


def test_jumps_and_trims_lay_no_thread():
    """Travel moves the needle without stitching. Drawing through a jump
    would paint travel as coverage — the exact error that would make a
    sparse design look solid."""
    walk = (_run(0, 0, 0, 100, n=20)
            + [{"x": 0, "y": 100, "type": "trim"},
               {"x": 900, "y": 100, "type": "jump"}]
            + _run(900, 100, 900, 200, n=20))
    img = render_design(_design(walk), px_per_mm=10.0)
    # The horizontal gap the jump crossed must be bare.
    row = img[img.shape[0] // 2]
    bare = np.all(row == np.array(FABRIC_BGR), axis=1)
    assert bare.sum() > 0.5 * len(row), "the jump was drawn as thread"


def test_a_colour_change_advances_through_the_block_colour_list():
    """`adapter.plan_to_design` writes one colour PER BLOCK, so a design
    that returns to an earlier spool has that spool listed again. Rendering
    must walk the list rather than dedupe it, or a thread return paints in
    the wrong colour."""
    red, blue = {"r": 220, "g": 0, "b": 0}, {"r": 0, "g": 0, "b": 220}
    stitches = (_run(0, 0, 200, 0, n=20)
                + [{"x": 200, "y": 0, "type": "color"}]
                + _run(200, 0, 400, 0, n=20))
    img = render_design(_design(stitches, [red, blue]), px_per_mm=10.0)
    h, w = img.shape[:2]
    left, right = img[h // 2, : w // 3], img[h // 2, 2 * w // 3:]
    # BGR: the first half leans red, the second blue.
    assert left[:, 2].max() > left[:, 0].max()
    assert right[:, 0].max() > right[:, 2].max()


def test_coverage_is_zero_for_an_empty_design_and_high_for_a_solid_block():
    """The number's two ends. A filled square is nearly all thread; nothing
    sewn is none."""
    assert coverage(_design([])) == 0.0
    rows = []
    for i in range(60):                      # 6 mm of rows, 0.1 mm apart
        y = i * 1
        rows += _run(0, y, 600, y, n=30)
        rows += [{"x": 600, "y": y, "type": "jump"}]
    assert coverage(_design(rows)) > 0.9


def test_coverage_does_not_move_with_the_display_scale():
    """It is a MEASUREMENT, so it cannot depend on zoom. Thread width rounds
    to whole pixels, and before this was pinned the same design read 0.75 at
    8 px/mm and 0.67 at 14 — a number that drifts with how you look at it is
    not evidence. `coverage` takes no scale argument for exactly this
    reason; this test pins that it stays that way."""
    import inspect
    assert "px_per_mm" not in inspect.signature(coverage).parameters
    assert COVERAGE_PX_PER_MM >= 20.0, (
        "below ~20 px/mm the half-pixel rounding on a 0.4 mm filament is a "
        "few percent of its width, which lands straight in the number")


def test_png_bytes_are_a_real_png():
    """The sheet embeds these base64; a silent encode failure would render
    every cell as a broken image."""
    b = render_png_bytes(_design(_run(0, 0, 200, 200)))
    assert b[:8] == b"\x89PNG\r\n\x1a\n"


# --- the lit filament (2026-08-25) -----------------------------------------
# Kent, on a fill sheet: *"It feels like i'm looking at an image made up of
# vectors and not stitches."* The cause was that every stitch was shaded
# identically regardless of which way it ran, so a field of parallel rows was
# one flat tone. Scale was NOT the cause and was ruled out first: the same
# design reads as hatching at 6, 8, 16 and 28 px/mm alike.


def test_shading_cannot_move_coverage():
    """THE load-bearing test for the whole lit render.

    `coverage` is measured BY RENDERING, so any change to how thread is
    shaded threatens every coverage figure ever recorded -- and those figures
    are what the fill-tier, border and shade-bind rulings were decided on.
    The first cut of this shading moved coverage by 8e-4 across the board,
    purely because off-centre bands push their anti-aliased fringe a shade
    wider than centred ones do.

    The fix was to split the two: shading is display, coverage measures
    FOOTPRINT and renders `lit=False`. This pins that split by making the
    shading absurd -- one full-width band, no offsets -- and requiring the
    number not to twitch.
    """
    import digitizer_core.stitchviz as sv

    d = _design(_run(0, 0, 400, 0) + _run(0, 10, 400, 10) + _run(0, 20, 400, 20))
    before = coverage(d)

    original = sv._BANDS
    try:
        sv._BANDS = ((1.0, 0.0, 0.10),)          # nothing like the shipped bands
        assert coverage(d) == before, "shading leaked into the measurement"
        sv._BANDS = ((1.0, 0.49, 3.0), (0.2, 0.0, 0.1))
        assert coverage(d) == before, "shading leaked into the measurement"
    finally:
        sv._BANDS = original


def test_a_filament_is_lit_by_the_angle_it_runs_at():
    """The term that stops a tatami field being one flat tone. A row across
    the light is brighter than one along it; without this the render is
    hatching, which is exactly what it looked like."""
    import math

    import digitizer_core.stitchviz as sv

    lx, ly = sv._LIGHT
    along = math.degrees(math.atan2(ly, lx))

    def tone_of(deg):
        r = 400
        a = (0, 0)
        b = (int(r * math.cos(math.radians(deg))), int(r * math.sin(math.radians(deg))))
        d = _design([{"x": a[0], "y": a[1], "type": "stitch"},
                     {"x": b[0], "y": b[1], "type": "stitch"}])
        img = render_design(d, px_per_mm=20.0)
        px = img.reshape(-1, 3)
        thread = px[np.any(px != np.array(FABRIC_BGR), axis=1)]
        return float(thread.mean())

    # Design y is UP and the light is in image coords, so flip to compare.
    assert tone_of(-along + 90) > tone_of(-along), (
        "a filament across the light must read brighter than one along it")


def test_the_unlit_path_is_the_pre_shading_draw_exactly():
    """`lit=False` is the frozen measurement path, and it is frozen at three
    CENTRED bands in a specific order -- not at 'one opaque band of the same
    width', which was tried and moved coverage by 1.2e-3. Each anti-aliased
    pass re-blends the fringe of the one before, so the soft edge depends on
    how many passes there were, not only how wide they were."""
    d = _design(_run(0, 0, 0, 300))          # VERTICAL, so a row crosses it
    img = render_design(d, px_per_mm=20.0, lit=False)
    mid = img[img.shape[0] // 2]
    dist = np.linalg.norm(mid.astype(int) - np.array(FABRIC_BGR), axis=1)
    solid = np.where(dist > dist.max() / 2.0)[0]
    # Same nominal-width assertion the lit-agnostic width test makes, on the
    # path coverage actually uses.
    assert len(solid) == pytest.approx(THREAD_MM * 20.0, abs=2.0)


def _js_function_body(js: str, name: str) -> str:
    """The source of one top-level `export function NAME` in `preview.js`.

    Brace-matching, not the `\\n}\\n` scan the discarded version of this check
    used. That scan takes the first column-0 `}` after the signature, which is
    the end of the function only while nothing inside it ever closes a block at
    column 0 -- true today, silently wrong the first time someone reformats.
    Cheap to do properly, and a helper that quietly returns a FRAGMENT would
    weaken every assertion built on it instead of failing.
    """
    start = js.index(f"export function {name}(")
    depth = 0
    for i in range(js.index("{", start), len(js)):
        if js[i] == "{":
            depth += 1
        elif js[i] == "}":
            depth -= 1
            if depth == 0:
                return js[start:i + 1]
    raise AssertionError(f"{name} in preview.js has unbalanced braces")


def _js_top_level_locals(body: str) -> list[str]:
    """Every name a JS function body binds with `const`/`let` at ONE indent
    level, in source order. Nested-block locals legitimately shadow and are
    deliberately skipped.

    The discarded version of this was `^  (?:const|let) (\\w+)\\s*=`, which only
    sees a declaration whose FIRST declarator is immediately assigned. Measured
    against `renderRealistic` on 2026-08-26 it caught 20 of 30 top-level
    locals. The ten it missed were exactly the two forms that regex cannot
    express:

      const cw = ..., ch = ...;        -> sees `cw`, misses `ch`
      let t, TX0, TY0, pxPerMm0;       -> sees nothing at all

    That second form IS the transform block, which is precisely the region the
    two rival renderers kept fighting over -- so a stale block re-applied there
    would redeclare `t`/`TX0`/`TY0`/`pxPerMm0`, break `preview.js` with a
    SyntaxError, and leave this guard green. A guard blind to the exact case it
    exists for is worse than no guard, because it is quoted as coverage.
    """
    names: list[str] = []
    for m in re.finditer(r"^  (?:const|let)\s+(.+?);\s*$", body, re.MULTILINE | re.DOTALL):
        # Split the declarator list on commas that are not inside (), [], {},
        # so `const a = f(x, y), b = 1;` yields `a = f(x, y)` and `b = 1`.
        depth = 0
        buf = ""
        parts = []
        for ch in m.group(1):
            if ch in "([{":
                depth += 1
            elif ch in ")]}":
                depth -= 1
            if ch == "," and depth == 0:
                parts.append(buf)
                buf = ""
            else:
                buf += ch
        parts.append(buf)
        for part in parts:
            ident = re.match(r"\s*([A-Za-z_$][\w$]*)", part)
            if ident:
                names.append(ident.group(1))
    return names


def test_the_two_renderers_agree_on_the_light():
    """`preview.js` implements this same model for the Studio canvas. If the
    two lit from different corners, what Kent rules on in an acceptance sheet
    and what a customer sees would disagree -- which is the whole reason the
    model is shared. This pins the constant the JS side mirrors."""
    from pathlib import Path

    import digitizer_core.stitchviz as sv

    js = (Path(__file__).resolve().parents[2] / "app" / "src" / "lib" / "preview.js").read_text(encoding="utf-8")

    # Compare the constants the JS renderer ACTUALLY uses. The first version of
    # this test matched a `LIGHT_DEG = 225` that a later merge left behind as
    # dead code, so it went on passing while the live canvas lit from a
    # different corner entirely -- a test that cannot fail is worse than none.
    assert f"const LIGHT_X = {sv.LIGHT_X};" in js, (
        "preview.js and stitchviz disagree about the light direction")
    assert f"const LIGHT_Y = {sv.LIGHT_Y};" in js, (
        "preview.js and stitchviz disagree about the light direction")
    assert f"export const THREAD_WIDTH_MM = {sv.THREAD_MM};" in js, (
        "preview.js and stitchviz disagree about filament width")

    # AND THAT THOSE CONSTANTS ARE LIVE. Matching a declaration only proves the
    # name is present in the file; it says nothing about anything reading it.
    # That is not hypothetical -- it is how this test failed on 2026-08-25: a
    # merge left `LIGHT_DEG = 225` behind as dead code and the grep kept
    # passing for hours while the live canvas lit from a different corner.
    # Comparing live constants (above) fixed the WHICH; this fixes the WHETHER.
    #
    # The chain that has to hold: renderRealistic -> drawThreads -> LIGHT_*.
    # Assert every link. A dead constant breaks the last one, and a merge that
    # bolts a second renderer into renderRealistic breaks the middle one.
    render = _js_function_body(js, "renderRealistic")
    threads = _js_function_body(js, "drawThreads")
    assert "drawThreads(" in render, (
        "renderRealistic no longer routes through drawThreads -- the shared "
        "lighting model is bypassed, so these constants prove nothing")
    for const in ("LIGHT_X", "LIGHT_Y"):
        assert const in threads, (
            f"drawThreads does not read {const} -- the light constants are "
            "dead again, and this test would pass while the canvas disagrees")
    assert "THREAD_WIDTH_MM" in render, (
        "renderRealistic does not read THREAD_WIDTH_MM -- filament width is "
        "dead code and coverage in the preview no longer means anything")



def _render_realistic_body() -> str:
    """`renderRealistic`'s source, read from the Studio's preview.js."""
    from pathlib import Path

    js = (Path(__file__).resolve().parents[2] / "app" / "src" / "lib" / "preview.js").read_text(
        encoding="utf-8"
    )
    return _js_function_body(js, "renderRealistic")


def test_the_duplicate_declaration_guard_can_actually_fail():
    """The guard above is only worth its line count if it SEES the forms the
    bad merge produces. Its predecessor did not -- so this pins the parser on
    the two declarator shapes that defeated it, using the exact names from the
    transform block the rival renderers fought over.

    Written because the previous version of this guard passed against a
    `renderRealistic` it could only see two thirds of, and was cited as
    coverage for the one failure mode it was blind to.
    """
    # Multi-declarator: the regex form saw only the first name.
    assert _js_top_level_locals("  const cw = 1, ch = 2;\n") == ["cw", "ch"]

    # Declaration with no initializer: the regex form saw nothing at all. This
    # is the transform block.
    assert _js_top_level_locals("  let t, TX0, TY0, pxPerMm0;\n") == [
        "t", "TX0", "TY0", "pxPerMm0",
    ]

    # A comma inside a call argument list is not a declarator boundary.
    assert _js_top_level_locals("  const a = f(x, y), b = 1;\n") == ["a", "b"]

    # Nested-block locals still shadow legitimately and stay invisible.
    assert _js_top_level_locals("    const inner = 1;\n") == []

    # And end to end: a duplicate in EITHER form is caught. Both of these
    # passed the predecessor.
    for stale in ("  let t, TX0, TY0, pxPerMm0;\n", "  const cw = 9, ch = 9;\n"):
        # Leading newline: the extracted body ends at the closing brace with
        # no trailing newline, so a bare append lands on that same line.
        names = _js_top_level_locals(_render_realistic_body() + "\n" + stale)
        assert sorted({n for n in names if names.count(n) > 1}), (
            f"a re-applied {stale.strip()!r} is invisible to the guard"
        )


def test_render_realistic_declares_each_local_once():
    """A bad merge of `preview.js` has landed FOUR times, always the same way:
    a superseded copy of the thread-drawing block is re-applied on top of the
    current one inside `renderRealistic`, giving two `const lw` in one scope.

    The JS suite does catch it -- as `SyntaxError: Identifier 'lw' has already
    been declared`, with no hint of what merged wrong. This catches the same
    class here, in a job that runs separately from vitest, and names it.
    """
    from pathlib import Path

    body = _render_realistic_body()

    names = _js_top_level_locals(body)
    dupes = sorted({n for n in names if names.count(n) > 1})
    assert not dupes, (
        f"renderRealistic declares {dupes} more than once in one scope. This "
        "is the recurring bad merge: a stale thread-drawing block re-applied "
        "over the current one. Keep the block that calls drawThreads.")
