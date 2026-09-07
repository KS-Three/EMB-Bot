# The seam nothing guards, and what it is currently saying to customers

**2026-09-07.** One subject, two directions: the string literals that carry
warning codes from Python into the browser, and what those warnings actually
read like when they arrive. Read this before touching `warnings_codes.py`,
`WARNING_TEXT`, or any preflight code constant — and before deciding whether
a checker is worth building, because the ruling here corrects an
over-generalisation the previous day's entry invites.

## A sweep and a tripwire are judged by different questions

The standing rule from 2026-09-06 is: **before building a checker, sweep for
what it would catch, read the matches, and only then decide.** Five sweeps
had by then found 24→0, 6→0, 4→2, 8→2, 19→0, and the discriminator was
identified — *a check that resolves against an OBJECT pays; one that
pattern-matches prose does not.*

A sixth sweep the next day found **34 distinct code strings crossing a module
boundary as a bare literal, over six sites, every one live** — a zero. By the
rule, do not build it. It was built.

**The rule is about SWEEPS. A sweep asks "has this already drifted?" and a
zero answers it: the convention is sound, there is nothing to automate. A
TRIPWIRE asks "what does it cost when it drifts?" and a zero says nothing
about that at all.**

Here the cost is total silence. `describeWarnings` falls back to
`String(w.message)`, so a stranded translation ships the engine's
build-status prose to a customer without throwing, logging or blanking
anything — and looks exactly like a code nobody had translated yet. A
stranded `FIX_FOR` key just stops offering its button. Compare
`stage7_sequence.py`, which consumes the same codes by IMPORT: delete one and
the package will not load. **The by-string consumers are precisely the ones
that survive the edit and lose a feature quietly.**

The discriminator still picks which tripwires earn their keep, unchanged:
this one resolves against a set of live wire values parsed from both owners,
so its verdict needs no hand-classification.

## Two ways this class of test dies, both hit while writing it

`digitizer/tests/test_code_wires.py` is four "not in" assertions. **A parser
that finds nothing passes every one of them.** That is the same failure
`test_stitchviz.py` records — its first version matched a `LIGHT_DEG` a merge
had left behind as dead code and passed for weeks while the live canvas lit
from the wrong corner.

- **Slicing an object literal by a nearby brace works by luck.** The first
  `_map_keys` cut at the first `\n  };` after the declaration and returned the
  correct set for BOTH maps — because it never reached `FIX_FOR`'s nested
  value objects. Rewriting the slice to match the declaration's own
  indentation is what surfaced the nesting; no test did.
- **A MIRROR must never vouch for a consumer.** preflight holds private
  copies of four pipeline codes (`_CONTOUR_RING_UNREACHABLE`,
  `_CLASSIFIED_PHOTO`, `_PHOTO_AUTO_TIER`, `_PHOTO_FACES_DETECTED`) under a
  documented convention — by string so it neither imports the other lane nor
  breaks in a tree where that lane has not landed. Admitting them to the
  "live" set would let a stale copy of a deleted string keep every Studio
  assertion green: a check comparing a string against a second copy of
  itself. Excluded by leading underscore, and the exclusion is itself
  asserted non-circularly.

**Six mutations, six reds, tree restored.** One rename in each consumer, one
in each owner, plus dropping the mirror filter. Do that or the file is
decoration.

## What the panel is saying right now

`digitizer/tools/warning_coverage.py`, 26 fixtures at 80 mm / left_chest.
The delivery chain is `plan.warnings` → service → `job.warnings` →
`describeWarnings` → `otherWarningLines` → `<li>{w.text}</li>`, and it has
**no severity filter and no disclosure** — `otherWarningLines` hand-filters
exactly one code (`BACKGROUND_ENCLOSED`, which owns a banner). Everything
else the engine emits is rendered verbatim.

**27 distinct codes emitted, 11 untranslated.** Untranslated is not itself
the defect: the engine writes English by default and four of the eleven read
as plain sentences. The one that matters:

**`PHOTO_BACKGROUND_REMOVAL_UNAVAILABLE` prints the SERVER's filesystem path
to the customer** — *"isolated rembg venv not found at
/home/user/EMB-Bot/digitizer/rembg_isolated/venv/bin/python"*, on 9 of 26
fixtures. **Not a corpus artefact:** `cfg.photo_prep_background_removal`
defaults `True`, so this is every photographic design on any machine where
the optional isolated venv was never built. Six sibling `bg_reason` strings
reach the same sentence, one of them carrying the last line of the rembg
worker's STDERR. `pipeline.run_stages` already passes the string as a
separate `reason=` payload field, **so removing it from the human sentence
costs no diagnostic.** MASTER_SCOPE defect 29.

**FIXED the same day, and it was a FAMILY of three.** `detect_faces_seam`
(*"YuNet model file missing at ..."*) and the SAM2 seam (*"SAM2 worker exited
137: <last line of STDERR>"*) are built from the identical pattern —
`warn(CODE, f"X was skipped — {reason}. ...", reason=reason)` — so fixing only
the site that was MEASURED would have left two siblings doing the same thing,
which is the missing-port shape (defect 27) this repo keeps rediscovering.
**Sweep for the pattern, not the instance.** All three now route through
`pipeline._environment_warning`; the CONSEQUENCE clause is unchanged word for
word in all three and only the lead moves (*"X was skipped — <diagnostic>."* →
*"X could not run here."*, the interpolation coming out and the sentence still
needing a verb), and the reason goes to `reason=` alone — a move, not a
deletion, since all three already passed it there.
`tests/test_environment_warnings.py` (7) carries the tripwire: an AST walk
over `digitizer_core` rejecting any `warn()` message f-string that
interpolates a `*_reason` name. Run against the pre-fix file it names all
three by line. It also pins that the walk sees >= 30 `warn()` calls, because
the assertion is a "no hits" check, and it monkeypatches the venv path rather
than relying on its absence — **a test that only fires where rembg is missing
skips on the machines that ship it.**

**And the panel says one thing twice, once in each voice.**
`otherWarningLines` hand-filters exactly ONE code out of the plain list —
`BACKGROUND_ENCLOSED`, which owns a banner — and `SHAPES_LEFT_UNSEWN` carries
the same news untranslated: *"...planned but not sewn — enclosed background,
showing the garment through."* It fires on **10 fixtures and all 10 also emit
`BACKGROUND_ENCLOSED`** — total containment. The dedup works; the duplicate
arrives from a second code it cannot know about.

**That report produced five candidates and one survived reading.** The
overlap is required in BOTH directions (a one-way test is a base-rate
generator — `LONG_JUMPS_TRIMMED` fires on 20 of 26 fixtures), and the mutual
test still let four through, all of them just pairs of codes that fire on
photographs. **Read the matches, not the count** — the rule from the day
before, applied to a tool written the same hour, which is why the caveat is
printed beside the output instead of filed in a doc.

Two more kinds, both product calls rather than defects: engine telemetry
(`PHOTO_SEGMENT_REGION_COUNT`, `PHOTO_PALETTE_SELECTED` — 20/26 each,
*"982 superpixels"*, *"chart-restricted weighted k-medoids"*) and real events
in a unit nobody outside this repo reads (`THREAD_RESNAPPED_AFTER_DRIFT`
13/26, *"worst dE00 37.3"*).

**The measurement shipped without the fix, deliberately.** Measuring what a
customer sees and changing what a customer sees are different acts. Same
reasoning left the "Make it bigger" button in place after measuring it at one
in ten.

## Swept and clean, so nobody sweeps it again

All 57 of `warnings_codes.py`'s codes are **imported by name** somewhere in
`digitizer_core` — checked by walking each module's AST, because a grep
counts a mention in a comment; every one of `WARNING_TEXT`'s
28 keys resolves to a live wire value. **No dead codes, no dead
translations.**
