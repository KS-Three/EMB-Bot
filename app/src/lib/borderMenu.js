// The per-shape border decision as the canvas's right-click menu shows it.
//
// One field, two ways in: the Digitize panel's Border select writes
// `element.shapeOverrides[sid].border` ("off" | "auto" | "bean", or absent =
// the design-wide setting), and so does the field's context menu. This
// module is the menu's half: given the shape's override entry and the
// design-wide `params.border`, what does the shape effectively have, and
// which items does the menu offer. Pure, so the decision table is tested
// without a browser or a service.
//
// The engine's vocabulary (digitizer_core/config.py, `border`): "auto" sews a
// satin border on a fill shape wide enough to host a column and a bean run
// where it is not; "bean" the light tier wherever a centreline fits;
// "significant" is "auto" gated to shapes that earn it; "off" (or the null
// "let the class decide", which every non-photo class reads as off) none.
// A shape classified as satin never gets one — the panel's select has the
// same limit, and the item's title says so.

const BORDERED = new Set(["auto", "bean", "significant"]);

// -> { bordered: bool, source: "shape" | "design" }
export function effectiveBorder(entry, designBorder) {
  const own = entry && typeof entry.border === "string" ? entry.border.toLowerCase() : null;
  if (own === "off") return { bordered: false, source: "shape" };
  if (own && BORDERED.has(own)) return { bordered: true, source: "shape" };
  const design = typeof designBorder === "string" ? designBorder.toLowerCase() : null;
  return { bordered: !!design && BORDERED.has(design), source: "design" };
}

export const ADD_TITLE =
  "Satin border where the shape is wide enough for a column, a bean run where it is not. " +
  "A shape sewn as satin gets no border.";

// -> [{ id, label, value, title }] — `value` is what to store in
// shapeOverrides[sid].border (null clears the override).
export function borderMenuItems(entry, designBorder) {
  const eff = effectiveBorder(entry, designBorder);
  const items = eff.bordered
    ? [{ id: "remove", label: "Remove border", value: "off", title: "No border on this shape." }]
    : [{ id: "add", label: "Add border", value: "auto", title: ADD_TITLE }];
  if (eff.source === "shape") {
    items.push({
      id: "design",
      label: "Use design setting",
      value: null,
      title: "Sew whatever the design-wide Border setting says for this shape.",
    });
  }
  return items;
}

// ---------------------------------------------------------------------------
// PART TWO: what the engine actually SEWED.
//
// Everything above this line is about what was REQUESTED — `shapeOverrides`
// and `params.border`, the two fields the user writes. The engine is free to
// decline: a shape it tiers as satin never gets a border (a satin column
// already is an outline, so stage 7 returns before the border block ever
// runs), and a shape too narrow to hold a column gets a bean run instead — or,
// narrower still, nothing at all. Until `design.runs` existed the Studio had
// no way to read any of that back, so the canvas menu and the Layers list both
// said "bordered" about shapes with no border on them.
//
// `design.runs` is the read-back (contract 2026-09-15,
// digitizer_core/adapter.py::plan_to_design):
//
//   [{ i0, i1, kind, shape, role, block }]
//     i0/i1  inclusive indices into design.stitches
//     kind   the planner's own word, and the list is NOT closed — "satin",
//            "fill", "run", "underlay", "travel" are what the corpus shows,
//            and "border", "bean" and "tie" are equally legal
//     shape  shape_id VERBATIM, which is not always a review shape's id: the
//            blend tier stamps `<sid>-blend<i>`, streamline `-shade<i>`, and
//            the silhouette cap the sentinel "__edge_cap__"
//     role   "" | "border" | "edge_cap" — WHICH TIER asked for the run, the
//            axis `kind` cannot answer (a bean border and a rescued small
//            shape's outline are the same technique and different things)
//     block  index into design.colors
//
// IT MAY BE ABSENT — an older payload, a saved .embproj, the browser's own
// lettering and manual lanes. Every function here answers `null`/"unverified"
// in that case rather than guessing, and the UI falls back to the
// request-based reading with wording that does not claim to know: "border
// requested" is honest, "border sewn" would not be.
//
// Pure, like the decision table above, for the same reason: the interesting
// cases (the engine declining) are exactly the ones that are miserable to
// reproduce in a browser.

// Kinds that count as a border ON CLOTH, normalized to the two things it can
// look like. VERIFIED against the live service, 2026-09-15, not inferred:
// `stage6_border.border_runs` stamps BORDER ("border") when a satin column
// fits and BEAN ("bean") when the shape is too narrow and the tier lightens;
// the silhouette cap's bean style goes through `run_outline`, which stamps RUN
// ("run"). "satin" is accepted here too because `kind` is explicitly NOT a
// closed list (adapter.py: "treat an unknown kind as ordinary stitching"), so
// a future emitter that spells a column that way must not read as no border.
const SATIN_KINDS = new Set(["border", "satin"]);
const LIGHT_KINDS = new Set(["bean", "run"]);
// A run that lays no thread OF THE ARTWORK. Travel is the needle crossing
// work already sewn and a tie is a lock stitch; neither may make a shape read
// as "sewn", and neither is a border even when it carries the border role —
// `border_runs` emits its bridge as a TRAVEL run with role "border", so a
// shape whose border produced nothing but a bridge must still read as
// declined rather than bordered.
const NON_SEWING_KINDS = new Set(["travel", "tie"]);

// The design-silhouette cap's shape id (stage6_border.silhouette_cap). `role`
// is the contract and this is the older convention, kept as a belt-and-braces
// guard so a cap run can never be filed under a shape whatever the role says.
const EDGE_CAP_SENTINEL = "__edge_cap__";

export const BORDER_ROLE = "border";
export const EDGE_CAP_ROLE = "edge_cap";

// A shade band's runs do NOT carry their region's shape_id: stage6_blend
// stamps `<sid>-blend<i>` and stage6_streamline `<sid>-shade<i>`. Equality
// alone therefore reads "this shape sewed nothing" about a region the machine
// puts five cones into, and a plain prefix test picks the WRONG region when
// ids are not prefix-free (`S5afb1e0a` and `S5afb1e0a-2` both plan, and
// `S5afb1e0a-2-blend0` prefix-matches both). Same rule as the service's
// `preflight._owning_region_id`, ported: strip the one derived suffix and
// require the remainder to be a real id.
//
// Border runs are emitted with the plain shape id (stage7 hands `p.shape_id`
// to `border_runs`), so this only matters for deciding whether a shape sewed
// anything at all — but that is the difference between "the engine declined
// your border" and "this shape isn't sewn", which are different problems with
// different fixes.
const SHADE_SUFFIX = /^(.+)-(?:blend|shade)\d+$/;

export function owningShapeId(runShape, knownIds) {
  const sid = typeof runShape === "string" ? runShape : "";
  if (!sid) return "";
  if (!knownIds || !knownIds.has || knownIds.has(sid)) return sid;
  const m = SHADE_SUFFIX.exec(sid);
  if (m && knownIds.has(m[1])) return m[1];
  return sid;
}

// How many actual STITCH records a run covers. `i0`/`i1` index
// `design.stitches`, which also holds jump/trim/color/end records — counting
// the raw span would bill the cap for the needle lift that starts it. Falls
// back to the span when there are no stitches to look at (a payload carrying
// runs but no stitches is not a shape this has to be clever about).
function runStitches(stitches, run) {
  const i0 = Number.isFinite(run.i0) ? run.i0 : 0;
  const i1 = Number.isFinite(run.i1) ? run.i1 : -1;
  if (i1 < i0) return 0;
  if (!Array.isArray(stitches) || !stitches.length) return i1 - i0 + 1;
  let n = 0;
  const end = Math.min(i1, stitches.length - 1);
  for (let i = Math.max(0, i0); i <= end; i++) {
    if (stitches[i] && stitches[i].type === "stitch") n++;
  }
  return n;
}

// design -> the evidence, or NULL when the design carries no `runs` at all.
//
// null is the whole point: it is the one value that means "this payload cannot
// answer", and every caller below turns it into wording that does not claim to
// know. An EMPTY array is not the same thing and must not collapse into it — a
// design that sewed no runs is a design that sewed nothing, which is a real,
// reportable state.
//
// `knownIds` is the review's shape ids (optional); it only feeds
// `owningShapeId` above.
export function indexRuns(design, knownIds) {
  const runs = design && design.runs;
  if (!Array.isArray(runs)) return null;
  const stitches = (design && design.stitches) || null;
  const ids = knownIds instanceof Set ? knownIds : new Set(knownIds || []);
  const byShape = new Map();
  const edge = { runs: 0, satin: 0, light: 0, stitches: 0 };
  let body = 0;
  for (const r of runs) {
    if (!r || typeof r !== "object") continue;
    const kind = typeof r.kind === "string" ? r.kind.toLowerCase() : "";
    const role = typeof r.role === "string" ? r.role.toLowerCase() : "";
    if (role === EDGE_CAP_ROLE || r.shape === EDGE_CAP_SENTINEL) {
      // Travel inside the cap is still part of the cap's bill (the engine's
      // own `_cap_st` sums every run it appends), so it counts toward
      // `stitches` — it just is not a stretch of finished edge.
      edge.stitches += runStitches(stitches, r);
      if (NON_SEWING_KINDS.has(kind)) continue;
      edge.runs++;
      if (SATIN_KINDS.has(kind)) edge.satin++;
      else if (LIGHT_KINDS.has(kind)) edge.light++;
      continue;
    }
    const sid = owningShapeId(r.shape, ids);
    if (!sid) continue;
    let e = byShape.get(sid);
    if (!e) {
      e = { runs: 0, body: 0, satin: 0, light: 0, borderRuns: 0 };
      byShape.set(sid, e);
    }
    e.runs++;
    if (NON_SEWING_KINDS.has(kind)) continue;   // travel/tie is neither
    if (role === BORDER_ROLE) {
      e.borderRuns++;
      if (SATIN_KINDS.has(kind)) e.satin++;
      else if (LIGHT_KINDS.has(kind)) e.light++;
    } else {
      e.body++;
      body++;
    }
  }
  return { byShape, edge, bodyRuns: body, runCount: runs.length };
}

// ---- one shape's border, as sewn ------------------------------------------
//
// States, and the evidence behind each:
//
//   "none"        not asked for. No badge; there is nothing to report.
//   "satin"       a border run of kind satin carries this shape's id.
//   "bean"        a border run, but a light one — which IS the engine saying
//                 the shape had no room for a column (stage7's BORDER_LIGHTENED
//                 counts exactly these), so the reason is named, not guessed.
//   "declined"    asked for, the shape sewed, and NO border run carries its id.
//                 The case Kent cannot currently see at all.
//   "unsewn"      asked for and the shape produced no thread of its own, so the
//                 missing border is not the story — don't blame the border for
//                 a shape that isn't there.
//   "pending"     the request changed since this result sewed. The run evidence
//                 is about the PREVIOUS request and saying anything else would
//                 be reporting the old answer as the new one.
//   "unverified"  asked for, and `design.runs` is absent. Says "requested".
//
// `reason` is named only where it is knowable, per the standing rule in this
// file's header: "satin-tier" (stage 7 returns before the border block for a
// satin shape — the same fact ADD_TITLE already states), "too-narrow-column"
// (what a bean border means), "not-sewn". Anything else stays "" and the
// wording says it was not generated rather than inventing a cause.
//
// `tone` is how loudly to say it, and it is NOT a restatement of `state`: a
// satin-tiered shape declining a border is the engine working as documented
// and must read as quietly as "no border" does, while an unexplained decline
// is the one thing on the row worth a look. Driving the badge colour off
// `state` alone painted three of four rows red on the first design this was
// tried on (logo_script_tires, 2026-09-15) — a design with nothing wrong with
// it. "ok" | "note" | "warn" | "quiet".
export function shapeBorderState(opts) {
  const o = opts || {};
  const eff = effectiveBorder(o.entry, o.designBorder);
  const tier = typeof o.tier === "string" ? o.tier.toLowerCase() : null;
  const base = { requested: eff.bordered, source: eff.source, reason: "", verified: false, tone: "quiet" };

  if (!eff.bordered) {
    // An explicit "off" on a shape the design would otherwise border is a
    // decision worth showing back; a shape nobody asked to border is not.
    const own = o.entry && typeof o.entry.border === "string"
      && o.entry.border.toLowerCase() === "off";
    const designOn = typeof o.designBorder === "string" && BORDERED.has(o.designBorder.toLowerCase());
    return own && designOn
      ? { ...base, state: "off", label: "border off",
          title: "You turned this shape's border off; the design-wide Border setting would give it one." }
      : { ...base, state: "none", label: "", title: "" };
  }

  if (o.pending) {
    return { ...base, state: "pending", label: "border pending",
      title: "You changed this shape's border since it was last stitched. The design on the canvas is still the previous one." };
  }

  const ev = o.index && o.index.byShape ? o.index.byShape.get(o.shapeId) : null;

  // Knowable WITHOUT the run list, and worth saying either way: stage 7
  // returns before the border block for a satin-tiered shape, so the border
  // was never going to happen. `tier` is read off the plan that produced this
  // result (review.shapes[].tier), not off a pending override.
  if (tier === "satin" && (!ev || !ev.borderRuns)) {
    return { ...base, verified: !!o.index, state: "declined", reason: "satin-tier",
      label: "no border — sews as satin",
      title: "This shape sews as a satin column, which is already an outline, so the engine adds no border to it." };
  }

  if (!o.index) {
    return { ...base, state: "unverified", label: "border requested",
      title: "This design was stitched before the Studio could read back which runs actually sewed, so this says what was asked for, not what is on the cloth. Digitize again to see the real answer." };
  }

  if (ev && ev.satin) {
    return { ...base, verified: true, state: "satin", tone: "ok", label: "satin border",
      title: "A satin column sews around this shape." };
  }
  if (ev && ev.light) {
    return { ...base, verified: true, state: "bean", reason: "too-narrow-column", tone: "note",
      label: "bean border",
      title: "This shape had no room for a satin column, so its border sews as a bean run — a light outline, not a solid one." };
  }
  if (!ev || !ev.body) {
    return { ...base, verified: true, state: "unsewn", reason: "not-sewn", tone: "note",
      label: "not sewn",
      title: "This shape laid no thread of its own on this run, so there is nothing for a border to go around." };
  }
  return { ...base, verified: true, state: "declined", tone: "warn",
    label: "no border sewn",
    title: "You asked for a border here and the engine did not add one, so there is no outline on this shape. The usual cause is a shape too narrow to hold one — but this run does not say so outright, and naming a cause it did not give would be a guess." };
}

// ---- the whole design, in counts ------------------------------------------
//
// The number that has to MOVE when the Border select is toggled. Counts are
// over the shapes the Layers list shows as sewing; `rows` is
// review.shapes-shaped ({ id, tier }), `overrides` the element's
// shapeOverrides.
//
// `verified` is false when `index` is null — the caller must not print "sewn"
// off an unverified tally.
export function borderTally(opts) {
  const o = opts || {};
  const rows = Array.isArray(o.rows) ? o.rows : [];
  const overrides = o.overrides || {};
  const out = {
    total: rows.length, requested: 0, satin: 0, bean: 0, declined: 0,
    satinTier: 0, unsewn: 0, off: 0, verified: !!o.index, pending: !!o.pending,
  };
  for (const row of rows) {
    if (!row || !row.id) continue;
    const st = shapeBorderState({
      shapeId: row.id,
      entry: overrides[row.id],
      designBorder: o.designBorder,
      index: o.index,
      tier: row.tier,
      pending: false, // the design-level line carries staleness once, as a flag
    });
    if (st.requested) out.requested++;
    if (st.state === "satin") out.satin++;
    else if (st.state === "bean") out.bean++;
    else if (st.state === "declined") {
      // Split, because the two read completely differently to the person
      // looking: a satin-tiered shape declining a border is the engine working
      // as documented (a column already IS an outline), and lumping it in with
      // the unexplained ones makes a healthy design look broken. Measured on
      // logo_script_tires, 2026-09-15: 3 of the 4 requests were this.
      if (st.reason === "satin-tier") out.satinTier++;
      else out.declined++;
    } else if (st.state === "unsewn") out.unsewn++;
    else if (st.state === "off") out.off++;
  }
  return out;
}

// One sentence for the design-level border line. Written to be read while
// deciding — same brief EDGE_CAP_APPLIED's copy was written to, since these
// two lines sit next to each other under the two selects that cause them.
export function borderSummaryText(tally, designBorder) {
  const t = tally || {};
  const designOff = !(typeof designBorder === "string" && BORDERED.has(designBorder.toLowerCase()));
  if (!t.requested) {
    return designOff && !t.total
      ? "No shape borders."
      : "No shape borders — nothing is asking for one.";
  }
  if (!t.verified) {
    return `${t.requested} shape${t.requested === 1 ? "" : "s"} asking for a border. ` +
      "Stitched before the Studio could read back what sewed, so this is the request, not the cloth.";
  }
  const parts = [];
  if (t.satin) parts.push(`${t.satin} satin`);
  if (t.bean) parts.push(`${t.bean} bean`);
  const sewn = t.satin + t.bean;
  const head = sewn
    ? `${sewn} of ${t.requested} border${t.requested === 1 ? "" : "s"} sewn (${parts.join(", ")})`
    : `None of the ${t.requested} border${t.requested === 1 ? "" : "s"} asked for were sewn`;
  const tail = [];
  // Named reasons first, unexplained last — the unexplained one is what wants
  // a look, and it should not be buried behind three shapes doing exactly what
  // the engine documents.
  if (t.satinTier) {
    tail.push(t.satinTier === 1
      ? "1 on a shape that sews as satin"
      : `${t.satinTier} on shapes that sew as satin`);
  }
  if (t.unsewn) {
    tail.push(t.unsewn === 1
      ? "1 on a shape that sews nothing"
      : `${t.unsewn} on shapes that sew nothing`);
  }
  if (t.declined) tail.push(`${t.declined} not generated`);
  return tail.length ? `${head} · ${tail.join(" · ")}.` : `${head}.`;
}

// ---- the design edge (cfg.edge_cap) ---------------------------------------
//
// A SEPARATE control from the per-shape border and ON by default as "bean",
// which is why it needs its own readout: the two get confused constantly, and
// the edge pass is the expensive one — measured +18% to +58% of a design's
// stitches depending on size (docs/edge-cap-cliff-2026-09-12.md).
//
// Evidence, in order of authority:
//   1. `EDGE_CAP_APPLIED` — the engine's own bill, computed on THIS design
//      against the artwork's stitch count with the cap excluded. Preferred
//      whenever present, so this line and the warnings list cannot print two
//      different numbers for one thing.
//   2. `design.runs` with role "edge_cap" — what sewed. Confirms (1), and
//      stands alone when the payload has runs but no warning.
//   3. `EDGE_CAP_EMPTY` — switched on, no edge long enough to sew.
//
// The `dropped` flag matters even though the Studio cannot currently reach it:
// EDGE_CAP_APPLIED fires on every run where a cap was PRICED, including one
// the over-budget rule then threw away (stage7_sequence sets `cap_cost` either
// side of `if not cap_dropped`). Its own text says "adds N stitches" — of a
// pass that added none. Studio never sends `edge_cap_over_budget`, so the drop
// path is unreachable from here today; this reads the flag anyway rather than
// inherit the bug the day it becomes reachable.
export function edgeCapState(opts) {
  const o = opts || {};
  const mode = typeof o.mode === "string" ? o.mode.toLowerCase() : "bean";
  const warnings = Array.isArray(o.warnings) ? o.warnings : [];
  const find = (code) => warnings.find((w) => w && w.code === code) || null;
  const applied = find("EDGE_CAP_APPLIED");
  const empty = find("EDGE_CAP_EMPTY");
  const lightened = find("EDGE_CAP_LIGHTENED");
  const edge = o.index && o.index.edge ? o.index.edge : null;
  const base = { mode, stitches: null, percent: null, edges: null, lightened: 0, verified: false };
  if (lightened) base.lightened = lightened.count || 0;

  if (mode !== "bean" && mode !== "satin") {
    return { ...base, state: "off", label: "Design edge off",
      title: "The design's outer edge is left open. Fill rows that end on the silhouette end in open air." };
  }
  // The word in the label comes from the EVIDENCE, not from the select:
  // EDGE_CAP_APPLIED carries the `style` the cap actually sewed, and the runs
  // carry the kinds. So while a restitch is in flight this line keeps
  // describing the plan on the canvas rather than blanking or relabelling
  // itself to a request nothing has sewn yet — the block's own dimming and
  // "reads the previous stitch plan" note carry the staleness.
  const sewnWord = modeWord(
    (applied && typeof applied.style === "string" && applied.style.toLowerCase())
    || (edge && edge.runs ? (edge.satin ? "satin" : "bean") : mode),
  );
  if (applied && applied.dropped === true) {
    return { ...base, verified: true, state: "dropped",
      stitches: applied.stitches || 0, percent: applied.percent || 0,
      edges: applied.edges || 0,
      label: "Design edge priced, then dropped",
      title: "The edge pass cost more than the budget allows, so it was thrown away. There is no edge cap on this design." };
  }
  if (applied) {
    return { ...base, verified: true, state: "sewn",
      stitches: applied.stitches || 0, percent: applied.percent || 0,
      edges: applied.edges || 0,
      label: `${sewnWord} edge sewn`,
      title: "The design's outer silhouette is capped, so fill rows finish against thread instead of ending in open air." };
  }
  if (edge && edge.runs) {
    return { ...base, verified: true, state: "sewn", stitches: edge.stitches,
      percent: null, edges: null,
      label: `${sewnWord} edge sewn`,
      title: "The design's outer silhouette is capped. This run count is measured off the stitch plan; the engine did not bill it." };
  }
  if (empty || (edge && !edge.runs)) {
    return { ...base, verified: !!edge, state: "empty",
      label: "Design edge found nothing to sew",
      title: "The design edge is switched on, but no stretch of the silhouette is long enough to hold an outline — the design is too small or too narrow for it." };
  }
  return { ...base, state: "unverified", label: `${modeWord(mode)} edge requested`,
    title: "This design was stitched before the Studio could read back which runs sewed, so this says what was asked for, not what is on the cloth." };
}

function modeWord(mode) {
  return mode === "satin" ? "Satin" : "Bean";
}

// The design-edge line, with its cost where there is one to give.
export function edgeCapSummaryText(state) {
  const s = state || {};
  if (s.state === "sewn" && s.stitches != null) {
    const st = s.stitches.toLocaleString();
    const pct = s.percent != null ? ` (+${s.percent}% of the design)` : "";
    const edges = s.edges > 1 ? `, around ${s.edges} separate edges` : "";
    const light = s.lightened
      ? ` ${s.lightened} stretch${s.lightened === 1 ? "" : "es"} sewed as a light bean run instead of a column.`
      : "";
    return `${s.label} — ${st} stitches${pct}${edges}.${light}`;
  }
  return s.label ? `${s.label}.` : "";
}

// ---- "you changed it, it has not sewn yet" ---------------------------------
//
// The run evidence describes the request that produced THIS result. A border
// the user just toggled has not been stitched yet — the panel restitches after
// a 2 s idle, and not at all with the service offline — so between the two the
// readout must say "pending" rather than report the old answer as the new one.
//
// `element.appliedEdits` is exactly the right record: digitizer.js's `editsKey`
// stores `JSON.stringify([deleted, shape_overrides, merge, split])` at the
// moment a result lands, so slot 1 is the per-shape override set the current
// stitches were sewn with. Parsing it back gives PER-SHAPE precision, which
// matters: a pending edit on one shape must not make every other row claim to
// be out of date.
//
// -> Map(sid -> border string), or null when there is nothing to compare
// against (no result yet, or a payload that predates the field). null means
// "cannot tell", and the caller must read that as NOT pending — crying wolf on
// every row is its own kind of lie.
export function appliedBorders(appliedEditsKey) {
  if (typeof appliedEditsKey !== "string" || !appliedEditsKey) return null;
  let parsed = null;
  try {
    parsed = JSON.parse(appliedEditsKey);
  } catch (e) {
    return null;
  }
  if (!Array.isArray(parsed) || parsed.length < 2) return null;
  const ov = parsed[1];
  if (!ov || typeof ov !== "object") return new Map();
  const out = new Map();
  for (const sid of Object.keys(ov)) {
    const b = ov[sid] && ov[sid].border;
    if (typeof b === "string") out.set(sid, b.toLowerCase());
  }
  return out;
}

// Has this shape's border request moved since the stitches were made?
export function borderRequestPending(appliedMap, shapeId, entry) {
  if (!appliedMap) return false;
  const live = entry && typeof entry.border === "string" ? entry.border.toLowerCase() : null;
  const was = appliedMap.get(shapeId) || null;
  return live !== was;
}
