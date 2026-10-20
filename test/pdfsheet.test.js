const test = require("node:test");
const assert = require("node:assert/strict");

const { buildWorksheetPDF } = require("../src/pdfsheet.js");

// Recording stand-in for jsPDF: no PDF is produced, we assert on what the
// layout code asked it to draw.
function installFakes() {
  const calls = { text: [], rect: [], fill: [], pages: 0, saved: null, image: [], font: [] };
  class FakeDoc {
    constructor(opts) { calls.ctor = opts; }
    setFontSize() {}
    setFont(f, w) { calls.font.push(w); }
    text(t, x, y) { calls.text.push({ t, x, y, page: calls.pages }); }
    splitTextToSize(s) { return String(s).split("|"); }
    addImage(...a) { calls.image.push(a); }
    setFillColor(r, g, b) { calls.fill.push([r, g, b]); }
    rect(x, y, w, h, m) { calls.rect.push({ x, y, w, h, m }); }
    addPage() { calls.pages++; }
    save(n) { calls.saved = n; }
  }
  const ctx = new Proxy({}, { get: () => () => {}, set: () => true });
  globalThis.window = { jspdf: { jsPDF: FakeDoc } };
  globalThis.document = {
    createElement: () => ({ width: 0, height: 0, getContext: () => ctx, toDataURL: () => "data:png" }),
  };
  return calls;
}

function build(design, meta) {
  const calls = installFakes();
  const doc = buildWorksheetPDF(design, meta);
  return { calls, doc, lines: calls.text.map((c) => c.t) };
}

const color = (name, r, g, b) => ({ name, r, g, b });

test("saves under the given fileName, defaulting to worksheet.pdf, and returns the doc", () => {
  assert.equal(build({}, undefined).calls.saved, "worksheet.pdf");
  const r = build({}, { fileName: "x.pdf" });
  assert.equal(r.calls.saved, "x.pdf");
  assert.ok(r.doc);
  assert.deepEqual(r.calls.ctor, { unit: "in", format: "letter" });
});

test("stats: dimensions, grouped stitch count, colour count", () => {
  const { lines } = build({
    widthMM: 25.4, heightMM: 50.8, stitchCount: 26676, colors: [color("a", 0, 0, 0)],
  });
  assert.ok(lines.includes("Dimensions: 1.00 in x 2.00 in  (25.4 mm x 50.8 mm)"));
  assert.ok(lines.includes("Stitch count: 26,676"));
  assert.ok(lines.includes("Color count: 1"));
});

test("colorCount falls back to colors.length; explicit colorCount wins", () => {
  const cs = [color("a", 1, 2, 3), color("b", 4, 5, 6)];
  assert.ok(build({ colors: cs }).lines.includes("Color count: 2"));
  assert.ok(build({ colors: cs, colorCount: 7 }).lines.includes("Color count: 7"));
});

test("null/empty design does not throw and prints zeros", () => {
  const { lines } = build(null);
  assert.ok(lines.includes("Stitch count: 0"));
  assert.ok(lines.includes("Color count: 0"));
  assert.ok(lines.includes("Dimensions: 0.00 in x 0.00 in  (0.0 mm x 0.0 mm)"));
});

test("optional placement / hoop / hoopNote lines appear only when given", () => {
  const none = build({}).lines;
  assert.ok(!none.some((l) => /^(Placement|Hoop):/.test(l)));
  const { lines } = build({}, {
    garmentLabel: "Left Chest",
    hoop: { label: "5x7", widthMm: 130, heightMm: 180 },
    hoopNote: "Too big|for hoop",
  });
  assert.ok(lines.includes("Placement: Left Chest"));
  assert.ok(lines.includes("Hoop: 5x7 (130 mm x 180 mm)"));
  assert.ok(lines.includes("Too big") && lines.includes("for hoop"));
});

test("hoop without dimensions prints the label alone; without label prints nothing", () => {
  assert.ok(build({}, { hoop: { label: "Mega" } }).lines.includes("Hoop: Mega"));
  assert.ok(!build({}, { hoop: { widthMm: 1, heightMm: 2 } }).lines.some((l) => l.startsWith("Hoop:")));
});

test("sew: trims 0 is printed (absence != zero); thread only when > 0", () => {
  assert.ok(build({}, { sew: { trims: 0 } }).lines.includes("Trims: 0"));
  assert.ok(!build({}).lines.some((l) => l.startsWith("Trims:")));
  const withThread = build({}, { sew: { trims: 2, threadM: 2.54 } }).lines;
  assert.ok(withThread.includes("Thread: 2.5 m (estimate)"));
  assert.ok(!build({}, { sew: { threadM: 0 } }).lines.some((l) => l.startsWith("Thread:")));
});

test("run time line carries basis, machine label and custom spm", () => {
  const def = build({ stitchCount: 6500 }, {}).lines.find((l) => l.startsWith("Run time:"));
  assert.match(def, /^Run time: ~\d+ min at 650 spm \(incl\. trims\)$/);
  const custom = build({ stitchCount: 6500 }, { sew: { spm: 1000, machineLabel: "Acme" } })
    .lines.find((l) => l.startsWith("Run time:"));
  assert.match(custom, / on your Acme at 1,000 spm /);
  // non-positive spm falls back to the planning rate
  const bad = build({ stitchCount: 6500 }, { sew: { spm: 0 } }).lines.find((l) => l.startsWith("Run time:"));
  assert.match(bad, /at 650 spm/);
});

test("bobbin line: ~x m, or 'under 0.1' for tiny thread; absent without thread", () => {
  const big = build({}, { sew: { threadM: 10 } }).lines.find((l) => l.startsWith("Bobbin:"));
  assert.equal(big, "Bobbin: ~6.0 m (3/5 of top thread)");
  const tiny = build({}, { sew: { threadM: 0.05 } }).lines.find((l) => l.startsWith("Bobbin:"));
  assert.equal(tiny, "Bobbin: under 0.1 m (3/5 of top thread)");
  assert.ok(!build({}).lines.some((l) => l.startsWith("Bobbin:")));
});

test("quoteLines: strings only, empties skipped, non-array ignored", () => {
  const { lines } = build({}, { quoteLines: ["Cost: $5", "", 3, null, "Margin: 40%"] });
  assert.ok(lines.includes("Cost: $5") && lines.includes("Margin: 40%"));
  assert.ok(!lines.includes("3"));
  assert.doesNotThrow(() => build({}, { quoteLines: "nope" }));
});

test("hooping rows: unknown/absent garment prints none; escalation past cutaway threshold", () => {
  const { hoopingAdvice, hoopingLine } = require("../src/fabrics.js");
  assert.ok(!build({}, {}).lines.some((l) => l.startsWith("Stabilizer:")));
  assert.ok(!build({}, { garmentId: "no-such-garment" }).lines.some((l) => l.startsWith("Stabilizer:")));
  const id = Object.keys(require("../src/fabrics.js").GARMENT_FABRIC)[0];
  const lines = build({ stitchCount: 30000 }, { garmentId: id }).lines;
  for (const row of hoopingAdvice(id, 30000).rows) assert.ok(lines.includes(hoopingLine(row)));
});

test("thread list: numbered, named, default name, swatch fill colours clamped", () => {
  const { calls, lines } = build({
    colors: [color("Red", 255, 0, 0), { r: 300, g: -5, b: 12.9 }],
  });
  assert.ok(lines.includes("1. Red"));
  assert.ok(lines.includes("2. Color 2"));
  assert.deepEqual(calls.fill[0], [255, 0, 0]);
  assert.deepEqual(calls.fill[1], [255, 0, 12]);
});

test("a null colour entry throws (current behaviour: rgbCss tolerates null, label read does not)", { todo: "colors[i] null crashes at color.name; rgbCss's null guard is unreachable" }, () => {
  assert.doesNotThrow(() => build({ colors: [null] }));
});

test("chart label printed above the rows only when given", () => {
  const { lines } = build({ colors: [color("A", 0, 0, 0)] }, { chartLabel: "Isacord 40" });
  const ci = lines.indexOf("Chart: Isacord 40");
  assert.ok(ci > lines.indexOf("Thread Sequence") && ci < lines.indexOf("1. A"));
  assert.ok(!build({ colors: [color("A", 0, 0, 0)] }).lines.some((l) => l.startsWith("Chart:")));
});

test("pagination: every text/swatch stays inside the bottom margin; no blank trailing page", () => {
  for (const n of [0, 1, 7, 30, 31, 40, 120]) {
    const colors = Array.from({ length: n }, (_, i) => color("c" + i, i, i, i));
    const { calls } = build({ colors }, { chartLabel: "X", hoopNote: "n" });
    for (const t of calls.text) assert.ok(t.y <= 11 - 0.5 + 1e-9, `n=${n} y=${t.y}`);
    // last page index holds at least one text call
    assert.ok(calls.text.some((t) => t.page === calls.pages), `n=${n} trailing blank page`);
  }
});

test("long list continues on following pages in order with all rows present", () => {
  const colors = Array.from({ length: 60 }, (_, i) => color("c" + i, 0, 0, 0));
  const { calls, lines } = build({ colors });
  assert.ok(calls.pages >= 1);
  for (let i = 1; i <= 60; i++) assert.ok(lines.includes(i + ". c" + (i - 1)));
});

test("thread heading is not stranded: heading and first row share a page", () => {
  for (let n = 1; n <= 3; n++) {
    const colors = Array.from({ length: n }, () => color("z", 0, 0, 0));
    for (const extra of [0, 1, 2, 3, 4, 5, 6, 7, 8]) {
      const quoteLines = Array.from({ length: extra * 2 }, (_, i) => "q" + i);
      const { calls } = build({ colors }, { quoteLines });
      const head = calls.text.find((t) => t.t === "Thread Sequence");
      const row = calls.text.find((t) => t.t === "1. z");
      assert.equal(head.page, row.page, `extra=${extra}`);
    }
  }
});

test("image is square, capped at 5.5 in, drawn with MEDIUM zlib", () => {
  const { calls } = build({});
  const [, fmt, x, , w, h, , comp] = calls.image[0];
  assert.equal(fmt, "PNG");
  assert.equal(x, 0.5);
  assert.equal(w, 5.5);
  assert.equal(h, 5.5);
  assert.equal(comp, "MEDIUM");
});
