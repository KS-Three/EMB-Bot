const assert = require("node:assert");
const { test } = require("node:test");
const exp = require("../src/exp.js");
test("stitch deltas signed", () => {
  const out = exp.encodeEXP({ stitches:[{x:0,y:0,type:"stitch"},{x:5,y:-3,type:"stitch"}], colors:[{r:0,g:0,b:0,name:"a"}] });
  // first record from (0,0) is [0,0]; second is [5, -3 => 0xFD]
  assert.deepStrictEqual(Array.from(out.slice(0,4)), [0,0,5,0xFD]);
});
test("trim emits Melco 4-byte trim control 0x80 0x80 0x07 0x00", () => {
  // The 2-byte 0x80 0x03 form is not a control code standard (pyembroidery-
  // convention) readers know -- see docs/pes-crossval-verdict-2026-08-04.md
  // section 4. 0x80-prefixed records are fixed 4 bytes.
  const out = exp.encodeEXP({ stitches:[{x:0,y:0,type:"stitch"},{x:0,y:0,type:"trim"}], colors:[{r:0,g:0,b:0,name:"a"}] });
  const arr = Array.from(out);
  let found=false;
  for(let i=0;i<arr.length-3;i++){
    if(arr[i]===0x80&&arr[i+1]===0x80&&arr[i+2]===0x07&&arr[i+3]===0x00) found=true;
  }
  assert.ok(found, "expected 0x80 0x80 0x07 0x00 trim control");
});
test("trim tracks position; delta sum correct after trim", () => {
  // trim moves +40,-20 then a stitch to (50,-20): stitch delta must be +10,0
  const out = exp.encodeEXP({ stitches:[
    {x:0,y:0,type:"stitch"},
    {x:40,y:-20,type:"trim"},
    {x:50,y:-20,type:"stitch"},
  ], colors:[{r:0,g:0,b:0,name:"a"}] });
  const arr = Array.from(out);
  // last record is the stitch: 2 bytes [dx, dy]. dx=10, dy=0.
  assert.deepStrictEqual(arr.slice(-2), [10, 0]);
});
test("color change bytes present", () => {
  const out = exp.encodeEXP({ stitches:[{x:0,y:0,type:"stitch"},{x:0,y:0,type:"color"},{x:1,y:0,type:"stitch"}], colors:[{},{}] });
  const arr = Array.from(out);
  // contains 0x80,0x01 sequence
  let found=false; for(let i=0;i<arr.length-1;i++){ if(arr[i]===0x80&&arr[i+1]===0x01) found=true; }
  assert.ok(found);
});
test("terminal end record is not encoded as a stitch (2026-08-06 fix)", () => {
  // stitchModel.js always appends {type:"end"} as the last stitches-array
  // entry -- a design-list sentinel, not a real stitch. Before this fix
  // encodeEXP fell through to the generic stitch path for any type it didn't
  // recognize, writing "end" as a real zero-delta [0,0] record that standard
  // readers decode as one extra phantom stitch. pes.js's own encoder already
  // stops at "end" the same way (src/pes.js, both its CSewSeg loop and its
  // decoder). See docs/pes-crossval-verdict-2026-08-04.md section 4.
  const withEnd = exp.encodeEXP({ stitches:[
    {x:0,y:0,type:"stitch"},
    {x:5,y:-3,type:"stitch"},
    {x:5,y:-3,type:"end"},
  ], colors:[{r:0,g:0,b:0,name:"a"}] });
  const withoutEnd = exp.encodeEXP({ stitches:[
    {x:0,y:0,type:"stitch"},
    {x:5,y:-3,type:"stitch"},
  ], colors:[{r:0,g:0,b:0,name:"a"}] });
  // "end" must produce byte-identical output to simply omitting it -- not
  // one more [0,0] stitch record appended.
  assert.deepStrictEqual(Array.from(withEnd), Array.from(withoutEnd));
  assert.strictEqual(withEnd.length, 4, "two 2-byte stitch records, nothing more");
});
test("a record after end is never encoded (end is terminal, matching pes.js)", () => {
  const out = exp.encodeEXP({ stitches:[
    {x:0,y:0,type:"stitch"},
    {x:5,y:-3,type:"end"},
    {x:9,y:9,type:"stitch"},
  ], colors:[{r:0,g:0,b:0,name:"a"}] });
  // Only the one real stitch before "end" -- the trailing stitch after it
  // (which should never occur in practice, but pes.js's loop unconditionally
  // breaks rather than trusting that) must not appear either.
  assert.strictEqual(out.length, 2);
  assert.deepStrictEqual(Array.from(out), [0, 0]);
});

// ---- a stitch that follows travel ----------------------------------------
//
// THE CHAIN RULE, in the third encoder. dst.js has had it since 2026-09-07 and
// pes.js since 2026-09-12: a move splits into STITCHES only when it CONTINUES
// a sewn run. The move to the first stitch after a jump, a trim, a colour
// change or the start of the file is TRAVEL, and is laid as jumps up to its
// last record, which is the stitch.
//
// exp.js was the encoder dst.js was matched to that day ("a stitch splits
// into stitches") and it never got the second half: it split EVERY stitch
// record into stitches. So where a stitch lay more than one record from where
// travel ended, the EXP put the needle down part-way along a move the DST and
// the PES travel. Found 2026-10-06 by the independent re-measure of
// `cutFloats`, on one stream written three ways:
//
//   j0,0 s0,0 s30,0 j230,0 s430,0 s460,0
//   DST  J0 S0 S30 J100 J100 J100 S100 S30
//   EXP  J0 S0 S30 J100 J100 S100 S100 S30   <- a needle hole at x=330
//   PES  J0 S0 S30 J200 S200 S30
//
// The first four tests are dst.test.js's own, re-aimed at this file's bytes
// as pes.test.js re-aimed them: one rule, three encoders, and no way to
// satisfy one encoder's idea of it and not another's.

// The file's records, read from the format: a stitch is two signed bytes, and
// a first byte of 0x80 opens a four-byte control (01 colour change, 04 jump,
// 80 trim).
function expRecords(design) {
  const bytes = exp.encodeEXP(design), out = [], s8 = (v) => (v > 127 ? v - 256 : v);
  for (let i = 0; i < bytes.length;) {
    if (bytes[i] !== 0x80) { out.push({ kind: "stitch", dx: s8(bytes[i]), dy: s8(bytes[i + 1]) }); i += 2; continue; }
    const code = bytes[i + 1];
    if (code === 0x04) out.push({ kind: "jump", dx: s8(bytes[i + 2]), dy: s8(bytes[i + 3]) });
    else if (code === 0x01) out.push({ kind: "color", dx: 0, dy: 0 });
    else if (code === 0x80) out.push({ kind: "trim", dx: 0, dy: 0 });
    else assert.fail("a control no reader knows: 0x" + code.toString(16));
    i += 4;
  }
  return out;
}
// Where the needle goes down, in order.
function holesOf(records) {
  const out = [];
  let x = 0, y = 0;
  for (const r of records) { x += r.dx; y += r.dy; if (r.kind === "stitch") out.push([x, y]); }
  return out;
}
const sewn = (design) => holesOf(expRecords(design)).length;
const BLACK = [{ r: 0, g: 0, b: 0 }, { r: 1, g: 1, b: 1 }];
// "j0,0 s30,0 t30,0 c30,0" -> stream records
const stream = (text) => text.split(" ").map((t) => {
  const [x, y] = t.slice(1).split(",").map(Number);
  return { x, y, type: { j: "jump", s: "stitch", t: "trim", c: "color" }[t[0]] };
});

test("a long move INSIDE a stitch run is sewn, not travelled", () => {
  const near = { stitches: stream("j0,0 s0,0 s100,0"), colors: BLACK };
  const far = { stitches: stream("j0,0 s0,0 s300,0"), colors: BLACK };
  assert.strictEqual(sewn(near), 2);
  assert.strictEqual(sewn(far), 4, "300 units needs three records, all of them stitches");
  assert.deepStrictEqual(expRecords(far).map((r) => r.kind), ["jump", "stitch", "stitch", "stitch", "stitch"]);
});

test("the move to the FIRST stitch is travel, however far", () => {
  // Nothing to sew between where the needle was and where the design begins.
  // An imported stitch file whose first record is a stitch is exactly this:
  // the builder centres it and moves it to where it was placed, and the
  // writer starts at the middle of the hoop.
  const d = { stitches: stream("s400,500 s450,500"), colors: BLACK };
  assert.strictEqual(sewn(d), 2);
  assert.deepStrictEqual(holesOf(expRecords(d)), [[400, 500], [450, 500]]);
  // However far: 39 cm from the origin, and 33.5 cm from where a jump landed,
  // the longest such move a shipped lane was seen to lay (a float across a
  // drawn shape set to satin, on a full back).
  assert.deepStrictEqual(holesOf(expRecords({ stitches: stream("s3000,-2500 s3050,-2500"), colors: BLACK })), [[3000, -2500], [3050, -2500]]);
  assert.deepStrictEqual(holesOf(expRecords({ stitches: stream("j0,0 s0,0 j1500,-900 s-1855,-900 s-1855,-870"), colors: BLACK })),
    [[0, 0], [-1855, -900], [-1855, -870]]);
});

test("a trim and a colour change both cut the chain", () => {
  for (const cut of ["t50,0", "c50,0", "t50,0 c50,0"]) {
    const d = { stitches: stream(`j0,0 s0,0 s50,0 ${cut} s400,0 s450,0`), colors: BLACK };
    assert.strictEqual(sewn(d), 4, cut + " must not leave the next long move sewing across the garment");
    assert.deepStrictEqual(holesOf(expRecords(d)), [[0, 0], [50, 0], [400, 0], [450, 0]]);
  }
});

test("a long JUMP is still a jump", () => {
  const d = { stitches: stream("j0,0 s0,0 j900,0 s950,0"), colors: BLACK };
  assert.strictEqual(sewn(d), 2);
});

test("a stitch far from where a JUMP landed is travelled to, as the DST and the PES do (found 2026-10-06)", () => {
  const d = { stitches: stream("j0,0 s0,0 s30,0 j230,0 s430,0 s460,0"), colors: BLACK };
  const recs = expRecords(d);
  assert.deepStrictEqual(holesOf(recs), [[0, 0], [30, 0], [430, 0], [460, 0]], "no needle hole at x=330");
  // The DST's own records for this stream, to the record.
  assert.deepStrictEqual(recs.map((r) => r.kind[0].toUpperCase() + r.dx).join(" "), "J0 S0 S30 J100 J100 J100 S100 S30");
  // Where it comes from in a real design: the shape tool's satin floats to a
  // far arm and sews back where it was (a four-point star, 20 mm).
  const star = { stitches: stream("j-93,2 s-93,2 j98,0 s-98,0 s-98,30"), colors: BLACK };
  assert.deepStrictEqual(holesOf(expRecords(star)), [[-93, 2], [-98, 0], [-98, 30]], "no needle hole in the middle of the star");
  // A jump that moves nothing cuts the chain like any other: the satin lays
  // one where a stroke ends on the point the next begins, and the stitch
  // after it can be far. (Found by the independent re-measure: a writer that
  // let such a jump keep the chain passed every test here and sewed again.)
  const onTheSpot = expRecords({ stitches: stream("j0,0 s0,0 s30,0 j30,0 s430,0"), colors: BLACK });
  assert.deepStrictEqual(holesOf(onTheSpot), [[0, 0], [30, 0], [430, 0]]);
  assert.deepStrictEqual(onTheSpot.map((r) => r.kind[0].toUpperCase() + r.dx).join(" "), "J0 S0 S30 J0 J100 J100 J100 S100");
  for (const cut of ["t30,0", "c30,0", "j30,0 j30,0"]) {
    assert.deepStrictEqual(holesOf(expRecords({ stitches: stream(`j0,0 s0,0 s30,0 ${cut} s430,0`), colors: BLACK })), [[0, 0], [30, 0], [430, 0]], cut);
  }
});

test("travel into a run is jumps up to its last record, and lands exactly", () => {
  const d = { stitches: stream("j0,0 s0,0 t0,0 s-437,289 s-437,300"), colors: BLACK };
  const recs = expRecords(d), i = recs.findIndex((r) => r.kind === "trim");
  const travel = recs.slice(i + 1, recs.length - 1);
  assert.ok(travel.length > 1, "437 units is more than one record");
  assert.deepStrictEqual(travel.map((r) => r.kind), travel.map((_, k) => (k === travel.length - 1 ? "stitch" : "jump")));
  assert.deepStrictEqual(travel.reduce((a, r) => [a[0] + r.dx, a[1] + r.dy], [0, 0]), [-437, 289]);
  let x = 0, y = 0;
  for (const r of travel) {
    x += r.dx; y += r.dy;
    assert.ok(Math.abs(r.dx) <= 121 && Math.abs(r.dy) <= 121, "each record within one DST record, as before the rule");
    assert.ok(Math.abs(-437 * y - 289 * x) / Math.hypot(437, 289) < 1, `(${x},${y}) is off the line of the move`);
  }
});

test("no stitch record carries more than 12.1 mm, sewn or reached by travel; a jump keeps the record's reach", () => {
  // Where a move is split did not change with the chain rule, only what the
  // records before the last are. A stitch 125 units from where a jump landed
  // is still two records, as it was and as the DST lays it: now a jump and a
  // stitch. One stitch record of 125 would be a kind of record no EXP of this
  // repo has held since Kent's ruling of 2026-09-13 (split at 121); pes.js
  // lets travel's last record run to PEC's reach, and that is not copied here.
  const afterTravel = expRecords({ stitches: stream("j0,0 s0,0 j200,0 s325,0"), colors: BLACK });
  assert.deepStrictEqual(afterTravel.slice(-2), [{ kind: "jump", dx: 63, dy: 0 }, { kind: "stitch", dx: 62, dy: 0 }]);
  assert.strictEqual(afterTravel.filter((r) => r.kind === "stitch").length, 2);
  // Sewn, the same 125 is two stitches: 121 is what may be sewn.
  const chained = expRecords({ stitches: stream("j0,0 s0,0 s125,0"), colors: BLACK });
  assert.deepStrictEqual(chained.map((r) => r.kind[0] + r.dx).join(" "), "j0 s0 s63 s62");
  // And a jump of 12.7 mm is one record, a trim's move too: travel that ends
  // on no stitch keeps the format's own reach.
  const jump = expRecords({ stitches: stream("j0,0 s0,0 j127,-127 s127,-127 t0,0 s0,0"), colors: BLACK });
  assert.deepStrictEqual(jump.map((r) => r.kind[0] + r.dx + "," + r.dy).join(" "), "j0,0 s0,0 j127,-127 s0,0 t0,0 j-127,127 s0,0");
  for (const far of ["j0,0 s0,0 j200,0 s325,0", "s400,500 s450,500", "j0,0 s0,0 t0,0 s-437,289", "j0,0 s0,0 s125,0", "j0,0 s0,0 c0,0 s122,-127"]) {
    for (const r of expRecords({ stitches: stream(far), colors: BLACK })) {
      if (r.kind === "stitch") assert.ok(Math.abs(r.dx) <= 121 && Math.abs(r.dy) <= 121, `${far}: a stitch record of (${r.dx},${r.dy})`);
    }
  }
});

test("the EXP puts the needle down where the DST does", () => {
  // The DST's records, read with the importer's own bit table.
  const { decodeDelta } = require("../src/dstimport.js");
  const dst = require("../src/dst.js");
  const dstRecords = (design) => {
    const bytes = dst.encodeDST(design), out = [];
    for (let i = 512; i + 2 < bytes.length && bytes[i + 2] !== 0xf3; i += 3) {
      const [dx, dy] = decodeDelta(bytes[i], bytes[i + 1], bytes[i + 2]), flags = bytes[i + 2] & 0xc0;
      out.push({ kind: flags === 0xc0 ? "color" : flags ? "jump" : "stitch", dx, dy });
    }
    return out;
  };
  // The thread a reader sees: from one needle hole to the next when nothing
  // stands between their two records.
  const threadOf = (records) => {
    const out = [];
    let x = 0, y = 0, sewing = false;
    for (const r of records) {
      if (r.kind === "stitch" && sewing) out.push(`${x},${y}>${x + r.dx},${y + r.dy}`);
      x += r.dx; y += r.dy;
      sewing = r.kind === "stitch";
    }
    return out;
  };
  const drawn = [
    "j0,0 s0,0 s30,0 j230,0 s430,0 s460,0",
    "j-93,2 s-93,2 j98,0 s-98,0 s-98,30",
    "s400,300 s430,300",
    "j0,0 s0,0 s30,0 t30,0 s430,-260 s460,-260",
    "j0,0 s0,0 s30,0 t30,0 c30,0 s-900,700 s-900,650",
    "j0,0 s0,0 s300,0 j310,0 s310,250 s310,-250",
    // a jump, a trim and a colour change that move nothing, then a far stitch
    "j0,0 s0,0 s30,0 j30,0 s430,0",
    "j0,0 s0,0 s30,0 t30,0 t30,0 s430,0",
    "j0,0 s0,0 s30,0 c30,0 c30,0 s-430,0",
    // a colour change that carries a move, as a stitch file's can: the DST
    // lays the move in the colour record, the EXP in the stitch after it
    "j0,0 s0,0 s30,0 c200,-150 s230,-150 s260,-150",
    "c300,300 s300,300 s330,300 c-200,0 s700,0",
    // a record of no type is a stitch to all three writers
    "j0,0 s0,0 u300,0 u300,40 j600,40 u900,40",
    // 33.5 cm and 39 cm of travel
    "j0,0 s0,0 j1500,-900 s-1855,-900 s-1855,-870",
    "s3000,-2500 s3050,-2500 t3050,-2500 s-900,1400",
  ];
  // And streams nobody chose: every kind of record, near, far and on the spot.
  let seed = 20261006;
  const rnd = () => { seed = (Math.imul(seed, 1103515245) + 12345) >>> 0; return seed / 4294967296; };
  for (let t = 0; t < 400; t++) {
    const recs = [];
    let x = 0, y = 0;
    for (let k = 4 + Math.floor(rnd() * 20); k > 0; k--) {
      const q = rnd(), reach = q < 0.1 ? 0 : q < 0.65 ? 60 : q < 0.95 ? 600 : 3500;
      const p = rnd(), kind = p < 0.57 ? "s" : p < 0.6 ? "u" : p < 0.8 ? "j" : p < 0.92 ? "t" : "c";
      // A colour change stands where the needle is, as every builder lays
      // it, three times in four; the fourth carries a move.
      if (kind !== "c" || rnd() < 0.25) { x += Math.round((rnd() - 0.5) * 2 * reach); y += Math.round((rnd() - 0.5) * 2 * reach); }
      recs.push(`${kind}${x},${y}`);
    }
    drawn.push(recs.join(" "));
  }
  // And six as long as a small design: a rule that held only for a stream's
  // first records would pass every stream above.
  for (let t = 0; t < 6; t++) {
    const recs = [];
    let x = 0, y = 0;
    for (let k = 400; k > 0; k--) {
      const q = rnd(), reach = q < 0.05 ? 0 : q < 0.8 ? 40 : 500, p = rnd();
      x += Math.round((rnd() - 0.5) * 2 * reach); y += Math.round((rnd() - 0.5) * 2 * reach);
      recs.push(`${p < 0.8 ? "s" : p < 0.93 ? "j" : "t"}${x},${y}`);
    }
    drawn.push(recs.join(" "));
  }
  // A stitch that follows travel and lies more than a record (121 an axis)
  // from where the needle stands: what the rule is about. The place is kept
  // as this writer keeps it: a colour change moves nothing.
  const sews = (s) => s.type === "stitch" || s.type === undefined;
  const farAfterTravel = (st) => {
    let x = 0, y = 0, lastWasStitch = false, n = 0, longest = 0;
    for (const s of st) {
      if (s.type === "color") { lastWasStitch = false; continue; }
      const reach = Math.max(Math.abs(s.x - x), Math.abs(s.y - y));
      if (sews(s) && !lastWasStitch && reach > 121) { n++; longest = Math.max(longest, reach); }
      lastWasStitch = sews(s);
      x = s.x; y = s.y;
    }
    return { n, longest };
  };
  // The stitches a stream lays where this writer's needle already stands.
  const sewnOnTheSpot = (st) => {
    let x = 0, y = 0, n = 0;
    for (const s of st) {
      if (s.type === "color") continue;
      if (sews(s) && s.x === x && s.y === y) n++;
      x = s.x; y = s.y;
    }
    return n;
  };
  let travelled = 0, splitSewn = 0, onTheSpot = 0, longest = 0;
  for (const text of drawn) {
    const d = { stitches: stream(text), colors: BLACK };
    const recs = expRecords(d), holes = holesOf(recs), theirs = dstRecords(d);
    assert.deepStrictEqual(holes, holesOf(theirs), text.slice(0, 400));
    // Equal holes are not the whole of it. A jump laid between two sewn
    // stitches leaves both holes and takes the thread from between them;
    // a writer that cut the thread before long travel, or laid travel's
    // last record at the format's 127, puts the needle down in the same
    // places too.
    assert.deepStrictEqual(threadOf(recs), threadOf(theirs), text.slice(0, 400) + ": the thread between the holes");
    // And travel ends ON its stitch: not a jump to the place and a stitch
    // record of no length there, which is one record more for the same hole.
    // (Counted against the stream, not the DST: a colour change that carries
    // a move is where the two files lay the same stitch differently.)
    assert.strictEqual(recs.filter((r) => r.kind === "stitch" && !r.dx && !r.dy).length, sewnOnTheSpot(d.stitches), text.slice(0, 400) + ": stitch records of no length");
    for (const r of recs) {
      const reach = Math.max(Math.abs(r.dx), Math.abs(r.dy));
      assert.ok(reach <= (r.kind === "stitch" ? 121 : 127), `${text}: a ${r.kind} record of (${r.dx},${r.dy})`);
    }
    for (const [kind, type] of [["trim", "trim"], ["color", "color"]]) {
      assert.strictEqual(recs.filter((r) => r.kind === kind).length, d.stitches.filter((s) => s.type === type).length, `${text}: ${kind} records`);
    }
    const end = recs.reduce((a, r) => [a[0] + r.dx, a[1] + r.dy], [0, 0]), last = d.stitches.filter((s) => s.type !== "color").pop();
    assert.deepStrictEqual(end, last ? [last.x, last.y] : [0, 0], `${text}: where the file ends`);
    const far = farAfterTravel(d.stitches);
    if (far.n) travelled++;
    longest = Math.max(longest, far.longest);
    if (holes.length > d.stitches.filter(sews).length) splitSewn++;
    if (d.stitches.some((s, i) => i > 0 && s.type === "jump" && s.x === d.stitches[i - 1].x && s.y === d.stitches[i - 1].y)) onTheSpot++;
  }
  assert.ok(travelled > 150, `only ${travelled} streams have a far stitch after travel`);
  assert.ok(splitSewn > 150, `only ${splitSewn} streams split a sewn move, which must stay sewn`);
  assert.ok(onTheSpot > 50, `only ${onTheSpot} streams have a jump that moves nothing`);
  assert.ok(longest > 3000, `the longest travel into a run is ${longest} units; the product lays 3,355`);
});

test("a design with no stitch more than a record from where travel ended is byte-identical to before", () => {
  // The safety property, in miniature: a leading jump, a sewn move of 30 mm
  // (split into stitches), one of exactly 12.1 mm, a long jump, a trim that
  // carries a move, a trim on the spot, a colour change, and stitches 10.0,
  // 12.1 and 12.0 mm from where travel ended. These are the bytes main's
  // writer laid for it on 2026-10-07, before the chain rule.
  const d = { stitches: stream("j50,-20 s50,-20 s80,-20 s380,-20 s380,101 j1280,101 s1280,101 s1310,131 t1000,400 s1100,400 t1100,400 c1100,400 s1221,279 s1200,300 j900,300 s780,180"), colors: BLACK };
  d.stitches.push({ x: 780, y: 180, type: "end" });
  assert.strictEqual(Buffer.from(exp.encodeEXP(d)).toString("hex"),
    "800432ec00001e006400640064000079800471008004700080047100800470008004710080047000800471008004700000001e1e" +
    "808007008004995a800498598004995a640080800700800100007987eb1580049c0080049c0080049c008888");
});
