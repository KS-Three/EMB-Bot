import { designToStrands, jumpTrimMarks } from "./strands.js";

// ---- Fabric contrast helpers (Slice 8 Task 2, B7) --------------------------
// Perceived brightness (ITU-R BT.709 relative-luminance weights), normalized
// to 0 (black) .. 1 (white). Pure + cheap on purpose: every render-path
// decision that needs to stay legible against an arbitrary fabric color
// (hoop outline, its dashed inset, the selection box + corner handles) reuses
// this SAME helper, so "what counts as dark" can never drift between them.
export function luminance(rgb) {
  const [r, g, b] = rgb;
  return (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255;
}

// Below 0.5 the fabric reads as "dark" -- callers should switch whatever
// chrome they're drawing to a light variant to stay legible on top of it.
export function isDark(rgb) {
  return luminance(rgb) < 0.5;
}

const DEFAULT_FABRIC_RGB = [235, 232, 223]; // matches project.js's defaultProject() fabricRgb

function rgbCss(rgb, alpha) {
  return alpha == null
    ? `rgb(${rgb[0]},${rgb[1]},${rgb[2]})`
    : `rgba(${rgb[0]},${rgb[1]},${rgb[2]},${alpha})`;
}

// A cheap procedural weave: a low-alpha crosshatch (both directions, every
// ~3px) in a tone darkened off the fabric color, drawn AFTER the bg fill but
// BEFORE strands. Skipped when the view is zoomed out enough that the lines
// would just read as noise (< 1.5 px/mm) rather than texture. Kept as a pure,
// spy-testable helper -- it only calls ctx methods, no state of its own.
export function weavePattern(ctx, w, h, rgb, pxPerMm) {
  if (pxPerMm < 1.5) return;
  const step = 3;
  const dr = Math.max(0, rgb[0] - 30);
  const dg = Math.max(0, rgb[1] - 30);
  const db = Math.max(0, rgb[2] - 30);
  ctx.save();
  ctx.strokeStyle = rgbCss([dr, dg, db], 0.08);
  ctx.lineWidth = 1;
  ctx.beginPath();
  for (let x = 0; x <= w; x += step) { ctx.moveTo(x, 0); ctx.lineTo(x, h); }
  for (let y = 0; y <= h; y += step) { ctx.moveTo(0, y); ctx.lineTo(w, y); }
  ctx.stroke();
  ctx.restore();
}

// ---- Realistic thread rendering -------------------------------------------
//
// A stitch is a short length of thread lying on cloth, and what makes a render
// read as embroidery rather than as a line drawing is that a thread is a
// CYLINDER lit from one side. Three things follow from that, and this section
// exists to do all three:
//
//   1. Across the thread, brightness runs dark edge -> lit core -> dark edge.
//      Drawn as concentric strokes of decreasing width, each stepped toward
//      the lit side, rather than one flat stroke.
//   2. Along the thread, sheen depends on DIRECTION. A cylinder throws its
//      strongest specular when it runs ACROSS the light and almost none when
//      it runs along it. This is the signature of real embroidery: two fill
//      areas of one thread colour look like different colours when their rows
//      run different ways, and a satin column flashes as it curves. The old
//      renderer offset every highlight by a fixed (-0.6,-0.9) px regardless of
//      the strand's direction, which is why its output read as outlined lines.
//   3. The thread has real WIDTH in mm, so coverage in the preview is the
//      coverage the machine will actually lay down.
//
// On (3) and honesty: THREAD_WIDTH_MM below is the nominal laid width of 40wt
// embroidery thread, the weight this project plans for. It is a DISPLAY
// constant — it scales pixels, never stitch geometry, and no planner value is
// derived from it.
//
// It is deliberately NOT inflated to make fills look solid, and not narrowed
// to make dense ones readable. Against the engine's fill row — 0.15 mm since
// Kent's density ruling of 2026-09-03 (`machine.FILL_ROW_MM`, PR #339; the
// browser engine's `fillRowMm`, PR #341) — 0.4 mm thread is coverage 2.67:
// rows overlap by more than half, which is what the professional's files
// measure (rows 0.14–0.17 mm apart under the same 40wt thread). Against the
// 0.4 mm satin spacing it is coverage 1.0, columns that just touch. A fill
// that is too open still looks too open here; a fill at the ruled row looks
// solid because it IS solid.
//
// The row was undecided and sew-out-gated until that ruling, and an earlier
// version of this comment argued the preview must not prejudge it. It is
// decided now, on the professional's measured files, and the rule for this
// constant is unchanged: it is the physical laid width, so what you see at
// zoom is the coverage the cloth gets — never a knob to make a density look
// better or worse than it is.
//
// One caveat this comment owes the reader: `lw` has a 1.2 px visibility floor
// (see renderRealistic). Below ~3 px/mm the floor, not this constant, sets the
// drawn width, so thread renders WIDER than physical and coverage reads high.
// The "what you see is what it lays" property holds when zoomed in, not on a
// thumbnail.
export const THREAD_WIDTH_MM = 0.4;

// Light from the upper left, in CANVAS space (y grows downward), normalized.
// One shared direction for the cylinder shading, the sheen falloff and the
// drop shadow, so they can never disagree about where the light is.
const LIGHT_X = -0.5547;
const LIGHT_Y = -0.8321;

// Sheen floor/ceiling as the thread turns from along-the-light to across it.
const SHEEN_MIN = 0.08;
const SHEEN_MAX = 0.52;

// Strands are bucketed by direction so that every strand in a bucket shares one
// shading profile and can be drawn as a SINGLE path per layer. That keeps the
// cost of the extra layers off the per-strand hot path: style changes go from
// O(strands x layers) to O(buckets x colours x layers), and the whole renderer
// ends up issuing FEWER stroke() calls than the old three-pass version, which
// began and stroked a fresh path per strand. Direction is taken modulo 180
// degrees — a thread looks the same drawn either way round.
const DIR_BUCKETS = 24;

// ---- What KIND of stitching a strand is ------------------------------------
//
// Real embroidery reads as embroidery largely because satin and tatami look
// nothing alike: satin is a tight ladder of parallel crossings with a sheen
// that runs along the column, tatami is sparse staggered rows that scatter the
// light instead of returning it. Until `design.runs` existed the browser had
// no way to tell them apart (see strands.js), so every kind was drawn with one
// profile and a satin border vanished into the fill it borders.
//
// A style is a set of MULTIPLIERS on the one cylinder model above, never a
// second shading system and never a colour of its own:
//
//   w       drawn width, as a fraction of the physical thread width
//   tone    darkening of the thread's own colour (a layer that lies UNDER
//           another is in its shadow; nothing here shifts hue)
//   sheen   specular strength (how much light the thread returns)
//   bead    length of the plied-sheen dash (short beads = broken sheen)
//   rim     darkening of the silhouette layer (edge definition)
//   shadow  drop-shadow offset and opacity (how proud of the cloth it sits)
//   z       draw order WITHIN one colour block: low sits under high
//
// Two rules this table is not allowed to break, and both are tested:
//
//   1. **No kind is ever drawn WIDER than the physical thread** (`w <= 1`).
//      THREAD_WIDTH_MM is a physical constant precisely so preview coverage is
//      the coverage the machine lays; a kind that inflated itself would make
//      an open fill look solid, which is the defect the anti-flattery guard
//      exists for. Kinds may sit UNDER that width (a lone running stitch does
//      sink into the weave, an underlay is buried) — never over it. The two
//      coverage-bearing kinds, satin and fill, stay at exactly 1.
//   2. **No style carries a colour.** Every stroke is derived from the
//      strand's own rgb, so the canvas remains something Kent can judge thread
//      colour by. Structure is shown with light and width, which is how a
//      photograph of real embroidery shows it.
const NEUTRAL_THREAD_STYLE = Object.freeze({
  key: "stitch|", w: 1, tone: 1, sheen: 1, bead: 1, rim: 1, shadow: 1, z: 2, raised: false,
});

// Satin: long taut parallel crossings, the shiniest thing on a finished patch.
// Brighter specular and a LONGER bead, because an unbroken column returns light
// in a continuous band instead of scattering it.
const SATIN_STYLE = { w: 1, tone: 1, sheen: 1.3, bead: 1.3, rim: 1, shadow: 1.1, z: 4 };
// Bean/running stitch: a single pass of thread with nothing beside it to hold
// it up, so it settles into the weave and reads as a thin line.
const RUN_STYLE = { w: 0.9, tone: 1, sheen: 0.9, bead: 0.7, rim: 1, shadow: 0.9, z: 3 };

// The per-kind table. `stitch` is the kindless strand every pre-`runs` design
// produces and is the NEUTRAL style by definition — that is what makes the
// no-runs fallback byte-identical rather than merely similar.
//
// The keys are the planner's OWN kind names (`digitizer_core/stitches.py`),
// not a vocabulary invented here, and that list is explicitly open: an
// unrecognised kind falls through to neutral and renders as ordinary
// stitching, which is what the adapter's contract asks a reader to do.
const KIND_STYLES = {
  satin:    SATIN_STYLE,
  // `border` is a KIND, not only a role: the planner's closed outline circuit
  // sewn as a satin column (stitches.py BORDER). It is satin, so it is drawn
  // as satin — a border that fell through to neutral here would have been
  // exactly the strand Kent cannot see.
  border:   SATIN_STYLE,
  // Tatami: short stitches, staggered penetrations, every row end breaking the
  // sheen. Dimmer, and a much SHORTER bead so each row reads as a separate
  // stitch rather than as part of a sheet — that broken-up specular is what
  // makes a fill look matte beside a satin column.
  fill:     { w: 1,    tone: 1,    sheen: 0.78, bead: 0.45, rim: 1, shadow: 0.9,  z: 3 },
  run:      RUN_STYLE,
  // `bean` is the light outline tier — a triple run over one ring. Same thin
  // single line as a run, which is what it physically is.
  bean:     RUN_STYLE,
  // Underlay: the layer BENEATH. Thin, dark (it is in the top layer's
  // shadow), almost no sheen (it is covered), and barely any shadow of its
  // own — it is sunk into the cloth, not sitting on it.
  underlay: { w: 0.66, tone: 0.78, sheen: 0.25, bead: 1,    rim: 1, shadow: 0.35, z: 1 },
  // A tie is a 2 mm lock bounce that the run it protects then sews over. It is
  // real thread, so it is drawn — quietly, because on the cloth it is buried.
  tie:      { w: 0.6,  tone: 0.85, sheen: 0.25, bead: 1,    rim: 1, shadow: 0.35, z: 1 },
  // Needle-down travel: real thread on the cloth, usually covered by what
  // comes after it, never a design element. De-emphasised the same honest way
  // underlay is — thin, dull, flat — so it stops competing with stitching.
  travel:   { w: 0.5,  tone: 0.88, sheen: 0.2,  bead: 1,    rim: 1, shadow: 0.3,  z: 0 },
};

// A border/edge cap is not a different THREAD, it is the same thread sitting
// PROUD of what it borders: sewn last, usually over its own underlay, standing
// above the fill it encloses. So it gets the cue a raised object gets in any
// photograph — a longer, darker drop shadow — plus a crisper silhouette and a
// little more specular, and it draws LAST within its colour block.
//
// That shadow is also why `raised` exists: a raised group's shadow is drawn
// immediately before the group itself, not in the global pre-pass, so it falls
// ON the fill that was drawn beneath it instead of being painted over by it.
//
// This is deliberately NOT a highlight colour. Kent judges thread colour off
// this canvas, so marking structure by recolouring thread would trade one
// unreadable canvas for a lying one.
const ROLE_STYLES = {
  border:   { sheen: 1.12, rim: 0.9, shadow: 1.7, z: 2, raised: true },
  edge_cap: { sheen: 1.12, rim: 0.9, shadow: 1.7, z: 2, raised: true },
};

// ...but a role does NOT raise a run that is underneath by nature. The border
// tier stamps `role: "border"` on its bridge TRAVEL runs too (they exist only
// to reach the ring — stage6_border.border_runs), and a connector that lifted
// off the cloth and cast a border's shadow would be advertising thread the
// design hides on purpose. Only the stitching that FORMS the border stands
// proud of what it borders.
const ROLE_EXEMPT_KINDS = { underlay: true, travel: true, tie: true };

const STYLE_CACHE = new Map([[NEUTRAL_THREAD_STYLE.key, NEUTRAL_THREAD_STYLE]]);

// Resolve (kind, role) to a style. Pure, memoized, and exported so the table
// above can be asserted directly — including the two rules it must not break.
// An unknown kind or role falls back to neutral rather than throwing: a kind
// this renderer has not been taught yet should cost distinction, not a blank
// canvas.
export function kindStyle(kind, role) {
  const k = kind || "stitch";
  const r = role || "";
  const key = k + "|" + r;
  const hit = STYLE_CACHE.get(key);
  if (hit) return hit;
  const base = KIND_STYLES[k] || NEUTRAL_THREAD_STYLE;
  const mod = ROLE_EXEMPT_KINDS[k] ? null : (ROLE_STYLES[r] || null);
  const st = Object.freeze({
    key,
    w: Math.min(1, base.w),
    tone: base.tone,
    sheen: base.sheen * (mod ? mod.sheen : 1),
    bead: base.bead,
    rim: base.rim * (mod ? mod.rim : 1),
    shadow: base.shadow * (mod ? mod.shadow : 1),
    z: base.z + (mod ? mod.z : 0),
    raised: !!(mod && mod.raised),
  });
  STYLE_CACHE.set(key, st);
  return st;
}

// The style for one strand, with an allocation-free fast path for the kindless
// strand a pre-`runs` design is made entirely of.
function styleForStrand(s) {
  if (!s.role && (!s.kind || s.kind === "stitch")) return NEUTRAL_THREAD_STYLE;
  return kindStyle(s.kind, s.role);
}

// A style's drawn width. `w === 1` returns `lw` ITSELF (x * 1 is exact in
// IEEE754, but returning the value skips the floor entirely) so the neutral
// path cannot drift by a floating-point hair from what it drew before.
function styleWidth(lw, st) {
  return st.w === 1 ? lw : Math.max(0.6, lw * st.w);
}

function shade(rgb, f) {
  return `rgb(${Math.round(rgb[0] * f)},${Math.round(rgb[1] * f)},${Math.round(rgb[2] * f)})`;
}

function lighten(rgb, f) {
  return `rgb(${Math.round(rgb[0] + (255 - rgb[0]) * f)},${Math.round(rgb[1] + (255 - rgb[1]) * f)},${Math.round(rgb[2] + (255 - rgb[2]) * f)})`;
}

// The cross-section of one lit thread, as concentric strokes drawn widest
// first. `angle` is the strand's direction in canvas space; `lw` its width in
// px. Returned offsets are ALONG THE NORMAL in px — the caller displaces each
// layer's endpoints by (nx,ny) * offset.
//
// Exported because it is the whole visual model in one pure function: given a
// direction and a colour it answers "what does this thread look like", with no
// canvas involved, so the direction-dependent sheen can be asserted directly.
// `style` (optional) is a kindStyle() — the multipliers that make satin,
// tatami, a bean run, underlay and travel look like different things. Omitting
// it is the NEUTRAL style, i.e. every multiplier 1, which is exactly the
// arithmetic this function did before kinds existed.
export function threadLayers(rgb, angle, lw, style) {
  const st = style || NEUTRAL_THREAD_STYLE;
  const dx = Math.cos(angle), dy = Math.sin(angle);
  const nx = -dy, ny = dx; // unit normal
  // How much the +normal side faces the light, and how much the thread runs
  // ALONG the light (axial ~ 1 -> pointing at the lamp -> almost no sheen).
  const k = nx * LIGHT_X + ny * LIGHT_Y;
  const axial = Math.abs(dx * LIGHT_X + dy * LIGHT_Y);
  // The kind's sheen multiplier rides on top of the direction term, so the
  // DIRECTIONAL signature survives it — a satin column still flashes as it
  // curves, it just returns more light than a tatami row does at every angle.
  // Clamped so no multiplier can drive the specular to white; the ceiling is
  // above SHEEN_MAX, so the neutral path never touches it.
  const sheen = Math.min(0.72, Math.max(0, (SHEEN_MIN + (SHEEN_MAX - SHEEN_MIN) * (1 - axial)) * st.sheen));
  // Where the specular sits across the thread: toward the lit edge, never on
  // it (a real cylinder's highlight is inboard of its silhouette).
  const hi = Math.max(-0.36, Math.min(0.36, 0.34 * k)) * lw;
  return [
    { width: lw, offset: 0, color: shade(rgb, 0.66 * st.tone * st.rim), dash: null },
    { width: lw * 0.78, offset: hi * 0.4, color: shade(rgb, 0.85 * st.tone), dash: null },
    { width: lw * 0.5, offset: hi * 0.75, color: shade(rgb, st.tone), dash: null },
    { width: lw * 0.28, offset: hi, color: lighten(rgb, sheen * 0.55), dash: null },
    // The narrowest specular is DASHED, phase-free: embroidery thread is
    // plied, so its sheen beads along the length instead of running as one
    // unbroken line. Cheap, and it is what stops a satin column from reading
    // as a plastic tube.
    //
    // Duty cycle is deliberately lopsided (~3:1 on:off). An even dash reads as
    // a DASHED LINE on any strand longer than a few thread-widths — a travel
    // run or a long fill row — instead of as modulated sheen on a continuous
    // thread. Mostly-on with short breaks reads as the latter at every length.
    //
    // `bead` scales BOTH halves of that duty cycle, keeping the ~3:1 ratio and
    // so the "modulated sheen, not a dashed line" reading, while changing how
    // often the sheen breaks. It is the cheapest honest difference between a
    // satin column (long unbroken beads) and a tatami row (short ones, because
    // every row end is a penetration that interrupts the light).
    { width: Math.max(0.5, lw * 0.13), offset: hi * 1.12, color: lighten(rgb, sheen), dash: [lw * 1.7 * st.bead, lw * 0.55 * st.bead] },
  ];
}

// The index of the layer carrying the thread's undarkened, unlightened colour.
// Exported so a test can assert every LOD rung includes it without hardcoding
// the stack's shape in two places.
export const TRUE_COLOUR_LAYER = 2;

// WHICH of threadLayers()' layers to draw, as explicit indices.
//
// This returns a SUBSET, not a prefix, and that is the whole point. Layer 2 is
// the only one painted in the thread's true colour (`shade(rgb, 1)`); layers 0
// and 1 are the darkened rim and its inboard step. A prefix ladder that took
// the first two layers therefore never painted the true colour at all — every
// zoomed-out preview and every design past the strand ceiling rendered about
// 15% dark, uniformly, and nothing caught it because no test compared a
// low-LOD render's colour against the thread's own. Found by review, 2026-08-25.
//
// So every rung includes layer 2. What gets dropped is sheen detail, in order
// of how much it costs versus how much it shows:
//   - the beaded specular (4) goes first
//   - then the broad specular (3) and the rim step (1)
//
// Two independent reasons to drop layers, and either one alone is enough:
//   - Thin thread (zoomed out): below ~1.6 px the narrow layers land inside
//     the same pixel as the wide ones, so they cost time to draw nothing.
//   - Big design: the per-strand path work is what scales, so a design past
//     these counts trades sheen detail for a preview that still repaints
//     while the user pans.
//
// Pure and exported so the ladder can be asserted directly — testing it
// through renderRealistic would mean building a 60k-stitch design per
// assertion, which is exactly the kind of test that starves a parallel suite.
export function threadLodLayers(lw, strandCount) {
  if (lw < 1.6 || strandCount > 60000) return [0, 2];
  if (lw < 2.6 || strandCount > 24000) return [0, 1, 2, 3];
  return [0, 1, 2, 3, 4];
}

// A layer COUNT, as renderRealistic's `threadLayers` option still accepts,
// resolved to a subset that obeys the same rule as the ladder above: the true
// colour is never what gets dropped.
//
// This used to be `[0,1,2,3,4].slice(0, n)` inline in drawThreads -- the same
// prefix bug as the LOD ladder's, just one layer down and missed when that one
// was fixed, because the ladder stopped producing counts while this public
// option went on accepting them. `{ threadLayers: 2 }` painted rgb(132,7,7)
// and rgb(170,9,9) for a rgb(200,10,10) thread: the true colour never appeared
// at all. Found by review, 2026-08-26.
//
// Counts outside 1..5 clamp rather than throw: this is a display hint from a
// caller tuning preview cost, and a bad number should cost detail, not a
// blank canvas.
export function layerSubsetForCount(n) {
  const c = Math.max(1, Math.min(5, Math.round(n)));
  if (c === 1) return [TRUE_COLOUR_LAYER];
  if (c === 2) return [0, TRUE_COLOUR_LAYER];
  if (c === 3) return [0, TRUE_COLOUR_LAYER, 3];
  if (c === 4) return [0, 1, TRUE_COLOUR_LAYER, 3];
  return [0, 1, 2, 3, 4];
}

// One black drop-shadow path for a set of strands that share a style. The
// neutral style reproduces the original single pre-pass EXACTLY: `* 1` is
// exact in IEEE754 and the alpha is rounded back onto 0.22, so the emitted
// strokeStyle string, lineWidth and offsets are bit-for-bit what they were.
function strokeShadow(ctx, items, SX, SY, lw, st) {
  if (!items.length) return;
  const slw = styleWidth(lw, st);
  const off = (slw * 0.18 + 0.5) * st.shadow;
  const sx = -LIGHT_X * off;
  const sy = -LIGHT_Y * off;
  // Opacity tracks how proud the thread sits, capped so a raised border casts
  // a deeper shadow without turning into a black outline.
  const alpha = Math.min(0.42, Math.round(0.22 * st.shadow * 1000) / 1000);
  ctx.strokeStyle = `rgba(0,0,0,${alpha})`;
  ctx.lineWidth = slw * 1.04;
  ctx.beginPath();
  for (const s of items) {
    ctx.moveTo(SX(s.x0) + sx, SY(s.y0) + sy);
    ctx.lineTo(SX(s.x1) + sx, SY(s.y1) + sy);
  }
  ctx.stroke();
}

// Draw every strand as a lit thread. Pure canvas work — no transform state of
// its own; the caller supplies SX/SY already carrying zoom/pan.
export function drawThreads(ctx, strands, SX, SY, lw, opts) {
  if (!strands.length) return;
  const o = opts || {};
  const flat = !!o.flat;
  ctx.lineCap = "round";
  ctx.lineJoin = "round";

  // FLAT view: one solid stroke per colour, at the same physical width, and
  // nothing else — no shadow, no cylinder shading, no sheen. This is the
  // schematic view, and it is not a cheaper approximation of the realistic one
  // so much as a different question: with the lighting gone, coverage and
  // stitch structure read as flat areas of colour, which is what you want while
  // judging whether a shape is filled rather than how it will look sewn.
  // Physical width is kept precisely so the coverage answer does not change
  // between the two views.
  if (flat) {
    // Grouped into consecutive-colour BLOCKS, not keyed by colour. A colour
    // that RECURS later in the sequence is a separate block, sewn on top of
    // whatever ran between; keying by colour alone merged it back into its
    // first appearance and quietly moved those strands earlier in z-order.
    // That made flat and realistic disagree about which colour covers which
    // -- on the one view you pick specifically to judge coverage. Same bug,
    // same fix, as reason 2 in the lit path's block grouping below (found by
    // review 2026-08-26, after the lit path had already been corrected).
    const blocks = [];
    let curFlat = null;
    let prevFlatRgb = null;
    for (const s of strands) {
      const rgb = s.rgb;
      if (!curFlat || !prevFlatRgb || rgb[0] !== prevFlatRgb[0] || rgb[1] !== prevFlatRgb[1] || rgb[2] !== prevFlatRgb[2]) {
        curFlat = { rgb, items: [] };
        blocks.push(curFlat);
      }
      prevFlatRgb = rgb;
      curFlat.items.push(s);
    }
    ctx.setLineDash([]);
    ctx.lineWidth = lw;
    for (const c of blocks) {
      ctx.strokeStyle = `rgb(${c.rgb[0]},${c.rgb[1]},${c.rgb[2]})`;
      ctx.beginPath();
      for (const s of c.items) {
        ctx.moveTo(SX(s.x0), SY(s.y0));
        ctx.lineTo(SX(s.x1), SY(s.y1));
      }
      ctx.stroke();
    }
    return;
  }

  // Drop shadow: one path for EVERY strand regardless of colour (it is all
  // black), offset away from the light so it agrees with the cylinder shading.
  //
  // Split by SHADOW CLASS once kinds are in play, because how proud of the
  // cloth a thread sits is part of what it is: an underlay is sunk into the
  // weave and casts almost nothing, a border stands above the fill it encloses
  // and casts the most. A design of kindless strands has exactly one class, so
  // this collapses to the single pre-pass it has always been.
  //
  // RAISED classes (border/edge cap) are skipped here on purpose and drawn
  // inside the block loop instead — a shadow cast onto a fill has to be
  // painted AFTER that fill, or the fill covers the very cue that says the
  // border sits on top of it.
  //
  // Splitting does mean two classes that overlap darken each other's shadow
  // slightly, where one path over the same crossing would not. That is the
  // correct direction (two layers of thread do cast more shadow than one) and
  // it cannot arise at all in the single-class fallback.
  const shadowGroups = new Map();
  for (const s of strands) {
    const st = styleForStrand(s);
    if (st.raised) continue;
    let g = shadowGroups.get(st.key);
    if (!g) { g = { style: st, items: [] }; shadowGroups.set(st.key, g); }
    g.items.push(s);
  }
  const shadowOrder = shadowGroups.size > 1
    ? Array.from(shadowGroups.values()).sort((a, b) => a.style.z - b.style.z)
    : Array.from(shadowGroups.values());
  for (const g of shadowOrder) strokeShadow(ctx, g.items, SX, SY, lw, g.style);

  // Group into colour BLOCKS first, then by direction inside each block.
  //
  // A block is a run of consecutive same-colour strands — i.e. what the machine
  // sews between two colour changes. Blocks matter for two reasons an earlier
  // version of this got wrong (both found by review, 2026-08-25):
  //
  //   1. Ordering has to be block-major. Drawing layer-major across ALL buckets
  //      put an earlier colour's layers 1..4 on top of a later colour's
  //      full-width layer 0, so wherever two colours overlap the UNDER colour
  //      bled through the over colour's edges — the exact opposite of the sew
  //      order this is supposed to reproduce.
  //   2. Keying buckets by colour alone merged a colour that RECURS later in
  //      the sequence back into its first block, silently moving those strands
  //      earlier in z-order.
  //
  // Inside one block, layer-major still holds, and still for its original
  // reason: a neighbouring strand's dark rim must not paint over this strand's
  // highlight and pock the surface with dark speckles. That hazard is
  // within-colour, so confining layer-major to a block keeps the benefit and
  // drops the cross-colour bug.
  //
  // Inside a block, strands are grouped by STYLE as well as direction, and the
  // style groups draw in `z` order: travel, underlay, fill/run, satin, then
  // anything raised. That is what puts an underlay visually UNDER the stitching
  // that covers it and a border on top of the fill it encloses, using the same
  // painter's-algorithm machinery the colour blocks already are — not a second
  // pass with its own idea of order.
  //
  // A design with no `runs` has exactly ONE style, so every block holds one
  // group and the iteration below is call-for-call the one this had before.
  const blocks = [];
  let curBlock = null;
  let prevRgb = null;
  for (const s of strands) {
    const rgb = s.rgb;
    if (!curBlock || !prevRgb || rgb[0] !== prevRgb[0] || rgb[1] !== prevRgb[1] || rgb[2] !== prevRgb[2]) {
      curBlock = { rgb, groups: new Map() };
      blocks.push(curBlock);
    }
    prevRgb = rgb;
    const st = styleForStrand(s);
    let grp = curBlock.groups.get(st.key);
    if (!grp) { grp = { style: st, buckets: new Map(), items: null }; curBlock.groups.set(st.key, grp); }
    // Raised groups keep a flat list too: their shadow is drawn as one path
    // right before they are, and that path needs the strands in sew order
    // rather than scattered across direction buckets.
    if (st.raised) { if (!grp.items) grp.items = []; grp.items.push(s); }
    const ang = Math.atan2(SY(s.y1) - SY(s.y0), SX(s.x1) - SX(s.x0));
    // Modulo PI, then quantized: a strand and its reverse share a bucket.
    let b = Math.floor((((ang % Math.PI) + Math.PI) % Math.PI) / (Math.PI / DIR_BUCKETS));
    if (b >= DIR_BUCKETS) b = DIR_BUCKETS - 1;
    let bucket = grp.buckets.get(b);
    if (!bucket) { bucket = { bucket: b, items: [] }; grp.buckets.set(b, bucket); }
    bucket.items.push(s);
  }

  // Indices preferred; a count goes through layerSubsetForCount so it can
  // never drop the true colour (see that function for the bug it replaces).
  const layerIdx = Array.isArray(o.layers)
    ? o.layers
    : (o.layers != null ? layerSubsetForCount(o.layers) : [0, 1, 2, 3, 4]);

  for (const blk of blocks) {
    const groups = blk.groups.size > 1
      ? Array.from(blk.groups.values()).sort((a, b) => a.style.z - b.style.z)
      : Array.from(blk.groups.values());
    for (const grp of groups) {
      const st = grp.style;
      const slw = styleWidth(lw, st);
      // A raised group casts its shadow here, onto whatever is already drawn.
      if (st.raised && grp.items) strokeShadow(ctx, grp.items, SX, SY, lw, st);
      const profiles = [];
      for (const b of grp.buckets.values()) {
        const angle = (b.bucket + 0.5) * (Math.PI / DIR_BUCKETS);
        profiles.push({ b, nx: -Math.sin(angle), ny: Math.cos(angle), layers: threadLayers(blk.rgb, angle, slw, st) });
      }
      for (const li of layerIdx) {
        for (const p of profiles) {
          const L = p.layers[li];
          if (!L) continue;
          ctx.strokeStyle = L.color;
          ctx.lineWidth = L.width;
          if (L.dash) ctx.setLineDash(L.dash); else ctx.setLineDash([]);
          const ox = p.nx * L.offset, oy = p.ny * L.offset;
          ctx.beginPath();
          for (const s of p.b.items) {
            ctx.moveTo(SX(s.x0) + ox, SY(s.y0) + oy);
            ctx.lineTo(SX(s.x1) + ox, SY(s.y1) + oy);
          }
          ctx.stroke();
        }
      }
    }
  }
  ctx.setLineDash([]);
}

// Design stitches are in DST units, whose Y axis points UP; canvas Y points
// DOWN. fitTransform therefore returns a transform whose TY NEGATES y
// (canvasY = oy - y*scale) — without that flip every glyph renders vertically
// mirrored (upside-down letters).
export function fitTransform(design, cw, ch, pad) {
  let minX = 1e9, minY = 1e9, maxX = -1e9, maxY = -1e9;
  for (const s of design.stitches) { if (s.type === "color" || s.type === "end") continue; if (s.x < minX) minX = s.x; if (s.x > maxX) maxX = s.x; if (s.y < minY) minY = s.y; if (s.y > maxY) maxY = s.y; }
  const w = Math.max(1, maxX - minX), h = Math.max(1, maxY - minY);
  const scale = Math.min((cw - 2 * pad) / w, (ch - 2 * pad) / h);
  const cx = (minX + maxX) / 2, cy = (minY + maxY) / 2;
  return { scale, ox: cw / 2 - cx * scale, oy: ch / 2 + cy * scale };
}

const MM_PER_INCH = 25.4; // inlined (no dependency on the engine global here)

// Maps HOOP mm-space (origin = hoop CENTER, +y UP — same convention as
// fitTransform, for the same DST-y-up reason) onto the canvas. Unlike
// fitTransform, this fits the full embroiderable hoop area — not just the
// design's bbox — into cw x ch, so the design renders at its true size and
// position within the garment/hoop frame instead of being stretched to fill
// the canvas.
// `hoop` is OPTIONAL and additive: the real hoop preset (`{ widthMm, heightMm }`
// from EMB.HOOPS) when the caller knows it. Omit it and every number below is
// exactly what it was before this parameter existed -- which is what keeps the
// design-fit callers and this module's own specs byte-identical.
//
// When it IS given, the fit spans the UNION of the placement box and the hoop,
// because the two are different rectangles and neither is reliably the larger:
// a 4x4 hoop (100 mm) is smaller than the left-chest box (101.6 mm), while a
// 6x10 hoop (160x250) dwarfs the hat-front box (127x57). Fitting only the
// placement box, which is what this did when its one caller passed a garment
// and called it a hoop, drew a 6x10 hoop off the edge of the canvas -- and
// fitting only the hoop would shrink the box the design is actually positioned
// against. The union costs a smaller design on a mismatched pair, and that
// shrink is the honest answer to "how much of this hoop am I using".
export function hoopTransform(garment, cw, ch, pad, hoop) {
  // The PLACEMENT BOX, in mm. Named `hoopWmm` for the callers and the specs
  // that already read it; it has never been a hoop. See `boxWmm` below for the
  // name this should have had.
  const hoopWmm = garment.widthIn * MM_PER_INCH;
  const hoopHmm = garment.heightIn * MM_PER_INCH;
  const realWmm = hoop ? hoop.widthMm : null;
  const realHmm = hoop ? hoop.heightMm : null;
  const fitW = realWmm ? Math.max(hoopWmm, realWmm) : hoopWmm;
  const fitH = realHmm ? Math.max(hoopHmm, realHmm) : hoopHmm;
  const scale = Math.min((cw - 2 * pad) / fitW, (ch - 2 * pad) / fitH);
  return { scale, ox: cw / 2, oy: ch / 2, hoopWmm, hoopHmm,
           boxWmm: hoopWmm, boxHmm: hoopHmm, realWmm, realHmm };
}

function roundRectPath(ctx, x, y, w, h, r) {
  const rr = Math.max(0, Math.min(r, w / 2, h / 2));
  ctx.beginPath();
  ctx.moveTo(x + rr, y);
  ctx.arcTo(x + w, y, x + w, y + h, rr);
  ctx.arcTo(x + w, y + h, x, y + h, rr);
  ctx.arcTo(x, y + h, x, y, rr);
  ctx.arcTo(x, y, x + w, y, rr);
  ctx.closePath();
}

// Draws the hoop ring as a rounded-rect outline, plus a dashed inset
// (~3mm) suggesting the safe stitching margin inside the hoop's clamp.
// `fabricRgb` (B7) picks the outline/inset tone: the original dark-on-light
// chrome when the fabric is light (or unspecified -- back-compat), a light
// variant when the fabric is dark enough that the dark chrome would wash out.
// `opts.inset: false` drops the dashed safe-margin ring, and `opts.dashed`
// strokes the outline itself dashed. Both exist to tell the two rectangles
// apart once they are BOTH on screen: the hoop keeps this function's original
// treatment -- solid ring plus the 3 mm margin, which is what the paragraph
// above describes and has always been about a hoop's clamp -- and the garment
// placement box, which merely says where on the shirt the design sits, becomes
// a dashed outline with no margin of its own. Defaults reproduce the original
// call exactly, so a caller that knows no hoop is unaffected.
export function drawHoopOutline(ctx, t, fabricRgb, opts) {
  const { inset = true, dashed = false } = opts || {};
  const dark = isDark(fabricRgb || DEFAULT_FABRIC_RGB);
  const outlineColor = dark ? "rgba(255,255,255,0.45)" : "rgba(60,50,40,0.35)";
  const insetColor = dark ? "rgba(255,255,255,0.35)" : "rgba(60,50,40,0.28)";
  const wPx = t.hoopWmm * t.scale, hPx = t.hoopHmm * t.scale;
  const x = t.ox - wPx / 2, y = t.oy - hPx / 2;
  const r = Math.min(16, wPx * 0.08, hPx * 0.08);
  ctx.save();
  ctx.lineWidth = 2;
  ctx.strokeStyle = outlineColor;
  if (dashed) ctx.setLineDash([7, 5]);
  roundRectPath(ctx, x, y, wPx, hPx, r);
  ctx.stroke();
  if (dashed) ctx.setLineDash([]);
  const insetPx = 3 * t.scale; // ~3mm stitch-limit margin
  const iw = wPx - 2 * insetPx, ih = hPx - 2 * insetPx;
  if (inset && iw > 0 && ih > 0) {
    ctx.setLineDash([5, 4]);
    ctx.lineWidth = 1;
    ctx.strokeStyle = insetColor;
    roundRectPath(ctx, x + insetPx, y + insetPx, iw, ih, Math.max(0, r - insetPx));
    ctx.stroke();
    ctx.setLineDash([]);
  }
  ctx.restore();
}

// opts:
//   fabric        CSS color string bg fill (FontSelect/exportPNG's existing
//                  contract -- stays working, B5).
//   fabricRgb      [r,g,b] bg fill; WINS over `fabric` when both given (B5).
//   colorOverride  existing strand-recolor contract -- unchanged.
//   weave          true -> draw weavePattern() over the bg fill (needs
//                  fabricRgb; a no-op without it).
//   dpr            device pixel ratio the canvas BITMAP is sized for; the
//                  caller sets canvas.width = cssWidth * dpr and this scales
//                  the context to match. Defaults to 1 (bitmap == CSS box),
//                  which is every caller but EmbroideryField. The returned
//                  transform is in CSS px at any dpr, so hit-testing and
//                  overlay code need no dpr of their own -- but a caller that
//                  reads canvas.width directly must divide by dpr.
//   view           { zoom, panX, panY } -- defaults to identity, so callers
//                  that never pass one (FontSelect thumbnails, exportPNG) get
//                  back exactly the pre-Slice-8 transform. B1 (BLOCKING): the
//                  returned contract is POST-VIEW -- scale = base.scale *
//                  view.zoom, and toCanvas already has pan baked in. zoom is
//                  applied about the CANVAS CENTER (so plain zoom-in-place
//                  keeps the hoop centered) and pan is then added in canvas
//                  px -- wheel-zoom-around-cursor is the caller's job (solve
//                  for the panX/panY that keep the cursor's mm-point fixed;
//                  see EmbroideryField's zoomBy()), not this function's.
export function renderRealistic(canvas, design, opts) {
  const o = opts || {};
  const ctx = canvas.getContext("2d");
  // `dpr` (default 1) lets a caller back the canvas with a bitmap denser than
  // its CSS box -- the Studio field does, so the preview is sharp on HiDPI
  // screens instead of drawn at half resolution and upscaled by the browser.
  // Everything below this line keeps working in CSS px: the base transform
  // does the scaling ONCE, so every px constant in here (the thread-width
  // floor, the trim-marker radius, `pad`) still means the same physical size
  // it always did. dpr === 1 skips setTransform entirely, which is what keeps
  // every other caller -- and the ctx doubles in the specs, which have no
  // setTransform -- behaving exactly as before.
  const dpr = o.dpr > 0 ? o.dpr : 1;
  if (dpr !== 1) ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  const cw = canvas.width / dpr, ch = canvas.height / dpr;
  const view = o.view || { zoom: 1, panX: 0, panY: 0 };
  const zoom = view.zoom || 1;
  const panX = view.panX || 0;
  const panY = view.panY || 0;

  ctx.fillStyle = o.fabricRgb ? rgbCss(o.fabricRgb) : (o.fabric || "#e9e6df");
  ctx.fillRect(0, 0, cw, ch);

  const hooped = !!(o.hoop && o.hoop.garment);
  let t, TX0, TY0, pxPerMm0;

  if (hooped) {
    t = hoopTransform(o.hoop.garment, cw, ch, o.pad || 24, o.hoop.hoop);
    TX0 = (xMm) => t.ox + xMm * t.scale;
    TY0 = (yMm) => t.oy - yMm * t.scale; // Y-flip: hoop mm y-up -> canvas y-down
    pxPerMm0 = t.scale;
  } else {
    t = fitTransform(design, cw, ch, o.pad || 24);
    TX0 = (x) => t.ox + x * t.scale;
    TY0 = (y) => t.oy - y * t.scale; // Y-flip: DST y-up -> canvas y-down
    pxPerMm0 = t.scale * 10; // design-fit's scale is px per DST unit (0.1mm)
  }

  // Post-view transform (B1): zoom about the canvas center, then translate by
  // pan (both in canvas-px). With the default identity view (zoom=1,
  // panX=panY=0) this reduces to exactly TX0/TY0 -- unchanged behavior for
  // every caller that doesn't pass `view`.
  const ccx = cw / 2, ccy = ch / 2;
  const TX = (v) => ccx + (TX0(v) - ccx) * zoom + panX;
  const TY = (v) => ccy + (TY0(v) - ccy) * zoom + panY;
  const pxPerMm = pxPerMm0 * zoom;

  if (o.weave && o.fabricRgb) weavePattern(ctx, cw, ch, o.fabricRgb, pxPerMm);
  if (hooped) {
    // t.ox/t.oy run through the SAME TX/TY used for strands below, so the
    // outline is always drawn at the current view's scale/position -- one
    // shared transform, not a second parallel calculation (B4).
    const viewedT = { scale: pxPerMm, ox: TX(0), oy: TY(0), hoopWmm: t.hoopWmm, hoopHmm: t.hoopHmm };
    if (t.realWmm) {
      // The real hoop FIRST, so the placement box reads as sitting inside it
      // rather than the other way round -- and so a caller that passes no hoop
      // leaves this module's stroke order, which one spec asserts by index,
      // exactly as it was.
      drawHoopOutline(ctx, { ...viewedT, hoopWmm: t.realWmm, hoopHmm: t.realHmm },
                      o.fabricRgb);
      drawHoopOutline(ctx, viewedT, o.fabricRgb, { inset: false, dashed: true });
    } else {
      drawHoopOutline(ctx, viewedT, o.fabricRgb);
    }
  }

  // Strand coordinates come straight from design.stitches, i.e. DST units
  // (0.1mm each). fitTransform's scale already absorbs that (it's computed
  // from the same raw units), so the design-fit path can feed them to TX/TY
  // untouched. hoopTransform's scale is px-per-mm though, so in hoop mode we
  // must convert DST units -> mm (/10) before applying it.
  const SX = hooped ? (x) => TX(x / 10) : TX;
  const SY = hooped ? (y) => TY(y / 10) : TY;

  let strands = designToStrands(design, { colorOverride: o.colorOverride });
  // Simulator support: draw only the first `limitStrands` segments (sew
  // order IS strand order — designToStrands walks design.stitches start to
  // finish), so scrubbing/playing renders the design exactly as the machine
  // would sew it. undefined/null = draw everything (every existing caller).
  if (o.limitStrands != null) strands = strands.slice(0, Math.max(0, o.limitStrands));
  // Thread width is PHYSICAL (THREAD_WIDTH_MM), with a px floor so a thread
  // stays visible in the small font/template previews where pxPerMm is tiny.
  const threadMm = o.threadWidthMm != null ? o.threadWidthMm : THREAD_WIDTH_MM;
  const lw = Math.max(1.2, threadMm * pxPerMm);
  const layers = o.threadLayers != null ? o.threadLayers : threadLodLayers(lw, strands.length);
  // threadStyle: "realistic" (default, every existing caller) | "flat".
  drawThreads(ctx, strands, SX, SY, lw, { layers, flat: o.threadStyle === "flat" });

  // Diagnostic overlays (drawn ON TOP of thread so they're never buried):
  // showJumps -> dashed travel lines; showTrims -> an X marker per trim.
  if (o.showJumps || o.showTrims) {
    const marks = jumpTrimMarks(design);
    ctx.save();
    if (o.showJumps) {
      ctx.strokeStyle = "rgba(37,99,235,0.8)";
      ctx.lineWidth = 1;
      ctx.setLineDash([4, 3]);
      for (const j of marks.jumps) {
        ctx.beginPath();
        ctx.moveTo(SX(j.x0), SY(j.y0));
        ctx.lineTo(SX(j.x1), SY(j.y1));
        ctx.stroke();
      }
      ctx.setLineDash([]);
    }
    if (o.showTrims) {
      ctx.strokeStyle = "rgba(220,38,38,0.9)";
      ctx.lineWidth = 1.5;
      const r = 4;
      for (const t of marks.trims) {
        const cx2 = SX(t.x), cy2 = SY(t.y);
        ctx.beginPath();
        ctx.moveTo(cx2 - r, cy2 - r);
        ctx.lineTo(cx2 + r, cy2 + r);
        ctx.moveTo(cx2 - r, cy2 + r);
        ctx.lineTo(cx2 + r, cy2 - r);
        ctx.stroke();
      }
    }
    ctx.restore();
  }

  if (!hooped) return undefined;

  let minX = 1e9, minY = 1e9, maxX = -1e9, maxY = -1e9, any = false;
  for (const s of design.stitches) {
    if (s.type === "color" || s.type === "end") continue;
    any = true;
    if (s.x < minX) minX = s.x; if (s.x > maxX) maxX = s.x;
    if (s.y < minY) minY = s.y; if (s.y > maxY) maxY = s.y;
  }
  const designBBoxMm = any ? { x0: minX / 10, y0: minY / 10, x1: maxX / 10, y1: maxY / 10 } : null;
  return {
    // POST-VIEW contract (B1): toCanvas already bakes in pan; scale already
    // has view.zoom multiplied in (pxPerMm === t.scale * zoom for the hoop
    // path) -- interact.js's px<->mm math (designRectPx/hitTest/dragResize/
    // dragMove/clampOffsets) consumes this as-is, with ZERO changes needed.
    toCanvas: (xMm, yMm) => ({ x: TX(xMm), y: TY(yMm) }),
    scale: pxPerMm,
    designBBoxMm,
  };
}
