<script>
  // Shared inline-SVG icon set (UI Icon System Foundation). Replaces the raw
  // Unicode/emoji glyphs (↶ ↷ 💡 ✕ − + ⤢ 🧲 ⤳ ✂ ▶ ▾ etc.) that were
  // standing in for real icon affordances across the app -- see the PR body
  // for the full inventory and rationale. Every icon shares one visual
  // language so the set reads as ONE system, not a hodgepodge: 24x24 grid,
  // ~1.75px stroke, round caps/joins, `stroke="currentColor"` + `fill="none"`
  // at the root so color always inherits from the surrounding text color /
  // theme.css tokens (--ink / --muted / --accent / --danger etc.) exactly
  // like every other themed control in this app -- no icon-specific color
  // ever needs to be set by a caller.
  //
  // Usage: <Icon name="undo" /> or <Icon name="close" size={14} class="x" />.
  // Unrecognized names fall back to a dashed rounded square (see `unknown`
  // below) rather than rendering nothing or throwing -- an empty icon slot
  // is easy to miss in review/QA, a visibly "this isn't a real icon" glyph
  // is not. It's the only dashed shape in the set for exactly that reason:
  // if you ever see a dashed square in the running app, a `name` typo'd.
  //
  // This is the FOUNDATION component -- several follow-up PRs wire it into
  // the other files still carrying raw glyphs (see MASTER_SCOPE.md / the PR
  // body's "still waiting on follow-up" list). Extending it for a new icon
  // is as simple as adding a key to ICONS below; keep new entries in the
  // same stroke weight / corner language as the existing ones.
  //
  // Only `play`/`pause` (and the small route-endpoint dots in `jump`) break
  // the stroke-only convention with a `fill="currentColor"` override --
  // solid triangles/bars are how play/pause buttons are universally read,
  // an outlined triangle reads as a "delta" or warning glyph instead.

  export let name;
  export let size = 18;

  // Raw inner-SVG markup per icon, keyed by name. Plain strings (not
  // per-icon Svelte components) so adding one is a one-line addition and
  // every icon renders through the exact same root <svg> (same viewBox,
  // stroke, size handling) below -- no per-icon drift possible. Content is
  // 100% author-controlled/static, never derived from user input, so the
  // {@html} below carries no injection risk.
  const ICONS = {
    // Curved "back"/"forward" arrows -- topbar undo/redo (App.svelte).
    // redo is undo mirrored left-right (reflecting an arc flips its sweep
    // flag: 1 -> 0) so the pair reads as deliberate opposites, not two
    // unrelated squiggles.
    undo: `<path d="M7 7L3 11L7 15"/><path d="M3 11H14A5 5 0 0 1 19 16"/>`,
    redo: `<path d="M17 7L21 11L17 15"/><path d="M21 11H10A5 5 0 0 0 5 16"/>`,

    // Onboarding hint bubble icon (Hint.svelte). Circular bulb + tapering
    // base rungs -- a real lightbulb silhouette, not an abstract stand-in.
    lightbulb: `<circle cx="12" cy="9" r="6"/><line x1="9.5" y1="15" x2="14.5" y2="15"/><line x1="9.5" y1="18" x2="14.5" y2="18"/><line x1="10.5" y1="21" x2="13.5" y2="21"/>`,

    // Dismiss / remove -- Hint.svelte's ✕, and every other close button
    // this PR doesn't touch yet (FontBrowser, ProjectsDrawer, FontCredits,
    // ContentStep, ManualPanel, DigitizePanel, EmbroideryField's simulator).
    close: `<line x1="6" y1="6" x2="18" y2="18"/><line x1="18" y1="6" x2="6" y2="18"/>`,

    // Zoom out / zoom in / generic "add" -- EmbroideryField's zoom control
    // and ContentStep's "+ Text"/"+ Image" affordances (follow-up work).
    minus: `<line x1="5" y1="12" x2="19" y2="12"/>`,
    plus: `<line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>`,

    // "Fit to hoop" -- four independent corner brackets, the standard
    // fit-to-frame/viewfinder idiom. EmbroideryField's ⤢.
    expand: `<path d="M4 9V4H9"/><path d="M15 4H20V9"/><path d="M20 15V20H15"/><path d="M9 20H4V15"/>`,

    // Auto-snap toggle -- EmbroideryField's 🧲. A horseshoe body (one
    // quarter-circle-based U) with a short cross-tick near each open tip
    // standing in for the traditional magnet color band.
    magnet: `<path d="M7 4V14A5 5 0 0 0 17 14V4"/><line x1="5.5" y1="8" x2="8.5" y2="8"/><line x1="15.5" y1="8" x2="18.5" y2="8"/>`,

    // Realistic-thread toggle (EmbroideryField's view toolbar). A big
    // four-point sparkle plus a small one -- "shine" is what that toggle
    // literally adds, since the realistic render is the lit-cylinder shading
    // in preview.js. Deliberately NOT the lightbulb: that one already means
    // "onboarding hint" on another surface, and one glyph meaning two
    // unrelated things is exactly the hodgepodge this set exists to avoid.
    sparkle: `<path d="M10 3C10 7 11 8 15 8C11 8 10 9 10 13C10 9 9 8 5 8C9 8 10 7 10 3Z"/><path d="M17 13C17 15.2 17.4 15.6 19.5 15.6C17.4 15.6 17 16 17 18.2C17 16 16.6 15.6 14.5 15.6C16.6 15.6 17 15.2 17 13Z"/>`,

    // "Show shape outlines" -- an open path with a node on each vertex,
    // which is literally what the toggle draws on the field. Nodes are
    // stroked rings rather than solid dots so it reads as an editable
    // outline (the `edit` pencil is about editing ONE boundary, this is
    // about seeing them all).
    nodes: `<path d="M6 17.5L12 6.5L18 14"/><circle cx="6" cy="17.5" r="2"/><circle cx="12" cy="6.5" r="2"/><circle cx="18" cy="14" r="2"/>`,

    // "Show jumps" (needle-up travel between stitch points) -- a dashed
    // route between two solid points. EmbroideryField's ⤳.
    jump: `<line x1="5" y1="19" x2="19" y2="5" stroke-dasharray="3 2.5"/><circle cx="5" cy="19" r="1.3" fill="currentColor" stroke="none"/><circle cx="19" cy="5" r="1.3" fill="currentColor" stroke="none"/>`,

    // "Show trims" / cut -- EmbroideryField's and DigitizePanel's ✂. Two
    // finger loops with blades crossing up to opposite top corners.
    scissors: `<circle cx="7" cy="17" r="2.3"/><circle cx="17" cy="17" r="2.3"/><line x1="8.6" y1="15.4" x2="19" y2="5"/><line x1="15.4" y1="15.4" x2="5" y2="5"/>`,

    // Stitch simulator play/pause -- EmbroideryField's ▶ / ⏸. Solid fill,
    // see the file-level note on why these two break the stroke-only rule.
    play: `<path d="M8 5.5L19 12L8 18.5Z" fill="currentColor" stroke="currentColor" stroke-linejoin="round"/>`,
    pause: `<rect x="7" y="5" width="3.5" height="14" rx="1" fill="currentColor" stroke="none"/><rect x="13.5" y="5" width="3.5" height="14" rx="1" fill="currentColor" stroke="none"/>`,

    // Dropdown/disclosure caret -- ThreadPicker's ▾ and DigitizePanel's
    // sequencer caret. Points down at rest; existing callers already rotate
    // an inline glyph 180deg via a CSS `.open` class (see ThreadPicker's
    // `.tp-chevron.open`) -- follow-up work should keep using that same
    // rotate-in-CSS pattern with this one icon rather than adding
    // direction-specific chevron variants.
    chevron: `<path d="M6 9L12 15L18 9"/>`,

    // Passed-step indicator -- StepNav's aria-hidden ✓.
    check: `<path d="M5 12.5L9.5 17L19 7"/>`,

    // Resize-warning banner -- DesignPanel's ⚠.
    warning: `<path d="M12 4L21 20H3Z" stroke-linejoin="round"/><line x1="12" y1="10" x2="12" y2="14.5"/><circle cx="12" cy="17.3" r="0.9" fill="currentColor" stroke="none"/>`,

    // "Sew earlier"/"Sew later" -- DigitizePanel's Layers-list and Sequencer
    // reorder buttons' ↑/↓ (moveShape/moveBlock, cross-layer moves). A plain
    // vertical stem with an arrowhead cap -- deliberately a DIFFERENT shape
    // family from `chevron` (reused, rotated, for the within-layer nudge
    // buttons below) so the two reorder mechanisms stay visually distinct at
    // a glance, same as the ↑/↓ vs ▲/▼ glyphs they replace.
    arrowUp: `<line x1="12" y1="18" x2="12" y2="7"/><path d="M7 12L12 7L17 12"/>`,
    arrowDown: `<line x1="12" y1="6" x2="12" y2="17"/><path d="M7 12L12 17L17 12"/>`,

    // Mark-as-not-sewn-again -- DigitizePanel's restored-enclosed-area ⦸
    // (unrestoreStitching). Standard circle-slash "exclude/forbid" mark.
    exclude: `<circle cx="12" cy="12" r="7.5"/><line x1="6.8" y1="17.2" x2="17.2" y2="6.8"/>`,

    // Undo a single applied merge/split -- DigitizePanel's ⎌ (undoMerge,
    // undoSplit; same glyph, same meaning: "revert this one action back to
    // its source shapes"). Deliberately its own shape, not a reuse of
    // `undo`/`redo` above -- those read as "step back in a linear sequence"
    // (the topbar's edit history), this is "revert one specific thing back
    // to how it started", so it gets a closed loop instead of an open arc.
    revert: `<path d="M5 12A7 7 0 1 0 7.5 6.5L5 9"/><path d="M5 5V9H9"/>`,

    // Edit this shape's boundary -- DigitizePanel's ✎. A simple closed-outline
    // pencil silhouette (tip lower-left, body upper-right), stroke-only like
    // everything else in this set.
    edit: `<path d="M15 5L19 9L8.5 19.5L4 20.5L5 16Z"/>`,
    // "Reset to original" -- ImagePanel's per-swatch thread-override reset
    // button (↺). A near-full circle arc with a corner arrowhead at its open
    // end -- reads unambiguously as "revert" without borrowing the topbar
    // undo/redo pair's straight-arrow language, which is a different action
    // (step back through history) from "discard this one override".
    reset: `<path d="M1 4L1 10L7 10"/><path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10"/>`,

    // Fallback for an unrecognized `name` -- see the file-level note above
    // for why a dashed placeholder (not nothing, not a crash) is the sane
    // choice here.
    unknown: `<rect x="4" y="4" width="16" height="16" rx="3" stroke-dasharray="3 3"/>`,
  };

  $: known = Object.prototype.hasOwnProperty.call(ICONS, name);
  $: svgInner = known ? ICONS[name] : ICONS.unknown;
</script>

<svg
  xmlns="http://www.w3.org/2000/svg"
  width={size}
  height={size}
  viewBox="0 0 24 24"
  fill="none"
  stroke="currentColor"
  stroke-width="1.75"
  stroke-linecap="round"
  stroke-linejoin="round"
  aria-hidden={$$restProps["aria-hidden"] ?? "true"}
  data-icon={name}
  data-icon-fallback={known ? undefined : "true"}
  {...$$restProps}
>{@html svgInner}</svg>
