"""Stage 6 — the sketch tier (photo plan, technique-menu row 12).

The plan row's own words: "Building tiers 8–11 delivers law 10 nearly free —
a config preset, not a new engine." This module IS that preset, and nothing
more: it owns no tracing, no field, no line extraction — every stitch a
sketch sews comes out of machinery rows 10 and 11 already landed and test:

1. **Sparse mono line work** — `stage6_streamline.streamline_fill` (row 10)
   in forced MONO mode, with the darkness field attenuated by
   `SKETCH_DARKNESS_SCALE` before the tier reads it. That one number is the
   whole "sketch" of it: streamlines still follow the ETF direction field
   (or the house angle where coherence fails — the row-10 contract,
   unchanged), but they seed sparser everywhere and give up to bare fabric
   sooner. Law 10's corpus fingerprint (corgi/snowman/rose: ~6 runs, 12k st,
   1 trim) is sparse line passes over fabric-as-value, not a dense
   thread-paint mat — the scale is how the same tracer sews the sparse
   class instead of the dense one.
2. **FDoG detail lines on top** — `stage6_detail.detail_runs` (row 11).
   `fill_technique == "sketch"` IMPLIES the detail layer: stage 7 appends
   the detail block for a sketch design whether or not `cfg.detail_layer`
   was set, because "layered run passes + FDoG detail lines" is the row-12
   recipe, not two independent knobs. (An explicit `detail_layer=True`
   composes with every OTHER technique exactly as before; nothing about
   row 11's own opt-in moved.) The detail extractor's honesty contract
   carries over verbatim: a source with no coherent lines appends nothing.

Routing (all of it stage 7's, none of it here):
- `cfg.fill_technique == "sketch"` sends every auto/fill-tier shape here,
  with the same never-drop-artwork ladder every tonal tier has — satin
  classification still runs first (a ribbon is still a ribbon), `empty`
  (all-highlight) falls back to tatami, no source pixels sews tatami.
- The shape-layers contract's `tier` override accepts `"sketch"` (contract
  v1.3): one shape can be forced to sketch rendering on the review screen
  while the rest of the design sews whatever it sews — the same three-layer
  wiring (service validation, `regions.apply_shape_edits`, stage-7
  consumption) every other tier value rides. A per-shape override does NOT
  imply the design-wide detail block; that composition belongs to the
  design-wide preset only.

Strictly opt-in, the standing rule: nothing routes here unless the technique
or a shape override names "sketch", and naming it is also what makes
`pipeline.run_stages` carry source pixels forward — the flat lane grows no
raster payload otherwise, and the byte-identity suites pin that.

Underlay: none, inherited from the streamline tier by construction — this is
the fabric-as-value class (plan row 14's "none under meander/sketch").
"""
from __future__ import annotations

from dataclasses import replace

from .regions import Region
from .stage6_blend import SourcePixels
from .stage6_streamline import streamline_fill
from .stitches import StitchRun

# The one number that turns thread-paint into sketch: the darkness field is
# read at half strength. Consequences, all measured through the row-10
# mapping rather than re-tuned here (tests/test_stage6_sketch.py pins them
# from emitted geometry):
#   - full black seeds at ~2.1 mm separation instead of 0.8 — sparse strokes
#     that read as drawing, not coverage;
#   - midtones land near the sparse end of the d_sep ladder and mostly drop
#     out, which is the sketch economy (tone is SUGGESTED, fabric carries
#     the highlight and most of the midtone value);
#   - the effective highlight cutoff doubles (raw darkness below
#     2 x STREAMLINE_CUTOFF_DARKNESS sews nothing, i.e. luminance above
#     ~0.84 is bare fabric instead of ~0.92).
# 0.5 is the smaller, conservative choice: it stays inside the tracer's own
# calibrated darkness->spacing band (no new constants, no new floors) and
# the whole preset reverts to row-10 behaviour at 1.0.
SKETCH_DARKNESS_SCALE = 0.5


def sketch_fill(region: Region, source_pixels: SourcePixels, cfg
                ) -> tuple[list[StitchRun], dict]:
    """One shape -> its sketch runs plus the standard tier report.

    Same `(runs, report)` contract as every stage-6 sibling (`too_thin` /
    `jumps` / `empty`, mm / y-down): this is `streamline_fill` mono with the
    sketch attenuation, nothing else. Mono is FORCED — a sketch is one
    thread of line work by definition (law 10's mono fingerprint), so
    `cfg.streamline_mode = "layered"` applies to the streamline technique
    only and is deliberately not honoured here.
    """
    mono_cfg = (cfg if str(cfg.streamline_mode or "mono").lower() == "mono"
                else replace(cfg, streamline_mode="mono"))
    return streamline_fill(region, source_pixels, mono_cfg,
                           darkness_scale=SKETCH_DARKNESS_SCALE)
