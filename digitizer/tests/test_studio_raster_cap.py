"""The Studio sends the digitizer a 1,200-px raster, not the customer's file —
and the engine was being measured on the file (found 2026-09-19).

`app/src/ui/DigitizePanel.svelte` downsamples every upload to `PROCESS_MAX_PX`
on its long edge (`rasterize.js` `loadImage` + `rasterSize`, a canvas
`drawImage`, `toDataURL("image/png")`) before the service sees a pixel. Seven
of the nine REAL_ART logos are larger than that, so a measurement on the file
in `digitizer/testdata/` reads a raster no customer sends. On ENTHUSIAST the
file reads 2,318 stitches / 14 trims / grade B and the Studio's raster 2,311 /
9 / grade A, and no cv2 resample of the file reproduces the browser's
(INTER_AREA 14 trims, INTER_LINEAR 13). `tools/studio-raster.mjs` runs the
Studio's own `rasterize.js` in Playwright's Chromium and writes that raster;
its output reproduced the quality-report e2e's job to the stitch
(2,311 / 9 / 30 jumps / A, 2026-09-20).

Pinned here, all read from source so a change fails loudly instead of
drifting: the tool's default cap IS the panel's constant; the tool loads the
checkout's `rasterize.js` (not a copy) and the functions it calls still exist
under those names; and the corpus population that crosses the cap — the
"seven of nine" DOCTRINE cites — plus the plan's two MARINE fixtures, one
each side of the line.
"""
from __future__ import annotations

import re
from pathlib import Path

import cv2
import numpy as np

from tools.studio_raster_census import bleed
from tools.thin_strokes import corpus_cases

ROOT = Path(__file__).resolve().parents[2]
PANEL = ROOT / "app" / "src" / "ui" / "DigitizePanel.svelte"
TOOL = ROOT / "tools" / "studio-raster.mjs"
RASTERIZE = ROOT / "app" / "src" / "lib" / "rasterize.js"
RENDERS = ROOT / "docs" / "renders"
MARINE_80 = RENDERS / "lettering-route-2026-09-19" / "marine_80mm_traced_input.png"
MARINE_127 = RENDERS / "lettering-split-2026-09-19" / "marine_127mm_traced_input.png"


def _panel_cap() -> int:
    m = re.search(r"^\s*const PROCESS_MAX_PX = (\d+);", PANEL.read_text(encoding="utf-8"), re.M)
    assert m, "DigitizePanel.svelte no longer declares PROCESS_MAX_PX where this test reads it"
    return int(m.group(1))


def _tool_cap() -> int:
    m = re.search(r"^let max = (\d+);", TOOL.read_text(encoding="utf-8"), re.M)
    assert m, "tools/studio-raster.mjs no longer declares its default cap as `let max = N;`"
    return int(m.group(1))


def _long_edge(path: Path) -> int:
    im = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    assert im is not None, path
    h, w = im.shape[:2]
    return max(w, h)


def test_the_tool_defaults_to_the_panels_cap():
    """1,200 measured 2026-09-19. If the panel moves, move the tool's default
    with it AND re-read the census in scope-history 2026-09-20 — every number
    there is a function of this constant."""
    assert _tool_cap() == _panel_cap() == 1200


def test_the_tool_runs_the_studios_own_rasterizer_not_a_copy():
    src = TOOL.read_text(encoding="utf-8")
    assert '"app", "src", "lib", "rasterize.js"' in src
    assert RASTERIZE.exists()
    module = RASTERIZE.read_text(encoding="utf-8")
    for fn in ("loadImage", "rasterSize", "isVectorFile"):
        assert f"export function {fn}(" in module, fn
        assert fn in src, fn
    # the panel's own canvas calls, in the panel's order
    for call in ('document.createElement("canvas")', "drawImage(img, 0, 0, w, h)", 'toDataURL("image/png")'):
        assert call in src, call


def test_the_tools_default_smoothing_is_the_panels_which_sets_none():
    """Chrome's default `imageSmoothingQuality` is "low" — a bilinear tap with
    no area averaging — and the panel never sets it; that filter is what
    turns the 1,585-px tires logo into 14 trims where INTER_AREA at the same
    size reads 8 (scope-history 2026-09-20). The tool's `--smoothing` exists
    to measure a candidate fix, so its default must stay the panel's: set
    only when asked, and the output name must say so."""
    panel = PANEL.read_text(encoding="utf-8")
    assert "imageSmoothingQuality" not in panel
    src = TOOL.read_text(encoding="utf-8")
    assert "let smoothing = null;" in src
    assert "if (smoothing) ctx.imageSmoothingQuality = smoothing;" in src
    assert "`.studio-${smoothing}.png`" in src


def test_seven_of_the_nine_corpus_logos_cross_the_cap():
    """The population DOCTRINE's "seven of nine" rests on (measured
    2026-09-20). Becker (146 px) and Bridge Bar (400 px) pass through the
    canvas unresized; everything else is resampled before the engine sees it."""
    cap = _panel_cap()
    cases = corpus_cases()
    assert len(cases) == 9
    over = {name for name, path, _w, _g in cases if _long_edge(Path(path)) > cap}
    assert over == {"tires", "enthusiast", "fremont", "golden_tee", "gaulke", "drone", "screenshot"}, over


def test_the_plans_two_marine_fixtures_sit_either_side_of_the_cap():
    """MARINE traced at 80 mm (1,058 px) reaches the engine as it is; at
    127 mm (1,624 px) the Studio would send 1,200 — so the plan's 80 mm
    yardstick numbers are the customer's and its 127 mm numbers were not."""
    cap = _panel_cap()
    assert _long_edge(MARINE_80) <= cap
    assert _long_edge(MARINE_127) > cap


def test_the_edge_bleed_fills_every_non_opaque_pixel_from_its_nearest_opaque_one():
    """The cure DOCTRINE 2026-09-20 measured on Becker (flat / 17 / 8,440 /
    54 from both rasters). Alpha is untouched; opaque RGB is untouched; a
    transparent or semi-transparent pixel takes the RGB of the nearest opaque
    pixel whatever the canvas or the exporter left there; an image with no
    alpha, or no partial alpha, is left alone (None, the identity)."""
    img = np.zeros((4, 6, 4), np.uint8)
    img[:, :3, :3] = (10, 20, 30); img[:, 3:, :3] = (200, 210, 220)        # two opaque colours...
    img[..., 3] = 255
    img[0, :, 3] = 0; img[0, :, :3] = (0, 0, 0)                            # ...a transparent row the canvas made black
    img[1, 2, 3] = 128; img[1, 2, :3] = (99, 99, 99)                       # ...and one noisy semi-transparent pixel
    out = bleed(img)
    assert out is not None
    assert np.array_equal(out[..., 3], img[..., 3])
    assert np.array_equal(out[1:, :, :3][img[1:, :, 3] == 255], img[1:, :, :3][img[1:, :, 3] == 255])
    assert tuple(out[0, 0, :3]) == (10, 20, 30) and tuple(out[0, 5, :3]) == (200, 210, 220)
    assert tuple(out[1, 2, :3]) == (10, 20, 30)
    assert bleed(img[..., :3]) is None                                     # no alpha
    opaque = img.copy(); opaque[..., 3] = 255
    assert bleed(opaque) is None                                           # nothing to fill


def test_the_panel_sends_the_file_itself_for_rasters_the_service_decodes():
    """Kent's pick on the census (2026-09-20): the customer's bytes go to
    /digitize and the 1,200-px canvas is the preview. Pinned by reading the
    source, like the cap above: the panel routes uploads through `uploadPlan`
    and stores the original (`putSource`), the request builder accepts bytes,
    and the policy names exactly the formats cv2 decodes — GIF and SVG stay
    on the canvas path, which is what this file's tool still measures."""
    panel = PANEL.read_text(encoding="utf-8")
    assert "uploadPlan(file, img, health && health.limits)" in panel
    assert "await putSource(key, { bytes, type, name: file.name })" in panel
    assert "sourceFile" in panel
    client = (ROOT / "app" / "src" / "lib" / "digitizer.js").read_text(encoding="utf-8")
    assert "new Blob([image.bytes], { type: image.type" in client
    policy = RASTERIZE.read_text(encoding="utf-8")
    assert 'SERVICE_DECODES = new Set(["image/png", "image/jpeg", "image/webp", "image/bmp"])' in policy
    assert "image/gif" not in policy.split("SERVICE_DECODES = new Set(")[1].split(")")[0]
    assert "return { asIs: false, reason: \"vector\"" in policy
