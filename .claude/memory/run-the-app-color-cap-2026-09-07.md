# Run the app. The screenshot found what the reading did not.

**2026-09-07, late.** Kent: *"burn all of the tokens to make this app saleable
tomorrow!"* Read this before another session spent measuring the product by
reading it.

## The finding, and why nothing in the repo could see it

The Studio was launched and `logo_bridge_bar.jpg` pushed through the real UI at
shipped defaults. The slider read **"Colors (max 6)"**. The caption read
**"15,640 stitches · 80×79 mm · 13 colors"**.

**Thread count is the cost driver in embroidery** — one spool to buy and, on a
single-needle machine, one manual re-thread per cone. Six against thirteen is a
quote a customer refuses to pay, not a cosmetic gap.

**Nothing was hidden.** `tools/warning_coverage.py` had run over that same
fixture hours earlier and could not see it (it reads warnings). MASTER_SCOPE
had said for weeks that **stage 0 routes six of seven real customer logos to
GRADIENT**. `stage2_quantize`'s hard cap has a comment explaining itself. **The
defect was the JOIN of three documented facts**, and a join is what a
screenshot shows and a one-file-at-a-time instrument does not — which is every
instrument in this repo.

Root cause: `stage2_quantize` caps the FLAT lane (largest populations kept, the
rest merged into their closest match, `COLOR_CAP_APPLIED` emitted). The SLIC+RAG
lane passes `max_k=cfg.max_colors` into k-medoids — a **clustering parameter,
not a cap** — and the re-snap can add spools afterwards. So the customer's one
thread-count control was enforced on the artwork type they do not have.

Measured (`tools/color_cap.py`, 26 fixtures at the shipped default of 6):
**6 over the cap, all six gradient** — flat 0/6, photo_scene 0/7, photo_subject
0/2 — worst `drone_render` at **22 cones and 21 colour stops**.
`COLOR_CAP_APPLIED` fired on **zero of twenty-six**.

## The five-minute probe that decided fix vs rewrite

A stage-4 cap only works if the surplus cones are REGION threads; if they were
shade bands built in stage 6 it would be useless there. One probe: on
`drone_render` (74 regions, 24 region threads, 22 sewn) and `logo_bridge_bar`
(74, 13, 13), the set of block threads that are NOT region threads is **empty
on both**. Build at stage 4.

**Ask WHERE the thing comes from before capping, splitting or merging
anything.**

## `cfg.enforce_color_cap` — default OFF, byte-identical off

The flat lane's own rule ported to the region level: rank by SEWN area
(enclosed-background regions buy no slot — their area evicting a thread that
sews would spend the colour budget on bare fabric — but they are still
remapped), keep `max_colors`, merge the rest into the nearest kept cone by
CIEDE2000, emit the flat lane's **own** `COLOR_CAP_APPLIED` sentence so no new
customer copy is needed.

**6 of 26 over → 1 of 26.** drone 22→6 cones / 21→9 stops, screenshot 15→6 /
14→6, golden_tee 14→6, bridge_bar 13→6 / 12→5, summit 12→6. The twenty designs
already inside budget are untouched; drone pays +1.1% stitches. On bridge_bar
**24 shapes move and every one is 0.38–7.21 mm²** — the renders read as the
same design (`docs/renders/color-cap-2026-09-07/`). Flipping it ON is Kent's;
it is row 5 in `docs/pending-flag-decisions-2026-09-06.md` and the only one of
the five with a broken PROMISE behind it.

## The residual is a different mechanism, and saying so was the honest move

`region_blobs` stays at 15 cones. It has only **4 REGION threads** — under the
cap, so the cap correctly does nothing — and **12 of its 15 sewn cones are
built after it, in stage 6 blend bands**: defect 16's open half, on a GENERATED
fixture no client artwork produces. A shade-band cap must run in stage 6/7.
"6 of 6 fixed" was the available sentence and it was not true.

## Also from this push

- **The panel stopped reading like a build log.** Eleven untranslated codes,
  two of them superpixels and k-medoids on 20 of 26 fixtures. Eight translated,
  four silenced, one conditionally silent; a twenty-word jargon blocklist over
  every translation is the tripwire, and `SILENT_WARNINGS` joined
  `test_code_wires.py` as a fifth by-string crossing.
- **Ten equal bullets read as ten faults.** A real logo produced ten warning
  lines and exactly one asked for anything. Split into "things to check" and a
  collapsed "N notes about how this was digitized" — bridge_bar goes to **one
  line plus nine notes**. Unlisted codes default to NOTE deliberately: an
  unlisted actionable warning is one click away, the other default is how a
  panel becomes a wall nobody reads.
- **MASTER_SCOPE hit the budget its own new test enforces**, hours after
  predicting it. The reclaim its own tool named was used: two per-mechanism
  lettering paragraphs moved VERBATIM into `docs/scope/1-auto-digitizing-
  quality.md`, **799 → 788**, pointer left. A move is not the editorial call
  that was left to Kent, and the file's own rules prescribe it.
- **`tools/thread_color_render.py` A/Bs any boolean flag now** (`--flag`),
  which keeps one renderer instead of a copy per flag.

## What did not get fixed, and will not be by copy

The grade: **7 of 26 fixtures read F 0**, and 12 of 52 design/garment combos
sit on a clamped zero with true scores −272 to −38 (defect 28). And ROADMAP
gate 1 — **one sew-out on record, 6/10** — is the whole physical evidence base.
Neither is a wording problem.
