# DST Codec Dispute — Verdict Memo

**Date:** 2026-07-31 · **Verdict: EMB-Bot's JS table is transposed. The consensus table is correct.**

## 1. What the published record says

Four independent sources were extracted: pyembroidery (reader + writer cross-checked bit-for-bit), libembroidery (decode + encode functions cross-checked), EduTech Wiki (transcribed twice, identical), and achatina.de (the earliest known public DST decode, late 1990s, pre-dating pyembroidery, recovered via Wayback Machine and verified against its own worked example). **All four agree bit-for-bit: low nibble = X, high nibble = Y** in every record byte (byte1 = ±1/±9, byte2 = ±3/±27, byte3 bits 2–5 = ±81, bits 6–7 = control, bits 0–1 always set). Zero disagreement on movement bits. The only nuances in the record: X pairs put positive on the lower bit while Y pairs put positive on the higher bit (a table can look "off" without being transposed), and achatina's byte-3 control reading is slightly simplified vs. real machine behavior — neither touches the axis question.

## 2. What the clean-room decode proves

A clean-room decoder ran both tables against a third-party fixture (`beckers logo hat.DST`, known ground truth 101.9 × 62.1 mm). The consensus table reproduces the exact dimensions, matches the file's own header extents, renders "BECKER'S MARINE" upright and legible, and decodes with zero errors. Our table produces a transposed portrait of garbled diagonal noise. Run against EMB-Bot's own output (`EMBBOT_hat-text-PRECISION.dst`), the situation inverts: our table reads it fine; a standards-compliant reader sees it transposed, and the file's header (written in standard convention) contradicts its own stitch data. Bonus finding: `dst.js` line 67 writes color change as `0x43` instead of `0xC3`, which a standard reader interprets as a spurious sequin-mode toggle — the 2-color file shows zero color changes to third parties. **EMB-Bot round-trips only itself.** This is no longer a theory dispute; it's empirical.

## 3. Why Kent's sew-outs worked anyway — and the 30-second test

Candidate reconciliations, most to least likely:

- **Cap-frame rotation.** Cap drivers sew designs rotated 90° relative to flat hooping; if the test pieces were hats, a transposed file plus the cap-frame rotation could land close enough to look right — especially for designs Kent also previewed in EMB-Bot's own (self-consistent) renderer.
- **Machine auto-orientation / design rotate setting** left at 90° from a prior job.
- **Operator hooping choice** — the design "looked sideways" so the blank was hooped sideways, silently absorbing the transpose.

**The 30-second test:** load an EMB-Bot DST on the Tajima and look at the panel's design preview and its reported X/Y dimensions *before touching rotation settings, with the cap driver profile off*. EMB-Bot says the PRECISION file is 127.0 wide × 43.4 tall. If the machine shows **~127 × 43**, the machine is somehow reading our convention (surprising — report back). If it shows **~43 × 127** (portrait, text sideways), the transposition is confirmed on hardware and the sew-outs succeeded via one of the rotations above. Also check the color-change count on the panel: standard reading of that file shows 0 color changes; EMB-Bot intends 2.

## 4. Recommended posture (Kent's call)

- **Fix the encoder/decoder, don't defend it.** The standing "don't change on theory" decision was right when evidence was one library's opinion; it's now four independent sources plus a ground-truth fixture. Recommend swapping `dst.js` / `dstimport.js` movement bits to the consensus table and writing color change as `0xC3`. Old EMB-Bot-written files would need a one-time migration read path (detect via header-vs-stitch extent mismatch).
- **Service `/export` is the trustworthy path today.** pyembroidery convention matches the standard; keep `X-Stitch-Convention` labeling until the browser codec is fixed, then retire it.
- **Until the browser codec is fixed:** browser-produced DSTs are safe only within EMB-Bot; do not hand them to customers or third-party software. Sequence the fix before any launch milestone that ships DST files externally.

Verification wants one confirming sew-out (or the panel-preview check above) after the code change before closing the memory item.

Artifacts: `C:\Users\EE-LT-~1\AppData\Local\Temp\claude\C--Users-EE-LT-11030\b845a108-6467-4184-b54f-1f888a276bca\scratchpad\` (`dst_cleanroom.py`, `beckers_consensus.png`, `beckers_ours.png`, `embbot_consensus.png`, `embbot_ours.png`). Code under dispute: `C:\Users\EE-LT-11030\EMB-Bot\src\dst.js` (lines 9–24, 67), `C:\Users\EE-LT-11030\EMB-Bot\src\dstimport.js` (lines 14–33).