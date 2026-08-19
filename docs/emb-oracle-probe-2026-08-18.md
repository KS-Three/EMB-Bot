# Wilcom `.EMB` as a stitch-type oracle — probe result: NO (2026-08-18)

**Verdict: the payload is encrypted. Do not spend more time on this.**

## The hypothesis worth testing

Live defect 5 (satin-vs-fill routing at chance) is measured against stitch
type *inferred* from decoded geometry — `scorecard.py` builds `typ_map` as
`0=run 1=satin 2=fill` from what the needle did, because that is all a DST or
PES carries. An oracle knowing the pro's per-shape answer scores **76.6%
against our 55.4%**, so the inference itself is a ceiling on the measurement.

The tracked `Embroidery Files.zip` carries **14 `.EMB` files** — Wilcom's
native format — alongside the PES/DST for the same designs. Wilcom is an
object-based editor: if `.EMB` stores per-object stitch type, angle and
underlay, that is *given* ground truth rather than derived, and defect 5's
measurement stops being capped by inference.

No document in the repo had ever mentioned those 14 files.

## What they actually are

OLE/CFBF compound documents (`d0cf11e0a1b11ae1`). Seven streams, uniform
across all 14 files:

| stream | size (typical) | state |
|---|---|---|
| `DesignDocument` | 77 KB – 217 KB | **encrypted** |
| `\x05WilcomDesignInformationDDD` | ~6 KB | **readable** |
| `Contents` | ~2 KB | high entropy |
| `DESIGN_ICON` | 536 – 1,117 B | no image magic |
| `\x05SummaryInformation` | ~385 B | standard OLE property set |
| `AUX_INFO` | 5 B | — |
| `Root Entry` | — | — |

`DesignDocument` is where the objects would live. Measured entropy across all
14 files: **7.998 – 7.999 bits/byte**, with a flat byte histogram (top three
byte values 950 / 933 / 924 out of 216,972 — uniform is ~847) and no zlib
stream at any offset in the first 4 KB. Compression alone does not produce a
histogram that flat with no framing; this is encryption. `DESIGN_ICON` carries
no BMP or PNG magic either, so even the thumbnail is obfuscated.

**There is no clean-room path to the object data.** Anything further would mean
attacking the encryption, which is neither legal-safe nor in scope.

## The one thing that IS recoverable, and what it is worth

`\x05WilcomDesignInformationDDD` is plaintext and carries the pro's **actual
thread selections**, by chart and catalogue number — extracted cleanly from all
14 files:

```
beckers logo hat.EMB        Madeira Classic 1041, Madeira Classic 1000, APMS 431
HOTEL FREMONT HAT.EMB       Madeira Classic 1005/1000/1126, APMS 729
PRECISION DRON HAT 2.EMB    Madeira Classic 1278/1041, APMS 431, APMS 151
```

**This differs from what the stitch file reports.** The same design's PES
threadlist reads `Brother "Gray" 39` and `Brother "Black" 20` — the export
re-mapping the pro's threads onto Brother's chart. The pro specified Madeira
Classic 1041, which the shipped `tools/palettes/InkStitch Madeira Rayon.gpl`
resolves to RGB (110,116,123) "Metal"; Brother Gray 39 is (135,135,135).
(Madeira "Classic 40" is the Rayon line, so our existing chart already covers
these codes — 1041, 1000, 1005 and 1278 all resolve.)

**Be honest about the size of this.** `scorecard.py`'s `WEIGHTS` are
`coverage 20 / direction 20 / sttype 20 / density 15 / underlay 10 /
travel 15` — **there is no thread or colour component**, so none of this moves
the score. Two smaller consequences are real:

1. `prep_all.py:247` builds the recon lane's artwork from the pro's PES
   threadlist RGB, i.e. from the Brother re-mapping rather than the pro's
   actual thread. The recon lane's input colours are therefore slightly wrong.
   The real-art lane is unaffected, and it is the lane that matters.
2. The diagnostics that DO look at colour (`colour_recall`,
   `colour_surface_agreement`, `scorecard.py:541,554`) compare against the
   same re-mapped reference.

So: a genuine correction to a reference value, in a place nothing currently
scores. Worth knowing, not worth a work item on its own.

## Method, for anyone re-checking

A throwaway minimal CFBF reader (~90 lines: header, DIFAT, FAT, directory,
mini-stream) was written to enumerate and extract streams, then discarded — it
is not in the repo. `olefile` would do the same job and is deliberately NOT
added as a dependency for a probe that returned a negative.

## Bottom line

- **Stitch-type oracle: dead.** Encrypted payload, no clean-room route.
- **Defect 5's 76.6% oracle ceiling stands** as the best available bound;
  nothing here lifts it.
- The 14 `.EMB` files are still worth knowing about for one reason unrelated to
  this probe: they are a third-party digitizer's editable source files sitting
  in a public repo, and `CLAUDE.md`'s exposure note lists only the `.pes`/`.dst`
  output.
