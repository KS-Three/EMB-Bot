// The help copy behind every "?" in the Studio (2026-09-30, Kent's ask: hover
// a setting and get "a brief description that pops up with what it does and
// how it changes the digitizing").
//
// ONE FILE, ONE SHAPE. Every entry has the same three sentences, in the same
// order, so a customer learns to read them once:
//   what     — what the setting IS, in embroidery terms, one sentence.
//   changes  — what moves in the stitch-out when you change it.
//   when     — when you would touch it, and when you would leave it alone.
// Plain words, no engine vocabulary the customer has not met on screen.
// `title` is the name as it appears on the control (or the fuller name where
// the control's label is abbreviated), so the popover reads as a caption of
// the thing under the pointer.
//
// This is DATA, deliberately: Kent edits the wording here without touching a
// component, and lib/settingHelp.spec.js holds every entry to the shape.
// Components attach an entry with the `tip` action (lib/tip.js) by key.

export const HELP = {
  // ---- Digitize panel: design settings ----------------------------------
  designWidth: {
    title: "Design width",
    what: "How wide the finished embroidery will be, in millimetres — the artwork is scaled to this before anything is stitched.",
    changes: "Everything scales with it: stitch count, thread used, and how fine the detail can be. Small text and thin lines that sew cleanly at 100 mm can fall below what a needle can sew at 50 mm.",
    when: "Set it to the space on the garment first; the placement box on the canvas shows the limit for the garment you picked.",
  },
  colors: {
    title: "Colors (max)",
    what: "The most thread colours the digitizer may use — it merges the artwork's colours down to this many.",
    changes: "Fewer colours means fewer thread changes and trims on the machine and a cleaner sew; more keeps subtle shades, but every extra colour is another spool to load.",
    when: "Match it to the artwork: a two-colour logo wants 2. Lower it if the preview shows near-identical shades sewn as separate blocks.",
  },
  satinThin: {
    title: "Satin for thin shapes",
    what: "Sews narrow shapes — letter strokes, outlines, thin bars — as satin columns (side-to-side stitches) instead of fill rows.",
    changes: "Satin gives thin shapes a smooth, raised, glossy look that follows their direction. Off, they sew as flat rows and can look ragged when narrower than a few millimetres.",
    when: "Leave it on for lettering and line art. Turn it off only if a shape the digitizer called thin is really a wide area that should sew flat.",
  },
  evenWidths: {
    title: "Even out lettering widths",
    what: "Gives every letter of a detected word the same satin column width, taken from the word as a whole.",
    changes: "A letter traced fatter or thinner than its neighbours is evened out to them. Off, each letter sews the width it was drawn at.",
    when: "Turn it on when lettering looks lumpy in the preview. Leave it off for fonts whose strokes vary on purpose.",
  },
  fillAngle: {
    title: "Fill angle",
    what: "The direction the rows of thread run inside filled areas.",
    changes: "Auto picks a direction per shape along its longest axis, so fills follow their shapes. A fixed angle makes every shape sew the same way, which reads more uniform on flat logos but can leave wide shapes with visible banding.",
    when: "Stay on Auto unless the preview shows neighbouring fills fighting each other; then try 45°.",
  },
  border: {
    title: "Border",
    what: "Whether each shape gets an outline stitched around its edge.",
    changes: "Automatic lets the digitizer decide by artwork type (outlines on photos, none on flat art). Auto adds a satin outline where one fits and a bean line — a light triple-run — where it doesn't. Bean is always the light line. None leaves edges bare.",
    when: "Add a border when fill edges look fuzzy against the fabric or the piece will be washed hard. Skip it on small text, where it thickens the letters.",
  },
  designEdge: {
    title: "Design edge",
    what: "An outline around the outside of the whole design — its silhouette — rather than around each shape.",
    changes: "Leave open lets fill rows end at the edge, which can fray on stretchy or towelling fabric. Bean cap adds a light line; Satin cap a full column, the patch look.",
    when: "Cap it on patches, towels and anything washed often. Leave it open for lettering and light logos on flat shirts.",
  },
  photoReading: {
    title: "How the artwork was read",
    what: "The digitizer decides this on its own: flat art sews as solid colour regions, shaded art in blended thread shades, and a photo with a face in it sews as flat art, which reads best for a face.",
    changes: "Nothing here is a switch. Add fine detail lines, offered on photos and shaded art, stitches a layer of fine lines on top: more stitches, more detail up close.",
    when: "If the reading looks wrong for your artwork, the fix is cleaner artwork — solid colours and no shading for a logo, a clear face for a portrait — not a setting.",
  },

  // ---- Digitize panel: per-shape controls -------------------------------
  shapeTier: {
    title: "Stitch type",
    what: "How this one shape is sewn. Auto is the digitizer's own choice, shown in brackets.",
    changes: "Satin: smooth side-to-side columns, for narrow shapes. Fill: rows of thread, for areas. Run: a single line. Sketch, Streamline, Cross-hatch, Wave, Chevron and Brick are decorative fill textures.",
    when: "Override when a shape sewed the wrong way — a thin one as fill, or a wide one as satin that is broader than a needle can throw.",
  },
  shapeAngle: {
    title: "Fill angle, this shape",
    what: "The direction of the thread rows inside this shape only.",
    changes: "Overrides the design-wide fill angle for this one shape.",
    when: "Turn it so rows run along the shape's long axis, or set it against a neighbour so the two read as separate pieces.",
  },
  shapeUnderlay: {
    title: "Underlay",
    what: "The foundation stitches sewn under this shape's fill, before the fill itself.",
    changes: "Auto follows the fabric you picked. None is fastest but can sink into soft fabric. Edge run holds the outline; Center run backs the middle; Edge + lattice or zigzag steady large areas and stop them puckering.",
    when: "Reach for lattice or zigzag on knits, towels and big fills. None only on stable fabric where the stitch count matters.",
  },
  shapeBorder: {
    title: "Border, this shape",
    what: "An outline around this shape only.",
    changes: "Design uses the setting above. No border removes it. Auto adds satin where it fits and bean where it doesn't; Bean is always the light line. A shape sewn as satin takes no border either way.",
    when: "Add one to a fill whose edge looks soft. Remove it from small text, where it thickens the letters.",
  },
  stitchWidth: {
    title: "Stitch width",
    what: "The width of the satin column this shape sews, in millimetres.",
    changes: "Wider makes small letters bolder and heavier; narrower opens their counters and lightens them. Empty uses the engine's own measurement.",
    when: "Adjust when lettering looks too thin or too heavy in the preview. The whole word changes together unless 'whole word' is off.",
  },
  wholeWord: {
    title: "Whole word",
    what: "Applies a stitch width change to every letter of this word at once.",
    changes: "On, one width for the whole word. Off, only this letter changes.",
    when: "Leave it on for normal lettering. Turn it off to fix one odd letter.",
  },

  // ---- Canvas toolbar ---------------------------------------------------
  fitToHoop: {
    title: "Fit to hoop",
    what: "Zooms back out so the whole hoop is on screen.",
    changes: "The view only — nothing about the design changes.",
    when: "After zooming in to inspect stitches.",
  },
  autoSnap: {
    title: "Auto-snap",
    what: "Snaps a dragged design to the hoop's centre lines and to the edges of other elements.",
    changes: "Placement only. Hold Alt while dragging to place freely for one drag.",
    when: "Leave it on for centred designs. Turn it off for a deliberate off-centre placement.",
  },
  outlines: {
    title: "Shape outlines",
    what: "Draws the outline of every shape the digitizer recognised over the stitch-out.",
    changes: "The view only. Each outline is clickable: select one to drag its nodes, press Delete to remove it, or right-click to add a border.",
    when: "Turn it on to see how the artwork was split into shapes. Off for a clean look at the stitching — a shape still outlines itself when you point at it.",
  },
  jumps: {
    title: "Jumps",
    what: "Shows where the needle travels between shapes without stitching, as dashed lines.",
    changes: "The view only. A long jump is thread lying on the back that the machine must trim.",
    when: "Check it before exporting a design with many small shapes.",
  },
  trims: {
    title: "Trims",
    what: "Marks every place the machine will cut the thread.",
    changes: "The view only. Each trim is two to three seconds of machine time; the quality check counts them per 1,000 stitches.",
    when: "If the count is high, merge or remove the smallest shapes.",
  },
  flatView: {
    title: "Stitches view",
    what: "Draws every stitch as a plain line, without the thread's sheen.",
    changes: "The view only. Gaps, density and the direction of each fill are easier to see than in the realistic render.",
    when: "Use it to judge the engineering — coverage, banding, where satin turns — before you judge the look.",
  },
  realistic: {
    title: "Realistic view",
    what: "Renders the thread with its sheen and thickness, the way it looks sewn.",
    changes: "The view only. Off, the flat view shows stitch structure and coverage more honestly — gaps and density are easier to see.",
    when: "Realistic to judge the look; flat to judge the engineering.",
  },
  originalView: {
    title: "Original view",
    what: "Shows the artwork you uploaded in place of the stitches.",
    changes: "The view only. Nothing about the design or the file changes.",
    when: "Flip between this and the stitches to check the digitizing against what you asked for.",
  },
  simulator: {
    title: "Stitch simulator",
    what: "Plays the design in the order the machine will sew it.",
    changes: "The view only. Editing is paused while it runs.",
    when: "Watch it to understand the colour sequence and where the trims happen.",
  },

  // ---- Text step --------------------------------------------------------
  letterSpacing: {
    title: "Letter spacing",
    what: "Extra space between letters, in millimetres.",
    changes: "Positive spreads the letters; negative tightens them until they touch, which then sews as one block.",
    when: "Open it up on small lettering so the satin columns don't crowd. Tighten it for a logo look.",
  },
  curve: {
    title: "Curve",
    what: "Bends the text along an arc.",
    changes: "Positive arcs upward (a smile), negative downward (a frown). The letters stay upright to the arc.",
    when: "For hats and rounded logos. Keep it small on long words, or the ends distort.",
  },
  rotation: {
    title: "Rotation",
    what: "Turns the whole element on the hoop.",
    changes: "Placement only. The stitches are generated again, so satin still runs across the letters.",
    when: "For sleeves and diagonal placements.",
  },
};

// The keys, for components and the spec.
export const HELP_KEYS = Object.keys(HELP);

// Plain-text form, for a `title` fallback or a screen reader: the three
// sentences in order, labelled so the middle two read as what they are.
export function helpText(key) {
  const h = HELP[key];
  if (!h) return "";
  return `${h.title}. ${h.what} Changes: ${h.changes} When: ${h.when}`;
}
