---
name: dst-codec-axis-discrepancy
description: "EMB-Bot's JS DST codec uses a transposed bit table vs pyembroidery/the published Tajima one — unresolved, needs a sew-out to settle"
metadata: 
  node_type: memory
  type: project
  originSessionId: 2d770f79-2682-4e60-a75d-1d8031b1388f
  modified: 2026-08-10T21:13:26.276Z
---

Measured 2026-07-29 while verifying the Python digitizer's DST export. EMB-Bot's
`src/dst.js` / `src/dstimport.js` put **x in the high nibble** of each DST record
byte and y in the low nibble. pyembroidery — and the published Tajima bit-weight
table — do the opposite. Encoder and decoder in the browser engine share the
table, so EMB-Bot round-trips its own files perfectly and the disagreement only
appears against other software.

Evidence (repeatable):
- `Downloads/Other/2024/beckers logo hat.DST` (third-party, professionally
  digitized): pyembroidery → 101.9 x 62.1 mm, renders upright as "BECKER'S
  MARINE" when drawn **y-down**. `decodeDST` → 62.1 x 101.9 mm, rotated a
  quarter turn.
- `Downloads/EMBBOT_hat-text-PRECISION.dst` (written by EMB-Bot): pyembroidery
  reads it as 43.4 x 127.0 mm — a wide hat design reported as portrait.

**NOT changed, deliberately.** Kent has sewn EMB-Bot DSTs on his Tajima, so
something reconciles this on real hardware (cap-frame orientation is one
candidate), and rotating every design he owns on a theory would be reckless.
Resolving it needs a third opinion: a sew-out, his machine's own display, or any
viewer that is neither of these two implementations.

**Why:** it decides whether a real bug is shipping in the primary export format,
and it silently constrains how build step 10 wires the Python engine to the
browser.

**How to apply:** verify Python-side DST through pyembroidery, never through the
browser codec (`digitizer/digitizer_core/export.py` documents the y-down
convention and how it was measured). If Kent reports imported third-party
designs appearing rotated in Studio, this is the cause. See
[[emb-bot-digitizer]].

**ROUTED AROUND, not resolved (2026-07-30, step 8).** The service hands the
browser an EMB-Bot `Design` rather than a DST, so the disputed format never
crosses that boundary and a digitized design cannot arrive transposed while the
question stays open. `digitizer/digitizer_core/adapter.py` owns the y-flip and
is the only place one happens; `digitizer/tests/test_adapter.py` holds the
goldens. `/export` writes machine files in pyembroidery's standard convention
and labels every response `X-Stitch-Convention`, but Studio's DST default stays
the browser encoder — that is the path with sew-out evidence behind it. PES and
JEF have no competing implementation, so they carry no conflict at all.

**DESK-RESOLVED 2026-07-31 (workflow: 4 independent sources + clean-room
decode; memo at `docs/dst-axis-verdict-2026-07-31.md` on feat/satin-rails).**
libembroidery, EduTech Wiki, pyembroidery, and achatina.de (1990s page
pre-dating pyembroidery) agree bit-for-bit: **low nibble = X, high nibble = Y.
Our JS table is the transposed one.** Clean-room decoder reproduced beckers
logo hat.DST at exactly 101.9 x 62.1 mm, "BECKER'S MARINE" upright
(render inspected); our table yields transposed noise on the same bytes.
**BONUS DEFECT: `src/dst.js` writes color change as `0x43` not `0xC3`** — a
standard reader sees a spurious sequin toggle and ZERO color changes in every
EMB-Bot DST. Kent's sew-outs likely reconciled via cap-frame rotation /
machine rotate setting / operator hooping. 30-second hardware check: load an
EMB-Bot DST on the Tajima panel with cap driver off — if it reports ~43 x 127
(portrait) for the PRECISION file, transposition is confirmed on hardware.
RECOMMENDED (not yet done, Kent's call — every existing EMB-Bot DST is
affected): swap dst.js/dstimport.js to the consensus table + 0xC3, one-time
migration read path for old files (detect via header-vs-stitch extent
mismatch). Until then browser DSTs are EMB-Bot-internal only; service
/export (pyembroidery convention) is the trustworthy external path.

**5TH SOURCE, 2026-08-10 (Ink/Stitch research pass, see [[inkstitch-research]]):**
read Ink/Stitch's own DST codec directly — it does NOT depend on
`pyembroidery`, it runs its own MIT-licensed fork `pystitch`
(github.com/inkstitch/pystitch). `DstReader.py`/`DstWriter.py` there use the
same low-nibble=X/high-nibble=Y encoding as the other 4 sources. Verdict now
has 5 independent confirmations; EMB-Bot's JS table is the outlier. Bonus:
`pystitch` is a live, actively-maintained, license-compatible candidate to
replace or supplement the Python digitizer's `pyembroidery` dependency
(broader format coverage per the research doc) — separate decision from the
axis fix itself.

---

## RESOLVED 2026-09-08 — and it never needed the sew-out

Both directions fixed. `src/dst.js`'s two weight tables and
`src/dstimport.js`'s `decodeDelta` swapped to low-nibble=X / high-nibble=Y,
exactly the change this entry RECOMMENDED on 2026-07-29 and exactly what all
five sources said. `decodeDSTStandard` — the 2026-09-07 import workaround —
collapsed to a plain alias of `decodeDST`, which its own comment had predicted
it would.

**The lesson is the sew-out.** This entry, and every doc that cited it, said
the fix was "gated on a sew-out" and "Kent's call". It sat for six weeks on
that. It did not need a sew-out, and could not have been settled by one any
faster: what settled it was

1. reading `pystitch.DstWriter.encode_record` — already installed in this
   repo's own venv — and comparing bytes. Ours came out **10/10 identical**
   across a spread of deltas once the tables were swapped;
2. the crossval harness, which already existed and already had a word for the
   answer: `identity`, the same verdict PES and EXP get;
3. a picture. `TEXT=FRITSCH node tools/run-lettering.mjs` → pystitch → PIL.
   The old bytes draw a vertical column of REVERSED letters; the new ones draw
   FRITSCH upright at the design's own 127.2 × 22.6 mm.

A sew-out settles a PHYSICAL question — will this thread, at this density, on
this fabric, hold. Which nibble carries X is not a physical question; it is a
question about a file format with a reference implementation sitting in
`digitizer/.venv`. Filing it behind a sew-out was a category error that cost
six weeks, and the tell was there the whole time: every one of the five
sources agreed, and none of them owned a machine.

**What the fix does not do:** a `.dst` written before it is in the old dialect
and re-imports transposed. The one-time migration read path this entry
suggested (detect via header-vs-stitch extent mismatch) was NOT built —
DesignPanel carries a scoped note instead ("a file this app wrote before
September 2026 comes back mirrored"), which is cheaper and honest. Build the
migration only if someone actually turns up with old files.

Two more DST defects closed the same week, both of which had been filed under
the same "it's the axis, it's Kent's call" umbrella and neither of which was
the axis:

- the colour-change byte was `0x43` where the standard wants `0xC3`, so a
  standard reader saw a sequin toggle and ZERO colour stops — every
  multi-colour DST sewed straight through elsewhere;
- `encodeDST` wrote the terminal `{type:"end"}` sentinel as a real stitch,
  which on a non-lettering design is a stray needle penetration reached by a
  jump run a reader counts as a TRIM, and which also widened the header's
  declared bounding box (a 50×20 mm design declared 90×50).

Both were independent of the axis, both moved no geometry, and both were
visible in this entry's own "bonus finding" from 2026-07-31. Bundling
independent defects under one reserved decision is how all three stayed open.
