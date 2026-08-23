# The first real photographs, and the four defects only they could find

**2026-08-23.** Kent attached four family photographs to the session chat —
after the Drive channel was measured broken the day before — and they became the
first genuinely tonal input EMB-Bot has ever been measured on. Every conclusion
below came from running them; none of it was reachable from the committed corpus.

## The headline: a fixture corpus cannot find these bugs

All four defects share a shape — **each needs an input property no committed
fixture has**, and each reported success or plausible output right up to the
moment it failed:

1. **A 7.4 MP phone photo OOM-killed the service** at 13.9 GB RSS in a 16 GB
   container. `MAX_PIXELS = 40_000_000` passed it: that ceiling protects against
   decode bombs, not against the pipeline's own memory curve. Needs: a photo
   larger than any fixture (max committed long side 2778 px). Fixed by a
   decode-time working ceiling of 2800 px (PR #214) — 2800, not the 2000 the
   service's own copy suggests, because four committed fixtures sit between.
2. **`select_palette` ran forever.** Its SWAP phase accepted any exchange
   improving cost by more than an ABSOLUTE `1e-9`, but weights are pixel areas,
   so a portrait's cost is ~1e7 where one double ulp is 1.9e-9 — larger than the
   epsilon. The two sides of that comparison come from different numpy
   reductions and disagree in the last ulp. The shipped chart holds two spools
   with **bit-identical Lab** (indices 8/9, ΔE00 exactly 0.0); SWAP alternated
   between them forever, "gaining" 3.7e-9 a sweep, total cost drop zero. One job
   sat 25+ minutes behind the service's single worker. **Two conditions must
   coincide** — cost above ~4.5e6 (= 2^52 × 1e-9) AND a true-zero-difference
   candidate pair. The other four portraits meet the first and not the second.
   Fixed with a scale-relative tolerance + sweep cap (PR #218); palettes come out
   byte-identical on all five photos, so only termination changed.
3. **Preflight condemned correct output.** `_density_findings` scored streamline
   thread-paint against the 0.40 mm *tatami* target and told 9 of 12 jobs the
   design "came out 4.3x its density target … re-digitize before sewing" —
   every measured advance (0.923–2.608 mm) sitting inside streamline's own
   0.8–3.2 mm band. The check's docstring promises a deliberate override never
   trips it; the pipeline's own tier choice is exactly that. Fixed by scoring
   against each tier's producing constants (PR #216).
4. **A 12-cone colour list sewed 31–35 spools.** See below.

## The palette escape, and why only half of it was mine to close

`select_palette` exists to cap a photo's spool count. Two passes escaped it by
running `argmin` over the full ~400-spool chart:

- `revalidate_threads` (region level) — **closed** (PR #217). Masked to the
  palette on photo classes only. Region threads now equal the palette exactly;
  out-of-palette 19/22/9/20 → 0; stops 92/81/30/84 → 78/68/25/75.
- The per-shade snap in `_shade_layers` — **left open deliberately.** Binding it
  makes adjacent shades collapse onto one palette spool, which re-flattens the
  tonal decomposition: defect 1's ghost. That is a quality trade, so it is
  Kent's, not an engineering default. He ruled the same day that v1 is not done
  until it is closed, and left the method to judgement.

The gating is load-bearing in both halves: flat and gradient keep the
unrestricted argmin byte-for-byte, because the phase-4 spec pins those lanes and
fix #6.3's motivating case is gradient-lane.

## What the sheet actually said about quality

Two failure modes at opposite ends, and the toggle is the only thing between:

- **Toggle route** (`photo_subject`): over-fragmented — 33–110 regions.
- **Default route**: real photos classify **gradient**, where the blend tier
  decomposes nothing (`BLEND_NO_REGIONS_DECOMPOSED` on all four) — a blurry face
  becomes 6 regions and 5 threads. Posterised flat patches.

**The funded speckle A/B answered, and the answer is "almost nothing".** Inert
on the toggle route (byte-identical on all four — the toggle route never
consults the blend tier). On the default route, where the tier does live, three
of four are byte-identical; only `sparkler_dusk` moves, by +21 stitches and
+2 stops. Kent paid for that arm; it deserves an honest report, not a rescue.

**Preflight grade stays F after all four fixes** — driven by
`THREAD_MATCH_POOR`, not the density bug, and arguably telling the truth: 12
cones cannot represent these photos faithfully. Blocks mostly improved (9→6,
10→9, 12→12) but `face_closeup_blur` went **1→3**: the real cost of forcing
shapes into seven cones. Do not quote the halved finding count without it.

## Process lessons

- **`pkill -f <pattern>` matches its own wrapper command line.** Hit three times
  in one session, including with bracketed patterns, because the compound command
  contains the pattern text. Kill and start must be separate calls. `pgrep -f`
  has the same flaw — it returned the wrapper's pid and py-spy failed on it.
- **Two agents in one checkout will collide.** One agent's branch creation moved
  HEAD out from under another's uncommitted edits. Give every agent its own
  worktree explicitly, and say so in the prompt.
- **The SAM2 venv is per-tree** (`<digitizer_root>/sam2_isolated/venv`), so a
  fresh worktree silently drops the SAM2 arm from the sheet. Symlink it in.
- **Claims outrun measurements easily.** Two comments written this session were
  falsified by the next measurement — "no accepted swaps on real art" (the
  portraits accept up to 3) and "cost above 4.5e6 is why it hung" (four other
  portraits clear it and converge). Both were corrected before push. Measure,
  then write the comment; not the other way round.
