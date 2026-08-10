# Browser PES / EXP Encoders — Cross-Validation Verdict Memo

**Date:** 2026-08-04 · **Verdict: browser PES is unreadable by standard readers (stitch stream mis-framed by 5 bytes); browser EXP has exact standard-conformant geometry but its trim record truncates the file for standard readers; the DST control reproduced the documented transposition exactly, validating the harness.**

Companion to `docs/dst-axis-verdict-2026-07-31.md` — same adversarial method, applied to the two formats nobody had ever checked against an independent decoder. Reference implementation: pyembroidery (in `digitizer/.venv`), the same standard-conformant library the DST verdict was built on and the one the Python digitizer's `/export` route uses.

## 1. Method

Harness: `tools/crossval-stitch-formats.mjs` (Node) + `tools/crossval_decode.py` (Python). A small **asymmetric** fixture design (18.0 × 8.0 mm, 15 stitches, 2 colors, a jump, a trim, an L-profile with a top-left second-color block — asymmetric under all 8 dihedral transforms, so an axis flip cannot hide) is encoded through the real browser encoders (`src/pes.js`, `src/exp.js`, `src/dst.js` — the exact modules `app/src/lib/exporters.js` invokes), decoded with pyembroidery, and measured: best-fit dihedral transform + residual on stitch coordinates, color count/order, trims/jumps, extents. Expected result for a correct encoder is **identity**: the Design model is 0.1 mm units +Y up, pyembroidery's internal convention is +Y down, so a design stitch (x, y) must decode as exactly (x, −y). Run it: `node tools/crossval-stitch-formats.mjs` (add `--json` for machine output, `--keep` to keep the encoded files in `scratch_crossval/`). Behavior is pinned by `test/crossval-stitch-formats.test.js` (skips without a pyembroidery Python; defect pins are marked "DOCUMENTS KNOWN DEFECT").

**Control (harness validation): DST reproduced its documented bug exactly.** Best-fit transform `anti-transpose` — decoded point = (y, −x) of the design point, i.e. the transposition the DST verdict memo documented — with **rms 0.0** over all 15 stitches, and the color change read as a spurious sequin-mode toggle (`0x43` vs `0xC3`), 0 color changes visible, exactly as documented. Trim-as-3-jumps does read back as a trim. A harness that failed to see this bug would itself be broken; this one saw it perfectly.

## 2. PES: mis-framed stitch stream — third-party readers decode garbage

Measured on the fixture, decoding the browser PES with pyembroidery:

- **354 stitches decoded where 15 exist** — 341 of them phantom zero-delta pairs parsed out of the blank-thumbnail bytes after the reader misses the end marker.
- **Decoded extents 8.0 × 74.2 mm vs. the true 18.0 × 8.0 mm.** No dihedral transform fits (best "fit" rms 23.5 mm — noise, not a clean flip).
- **The color change is lost** (0 decoded), phantom trims/jumps appear (3 TRIM, 7 JUMP where the design has 1 and 1).

Root cause, byte level (confirmed by a patch experiment — see §3): `src/pes.js`'s PEC block layout deviates from the standard by **+5 bytes before the stitch stream**:

1. **One extra header pad byte** — the palette padding loop (`for (i = 0; i <= 0x1cf - colorCount; i++)`, pes.js:159) writes `0x1D0 − colorCount` pad bytes where the standard header has `0x1CF − colorCount`; the PEC header comes out 513 bytes instead of 512.
2. **Two non-standard `u16be 0x9000` "start x/y" fields** (pes.js:174-175) after width/height/nominal-area — 4 bytes that do not exist in the standard block, which has exactly four u16 fields after the `0x31 0xff 0xf0` marker.
3. Consequently the **3-byte length/offset field sits at PEC-relative 515 instead of 514**, and its semantics differ (browser: graphics offset relative to the field + 2; standard: stitch-block length measured from PEC-relative 512) — so a standard reader also computes a garbage thumbnail position.

A standard reader starts decoding stitches at PEC-relative 528; the browser's stream starts at 533. The reader eats `0x01 0x90 0x00 0x90 0x00` as phantom records, comes out one byte out of phase (x/y pairing shifted — the fixture's x-deltas land on y), misses the `0xFF` terminator, and walks the thumbnail region as ~341 (0,0) stitches.

Independent of the framing bug, two more defects:

4. **Jump records carry the wrong long-form flag**: pes.js sets `0x2000` (PEC's TRIM code) for both jumps and trims; the standard jump flag is `0x1000`. Even with the framing fixed, every jump reads as a trim.
5. **Thread colors are never encoded.** No code path sets `paletteIndex` (verified repo-wide), so the PEC palette is always the fallback `(i % 64) + 1` — sequential Brother-chart indices. The fixture's red/blue decode as chart entries `#0e1f7c`, `#0a55a3` (two dark blues). Color **count and change positions** are correct; color **identity** is not recoverable by any reader.
6. Cosmetic: nominal design-area height written as `0x0140` (320) vs. the standard `0x01B0` (432).

Not assessed: the PES v1 `CEmbOne`/`CSewSeg` outer sections (pyembroidery ignores them and reads only the PEC block, as do Brother machines; other desktop software may read them — separate question).

## 3. The 5-byte patch experiment (root-cause proof)

Deleting exactly 5 bytes from a browser-encoded PES — one `0x20` pad byte from the header run plus the two `0x9000` shorts — makes pyembroidery decode it **perfectly**: 15/15 stitches, identity transform, rms 0.0, color change present, correct 18.0 × 8.0 mm extents. Remaining deviations after the patch are exactly defects 4–6 above (jumps read as TRIM+JUMP pairs; palette still wrong). So the framing bug is fully explained by those 5 bytes; there is no deeper stitch-encoding error — the PEC delta encoding itself (short form, 12-bit long form, color-change record, terminator) is correct.

## 4. EXP: geometry exact, trim record fatal to standard readers

- **No-trim fixture: perfect.** Identity transform, rms 0.0, offset [0,0], all 15 stitches exact, color change (`0x80 0x01`) and jump (`0x80 0x04`) both standard. The EXP stitch/jump/color encoding is genuinely standard-conformant — including the y-up file convention.
- **With a trim: the file truncates at the first trim.** `src/exp.js` writes trim as a 2-byte `0x80 0x03` record; pyembroidery's reader (and the Melco convention it implements — its own writer emits `0x80 0x80 0x07 0x00`) treats `0x80`-prefixed records as 4-byte controls and knows codes `0x80/0x02/0x04/0x01`. On `0x03` it consumes 2 bytes of the following record and **aborts the whole remaining file**. Measured: 11 of 15 stitches decoded, the trim, the color change, and the entire second color block silently gone. Real exports trim routinely (`trim_at_mm` 3.0), so in practice any multi-section EXP leaving this app loses everything after its first trim when opened in pyembroidery-based tooling (e.g. Ink/Stitch). Caveat: EXP trim encodings vary across vendors ("0x80 0x02" and bare-jump conventions both exist in the wild); "fatal to pyembroidery-convention readers" is the measured claim.
- Shared quirk with DST: the terminal `{type:"end"}` design record is encoded as one extra zero-delta plain stitch (16 decoded where 15 exist; pes.js is the only encoder that special-cases `"end"`).

## 5. Recommended posture (Kent's call — no shipped encoder was changed)

- **Treat browser PES exactly like browser DST: EMB-Bot-internal only.** Do not hand it to customers or third-party software; a Brother machine reading the PEC block with standard framing gets the same mis-framed stream pyembroidery does. The Python service's `/export` (pyembroidery writer) is the trustworthy PES path, same as for DST.
- **Browser EXP is fine only for designs with zero trims** — which real designs are not. Same posture: internal only until fixed; `/export` for anything leaving the app.
- The fixes themselves look small and low-risk **for PES/EXP specifically** (unlike DST there is no self-consistency to preserve: `src/` has no PES/EXP *importer*, so no round-trip or old-file migration concern — old exported files are simply broken for third parties either way): delete the extra pad byte, drop the two `0x9000` shorts, move/re-derive the length field, use flag `0x10` for jumps, write trim as `0x80 0x80 0x07 0x00`, and map design RGB to nearest Brother chart index for the palette. Each lands as a change to `src/pes.js` / `src/exp.js` with the harness re-run as acceptance (`identity`, rms < 0.5, colors/trims/changes preserved), plus updating the "DOCUMENTS KNOWN DEFECT" pins in `test/crossval-stitch-formats.test.js`. Sequencing with the DST fix is Kent's call.
- Verification before closing: after any fix, one real Brother-machine load (or PE-Design open) of a harness-clean PES; the harness proves standard-reader agreement, not machine behavior.

Artifacts: harness + decoder in `tools/`, pins in `test/crossval-stitch-formats.test.js`. Encoded fixture files regenerable any time via `node tools/crossval-stitch-formats.mjs --keep` → `scratch_crossval/` (gitignored). Code under scrutiny: `src/pes.js` (lines 155-159, 174-175, PEC flag in `pecWriteRecord`), `src/exp.js` (`trimRecord`), `src/dst.js` (control, unchanged posture).

## Addendum, 2026-08-06: the section 4 "shared quirk" is now fixed for EXP

Section 4's last bullet (`16 decoded where 15 exist`) is closed for EXP: `encodeEXP` (`src/exp.js`) now stops at the terminal `{type:"end"}` design-list sentinel the same way `pes.js`'s own encoder already did (`if (st.type === "end") break;`), instead of falling through to the generic stitch path and writing it as a real zero-delta record. Harness re-run: `exp.notrim`/`exp.full` both read `expected 15, decoded 15`. DST's copy of this same gap is untouched — deliberately, per this memo's own section 5 posture (`src/dst.js` unchanged) and CLAUDE.md's standing Kent's-call on the DST codec. EXP carried none of DST's migration risk to begin with (no importer, same reasoning section 5 already gives for the framing/trim fixes), so this closes cleanly on its own.
