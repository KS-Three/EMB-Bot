import { designToStrands, jumpTrimMarks, shrinkSatinStrands } from "./strands.js";

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
//   crown   how far the lit layers pull back from the two needle holes (see
//           CROWN_INSET below); 0 draws every layer end to end
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
  key: "stitch|", w: 1, tone: 1, sheen: 1, bead: 1, rim: 1, shadow: 1, z: 2, crown: 1, raised: false,
});

// Satin: long taut parallel crossings, the shiniest thing on a finished patch.
// Brighter specular and a LONGER bead, because an unbroken column returns light
// in a continuous band instead of scattering it.
const SATIN_STYLE = { w: 1, tone: 1, sheen: 1.3, bead: 1.3, rim: 1, shadow: 1.1, z: 4, crown: 1 };
// Bean/running stitch: a single pass of thread with nothing beside it to hold
// it up, so it settles into the weave and reads as a thin line — visibly
// thinner than a satin column's crossings (2026-11-07: at 0.9 a bean outline
// read as heavy as the column beside it), and duller, since a lone thread
// sunk into the weave returns less light than a packed column does.
const RUN_STYLE = { w: 0.7, tone: 0.95, sheen: 0.75, bead: 0.7, rim: 1, shadow: 0.8, z: 3, crown: 0.6 };

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
  fill:     { w: 1,    tone: 1,    sheen: 0.78, bead: 0.45, rim: 1, shadow: 0.9,  z: 3, crown: 1 },
  run:      RUN_STYLE,
  // `bean` is the light outline tier — a triple run over one ring. Same thin
  // single line as a run, which is what it physically is.
  bean:     RUN_STYLE,
  // Underlay: the layer BENEATH. Thin, dark (it is in the top layer's
  // shadow), almost no sheen (it is covered), and barely any shadow of its
  // own — it is sunk into the cloth, not sitting on it.
  underlay: { w: 0.66, tone: 0.78, sheen: 0.25, bead: 1,    rim: 1, shadow: 0.35, z: 1, crown: 0.5 },
  // A tie is a 2 mm lock bounce that the run it protects then sews over. It is
  // real thread, so it is drawn — quietly, because on the cloth it is buried.
  tie:      { w: 0.6,  tone: 0.85, sheen: 0.25, bead: 1,    rim: 1, shadow: 0.35, z: 1, crown: 0.5 },
  // Needle-down travel: real thread on the cloth, usually covered by what
  // comes after it, never a design element. De-emphasised the same honest way
  // underlay is — thin, dull, flat — so it stops competing with stitching.
  travel:   { w: 0.5,  tone: 0.88, sheen: 0.2,  bead: 1,    rim: 1, shadow: 0.3,  z: 0, crown: 0.4 },
};

// A border/edge cap is not a different THREAD, it is the same thread sitting
// PROUD of what it borders: sewn last, usually over its own underlay, standing
// above the fill it encloses. So it gets the cue a raised object gets in any
// photograph — a longer, darker drop shadow — plus a crisper silhouette and a
// little more specular, and it draws LAST within its colour block.
//
// That shadow is also why `raised` exists: a raised group's shadow is drawn
// immediately before the group itself, not in its block's shadow pass, so it
// falls ON the same-colour fill drawn beneath it instead of being painted over
// by it.
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
    crown: base.crown != null ? base.crown : 1,
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
  // `inset`: how far each layer pulls back from BOTH ends, as a fraction of
  // the strand's length (see CROWN_INSET). The silhouette (0) always runs
  // hole to hole.
  const c = st.crown != null ? st.crown : 1;
  return [
    { width: lw, offset: 0, color: shade(rgb, 0.66 * st.tone * st.rim), dash: null, inset: 0 },
    { width: lw * 0.78, offset: hi * 0.4, color: shade(rgb, 0.85 * st.tone), dash: null, inset: CROWN_INSET[1] * c },
    { width: lw * 0.5, offset: hi * 0.75, color: shade(rgb, st.tone), dash: null, inset: CROWN_INSET[2] * c },
    { width: lw * 0.28, offset: hi, color: lighten(rgb, sheen * 0.55), dash: null, inset: CROWN_INSET[3] * c },
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
    { width: Math.max(0.5, lw * 0.13), offset: hi * 1.12, color: lighten(rgb, sheen), dash: [lw * 1.7 * st.bead, lw * 0.55 * st.bead], inset: CROWN_INSET[4] * c },
  ];
}

// The CROWN of a stitch, per layer, as the fraction of the strand's length
// each layer gives up at EACH end.
//
// A stitch is not a straight cylinder lying on the cloth: it leaves one needle
// hole, rises over the stitching around it and dives into the next hole. Its
// middle stands highest and catches the light; its two ends are pulled down
// into the cloth and sit in shade. Drawing every layer end to end (what this
// renderer did until 2026-11-07) painted the specular right up to the needle
// hole, so:
//
//   - a satin column read as a stack of uniformly lit rods, with no lit band
//     down its middle and no darker edge where the crossings dive in, and
//   - a tatami fill read as long continuous lines, because consecutive
//     collinear stitches merged into one unbroken highlight, hiding the
//     staggered penetrations that ARE tatami's texture.
//
// Pulling the lit layers back from both holes fixes both with one rule: the
// highlight sits on the middle of every stitch (a band down a satin column,
// following the crossing angle as the column turns) and breaks at every
// penetration (the brick stagger of a fill). It changes only where each layer
// starts and stops along its own strand — no extra path, no extra stroke(),
// and the silhouette (0) still runs hole to hole, so coverage is untouched.
// A style's `crown` scales the row (thin runs and buried underlay crown less).
// A look, not a measurement: nothing here is calibrated against cloth.
const CROWN_INSET = [0, 0.04, 0.1, 0.22, 0.28];

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

// One black drop-shadow path for a set of strands that share a style. `items`
// are drawThreads' projected records ({ s, X0, Y0, X1, Y1 }, canvas px). The
// neutral style reproduces the original single pre-pass EXACTLY: `* 1` is
// exact in IEEE754 and the alpha is rounded back onto 0.22, so the emitted
// strokeStyle string, lineWidth and offsets are bit-for-bit what they were.
//
// `soft` (optional, from renderRealistic) turns on the SOFT shadow once the
// thread is wide enough on screen for an edge to read as hard (see
// softShadowFactor).
function strokeShadow(ctx, items, lw, st, soft) {
  if (!items.length) return;
  const slw = styleWidth(lw, st);
  const off = (slw * 0.18 + 0.5) * st.shadow;
  const sx = -LIGHT_X * off;
  const sy = -LIGHT_Y * off;
  // Opacity tracks how proud the thread sits, capped so a raised border casts
  // a deeper shadow without turning into a black outline.
  const alpha = Math.min(0.42, Math.round(0.22 * st.shadow * 1000) / 1000);
  const k = soft ? softShadowFactor(slw) : 1;
  if (k > 1) {
    const scratch = soft.scratch();
    if (scratch) { softShadow(ctx, scratch, soft, items, sx, sy, slw * 1.04, alpha, k); return; }
  }
  ctx.strokeStyle = `rgba(0,0,0,${alpha})`;
  ctx.lineWidth = slw * 1.04;
  ctx.beginPath();
  for (const p of items) {
    ctx.moveTo(p.X0 + sx, p.Y0 + sy);
    ctx.lineTo(p.X1 + sx, p.Y1 + sy);
  }
  ctx.stroke();
}

// ---- The soft contact shadow (2026-11-07) ---------------------------------
//
// Thread lying on thread does not cast a hard-edged shadow: the strand is
// round and sits close to what it covers, so its shadow fades out over about
// a third of its own width. The hard shadow above reads fine while a thread
// is two or three pixels wide, but zoomed in its razor edge is what makes
// lettering over a fill look like a paper cut-out laid on top.
//
// A blur filter or `shadowBlur` is the obvious way, and it is the expensive
// one: both blur the whole layer at full resolution, per colour block. This
// gets the soft edge for LESS than the hard shadow costs: the shadow path is
// stroked at 1/k resolution into a scratch canvas, then drawn back k times
// larger with bilinear smoothing. Upscaling is what softens it (the edge
// ramps over about k device px), and the stroke rasterizes 1/k^2 of the
// pixels. Strands whose shadow lands wholly off the canvas are dropped from
// the path; that would move other pixels in a full-resolution stroke (see the
// off-screen skip in drawThreads), but this one is blurred by design, so it
// costs nothing that can be seen.
//
// k grows with the drawn width (one step per 3 px of thread), from 2 at 6 px
// up to SOFT_SHADOW_MAX_K. Below 6 px it is 1 and the hard shadow is drawn
// exactly as before, so a fit-zoom render is untouched by this.
// A look, not a measurement: nothing here is calibrated against cloth.
const SOFT_SHADOW_MAX_K = 6;

export function softShadowFactor(slw) {
  const k = Math.floor(slw / 3);
  return k < 2 ? 1 : Math.min(SOFT_SHADOW_MAX_K, k);
}

function softShadow(ctx, scratch, soft, items, sx, sy, width, alpha, k) {
  const { dpr, cw, ch } = soft;
  const m = width + (2 * k) / dpr; // CSS px past an endpoint the result can reach
  let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  const kept = [];
  for (const p of items) {
    const ax = p.X0 + sx, ay = p.Y0 + sy, bx = p.X1 + sx, by = p.Y1 + sy;
    if ((ax < -m && bx < -m) || (ax > cw + m && bx > cw + m) || (ay < -m && by < -m) || (ay > ch + m && by > ch + m)) continue;
    kept.push(p);
    if (ax < x0) x0 = ax; if (bx < x0) x0 = bx; if (ax > x1) x1 = ax; if (bx > x1) x1 = bx;
    if (ay < y0) y0 = ay; if (by < y0) y0 = by; if (ay > y1) y1 = ay; if (by > y1) y1 = by;
  }
  if (!kept.length) return;
  // The region it touches, in scratch px (CSS px * dpr / k).
  const f = dpr / k;
  const X0 = Math.max(0, Math.floor((x0 - m) * f)), Y0 = Math.max(0, Math.floor((y0 - m) * f));
  const X1 = Math.min(scratch.width, Math.ceil((x1 + m) * f)), Y1 = Math.min(scratch.height, Math.ceil((y1 + m) * f));
  if (X1 <= X0 || Y1 <= Y0) return;
  const s = scratch.getContext("2d");
  s.setTransform(1, 0, 0, 1, 0, 0);
  // Cleared two texels wider than what is drawn back: bilinear sampling at
  // the edge of a source rect may read just past it, and what lies there is
  // an earlier block's shadow (a dark seam, seen in the first render).
  s.clearRect(X0 - 2, Y0 - 2, X1 - X0 + 4, Y1 - Y0 + 4);
  s.setTransform(f, 0, 0, f, 0, 0);
  s.lineCap = "round";
  s.lineJoin = "round";
  s.strokeStyle = "#000";
  s.lineWidth = width;
  s.beginPath();
  for (const p of kept) {
    s.moveTo(p.X0 + sx, p.Y0 + sy);
    s.lineTo(p.X1 + sx, p.Y1 + sy);
  }
  s.stroke();
  ctx.save();
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.globalAlpha = alpha;
  ctx.imageSmoothingEnabled = true;
  ctx.imageSmoothingQuality = "low";
  ctx.drawImage(scratch, X0, Y0, X1 - X0, Y1 - Y0, X0 * k, Y0 * k, (X1 - X0) * k, (Y1 - Y0) * k);
  ctx.restore();
}

// Draw every strand as a lit thread. Pure canvas work — no transform state of
// its own; the caller supplies SX/SY already carrying zoom/pan.
export function drawThreads(ctx, strands, SX, SY, lw, opts) {
  if (!strands.length) return;
  const o = opts || {};
  const flat = !!o.flat;
  ctx.lineCap = "round";
  ctx.lineJoin = "round";

  // Each strand is projected to canvas px ONCE, here, instead of once per
  // layer (the lit path strokes every strand five or six times). The values
  // are the same SX/SY results, so every coordinate handed to the canvas is
  // bit-for-bit what it was.
  //
  // `o.clip` ({ x0, y0, x1, y1 }, canvas px) culls a strand whose whole drawn
  // footprint lies outside that box -- in the FLAT view only. Measured
  // 2026-10-08 on a 22.8k-stitch design: ~80% of a zoom/pan frame is the
  // browser rasterizing stroke paths, most of them off-screen once zoomed
  // in. The margin (2 lw + 4 px) is wider than anything a strand paints past
  // its endpoints. The cull happens AFTER a strand is assigned to its colour
  // block, never before: dropping it earlier could merge the two blocks
  // either side of an all-off-screen colour, which changes z-order.
  //
  // The LIT view is not culled per strand: the same cull there changed
  // pixels, because the rasterizer anti-aliases a path by its whole geometry
  // (see the off-screen skip below, which drops only whole lit buckets).
  // No clip, no culling (every caller but renderRealistic, and every spec).
  const clip = flat && o.clip ? o.clip : null;
  const m = 2 * lw + 4;
  const cx0 = clip ? clip.x0 - m : 0, cy0 = clip ? clip.y0 - m : 0;
  const cx1 = clip ? clip.x1 + m : 0, cy1 = clip ? clip.y1 + m : 0;
  const project = (s) => {
    const X0 = SX(s.x0), Y0 = SY(s.y0), X1 = SX(s.x1), Y1 = SY(s.y1);
    const off = !!clip && ((X0 < cx0 && X1 < cx0) || (X0 > cx1 && X1 > cx1) || (Y0 < cy0 && Y1 < cy0) || (Y0 > cy1 && Y1 > cy1));
    return { s, X0, Y0, X1, Y1, off };
  };

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
      const p = project(s);
      if (!p.off) curFlat.items.push(p);
    }
    ctx.setLineDash([]);
    ctx.lineWidth = lw;
    for (const c of blocks) {
      if (!c.items.length) continue;
      ctx.strokeStyle = `rgb(${c.rgb[0]},${c.rgb[1]},${c.rgb[2]})`;
      ctx.beginPath();
      for (const p of c.items) {
        ctx.moveTo(p.X0, p.Y0);
        ctx.lineTo(p.X1, p.Y1);
      }
      ctx.stroke();
    }
    return;
  }

  // Drop shadow: black, offset away from the light so it agrees with the
  // cylinder shading, one path per colour BLOCK (below), drawn RIGHT BEFORE
  // the block that casts it.
  //
  // Per block, not one pre-pass under the whole design (2026-11-07). A
  // pre-pass put every shadow beneath every thread, so a later colour never
  // shaded the earlier one it lies on: lettering sewn over a fill, or a second
  // colour lapping a first, met it with a hard, shadowless edge, which is what
  // made overlaps read as flat cut-outs instead of thread lying on thread.
  // Drawn just before its block, a shadow lands on everything sewn before it
  // (the contact shadow) and is covered by the block itself.
  //
  // Per block rather than per style group on purpose, and measured: one path
  // per group (underlay, fill, satin each casting separately) cost the mixed
  // fixture +53% render time at fit zoom, because each alpha path is
  // rasterized over its own bounds and a block's groups share theirs. A raised
  // group (border, edge cap) still casts its own deeper shadow right before
  // it, as it always has. A single-colour design draws exactly ONE ordinary
  // shadow path, first, as it always has.
  const proj = strands.map(project);

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
  for (let i = 0; i < strands.length; i++) {
    const s = strands[i];
    const rgb = s.rgb;
    if (!curBlock || !prevRgb || rgb[0] !== prevRgb[0] || rgb[1] !== prevRgb[1] || rgb[2] !== prevRgb[2]) {
      curBlock = { rgb, groups: new Map() };
      blocks.push(curBlock);
    }
    prevRgb = rgb;
    const p = proj[i];
    const st = styleForStrand(s);
    let grp = curBlock.groups.get(st.key);
    if (!grp) { grp = { style: st, buckets: new Map(), items: [] }; curBlock.groups.set(st.key, grp); }
    // Every group keeps a flat list too, for the shadow paths (the block's
    // and a raised group's own), which need every strand once rather than
    // scattered across direction buckets.
    grp.items.push(p);
    const ang = Math.atan2(p.Y1 - p.Y0, p.X1 - p.X0);
    // Modulo PI, then quantized: a strand and its reverse share a bucket.
    let b = Math.floor((((ang % Math.PI) + Math.PI) % Math.PI) / (Math.PI / DIR_BUCKETS));
    if (b >= DIR_BUCKETS) b = DIR_BUCKETS - 1;
    let bucket = grp.buckets.get(b);
    if (!bucket) { bucket = { bucket: b, items: [], x0: Infinity, y0: Infinity, x1: -Infinity, y1: -Infinity }; grp.buckets.set(b, bucket); }
    bucket.items.push(p);
    if (p.X0 < bucket.x0) bucket.x0 = p.X0; if (p.X1 < bucket.x0) bucket.x0 = p.X1;
    if (p.X0 > bucket.x1) bucket.x1 = p.X0; if (p.X1 > bucket.x1) bucket.x1 = p.X1;
    if (p.Y0 < bucket.y0) bucket.y0 = p.Y0; if (p.Y1 < bucket.y0) bucket.y0 = p.Y1;
    if (p.Y0 > bucket.y1) bucket.y1 = p.Y0; if (p.Y1 > bucket.y1) bucket.y1 = p.Y1;
  }

  // Off-screen skip (LIT view, 2026-10-08), whole stroke() calls only. A
  // bucket whose every strand lies outside `o.clip` (canvas px) by more than
  // anything a layer paints past its endpoints (offset <= 0.41 lw, half-width
  // and round cap <= 0.5 lw; the margin is 2 lw + 4 px) touches no pixel, so
  // skipping it is pixel-exact by construction.
  //
  // It is deliberately NOT a per-strand cull. Chromium's rasterizer
  // anti-aliases a path according to the WHOLE path's geometry: one subpath
  // far off-canvas measurably moves the on-screen pixels of the rest of the
  // same stroke() (Chromium 1194, CPU and GPU canvas alike). Dropping strands
  // from a path that still draws therefore changed ~15k pixels at 5x zoom,
  // and even keeping the path's bounds intact left 28-55 pixels off by 1-2
  // levels. That is why PR #712's per-strand lit cull did not hold.
  const litClip = o.clip || null;
  const cm = 2 * lw + 4;
  const offClip = (b) => !!litClip && (b.x1 < litClip.x0 - cm || b.x0 > litClip.x1 + cm || b.y1 < litClip.y0 - cm || b.y0 > litClip.y1 + cm);

  // Indices preferred; a count goes through layerSubsetForCount so it can
  // never drop the true colour (see that function for the bug it replaces).
  const layerIdx = Array.isArray(o.layers)
    ? o.layers
    : (o.layers != null ? layerSubsetForCount(o.layers) : [0, 1, 2, 3, 4]);

  // The line dash in force. Every shadow is SOLID: until 2026-11-07 a shadow
  // set no dash of its own, so every block's contact shadow after the first
  // (and every raised border's) inherited the beaded specular's dash from the
  // last layer stroked before it, and was drawn as a dashed line. Reset only
  // when a dash is actually in force, so a render that never dashes issues
  // the calls it always did. Entry assumes solid, which every caller leaves.
  let dash = null;
  const solid = () => { if (dash) { ctx.setLineDash([]); dash = null; } };
  // renderRealistic's soft-shadow scratch (see softShadow), or none.
  const soft = o.softShadow || null;

  for (const blk of blocks) {
    const groups = blk.groups.size > 1
      ? Array.from(blk.groups.values()).sort((a, b) => a.style.z - b.style.z)
      : Array.from(blk.groups.values());
    // The block's contact shadow: ONE path for the block's stitching that is
    // neither raised (it casts its own, below) nor buried, at the strength of
    // its topmost such group (the stitching whose edge the shadow outlines),
    // drawn onto everything sewn before this block.
    //
    // BURIED kinds (z <= 1: travel, underlay, tie) are left out when the block
    // has anything else: merged into the top group's path they would cast at
    // fill strength instead of their own faint one, and wherever one is
    // exposed (a travel run across a hole the customer just opened) that
    // darkened bare fabric visibly — field-reshape-mode (e) caught it in CI,
    // 41 levels off the garment at a pixel inside the hole. Under the
    // stitching that covers them their faint shadow never showed anyway. A
    // block of buried kinds alone still casts at its own strength.
    let top = null, topBuried = null;
    for (const grp of groups) {
      if (grp.style.raised) continue;
      if (grp.style.z <= 1) topBuried = grp; else top = grp;
    }
    if (groups.length === 1 && (top || topBuried)) {
      solid();
      strokeShadow(ctx, (top || topBuried).items, lw, (top || topBuried).style, soft);
    } else if (top || topBuried) {
      const cast = top || topBuried;
      const items = [];
      for (const grp of groups) {
        if (grp.style.raised || (top && grp.style.z <= 1)) continue;
        for (const q of grp.items) items.push(q);
      }
      solid();
      strokeShadow(ctx, items, lw, cast.style, soft);
    }
    // Does this block lay satin over a same-colour fill (or run) of its own?
    let hasMid = false;
    for (const grp of groups) if (!grp.style.raised && grp.style.z === 3) hasMid = true;
    for (const grp of groups) {
      const st = grp.style;
      const slw = styleWidth(lw, st);
      // A raised group casts its own, deeper shadow here, onto the block's
      // stitching drawn beneath it.
      if (st.raised) { solid(); strokeShadow(ctx, grp.items, lw, st, soft); }
      // Satin over its OWN colour's fill: the block shadow cannot show it
      // (it is drawn before the fill), so the satin casts its own here, at
      // its ordinary strength, onto the fill beneath. At every zoom since
      // 2026-11-07: until then it was soft-only (drawn only once the thread
      // was wide enough for the soft shadow), on the reading that the hard
      // version at fit zoom was the +53% PR #1331 measured. That +53% was a
      // shadow path per STYLE GROUP in every block. This one is a single
      // path, for the satin of a block that also holds its own fill, and on
      // a fixture built to have exactly that (trace-holes-and-colors with
      // its satin recoloured onto the fill before it, 11,133 st) a fit-zoom
      // cold render measured 133.7 ms against main's 129.3 (+3.4%, and the
      // build without it +3.6%: the snapshot copy, not this).
      else if (hasMid && st.z >= 4) { solid(); strokeShadow(ctx, grp.items, lw, st, soft); }
      const profiles = [];
      for (const b of grp.buckets.values()) {
        if (offClip(b)) continue;
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
          dash = L.dash || null;
          const ox = p.nx * L.offset, oy = p.ny * L.offset;
          const f = L.inset || 0;
          ctx.beginPath();
          if (f > 0) {
            // The crown (CROWN_INSET): this layer stops short of both holes.
            for (const q of p.b.items) {
              const ex = (q.X1 - q.X0) * f, ey = (q.Y1 - q.Y0) * f;
              ctx.moveTo(q.X0 + ex + ox, q.Y0 + ey + oy);
              ctx.lineTo(q.X1 - ex + ox, q.Y1 - ey + oy);
            }
          } else {
            for (const q of p.b.items) {
              ctx.moveTo(q.X0 + ox, q.Y0 + oy);
              ctx.lineTo(q.X1 + ox, q.Y1 + oy);
            }
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
// The hoop ring's rectangle and corner radius in canvas px, from a viewed
// transform. One place, because the outline stroke and the surround's fabric
// clip must agree to the pixel.
export function hoopRectPx(t) {
  const w = t.hoopWmm * t.scale, h = t.hoopHmm * t.scale;
  return { x: t.ox - w / 2, y: t.oy - h / 2, w, h, r: Math.min(16, w * 0.08, h * 0.08) };
}

export function drawHoopOutline(ctx, t, fabricRgb, opts) {
  const { inset = true, dashed = false } = opts || {};
  const dark = isDark(fabricRgb || DEFAULT_FABRIC_RGB);
  const outlineColor = dark ? "rgba(255,255,255,0.45)" : "rgba(60,50,40,0.35)";
  const insetColor = dark ? "rgba(255,255,255,0.35)" : "rgba(60,50,40,0.28)";
  const { x, y, w: wPx, h: hPx, r } = hoopRectPx(t);
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

// Measuring grid across the whole canvas, anchored on the hoop centre so a
// line always passes through it: minor every 10 mm, major every 50 mm. Minor
// lines drop out when zoomed so far out they would read as a tint.
export function drawGrid(ctx, cw, ch, pxPerMm, ox, oy, g) {
  const minor = 10 * pxPerMm;
  if (!(minor > 0)) return;
  const draw = (step, color, width) => {
    ctx.strokeStyle = color;
    ctx.lineWidth = width;
    ctx.beginPath();
    for (let x = ox - Math.ceil(ox / step) * step; x <= cw; x += step) {
      const px = Math.round(x) + 0.5;
      ctx.moveTo(px, 0); ctx.lineTo(px, ch);
    }
    for (let y = oy - Math.ceil(oy / step) * step; y <= ch; y += step) {
      const py = Math.round(y) + 0.5;
      ctx.moveTo(0, py); ctx.lineTo(cw, py);
    }
    ctx.stroke();
  };
  ctx.save();
  if (minor >= 6) draw(minor, g.minor, 1);
  draw(minor * 5, g.major, 1);
  ctx.restore();
}

// ---- Simulator frames: snapshot the completed colour blocks ---------------
//
// Playback calls renderRealistic once per frame with a prefix one step
// longer than the last (`limitStrands`), and until 2026-11-07 every frame
// painted the whole prefix from the fabric up. Measured on a 22,533-stitch
// design at 8x: about half of all playback frames ran past 25 ms, and ~90%
// of a render is the rasterizer stroking paths (the JS around it is under
// 10%), so no amount of tidying the JS could fix that.
//
// What CAN be skipped is repeating work whose pixels are already known.
// drawThreads paints colour block by colour block, and a block that the
// prefix has moved past is complete: nothing later in the prefix changes
// how it is drawn, only what is drawn over it. So each frame is split at the
// start of its last (still open) block. The completed blocks are painted
// once and the canvas copied; every later frame of the same design, view and
// options restores that copy and paints only the open block.
//
// Pixel-exact by construction, and checked by hash against a fresh render
// (preview.spec.js asserts the call sequence; the lane's e2e harness hashed
// the canvases). The copy is a 1:1 'copy' blit at the identity transform,
// and the strokes after it are the ones a fresh render issues. Anything that
// could change a completed block's pixels — the design, its stitch array,
// the view, the hoop, the colours, the level of detail — is in the key, and
// a key change or a scrub back past the snapshot repaints from the fabric.
//
// Only hooped renders with `limitStrands` (the Studio field while
// simulating) take this path; thumbnails, export and every ordinary repaint
// draw exactly as before. It needs a way to make a canvas; without one (the
// specs' ctx doubles, a worker) it falls through to the plain path.
const SIM_SNAPSHOTS = new WeakMap();
const STRANDS_CACHE = new WeakMap();

function sameRgb(a, b) {
  return a === b || (!!a && !!b && a[0] === b[0] && a[1] === b[1] && a[2] === b[2]);
}

// designToStrands for a design the simulator replays every frame. Keyed on
// the stitch ARRAY as well as the design, plus its length, so a design that
// is rebuilt (every regenerate makes a new one) is never served stale.
function cachedStrands(design, colorOverride) {
  const hit = STRANDS_CACHE.get(design);
  if (hit && hit.stitches === design.stitches && hit.n === design.stitches.length && sameRgb(hit.co, colorOverride)) return hit.strands;
  const strands = designToStrands(design, { colorOverride });
  STRANDS_CACHE.set(design, { stitches: design.stitches, n: design.stitches.length, co: colorOverride || null, strands });
  return strands;
}

function makeCanvasLike(canvas) {
  const doc = canvas && canvas.ownerDocument;
  if (doc && typeof doc.createElement === "function") {
    const c = doc.createElement("canvas");
    c.width = canvas.width; c.height = canvas.height;
    return c;
  }
  if (typeof OffscreenCanvas === "function") return new OffscreenCanvas(canvas.width, canvas.height);
  return null;
}

// A 1:1 pixel copy, whatever transform or state `ctx` carries.
function copyCanvasInto(ctx, src) {
  ctx.save();
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.globalCompositeOperation = "copy";
  ctx.globalAlpha = 1;
  ctx.imageSmoothingEnabled = false;
  ctx.drawImage(src, 0, 0);
  ctx.restore();
}

// Everything besides the prefix length that decides a completed block's
// pixels. `view` and `hoop` are small plain objects; `layers` is the LOD rung,
// which can change as the prefix grows past a strand ceiling.
function simKey(canvas, o, layers) {
  return JSON.stringify([canvas.width, canvas.height, o.dpr, o.hoop, o.fabricRgb, o.fabric, o.weave, o.surround,
    o.grid, o.view, o.pad, o.threadStyle, o.sewnPullMm, o.colorOverride, o.threadWidthMm, layers]);
}

// null = not a simulator frame this can help (draw plainly). Otherwise
// { entry, lastStart, restoreFrom }: the snapshot record, where the prefix's
// open block starts, and how many leading strands the snapshot already holds
// (0 = none usable).
function simFrame(canvas, ctx, design, o, strands, layers) {
  if (typeof ctx.drawImage !== "function" || typeof ctx.setTransform !== "function") return null;
  if (!design || !Array.isArray(design.stitches)) return null;
  let entry = SIM_SNAPSHOTS.get(canvas);
  const key = simKey(canvas, o, layers);
  const snap = snapBitmap(canvas);
  if (!snap) return null;
  if (!entry) { entry = { canvas: snap.canvas }; SIM_SNAPSHOTS.set(canvas, entry); }
  // The bitmap is shared with the static-view cache below: whoever wrote it
  // last owns it, and a snapshot someone else overwrote is no snapshot.
  if (snap.owner !== entry || entry.key !== key || entry.design !== design || entry.stitches !== design.stitches || entry.n !== design.stitches.length) {
    entry.key = key; entry.design = design; entry.stitches = design.stitches; entry.n = design.stitches.length;
    entry.start = 0;
  }
  let lastStart = strands.length;
  if (lastStart > 0) {
    const rgb = strands[lastStart - 1].rgb;
    lastStart--;
    while (lastStart > 0 && sameRgb(strands[lastStart - 1].rgb, rgb)) lastStart--;
  }
  const restoreFrom = entry.start > 0 && entry.start <= lastStart ? entry.start : 0;
  return { entry, lastStart, restoreFrom };
}

// Half the canvas's bitmap in each direction: big enough for the smallest
// soft-shadow factor (k = 2), and every larger k uses its top-left corner.
const SOFT_SCRATCH = new WeakMap();
function softScratchFor(canvas) {
  const w = Math.ceil(canvas.width / 2), h = Math.ceil(canvas.height / 2);
  let c = SOFT_SCRATCH.get(canvas);
  if (c === null) return null;
  if (!c) {
    c = makeCanvasLike({ width: w, height: h, ownerDocument: canvas.ownerDocument });
    SOFT_SCRATCH.set(canvas, c || null);
    if (!c) return null;
  }
  if (c.width !== w || c.height !== h) { c.width = w; c.height = h; }
  return c;
}

function saveSimSnapshot(canvas, entry, start) {
  if (entry.canvas.width !== canvas.width || entry.canvas.height !== canvas.height) {
    entry.canvas.width = canvas.width; entry.canvas.height = canvas.height;
  }
  copyCanvasInto(entry.canvas.getContext("2d"), canvas);
  entry.start = start;
  SNAP_BITMAPS.get(canvas).owner = entry;
}

// ---- Static views: the finished render, kept (2026-11-07) -----------------
//
// The field repaints far more often than its picture changes. A hover over a
// shape, a selection, a jumps/trims toggle, a panel focus: every one calls
// renderRealistic again with the same design and the same view, and until
// now every one re-stroked every strand (~90% of a render is the rasterizer
// stroking paths; see SIM_SNAPSHOTS above) to paint what was already there.
//
// So a hooped, non-simulator render keeps a copy of its finished canvas
// (thread, bed, grid, hoop chrome; NOT the jumps/trims marks, which are drawn
// after the copy every time) and the next render with an identical key
// blits it back instead. Pixel-exact by construction: a 1:1 'copy' blit of
// what this same code painted under the same inputs. The key is everything
// the picture depends on:
//
//   - the design: its object, its stitch array, a fingerprint of every
//     stitch (so an in-place edit cannot be served stale), its colours and
//     its runs;
//   - every render option, the view (zoom AND pan) and the bitmap size;
//   - the context state the render INHERITS rather than sets (line cap and
//     join, dash, text alignment, shadow, filter, transform at dpr 1). Main
//     strokes the hoop chrome with whatever cap and join the last frame left
//     behind, so a first render on a fresh canvas and a repaint differ; the
//     key tells them apart instead of serving one for the other.
//
// After a blit the context is left in the state a fresh render leaves it in
// (end-of-render styles, recorded with the copy), so whatever the caller
// draws on top lands exactly as it would have.
//
// What it does NOT reuse, and why (measured 2026-11-07, PR body): a pan.
// Shifting the bitmap by the pan and painting only the exposed strip would be
// the obvious next step, and it is not pixel-identical to a fresh render, not
// even by a whole device pixel. The soft shadow is rasterized on a grid
// anchored to the canvas origin at 1/k resolution, so a shift that is not a
// multiple of k (2-6 when zoomed in) lands it differently: 7-53k px off by up
// to 34 levels at 4x and 8x on the four fixtures. Even at fit zoom, where the
// shadow is hard, Chromium anti-aliases a stroke by its whole path, and the
// strands a pan moves on or off the canvas move 2-94 px of the rest by up to
// 9 levels. Every zoom and pan therefore still draws from the fabric up.
//
// Memory: ONE bitmap per field canvas, the same size as the canvas, SHARED
// with the simulator's snapshot (each records that it wrote it last, and a
// snapshot the other overwrote is treated as absent), so this adds nothing
// to what playback already holds. Canvases over STATIC_CACHE_MAX_PX device
// px are not cached at all: at that cap the bitmap is <= 33.2 MB.
export const STATIC_CACHE_MAX_PX = 3840 * 2160;
const SNAP_BITMAPS = new WeakMap();
const STATIC_VIEWS = new WeakMap();

// The snapshot bitmap for a canvas, made on first use; null when no canvas
// can be made (the specs' ctx doubles, a worker).
function snapBitmap(canvas) {
  let r = SNAP_BITMAPS.get(canvas);
  if (r === null) return null;
  if (!r) {
    const c = makeCanvasLike(canvas);
    r = c ? { canvas: c, owner: null } : null;
    SNAP_BITMAPS.set(canvas, r);
  }
  return r;
}

// A fingerprint of every stitch, so a stitch array edited IN PLACE (same
// object, same length) still misses. Cheap next to a render: one pass, no
// allocation (~0.1 ms at 20k stitches).
function stitchPrint(stitches) {
  let h = stitches.length | 0;
  for (let i = 0; i < stitches.length; i++) {
    const s = stitches[i];
    const t = s.type ? s.type.charCodeAt(0) * 31 + s.type.length : 0;
    h = Math.imul(h ^ Math.round(s.x * 16), 0x9e3779b1) ^ Math.imul(Math.round(s.y * 16) + t, 0x85ebca6b);
    h ^= h >>> 15;
  }
  return h;
}

// Context state a render reads without setting first.
const INHERITED_STATE = ["lineCap", "lineJoin", "miterLimit", "lineDashOffset", "textAlign", "direction",
  "shadowBlur", "shadowColor", "shadowOffsetX", "shadowOffsetY", "filter", "letterSpacing", "wordSpacing",
  "fontKerning", "fontStretch", "fontVariantCaps", "textRendering", "imageSmoothingEnabled", "imageSmoothingQuality"];
// ...and what a render leaves behind, restored after a blit.
const END_STATE = INHERITED_STATE.concat(["strokeStyle", "fillStyle", "lineWidth", "font", "textBaseline", "globalAlpha", "globalCompositeOperation"]);

function readState(ctx, props) {
  const out = props.map((p) => ctx[p]);
  out.push(typeof ctx.getLineDash === "function" ? ctx.getLineDash() : null);
  return out;
}

function applyEndState(ctx, end) {
  for (let i = 0; i < END_STATE.length; i++) {
    if (end[i] !== undefined && ctx[END_STATE[i]] !== end[i]) ctx[END_STATE[i]] = end[i];
  }
  const d = end[END_STATE.length];
  if (d && typeof ctx.setLineDash === "function") ctx.setLineDash(d);
}

// null = this render cannot be cached (or served): its first fill would not
// cover the canvas opaquely, so what lies under it would show through.
function staticKey(canvas, ctx, design, o, dpr) {
  if (o.limitStrands != null || o.staticCache === false) return null;
  if (typeof ctx.drawImage !== "function" || typeof ctx.setTransform !== "function") return null;
  if (!design || !Array.isArray(design.stitches) || canvas.width * canvas.height > STATIC_CACHE_MAX_PX) return null;
  if (ctx.globalAlpha !== undefined && ctx.globalAlpha !== 1) return null;
  if (ctx.globalCompositeOperation !== undefined && ctx.globalCompositeOperation !== "source-over") return null;
  let tr = null;
  if (typeof ctx.getTransform === "function") {
    const m = ctx.getTransform();
    if (m.a !== dpr || m.b !== 0 || m.c !== 0 || m.d !== dpr || m.e !== 0 || m.f !== 0) return null;
    tr = dpr;
  }
  return JSON.stringify([canvas.width, canvas.height, dpr, tr, o.hoop, o.fabricRgb, o.fabric, o.weave, o.surround,
    o.grid, o.view, o.pad, o.threadStyle, o.sewnPullMm, o.colorOverride, o.threadWidthMm, o.threadLayers,
    o.softShadow, design.colors, design.runs, readState(ctx, INHERITED_STATE)]);
}

function staticHit(canvas, design, key) {
  if (!key) return null;
  const e = STATIC_VIEWS.get(canvas);
  const snap = SNAP_BITMAPS.get(canvas);
  if (!e || !snap || snap.owner !== e || e.key !== key || e.design !== design || e.stitches !== design.stitches || e.n !== design.stitches.length) return null;
  if (e.print !== stitchPrint(design.stitches)) return null;
  return { e, snap };
}

function saveStatic(canvas, ctx, design, key) {
  const snap = snapBitmap(canvas);
  if (!snap) return;
  if (snap.canvas.width !== canvas.width || snap.canvas.height !== canvas.height) {
    snap.canvas.width = canvas.width; snap.canvas.height = canvas.height;
  }
  copyCanvasInto(snap.canvas.getContext("2d"), canvas);
  const e = { key, design, stitches: design.stitches, n: design.stitches.length, print: stitchPrint(design.stitches), end: readState(ctx, END_STATE) };
  STATIC_VIEWS.set(canvas, e);
  snap.owner = e;
}

// opts:
//   grid          { bed, minor, major, label } CSS colours. With a hoop, paints
//                  a work bed inside the hoop plus drawGrid() across the canvas
//                  INSTEAD of fabric/weave/surround fill, and draws only the
//                  real hoop ring (no garment box) with a size label.
//   fabric        CSS color string bg fill (FontSelect/exportPNG's existing
//                  contract -- stays working, B5).
//   fabricRgb      [r,g,b] bg fill; WINS over `fabric` when both given (B5).
//   colorOverride  existing strand-recolor contract -- unchanged.
//   weave          true -> draw weavePattern() over the bg fill (needs
//                  fabricRgb; a no-op without it).
//   surround       CSS colour for the canvas OUTSIDE the hoop. With it, the
//                  fabric (and weave) fill only the hoop's rounded rect and
//                  the rest of the canvas is this colour. Ignored without a
//                  hoop, so thumbnails and PNG export never see it. Omit it
//                  and the fill is edge to edge exactly as before.
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

  const hooped = !!(o.hoop && o.hoop.garment);
  // A surround only means something when there is a hoop to float on it;
  // a design-fit render (thumbnails, PNG export) has no hoop, so its fabric
  // still fills the canvas exactly as before.
  const surrounded = hooped && !!o.surround;

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

  // The hoop's rectangle in canvas px, through the same TX/TY the strands
  // use, so it lands where the outline below is stroked at any zoom or pan.
  // Computed once here because the surround path needs it BEFORE the weave
  // and the outline needs it after.
  const viewedT = hooped
    ? { scale: pxPerMm, ox: TX(0), oy: TY(0), hoopWmm: t.hoopWmm, hoopHmm: t.hoopHmm }
    : null;
  const outerT = hooped && t.realWmm ? { ...viewedT, hoopWmm: t.realWmm, hoopHmm: t.realHmm } : viewedT;

  // Strand coordinates come straight from design.stitches, i.e. DST units
  // (0.1mm each). fitTransform's scale already absorbs that (it's computed
  // from the same raw units), so the design-fit path can feed them to TX/TY
  // untouched. hoopTransform's scale is px-per-mm though, so in hoop mode we
  // must convert DST units -> mm (/10) before applying it.
  const SX = hooped ? (x) => TX(x / 10) : TX;
  const SY = hooped ? (y) => TY(y / 10) : TY;

  // A static view this canvas already painted under the same key (see
  // STATIC_VIEWS): blit it back, and go straight to the overlays.
  let skey = hooped ? staticKey(canvas, ctx, design, o, dpr) : null;
  const shit = staticHit(canvas, design, skey);
  if (shit) {
    copyCanvasInto(ctx, shit.snap.canvas);
    applyEndState(ctx, shit.e.end);
    return finishRender(ctx, design, o, hooped, SX, SY, TX, TY, pxPerMm);
  }

  // Strands are worked out before anything is drawn (they are pure), so a
  // simulator frame can decide whether its snapshot is usable first.
  let strands = hooped && o.limitStrands != null
    ? cachedStrands(design, o.colorOverride)
    : designToStrands(design, { colorOverride: o.colorOverride });
  // Simulator support: draw only the first `limitStrands` segments (sew
  // order IS strand order — designToStrands walks design.stitches start to
  // finish), so scrubbing/playing renders the design exactly as the machine
  // would sew it. undefined/null = draw everything (every existing caller).
  if (o.limitStrands != null) strands = strands.slice(0, Math.max(0, o.limitStrands));
  // Sewn width (2026-10-06): `sewnPullMm` > 0 draws every satin strand with
  // that much pull compensation taken back off each end — the column at the
  // width the cloth will show, not the width the file carries. See
  // strands.js's shrinkSatinStrands; a view only, nothing in the design moves.
  if (o.sewnPullMm > 0) strands = shrinkSatinStrands(strands, o.sewnPullMm);
  // Thread width is PHYSICAL (THREAD_WIDTH_MM), with a px floor so a thread
  // stays visible in the small font/template previews where pxPerMm is tiny.
  const threadMm = o.threadWidthMm != null ? o.threadWidthMm : THREAD_WIDTH_MM;
  const lw = Math.max(1.2, threadMm * pxPerMm);
  const layers = o.threadLayers != null ? o.threadLayers : threadLodLayers(lw, strands.length);
  const threadOpts = { layers, flat: o.threadStyle === "flat", clip: { x0: 0, y0: 0, x1: cw, y1: ch } };
  // The soft shadow's scratch canvas, made on first use and kept per canvas.
  // None for a canvas that cannot make one (the specs' ctx doubles).
  if (o.threadStyle !== "flat" && o.softShadow !== false && typeof ctx.drawImage === "function") {
    threadOpts.softShadow = { dpr, cw, ch, scratch: () => softScratchFor(canvas) };
  }

  // Simulator frames (see SIM_SNAPSHOTS): when this canvas last drew an
  // earlier prefix of the same design under the same options, the colour
  // blocks that prefix completed come back from a snapshot instead of being
  // painted again, background and hoop chrome included.
  const sim = hooped && o.limitStrands != null ? simFrame(canvas, ctx, design, o, strands, layers) : null;
  const restored = !!(sim && sim.restoreFrom > 0);
  if (restored) {
    copyCanvasInto(ctx, sim.entry.canvas);
    // The plain path reaches the strands with a solid dash (the hoop chrome
    // resets it); whatever the caller drew over the last frame may not have.
    ctx.setLineDash([]);
  } else {
    ctx.fillStyle = surrounded ? o.surround : (o.fabricRgb ? rgbCss(o.fabricRgb) : (o.fabric || "#e9e6df"));
    // Only a render whose first fill is OPAQUE covers what was there before,
    // so only that render is a picture of its inputs alone and can be kept.
    // A real canvas reads an opaque colour back as #rrggbb.
    if (skey && !/^#[0-9a-f]{6}$|^rgb\(/i.test(String(ctx.fillStyle))) skey = null;
    ctx.fillRect(0, 0, cw, ch);
  }

  if (restored) {
    // The snapshot already holds the bed, grid, weave and hoop chrome.
  } else if (hooped && o.grid) {
    // Studio field: a neutral work bed + measuring grid instead of fabric.
    // Fabric colour and weave are not drawn at all; the hoop ring below is the
    // only frame, so it is the size reference.
    const r = hoopRectPx(outerT);
    ctx.save();
    roundRectPath(ctx, r.x, r.y, r.w, r.h, r.r);
    ctx.clip();
    ctx.fillStyle = o.grid.bed;
    ctx.fillRect(r.x, r.y, r.w, r.h);
    ctx.restore();
    drawGrid(ctx, cw, ch, pxPerMm, outerT.ox, outerT.oy, o.grid);
  } else if (surrounded) {
    // Fabric only INSIDE the hoop (the real one when it is known, else the
    // placement box standing in for it): the canvas outside the ring stays
    // the surround, so the fabric colour reads against a neutral instead of
    // against itself edge to edge, and at any zoom the ring's edge is where
    // fabric meets dark — orientation the old edge-to-edge fill could not
    // give. The weave is clipped to the same path. The rounded corners
    // match drawHoopOutline's radius rule exactly so the ring sits on the
    // fill's edge rather than a pixel inside or outside it.
    const r = hoopRectPx(outerT);
    ctx.save();
    roundRectPath(ctx, r.x, r.y, r.w, r.h, r.r);
    ctx.clip();
    ctx.fillStyle = o.fabricRgb ? rgbCss(o.fabricRgb) : (o.fabric || "#e9e6df");
    ctx.fillRect(r.x, r.y, r.w, r.h);
    if (o.weave && o.fabricRgb) weavePattern(ctx, cw, ch, o.fabricRgb, pxPerMm);
    ctx.restore();
  } else if (o.weave && o.fabricRgb) {
    weavePattern(ctx, cw, ch, o.fabricRgb, pxPerMm);
  }
  if (hooped && !restored) {
    // t.ox/t.oy run through the SAME TX/TY used for strands below, so the
    // outline is always drawn at the current view's scale/position -- one
    // shared transform, not a second parallel calculation (B4).
    if (o.grid) {
      // One frame only, drawn light-on-dark, plus its size as a label.
      drawHoopOutline(ctx, outerT, [0, 0, 0]);
      const hp = o.hoop.hoop;
      const label = hp && hp.label ? `${hp.label} hoop` : `${Math.round(outerT.hoopWmm)} × ${Math.round(outerT.hoopHmm)} mm`;
      const r = hoopRectPx(outerT);
      ctx.save();
      ctx.font = "11px ui-monospace, SFMono-Regular, Consolas, monospace";
      ctx.fillStyle = o.grid.label;
      ctx.textBaseline = "bottom";
      ctx.fillText(label, r.x + 2, r.y - 6);
      ctx.restore();
    } else if (t.realWmm) {
      // The real hoop FIRST, so the placement box reads as sitting inside it
      // rather than the other way round -- and so a caller that passes no hoop
      // leaves this module's stroke order, which one spec asserts by index,
      // exactly as it was.
      drawHoopOutline(ctx, outerT, o.fabricRgb);
      drawHoopOutline(ctx, viewedT, o.fabricRgb, { inset: false, dashed: true });
    } else {
      drawHoopOutline(ctx, viewedT, o.fabricRgb);
    }
  }

  // threadStyle: "realistic" (default, every existing caller) | "flat".
  if (!sim) {
    drawThreads(ctx, strands, SX, SY, lw, threadOpts);
  } else {
    // A simulator frame, split at the start of its LAST colour block (the one
    // still being sewn): the completed blocks first, then a snapshot of the
    // canvas, then the open block. drawThreads paints block by block, and
    // every block starts by setting all the state it strokes with (its
    // shadow is always solid), so two calls split there issue the same
    // strokes as one call. restoreFrom is never past lastStart (simFrame
    // only offers a snapshot of blocks this prefix has completed).
    const from = sim.restoreFrom;
    if (sim.lastStart > from) {
      drawThreads(ctx, strands.slice(from, sim.lastStart), SX, SY, lw, threadOpts);
      saveSimSnapshot(canvas, sim.entry, sim.lastStart);
    }
    drawThreads(ctx, strands.slice(sim.lastStart), SX, SY, lw, threadOpts);
  }
  if (skey) saveStatic(canvas, ctx, design, skey);

  return finishRender(ctx, design, o, hooped, SX, SY, TX, TY, pxPerMm);
}

// Everything renderRealistic does after the thread: the diagnostic overlays
// and the returned transform. Shared by a full render and a static-view blit.
function finishRender(ctx, design, o, hooped, SX, SY, TX, TY, pxPerMm) {
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
