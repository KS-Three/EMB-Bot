# The gap audit and the sourcing sweep (2026-09-12/13)

Two Workflow fan-outs — **73 agents across eleven phases** — pointed at "find the
gaps and unknowns" and "find repos we can use for fonts or digitizing quality".
Landed as PRs **#473**, **#476**, **#477**. The findings live in
[`docs/research-gap-audit-2026-09-12.md`](../../docs/research-gap-audit-2026-09-12.md)
and [`docs/external-repo-sourcing-2026-09-12.md`](../../docs/external-repo-sourcing-2026-09-12.md);
the durable rules are in `DOCTRINE.md`. **This note is about the METHOD** — what a
research fan-out against this repo is worth, and what breaks.

## What it actually bought

Two real defects, both invisible to a green suite because in each case the tests
compared this codebase to itself:

- **The only renderer in the repo drew every DST transposed.** `render-dst.mjs`
  kept a private delta table and missed the 2026-09-08 axis fix. Found by an
  EXTERNAL oracle — five commissioned Becker files' own Tajima headers.
- **EXP emitted sewn moves past the machine ceiling** (12.5 mm against 12.1),
  the last encoder using its record limit as its sewability split.

Plus **ten of thirteen load-bearing blocker claims false against HEAD**, all
failing toward refusal, and the answer to a question open since 2026-08-28 that
had been sitting behind a blocker that was never real.

## What a fan-out against THIS repo is worth

**An agent that reads MASTER_SCOPE and restates it is worth nothing.** Every
finding of value came from an agent that RAN something — digitized the corpus,
decoded bytes with pystitch, fetched an upstream SVG, installed a candidate into
a scratch venv. The briefs that worked said *check, do not summarise*, named the
fixtures, and required a grep of `DOCTRINE.md` before reporting so a settled
ruling came back as a ruling rather than a discovery.

**The repo's own documentation is the main adversary, not the code.** Roughly half
the sweep's value was finding sentences that had stopped being true. Point agents
at claims, not just at code.

**Budget for the sourcing half being mostly negative — and say so.** The font
lane returned one usable find (`honoka`) out of nine lanes and 86 candidates.
A well-evidenced "still empty, and here are the four new places I looked" is a
real deliverable; it is what stops the next sweep repeating this one.

## Workflow mechanics that cost something

- **Do not pass raw JSON into a synthesis prompt.** The triage prompt sliced its
  input at 220 000 characters, so **2 of 8 census domains never reached the
  ranker** — silently, and one of them was the highest-value lane (doc-vs-code).
  Pass a digest you construct in the script, or fan synthesis out per-domain.
- **Concurrency is `min(16, cpus − 2)`, and this box has 4 cpus** — so two agents
  at a time regardless of how many you queue. A 38-agent phase is not parallel,
  it is 19 sequential pairs. Size phases accordingly.
- **Usage limits kill the VERIFY stage first**, because it runs last — and verify
  is the stage that matters most. 1 of 18 ran; it returned
  *stands-with-corrections* and caught a genuine re-discovery on the first thing
  it looked at (a "new" measurement already published in a 2026-09-11 plan doc).
  **The prior is that unverified findings re-derive known numbers.** If the budget
  is tight, run fewer investigations with their verifiers, not more without.
- **Resume is genuinely idempotent.** Both workflows hit limits mid-flight;
  `Workflow({scriptPath, resumeFromRunId})` replayed the completed agents from
  cache and re-ran only the failures. Nothing was lost but wall-clock. Check the
  reset time before resuming — a resume into a live limit just fails again.
- **When synthesis dies, write it yourself from `journal.jsonl`.** One
  `{"type":"result"}` line per agent with its full return value. That is how both
  dossiers were written; it is faster than re-running the stage.

## The habit that kept showing up, including in my own work

**Four times a guard or a measurement caught its own author** — a phrase count
read as a declaration count (80 vs 46), a third copy of `FILL_ROW_MM` a
"first-declaration-wins" scan could not see, a name collision read as pure
coincidence, and a U01 correction that overshot in the opposite direction from
the claim it was fixing. Every one was caught by the instrument rather than by
review, which is the argument for pinning populations (`assert len(x) >= N` with
the measured N and its date) in any scanner-based test.

A fifth followed on 2026-09-14, in `test_machine_wire.py` written here: its
Python regex anchored `\s*$` after the value and was blind to **36 of
`machine.py`'s constants** that carry a trailing comment. Someone else's mutation
test found it. See DOCTRINE, *"A scanner-based guard needs a mutation aimed at
what the SCANNER cannot see"*.

## What happened to the recommendations

Tracked in the dossier's own "What happened next" section, kept current there
rather than here. In short, as of 2026-09-18: the `.embproj` blank-open, lock
stitches for lettering, `strip_letterbox` and the 20-glyph rebuild all landed
(#483, #485, #489); **area-weighting was built and REFUTED** (#496 — it fixes a
real instability but not the size cliff it was nominated for, whose cause is
input resolution); `honoka`, the commissioning route and the `corpus_scorecard`
exit-code widening are still open.

## One loose end that is not in the repo

The **Fold Ink/Stitch** case: the font ships under a name using its own OFL
Reserved Font Name ("Fold", James Kilfiger), inherited verbatim from upstream
with no permission on record anywhere — 1 hit in 82 shipped OFL sidecars, and 1
in 102 upstream. `test/font-license.test.js` guards the class and records this
one in `RESERVED_NAME_KNOWN_UNRESOLVED`. Kent's call 2026-09-13 was to **email
Kilfiger for permission**, since OFL clause 3 is satisfied outright by written
permission. A draft was written to the session scratchpad and **deliberately not
committed** — CLAUDE.md bars adding legal correspondence to a public repo without
asking. If no reply ever comes, silence resolves to a rename, and the guard's
entry is deleted along with it.
