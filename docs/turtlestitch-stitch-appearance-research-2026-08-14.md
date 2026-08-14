# TurtleStitch teardown — what's portable to stitch appearance in EMB-Bot

**Date:** 2026-08-14 · **Scope:** primary-source read of TurtleStitch 2.11.5's
turtle-path→stitch conversion (`embroider.js`, `embroidGeometry.js`,
`turtleShepherd.js`, plus the block-library XML layered on top), compared
line-by-line against EMB-Bot's own DST codec, fill/travel engine, and
lettering pipeline, for concrete techniques that would visibly improve
stitch appearance — not UI/blocks-editor findings.

**Sources read in full this session:**
- TurtleStitch: `src/embroider.js` (542 lines), `stitchcode/libraries/geometry/embroidGeometry.js`
  (1320 lines), `stitchcode/turtleShepherd.js` (939 lines), plus targeted
  grep/extraction of `libraries/embroidery_module.xml` (33.8 KB, minified),
  `libraries/VectorAndFill.xml` (215.5 KB, minified), `stitchcode/embroidery-library.xml`
  (2 KB), and `stitchcode/gui.js`/`src/gui.js` (grepped for stitch-related settings).
- EMB-Bot (scratch clone of `main`, HEAD `7bc0535`, cloned 2026-08-11):
  `src/dst.js`, `src/fonts.js`, `src/fontbin.js`, `src/satinfont.js`, `src/satin.js`,
  `src/flatten.js`, `app/src/lib/flatten.js`, `app/src/lib/emb.js`, `app/src/lib/generate.js`,
  `digitizer/digitizer_core/stage6_fill.py`, `stage7_sequence.py`, `stitches.py`,
  `preflight.py`, `machine.py` (grepped), plus the prior-art docs listed below.
- EMB-Bot prior research read first, to avoid re-deriving and to flag anything
  new: `docs/inkstitch-research-2026-08-10.md`, `docs/fill-techniques-2026-08-01.md`,
  `docs/dst-axis-verdict-2026-07-31.md`. (`docs/hatch-manual-teardown-2026-08-08.md`,
  `docs/masters-teardown-2026-08-01.md`, `docs/lettering-mastery-2026-08-01.md`, and
  `digitizer/docs/pro-digitizing-playbook.md` were consulted for cross-reference but
  did not surface additional claims that changed any finding below — the two docs
  actually load-bearing for this report's findings are the two named above.)

---

## Verdict

**Mixed, and the one genuinely interesting finding has nothing to do with
fill quality.** TurtleStitch is a simpler, education-first engine — plain
parallel-line fill, no underlay, no pull compensation, no tie/lock stitches,
no satin-rail construction, a crude density heuristic — and on every one of
those axes EMB-Bot's engine is already more advanced, confirmed by direct
comparison, not assumed. Its fill-line travel router (`moveToNextFilledline`
/ `findRoute`) is conceptually the same idea as EMB-Bot's own
`travel_path`/`_link_route`, and EMB-Bot's version is strictly more robust
(it has a detour-length sanity cap TurtleStitch's does not). **The single
most interesting finding is TurtleStitch's Tajima DST encoder, read
byte-for-byte, is a sixth independent source confirming the movement-bit
convention EMB-Bot's own `docs/dst-axis-verdict-2026-07-31.md` already
flagged as wrong in `src/dst.js` — and the live HEAD checkout (2026-08-11,
eleven days after that memo) shows the fix has still not shipped.** That is
worth Kent's attention regardless of anything else in this document. A
second, smaller and genuinely actionable finding: EMB-Bot's lettering
pipeline flattens every glyph curve to a **hardcoded 8 line segments**,
baked once into the compact font binary and geometrically scaled to
whatever size the user picks — TurtleStitch's own curve flattener at least
treats point count as a caller-supplied, clamped parameter (5–60) rather
than a silent constant, which is a real (if modest) idea worth borrowing
even though TurtleStitch's own default isn't the fix on its own.

---

## 1. DST movement-bit axis convention — still broken, freshly reconfirmed

**What TurtleStitch does.** Its Tajima `.dst` encoder is implemented twice,
essentially identically: `src/embroider.js` `encodeTajimaStitch()` (lines
170–282) and `stitchcode/libraries/geometry/embroidGeometry.js`
`encodeTajimaStitch()` (lines 881–993, called from `toDST()` at line 873).
Reading the bit assignments directly:

- `dx` (X movement) sets bits `0x01`/`0x02` (magnitude 1, `embroidGeometry.js`
  lines 966–974), `0x04`/`0x08` (magnitude 9 and 13-threshold combined in `b1`/`b2`,
  lines 906–914, 926–934), and `0x04`/`0x08` again in `b3` for magnitude 81
  (lines 886–894) — **every X bit used is in the low nibble (bits 0–3) of its byte.**
- `dy` (Y movement) sets bits `0x80`/`0x40` (magnitude 1, lines 976–984),
  `0x20`/`0x10` (magnitudes 9/13, lines 916–924, 936–944), and `0x20`/`0x10`
  again in `b3` for magnitude 81 (lines 896–904) — **every Y bit used is in
  the high nibble (bits 4–7).**

So TurtleStitch's convention, read straight from the source with no
interpretation needed, is **low nibble = X, high nibble = Y**, in both of
its independent encoder copies.

**What EMB-Bot's own prior research already established.**
`docs/dst-axis-verdict-2026-07-31.md` (lines 1–29) already concluded, from
four independent sources (pyembroidery, libembroidery, EduTech Wiki,
achatina.de) plus a clean-room ground-truth fixture decode, that "**low
nibble = X, high nibble = Y** in every record byte" (line 7) is the correct,
universally-agreed convention, and that **`src/dst.js`'s table is
transposed** — plus a second bug: "`dst.js` line 67 writes color change as
`0x43` instead of `0xC3`" (line 11). `docs/inkstitch-research-2026-08-10.md`
§6 (lines 582–653) independently re-confirmed the same convention against
`pystitch`'s (Ink/Stitch's own DST library) reader/writer source, calling it
"a fifth independent source." **TurtleStitch, read directly this session, is
a sixth** — an unrelated, unaffiliated open-source project with no
connection to pyembroidery/Ink/Stitch's lineage, arriving at the identical
bit table from its own from-scratch implementation.

**What the live EMB-Bot codebase actually does, checked this session.**
`src/dst.js` (HEAD `7bc0535`, 2026-08-11 — eleven days after the verdict
memo) still has the transposed table. The file's own comment states it
plainly (lines 8–11):

```
// Byte0: x+1=0x80 x-1=0x40 x+9=0x20 x-9=0x10  y-9=0x08 y+9=0x04 y-1=0x02 y+1=0x01
```

and the tables that follow confirm it: `X_WEIGHTS` (lines 12–18) assigns X
to `0x80`/`0x40`/`0x20`/`0x10` in every byte — **the high nibble** — while
`Y_WEIGHTS` (lines 19–25) assigns Y to `0x08`/`0x04`/`0x02`/`0x01` — **the low
nibble**. This is the exact opposite of both TurtleStitch's convention and
the consensus the verdict memo already established. **The fix recommended
in `docs/dst-axis-verdict-2026-07-31.md` §4 has not been applied as of this
checkout.**

The memo's second bug is also still present. `src/dst.js` line 67
(`else if (flag === "color") bytes[2] |= 0x40;`) combined with the
always-set `bytes[2] |= 0x03` on line 65 produces `0x43` for a color-change
record — not `0xC3`. TurtleStitch's own color-change emission
(`embroidGeometry.js` lines 1067–1070, and identically in `embroider.js`
lines 346–350) writes a dedicated, always-zero-movement three-byte record
`0x00, 0x00, 0xC3` for every color change — an independent structural
confirmation of both the correct control byte *and* the convention that a
color change is its own zero-delta record, not a flag folded onto whatever
movement happened to be pending. EMB-Bot's `encodeDST` (lines 176, 191)
folds the color flag onto the same record as any pending `dx,dy` movement
rather than emitting a dedicated zero-delta record first — a second,
smaller structural divergence from the pattern both TurtleStitch and the
verdict memo's four other sources use.

**Actionable:** this is not a new finding so much as fresh, independent,
free evidence that the already-identified `src/dst.js` fix is real, still
unshipped, and now confirmed by a sixth unrelated source. If Kent wants
another data point before prioritizing the fix, this is it — TurtleStitch
costs nothing to cite since it was already being read for this task.

---

## 2. Oversized-move splitting — TurtleStitch preserves stitch/jump state across the split; EMB-Bot's fallback path does not

**What TurtleStitch does.** When a single delta exceeds the Tajima
per-record limit, `encodeTajimaStitch` is called `dsteps` times in a loop
(`embroidGeometry.js` lines 1088–1113; identically in `embroider.js` lines
377–411 and `stitchcode/turtleShepherd.js` lines 790–826), and **every one
of those sub-calls passes the same `jump` flag** the original move had —
`encodeTajimaStitch(Math.round((x1-x0)/dsteps), Math.round((y1-y0)/dsteps), jump)`.
A long running stitch splits into several needle-down sub-stitches; a long
jump splits into several needle-up sub-jumps. The split is also evenly
divided (`dsteps = Math.abs(dmax / 121)`, each substep length
`(x1-x0)/dsteps` with the remainder folded into the final substep) rather
than repeatedly clamped-and-subtracted.

**What EMB-Bot does.** `src/dst.js`'s `encodeDST` (lines 176–193) handles a
move whose `dx`/`dy` exceeds `MAX_DELTA` (121) with its own comment stating
the intent plainly: `// Emit intermediate jump records for oversized moves.`
(line 178) — the `while` loop at lines 181–189 unconditionally emits every
intermediate sub-record with the `"jump"` flag, regardless of whether the
original move was a `"stitch"`, `"color"`, or `"jump"`; only the final
leftover sub-record (line 191) carries the move's real `flag`. Splitting is
also clamp-and-subtract (`clampStep`, lines 113–117) rather than evenly
divided, so an oversized move splits into `⌈|delta|/121⌉` full-121 steps
plus one short remainder step, not `⌈|delta|/121⌉` even steps.

**Is this a real gap?** Narrower than it looks. EMB-Bot's own stitch-length
ceiling (`digitizer/digitizer_core/machine.py` line 20, `MAX_STITCH_MM =
12.1`) is designed to keep every genuine "stitch"-type move under the
121-unit Tajima limit before it ever reaches `dst.js` — the same 121/12.1mm
constant TurtleStitch's own `turtleShepherd.js` line 22
(`this.maxLength = 121`) uses for the identical reason, a clean
cross-confirmation, not a gap. So in ordinary operation this path should
only ever fire for `"jump"`/`"trim"` moves (which legitimately should stay
jumps) — `dst.js`'s own `splitTrim` (lines 122–137) already handles trims
correctly and evenly. **The risk is narrow but real**: any future code path
that hands `encodeDST` a genuine long `"stitch"`-type delta (an imported
design, a bug in an upstream emitter, a hand-built `StitchRun`) will get
silently converted to several needle-up jumps instead of several
needle-down running stitches for everything but the last segment — a
visible defect (a gap in stitching where a continuous line was intended)
that would be easy to miss in review since the final segment still sews.
**Suggested fix, low effort:** change line 184's hardcoded `"jump"` to the
move's actual `flag`, and switch the split from clamp-and-subtract to even
division (mirroring `splitTrim`'s own even-division approach one function
up) for consistency and marginally straighter long runs.

---

## 3. Fill-line travel routing / jump minimization — EMB-Bot already does this, and does it better

**What TurtleStitch does.** `embroidGeometry.js` implements a genuine
fill-line-to-fill-line travel router: `findRoute()` (lines 314–377) picks
the shorter of two directions around a closed boundary line between two
points on it (indexed by a `lineNo` scheme keyed to `Math.round(lineNo/10000)`
identifying which closed line a point belongs to); `moveToNextFilledline()`
(lines 380–434) uses `findRoute` to walk along the boundary from the end of
one fill line to the start of the next when `turtle.avoidJumps` is set,
falling back to a pen-up jump only when no route exists; `seekNextFilledline()`
(lines 438–572) picks which remaining fill line to visit next by nearest
routable distance rather than raw Euclidean distance. This is a real,
non-trivial travel-continuity algorithm — genuinely more than "just jump
between rows."

**What EMB-Bot already does — and this is the closer, better match.**
EMB-Bot's own `docs/fill-techniques-2026-08-01.md` (Law 44, lines 42–43,
and §1.2 line 72) already documents "our existing edge-walk
`travel_path(poly, ring, a, b, slack)`" as a settled, reused piece of the
engine. Reading it directly: `digitizer/digitizer_core/stage6_fill.py`
`travel_path()` (lines 451–496) does the same core thing TurtleStitch's
`findRoute`/`moveToNextFilledline` do — project both endpoints onto a
boundary ring (`ring.project(Point(a))`, line 472), take the shorter of
`forward`/`backward` arc distance (lines 474–482) — **but adds a safety
check TurtleStitch's version lacks**: it computes the actual route length
and rejects the route (falls back to a jump) if it exceeds
`max(_TRAVEL_DETOUR_FLOOR_MM, direct * _TRAVEL_DETOUR_FACTOR)` (lines
486–489). TurtleStitch's `moveToNextFilledline`, when `avoidJumps` is on,
has **no such cap** — the `for` loop at lines 420–422 walks the full
computed route unconditionally, however long, with no fallback to a shorter
jump. A route that happens to wind most of the way around a large or
convoluted boundary would be walked in full rather than abandoned for a
short jump — a genuine quality gap in TurtleStitch's version, not
EMB-Bot's.

Separately, EMB-Bot's stage 7 (`stage7_sequence.py` `_link_cover`, lines
250–331, and `_link_route`, lines 334–401) solves a strictly harder,
higher-level version of the same problem across whole shapes and colors: a
Dijkstra shortest-path search over a visibility graph, constrained to stay
inside geometry that will actually be covered by *either* already-laid
thread or a future color's coverage (not just "this shape's own boundary"),
with an explicit stitch-count budget (`_link_budget_mm`, lines 204–214,
citing "Law 62"). This has no TurtleStitch analogue at all — TurtleStitch's
router only ever considers a single closed fill-boundary line, never
routes under *other* shapes' future coverage. `docs/inkstitch-research-
2026-08-10.md` §5 (lines 562–578) already reached the same "nothing to
port" conclusion comparing EMB-Bot's chaining laws against Ink/Stitch's own
travel routing — this document extends that same conclusion to
TurtleStitch, which is simpler still.

**Verdict on this section: not much here.** EMB-Bot's own travel routing is
already a superset of what TurtleStitch does, plus a sanity check
TurtleStitch's own version would benefit from copying. No action item.

---

## 4. Curve/glyph flattening point density — a real, actionable gap

**What TurtleStitch does.** `embroidGeometry.js`'s Bezier flatteners —
`bezierCurvePoints()` (quadratic, lines 584–601), `cubicBezierCurvePoints()`
(lines 603–634), and `smoothCubicBezierCurvePoints()` (lines 636–648) — all
take a caller-supplied point count `number` and clamp it: `if (nb < 5) { nb
= 5; }` / `if (nb > 60) { nb = 60; }` (lines 586–587, 605–606). This is
**not** arc-length- or curvature-adaptive — the caller still has to choose
`nb` — but it treats segment count as a parameter with headroom up to 60
points per curve, not a fixed constant, and the block library exposes it as
a user-facing number input (`eg_get_bezierCurvePoints`/`eg_get_cubicBezierCurvePoints`,
lines 1279–1304) rather than hiding it.

**What EMB-Bot does.** `src/fonts.js`'s `pathToPolygons()` (lines 202–258)
flattens every cubic (`flattenCubic`, lines 178–188) and quadratic
(`flattenQuadratic`, lines 190–200) curve command in a glyph's outline with
`const segments = curveSegments || 8;` (line 206) — and **every actual call
site in the file passes the literal `8`**, not a computed value: lines 280,
286, 291, 315, and 320 (`pathToPolygons(glyphPath, 8)` /
`pathToPolygons(path, 8)`). `src/satinfont.js`'s `capUnitsOf()` (lines
136–151) and the rest of that module read glyph geometry as pre-built
`.cols[].railA`/`railB` point rings — confirming this flattening happens
**once, offline, at font-import/bake time**, not per-request at the size the
user actually picks. `src/fontbin.js` (`quantizeFont`/`encodeFontBin`,
lines 23–60) is the compact binary encoder for exactly that pre-baked
geometry. `tools/glyph-satin.mjs` line 19 confirms the bake resolution is a
fixed em-square size (`SIZE = +(process.env.SIZE || 400)`), and line 29
(`pathToPolygons(font.getPath(CH, 0, 0, SIZE), 8)`) confirms the segment
count is still the hardcoded `8` at bake time regardless of that size.
`src/satinfont.js` lines 115–120 and 449 (`u2px = (emMm / font.unitsPerEm) *
pxPerMm`) confirm the baked rings are then **geometrically scaled** to
whatever `emMm` the live app requests — the curve fidelity is never
re-derived at the final embroidered size.

**Why this matters for appearance.** An 8-segment cubic flattening of a
letterform's round bowl (the curve of an "O", "S", "C", "G", "Q", ampersand
loops, etc.) is a fixed-facet polygon approximation. Because the baked
rings are scaled, not re-flattened, the absolute chord-to-arc deviation
scales linearly with final output size: the same facet that's invisible on
a 15 mm cap-height letter becomes a measurably faceted curve on a jumbo
100 mm monogram or jacket-back letter — exactly the kind of large,
show-piece lettering job a "sagitta/faceting" defect is most visible on
(the same physics EMB-Bot's own `docs/fill-techniques-2026-08-01.md` Law 42
already derives for curved fill rows: `sagitta ≈ L²/8R`, worse at larger R
with the same segment count).

**Suggested fix.** Two independent levers, either one cheap: (a) make the
bake-time `curveSegments` argument scale with the bake `SIZE`/font
`unitsPerEm` (or simplest: just raise the hardcoded constant — TurtleStitch's
own ceiling of 60 is a reasonable target to benchmark against, since the
bake happens once and is reused at every size afterward, so the cost is
paid once per font-import, not per design); or (b) keep 8 for small-size
defaults but expose `curveSegments` as a real parameter threaded from the
bake tooling's `SIZE` env var, so a font baked at a larger nominal size (for
fonts specifically intended for large lettering) gets proportionally more
points. Either is a small, mechanical change confined to `src/fonts.js` and
the bake tooling in `tools/`, with no runtime cost change (the flattening
still happens once, offline).

---

## 5. Stitch-length window (121 units / 12.1 mm) — cross-confirmation, not a gap

TurtleStitch's `maxLength = 121` (`stitchcode/turtleShepherd.js` line 22)
and its stitch-splitting divisor `dsteps = Math.abs(dmax / 121)`
(`embroidGeometry.js` line 1088, `embroider.js` line 378,
`turtleShepherd.js` line 791) is the same Tajima-format-derived constant as
EMB-Bot's own `MAX_STITCH_MM = 12.1` (`digitizer/digitizer_core/machine.py`
line 20) and `MAX_DELTA = 121` (`src/dst.js` line 6) — 12.1 mm × 10 DST
units/mm = 121. Independent re-derivation of the same physical constant
from the same file format, nothing to change on either side.

---

## 6. Density warning heuristic — TurtleStitch's is cruder; EMB-Bot's is already principled

**What TurtleStitch does.** `stitchcode/turtleShepherd.js`'s density check
(`moveTo()`, lines 188–198) increments a counter keyed by
`Math.round(x) + "x" + Math.round(y)` every time a stitch endpoint lands
near a previously-visited integer-rounded pixel coordinate, and flags a
warning once any single bucket exceeds `this.densityMax = 15` (line 24;
surfaced via `getDensityWarningStr()`, lines 108–113). This is a coarse
proxy — it only catches exact-coordinate revisits at whatever the pixel
scale happens to be, not a real spatial neighborhood density measure, and
has no relationship to the fabric's actual thread-coverage physics.

**What EMB-Bot does.** `digitizer/digitizer_core/preflight.py`'s
`_density_findings()` (lines 917–959) measures the actual median advance
between same-rail/same-row penetrations across the emitted plan
(`_fill_row_advance_mm`/`_satin_rail_advance_mm`, referenced at lines
932–938) and compares it against the planner's own density *target* for
that fabric preset (`fill_target`/`satin_target`, lines 929–930),
flagging only when the realized density falls outside a
`[1/DENSITY_RATIO_MAX, DENSITY_RATIO_MAX]` band of intent (lines 943–958) —
a measured-output-vs-declared-intent check, not a coordinate-collision
proxy. `docs/inkstitch-research-2026-08-10.md` §9.2 (lines 747–776)
separately already compared EMB-Bot's aggregate density scoring against
Ink/Stitch's own `density_map.py` (a spatial STRtree neighbor-count
heatmap, itself more sophisticated than TurtleStitch's rounded-coordinate
counter) and found EMB-Bot's aggregation more sophisticated while flagging
Ink/Stitch's point-local *visualization* as the one worth borrowing —
TurtleStitch's version adds nothing beyond what that comparison already
covers. No action item.

---

## 7. Block-level fill/stitch library (`VectorAndFill.xml`, `embroidery_module.xml`) — no additional algorithm found

Both files are minified single-line Snap!-block XML (33.8 KB and 215.5 KB
respectively). Extracting block spec strings (`s="..."` attributes) and
list contents rather than rendering them in the Snap! editor surfaced the
following block-level vocabulary, all built as thin wrappers around
primitives already covered above (the `SnapExtensions.primitives.set(...)`
calls at the bottom of `embroidGeometry.js`, lines 1206–1319, are exactly
the primitives these blocks call into — confirmed by cross-referencing spec
names):

- `fill the area ... direction ... dencity ...`, `move from filled line...
  to filled line...`, `seek next filledline point...` — direct wrappers
  around `moveToNextFilledline`/`seekNextFilledline`/`findRoute`, already
  covered in §3.
- `zigzag from %start to %end in steps of %step size width %width turn
  %turn` — a reporter that offsets alternating points perpendicular to
  travel direction by `width/2` using `sin`/`cos` of heading ± 90°
  (extracted list content shows the `reportMonadic`/`sin`/`cos` construction
  directly). This is the standard "two parallel offset rails" zigzag
  construction — no different from what a satin column already is
  conceptually, and far simpler than EMB-Bot's medial-axis-derived satin
  rails (`src/satin.js`).
  `%pattern stitch by %step size width %width center %centered` — a
  dispatcher over a small named list of point-placement patterns (`zigzag`,
  `random position`, and others not fully enumerated from the minified
  XML) — a convenience wrapper, not a new fill algorithm.
- `cross-stitch from %start to %end in steps of %step size width %width` and
  `running stitch from %start to %end in steps of %step size` — simple
  per-segment X-pattern and straight-run converters. EMB-Bot's own
  `docs/fill-techniques-2026-08-01.md` §2 already scopes a materially more
  sophisticated cross-stitch/motif plan citing Ink/Stitch's anchor-graph
  Eulerian routing as the target — TurtleStitch's version is simpler than
  even that reference point, nothing to add.
- `resample %path to %points points` — arc-length point redistribution,
  conceptually identical to `src/satin.js`'s own `resampleChain()`
  (referenced at lines 62, 232–233, 257, 485, 727) — already present on the
  EMB-Bot side.

No contour/offset fill, no angle-optimization heuristic, no distinct
underlay construction, and no density-field fill was found anywhere in
either XML file. This matches the task brief's expectation that TurtleStitch
is education-first and confirms there's no hidden algorithm here worth a
deeper read.

---

## Not relevant / already superseded — checked, dead end, don't re-investigate

- **Tie / lock stitches.** Read `embroider.js`, `embroidGeometry.js`, and
  `turtleShepherd.js` in full — **no tie, lock-stitch, or thread-securing
  logic exists anywhere in TurtleStitch.** A thread simply starts and stops
  at jump boundaries. EMB-Bot already has a dedicated, well-reasoned system
  (`digitizer/digitizer_core/stitches.py` `tie_run()`, lines 185–209, and
  `stage7_sequence.py` `_apply_ties()`, lines 480–511, including the
  documented "tying twice doubles the lock into eight stitches" guard at
  lines 505–506). Nothing to learn from TurtleStitch here; EMB-Bot is
  unambiguously ahead.
- **Underlay.** No underlay concept (center-walk, contour, zigzag, or
  otherwise) appears anywhere in the three core TurtleStitch files or the
  grepped XML block libraries. EMB-Bot's underlay system
  (`stage7_sequence.py` lines 652–664, `_PHOTO_FILL_UNDERLAY`/
  `_PHOTO_SATIN_UNDERLAY` etc.) has no counterpart to compare against.
- **Pull/push compensation.** No compensation logic anywhere in
  TurtleStitch's stitch-generation path. EMB-Bot's `end_cutback`/
  `directional_comp` handling (`stage7_sequence.py` lines 674–680) has
  nothing to compare against.
- **Satin rail/zigzag construction quality.** TurtleStitch's only satin-like
  primitive is the block-level `zigzag`/`%pattern stitch` wrapper in §7 above
  — a plain perpendicular-offset two-point zigzag with no rail
  interpolation, no station spacing control, and no underlay. EMB-Bot's
  medial-axis satin engine (`src/satin.js`, e.g. `resampleChain`-driven
  rail/spine fitting at lines 225–257, 463–485, 727) is categorically more
  sophisticated; confirmed by direct read, not assumed.
- **Curve-flattening adaptivity.** Neither TurtleStitch's `nb` clamp
  (§4 above) nor anything else found in this codebase is arc-length- or
  curvature-adaptive — TurtleStitch's clamp is a caller-chosen constant
  with headroom, not an algorithm. Don't mistake §4's finding for "port
  TurtleStitch's adaptive flattening" — there isn't one to port; the
  actionable idea is narrower (raise/parameterize EMB-Bot's own constant).
- **DXF/SVG/PNG export paths** (`embroidGeometry.js` `toDXF()`, lines
  1136–1191; `turtleShepherd.js` `toSVG()`/`toPNG()`, lines 345–480) —
  read, confirmed to be plain line-segment exporters with no
  stitch-appearance-relevant logic beyond what's already covered by the DST
  path above.
- **`stitchcode/embroidery-library.xml`** — read (2 KB) — a thin manifest/
  index over the module files above, no independent content.
