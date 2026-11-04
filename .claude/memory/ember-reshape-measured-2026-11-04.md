---
name: ember-reshape-measured-2026-11-04
description: Ember Design's reshape tool driven and pixel-diffed 2026-11-04 (behaviour only): one point moves, accept/reject session; what Kent built from it and what is still open
metadata:
  type: reference
---

Director drove Ember's editor (clicks, screenshots, pixel diffs), 226 % zoom.
Behaviour only; no Ember code or screenshots are kept in this repo.

- **Drag a point:** exactly one point moves (60.0 px asked, 60.0 px moved,
  0.0 px on every other point); the curve re-solves through neighbours;
  stitches regenerate once, on accept. A corner drags the same way.
- **Multi-select drag:** all selected move by the same delta.
- **Alt / Shift drag:** identical to a plain drag (no soft pull, no constraint).
- **Click on the path:** inserts a corner point (a click 4 px off did nothing).
- **Double-click a point:** toggles smooth / corner.
- **Shift-click:** replaces the selection, does not add. Right-click: selects, no menu.
- **Bare drag on empty canvas:** marquee. Hit radius ~6-10 px.
- **Arrows:** 1 unit, Shift = 10; each press one undo step.
- **Escape:** does nothing. **Enter / tick:** accept, one restitch. **Cross:** reject,
  rolls the whole session back.
- **Why it wins for precision:** few smooth nodes (edge = curve), not every trace vertex.

**Built from it (PR for ruling 8, Kent 11-04 "zero falloff + accept/reject"):**
bare drag exact, Alt soft; strip tick = Done, cross = Discard, Enter = Done.
**Not built (separate spec later):** sparse smooth nodes, insert on path click,
corner/smooth toggle. Escape stays Done here, deliberately unlike Ember.

Links: [[node-reshape-spec-2026-11-03]], [[reshape-mode-2026-11-03]].
