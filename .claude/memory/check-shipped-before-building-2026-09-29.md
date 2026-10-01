---
name: check-shipped-before-building-2026-09-29
description: "Kent asked for a manual digitizing tool that had already shipped (manual draw lane, 2026-08); showing it in the browser turned the ask into the real defect — the editing surface, not the capability"
metadata:
  node_type: memory
  type: feedback
  originSessionId: 63bb766a-bcb3-44ae-ada9-c50f6528d133
  modified: 2026-09-29T22:12:02.680Z
---

On 2026-09-29 Kent asked to "begin working on a tool that allows me to manually
digitize a logo or photo." The manual draw lane (ManualPanel, manualShapes.js,
manualTrace.js, per-shape satin/fill/angle, trace backdrop) had shipped in
August and he had forgotten it existed — his own words when offered the option.
Running it in the browser pane on the Becker logo (68 traced starter shapes,
five hole warnings) produced the real request within one message: the controls
live in a side panel and he wants to click the shape on the design and edit it
there. Spec: `docs/superpowers/specs/2026-09-29-shape-popover-design.md`.

**Why:** the capability areas here are large and months old; Kent's mental
model lags what shipped. A brainstorm that starts from his framing would have
re-specified an existing lane. The Explore survey plus one browser drive cost
~10 minutes and redirected the whole session.

**How to apply:** when Kent asks for a "tool" or "feature", first grep
MASTER_SCOPE/PRODUCT for it and, if it exists, put "I forgot it existed — show
me" in the option list and drive it in the browser pane before asking design
questions. The gap he names after seeing it is the spec. Related:
[[run-the-app-color-cap-2026-09-07]], [[studio-display-layer-2026-08-25]].
