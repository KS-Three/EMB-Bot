# `fold_inkstitch` — OFL Reserved Font Name case file (2026-09-13)

Sibling of [`bluenesia-permission-archive-2026-08-04.md`](bluenesia-permission-archive-2026-08-04.md),
and the same shape: a permission question about one shipped font, with the
evidence, the decision, and the message that settles it kept where they will be
found. Committed 2026-09-18 at Kent's request — the draft below had lived only
in a session scratchpad, which is how it would have been lost.

**Status: OPEN.** Guarded in code, awaiting a reply that may never come.

## The case

`src/fonts/fold_inkstitch.LICENSE.txt` line 8 reads *"with Reserved Font Name
Fold."* The manifest ships the font to users as **"Fold Ink/Stitch"**.

OFL-1.1 clause 3: *"No Modified Version of the Font Software may use the
Reserved Font Name(s) unless explicit written permission is granted by the
corresponding Copyright Holder. This restriction only applies to the primary
font name as presented to the users."*

Every font here is a Modified Version by the licence's own definition — it names
*"changing formats"*, and `.embf` is a format change over the adapter's SVG. The
manifest `name` is the string the font browser shows, so the clause governs it
directly. It is also the one OFL condition that **survives commercial
bundling**: the licence lets you sell the font inside a larger product, it does
not let you keep the reserved name while doing it. `PRODUCT.md` calls font-licence
compliance *"a hard gate before the first dollar"*, and this repo is public.

## What was measured (2026-09-13)

| | |
|---|---|
| Shipped fonts with OFL sidecars | 82 of 85 |
| Contain the phrase "Reserved Font Name" | 80 |
| Actually **declare** one | **46** — the other 34 match OFL's own DEFINITIONS boilerplate |
| Ship a display name using their own reserved name | **1** |

The other 45 are correctly renamed derivatives — Lobster → Stebor, Abril → Mai en
Fleur, Espresso Dolce → Caffeine, Limelight → Roaring Twenties. That is the
pattern the clause exists to produce, and it is what makes the single outlier
legible rather than ambiguous.

**It is inherited, not ours.** The same scan over upstream
`inkstitch/embroidery-fonts` (clone at `c7e3a05`) finds **1 hit in 102 OFL
fonts** — the same font. Our sidecar is byte-identical to upstream's
`src/fold_inkstitch/license` but for a trailing newline, and upstream's
`font.json` carries `"name": "Fold Ink/Stitch"`, `"original_font": "Fold"`. We
inherited the name; we did not coin it. Inherited is not discharged: we are the
party shipping it commercially.

**No permission is on record anywhere.** The only files naming Kilfiger in the
upstream repo are `fold_inkstitch`'s own three — the attribution itself, not a
grant. And upstream demonstrably **records permission where it has it**:
`bluenesia_satin`'s LICENSE cites the PR carrying the copy, `emilio_20`'s reads
*"used and distributed with permission from the author"*. Fold's says nothing of
the kind. That contrast is the strongest evidence available without asking.

Contact addresses for both the original designer and the Ink/Stitch adapter are
in `src/fonts/fold_inkstitch.LICENSE.txt` itself — not restated here, so the
sidecar stays the single source.

## The guard

`test/font-license.test.js` asserts that no shipped font's display name uses a
Reserved Font Name from its own licence, parsing all five declaration forms
upstream uses. This case is recorded in `RESERVED_NAME_KNOWN_UNRESOLVED`, which
is **a record of a live exposure, not a grant**: the test also asserts the case
is *still* detected, so if the font is renamed the entry goes stale loudly
instead of quietly exempting something that no longer needs exempting.

## Kent's decision, 2026-09-13

**Email Kilfiger and ask.** OFL clause 3 is satisfied outright by written
permission, so a short message is a complete fix that keeps the name. Silence
resolves to a rename, which means the clause is discharged either way and
nothing hangs on a reply arriving.

## The draft

To be sent by Kent in his own name. Address is in the sidecar named above.

> **Subject:** Permission request — use of the name "Fold" in an embroidery adaptation
>
> Hello James,
>
> I'm writing about your **Fold** typeface, which you released under the SIL Open
> Font License 1.1 with Reserved Font Name "Fold".
>
> I run a small embroidery-software project called **Fritsch's Stitches**. We ship
> a digitizing tool that includes a library of embroidery fonts. One of them
> descends from your work: in 2021 Marie-Françoise BRIS adapted Fold into a
> machine-embroidery font for the open-source Ink/Stitch project, keeping it under
> OFL 1.1 and naming it **"Fold Ink/Stitch"**. We package that adaptation into our
> own binary format and ship it inside our product, which we intend to sell.
>
> The OFL plainly allows all of that — bundling and selling a font inside a larger
> software package is expressly permitted, and we ship your licence text and the
> full attribution chain alongside every font.
>
> **The one thing I want to get right is the name.** Clause 3 reserves "Fold" for
> Modified Versions unless the copyright holder gives written permission, and as
> far as I can find, no such permission was ever recorded — not in the Ink/Stitch
> repository, not anywhere I can see. I would much rather ask you than assume.
>
> So, two simple options, and I am genuinely happy with either:
>
> 1. **You're fine with it** — a one-line reply to that effect is all I need, and
>    I'll keep it on file. The font keeps the name Marie-Françoise gave it.
> 2. **You'd rather it didn't carry the name** — also completely fine. Just say so
>    and I'll rename our copy. No hard feelings and no explanation needed.
>
> If I don't hear back, I'll take that as a no and rename it, which is the safe
> reading of the clause.
>
> Either way, thank you for releasing Fold openly in the first place. It has
> travelled further than you may realise — it is sewn in thread now.
>
> Best regards,
> Kent Schaefer
> Fritsch's Stitches

## What to do with the outcome

**A yes** discharges clause 3 and the name stays. Archive the reply as
`docs/fold-permission-archive-<date>.md` following the bluenesia precedent —
quote it verbatim where quotable, record date, participants and channel, and
flag honestly anything that is only a screenshot. Then re-point
`RESERVED_NAME_KNOWN_UNRESOLVED`'s note at the archive file: the case stops being
unresolved and becomes permission-on-record.

**A no, or silence,** means rename. Delete the `RESERVED_NAME_KNOWN_UNRESOLVED`
entry — the test asserts the case is still detected, so it will tell you if you
forget. Names that fit the library's own convention: `auberge_marif`,
`marifenda` and `ondulamarif_*` already ship under the adapter's `Marif` prefix,
so something in that family keeps her credit while dropping the reserved word.

**Either way the rename is cheap now, which it was not when this was drafted.**
`tools/build-embf.mjs` embeds `font.name` in the `.embf`, so a manifest edit
alone is not enough — but `--only <keys>` (added 2026-09-14, PR #488) re-emits
named fonts without the full build's orphan clean. A full rebuild in a cloud
checkout emits 55 of the 85 shipped fonts and deletes the other 30.

**Worth telling upstream either way.** `fold_inkstitch` is Ink/Stitch's only
clause-3 hit in 102 OFL fonts too. A yes is worth passing on so they can record
it; a no is a real bug in their library, not just in ours.
