---
name: hf-hub-check
description: Check a candidate model's licence, maintenance status or download counts on the Hugging Face Hub with the huggingface MCP server (mcp__huggingface__*). Use before recommending or vendoring any model or weights in EMB-Bot.
---

# Checking a model on the Hugging Face Hub

Moved from the root `CLAUDE.md` footgun 6 (2026-10-26). The server is anonymous on
purpose — see that footgun before touching `.mcp.json`.

**`.mcp.json` carries a SECOND server since 2026-09-12 — `huggingface`, and it
deliberately sends NO token.** A remote HTTP server at
`https://huggingface.co/mcp`, added so a session can check a candidate model's
**license and maintenance status against the Hub** instead of against its own
README — which matters here specifically because this is a commercial product
in a public repo and the embroidery-adjacent prior art is largely GPL-3.0
(Ink/Stitch). **But a Hub licence TAG is a publisher declaration, not a licence
GRANT — never stop at the tag.** `ZhengPeng7/BiRefNet` reads `license:mit` in
search results AND in its model card's YAML front matter, yet the weights repo
ships **no LICENSE file at all** — 9 files, none a licence (`hf_fs find --name
*LICENSE*` returns zero entries, checked 2026-09-12) — and a 3-vote
adversarial review REFUTED *"BiRefNet is MIT for BOTH code and published
weights"* **0-3**. Read the actual file with `hf_fs` before calling any licence
settled; `docs/tooling-research-2026-09-12.md` §3 carries the full trail.
**The two endpoints also disagree on DOWNLOAD counts** — `hub_repo_search`
reported 42.9K for `BiRefNet_HR-matting` where `hub_repo_details` says 2.5M,
and 1.9M vs 20.0M for `facebook/sam3` — so treat a count as order-of-magnitude
and never quote one as a measured figure. **Anonymous access is real, measured
2026-09-12:** `initialize` returns HTTP 200 with no credential and
`tools/list` gives four tools — `hf_whoami`, `hub_repo_search`,
`hub_repo_details`, `hf_fs` (which reads files out of a Hub repo, so a
`LICENSE` can be read directly rather than inferred from a tag). A token
would add more (paper/space/doc search), but there is **no
`Authorization` header on purpose**: an unset `${HF_TOKEN}` expands to a bare
`Bearer `, and sending an empty credential is worse than sending none — it
turns a working anonymous server into a 401. Add the header only alongside a
real token, never speculatively.
**That 200 is no longer the common case — re-measured 2026-09-15: 4 of 11.**
The other seven were `500` or, mostly, `504` after a THIRTY-SECOND hang, on a
machine where `https://huggingface.co/` itself answers 200 in 0.15 s. So a
hang or a 5xx here is the MCP endpoint, not your config and not a missing
token — do not go add `${HF_TOKEN}` to `.mcp.json` over it (see the paragraph
above for why that makes it worse). Retry two or three times: the runs that
did connect completed the handshake and returned the same four tools,
unchanged. **This is also why a session can see the server's instructions and
still have NO `mcp__huggingface__*` tools** — `initialize` succeeded and
`tools/list` did not, which looks like the server is tool-less rather than
flaky. Hit exactly that way on 2026-09-15.
**The trap is `hub_repo_search`'s parameter name.** It takes **`repo_types`, an
ARRAY** (`["model"]`), not `repo_type`. Pass the singular and the call
SUCCEEDS and returns *"No repositories found for the given criteria"* — a wrong
argument reads exactly like a true negative, so a session concludes the model
does not exist on the Hub. Hit while adding this, on a model with 985K
downloads. **This is NOT a runtime dependency** — nothing in `digitizer/`,
`src/`, or `app/` calls it, and it moves no defect on its own; it is a
research-loop tool for license and maintenance questions.
