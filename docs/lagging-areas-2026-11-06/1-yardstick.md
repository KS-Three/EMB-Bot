# Lagging area 1: the yardstick that does not agree with Kent's eye (research, 2026-11-06)

Read-only research; nothing built. [V] = checked against the primary source on 2026-11-06 (GitHub API, PyPI, Hugging Face API, LICENSE file). [U] = not checked. Ink/Stitch source was not read. InkSim (below) is a different project; only its README and docs were read, not its source.

## (a) Verdict

No library fixes this, and the sweeps keep confirming it: the gap is a *label* problem before it is an *instrument* problem. Kent decided a side on 49 of 115 pairs, his own repeat agreement on the 11-03 sitting was 1 of 4, and the pixels of every sitting except `pro-lettering-1102` are gone, so no new instrument can be retested on the old labels. Two things are worth doing. (1) One experiment that puts three off-the-shelf perceptual metrics (FLIP, which the 09-12 sweep verdict'd ADOPT but which was never run against Kent's labels; LPIPS; DreamSim) on the same re-rendered pairs, scored the way the vision judge was (3-way kappa, ties in, both intervals). The honest prior: they behave like the vision judge, finding "identical" and "damaged" but not construction preferences. Even so, that is a free pre-screen of the 43 "same" labels. (2) Run the judge a second way, with a pinned open-weight local model (Qwen VL, Apache-2.0), so it is reproducible and key-free, and test whether a more cloth-like render (InkSim, GPL, bench output only) moves the judge's kappa. Everything else (preference fitting, no-reference IQA, text-to-image reward models, active-learning libraries) is WATCH or REJECT at n = 49.

One finding for Kent, not a library: ROADMAP's exit clause "nothing he judges better ever scores worse" is a zero-tolerance clause against labels that repeat 1 of 4. No instrument can satisfy it as written; it needs a tolerance he sets.

## (b) Verdict table

| Candidate | Licence | Stars / last push | Verdict | Serves |
|---|---|---|---|---|
| DreamSim 0.2.1 [V] | MIT repo; backbone weights (CLIP, OpenCLIP, DINO) each own licence [U] | 633 / 2025-11-24 | PROTOTYPE | tie and damage pre-screen; distance to pro render |
| LPIPS 0.1.4 [V] | BSD-2-Clause | 4,310 / 2024-07-02 | PROTOTYPE (comparator arm, same experiment) | same |
| NVIDIA FLIP `flip-evaluator` 1.7 [V] | BSD-3-Clause | 664 / 2026-10-13 | PROTOTYPE (09-12 said ADOPT; never run on Kent's labels) | same |
| Local open-weight VLM judge: Qwen2.5-VL-7B / Qwen3-VL-8B [V] | Apache-2.0 | HF downloads 6.1M / 7.1M | PROTOTYPE, dev-time only | reproducible key-free judge |
| InkSim 0.5.6 [V] | GPL-3.0-or-later | 1 star / 2026-10-25; repo created 2026-08-07 | PROTOTYPE, bench output only | cloth-like render for the judge |
| Logistic Bradley-Terry on <= 4 features (scikit-learn) | BSD | n/a | PROTOTYPE, low prior | can instruments combine |
| `choix` 0.4.1 [V] | MIT | 207 / 2025-09-05; Python >= 3.10 | WATCH | arm ranking if a sitting has 3+ arms |
| scikit-activeml [V] | BSD-3 | 206 / 2026-11-06 | WATCH | choosing the next pair to label |
| `inspect_ai` [V] | MIT | 3,191 / 2026-11-06 | WATCH | eval harness; `vlm_judge.py` already covers it |
| Arena-Hard-Auto, FastChat [V] | Apache-2.0 | 1,087 / 2025-06; 39,546 / 2026-05 | REFERENCE | BT + bootstrap CI recipe |
| IQA-PyTorch / `pyiqa` (MUSIQ, CLIP-IQA, DISTS) [V] | PolyForm Noncommercial 1.0.0 | 3,445 / 2026-11-05 | REJECT | licence; no-reference scores |
| `piq` 0.8.0 [V] | Apache-2.0 | 1,581 / 2024-05-12 | REJECT | duplicates LPIPS, stale |
| PickScore, ImageReward [V] | MIT / Apache-2.0 | 606 / 2024-12 | REJECT | text-prompt preference models |
| `trueskill` 0.4.5 [V] | BSD, but brand non-commercial only | 803 / 2023-08 | REJECT | `choix` does the same job |

## (c) PROTOTYPE sections

### 1. One render-pair experiment: FLIP + LPIPS + DreamSim

**What.** Full-reference perceptual distances. FLIP is a hand-built human-vision model (BSD-3, zero runtime deps, vetted 09-12). LPIPS and DreamSim are learned; DreamSim ensembles CLIP, OpenCLIP and DINO finetuned on ~20k human triplets, with a single-branch model ~3x faster [V, README]. All run on CPU at render size. Two uses, both new relative to the 10-11 and 11-01 docs (which tested fidelity to the artwork, and distance to the pro's trim figures):
- **d(before, after)** on stitchviz renders. Prediction: large for damage, near zero for Kent's "same" (43 of 115). A tie detector, which is also what the vision judge was good at.
- **d(arm, pro render)** where a pro file exists: render the pro's DST through the same `stitchviz.render_design` path and ask which arm is perceptually nearer. First fidelity-shaped use of the pro file that is not a trim count.

**Plugs in.** New columns in `digitizer/tools/eye_pairs/` beside `features.py` and `pro_pooled.py`, scored by `analysis.py`'s kappa and bootstrap. Packages go in an isolated dev venv like `sam2_isolated/`, never `requirements.txt` or the wheel (`pyproject.toml` packages only `digitizer_core` and `digitizer_service`). Dev-time only; no runtime path.

**Cost.** 2 sessions: one to re-render (pro-pair kit: ~3 h CPU under `%TEMP%\embwt\cpu.lock`; share the render with the registered judge rerun), one to score and write up.

**Catch.** (i) Renders for older sittings are gone, so the labels available are `pro-lettering-1102` (54 live pairs) and the 100 pro-pair labels (need re-render). (ii) Kent's repeat rate caps what any instrument can show. (iii) A before-versus-after distance cannot say which side he prefers; expect it to clear on ties only. (iv) DreamSim backbone weight licences need a read before any shipping use; irrelevant for a dev instrument.

**First experiment.** Pre-register thresholds before opening a pair (as `vlm_judge.py` did), chosen on designs disjoint from the test designs. Score 3-way agreement (before / tie / after) on the 54 live 1102 pairs with the repo's kappa, pairs and designs bootstrap. **Success = lower bound of both intervals above 0, point estimate at least the trim column's +0.28.** Secondary: tie-versus-decided AUC with lower bound above 0.5. Control: the identical-pair control must read tie. Failure is a result; record it and stop buying perceptual metrics.

### 2. Local open-weight judge as a second, reproducible judge

**What.** The 11-04 judge was a Claude session: no key, but not re-runnable, and its repeats were void. A pinned Qwen2.5-VL-7B-Instruct or Qwen3-VL-8B-Instruct (Apache-2.0 [V]) can read the same renders offline with fixed weights, fixed prompt sha, both A/B orders.

**Plugs in.** `digitizer/tools/eye_pairs/vlm_judge.py` has `run` (API arms), `record` and `analyse`. Add a `local` arm writing the same verdict jsonl; reuse `analyse` unchanged. A new model is a new dated pre-registration (per the memory note), never pooled with 11-04.

**Cost.** 2 sessions. A 7-8B VLM on laptop CPU is slow; plan overnight for 54 pairs x 2 orders [U, not measured].

**Catch.** Small VLMs show strong position bias and weaker fine-detail judgement; the MLLM-as-a-Judge benchmark (ICML 2024) found pairwise comparison the best-aligned task and position bias real in open models [V via search; paper not read in full]. Both orders are mandatory; an order flip scores as tie. Never a runtime feature (08-11 local-first ruling).

**First experiment.** Same 54 pairs, same render files, both orders. **Success = 3-way kappa vs Kent with lower bound above 0, plus judge-judge kappa against the Claude session verdicts reported with its interval** (if it cannot reproduce Claude's ties, it is not a stand-in). Order-flip rate reported as a first-class number.

### 3. InkSim renders as the judge's picture (bench output only)

**What.** A new standalone viewer (repo created 2026-08-07, 1 star, 0.5.6 released 2026-09-24 [V]): GPL-3.0-or-later, Python >= 3.11, opens PES and others, CLI export `inksim design.pes --png` [V, user guide]. Renderers: shaded volume, twist texture, normal-mapped GPU mode; the author calls the realistic path approximate. Whether it descends from Ink/Stitch is not stated beyond thanks; do not read its source. Run it as an external tool on our exported files and look at the picture only.

**Plugs in.** Export each pair arm to PES with the existing pyembroidery path, run `inksim --png`, point section 1 metrics and `vlm_judge.py` at the new images. No code or dependency taken.

**Cost.** 1 session on top of sections 1-2. **Catch.** One-star project; headless PNG export untested here [U]; its lighting is invented, not measured against cloth. `stitchviz.py` itself says it shows no thread tension or fabric pull, and neither will InkSim, so this tests "does a prettier render help the judge", not "does a sew-out look like this".

**First experiment.** Paired: same 54 pairs, same judge, stitchviz versus InkSim renders. **Success = the paired bootstrap interval of the kappa difference excludes 0 on pairs and on designs.** If it does not move, render fidelity is not the limit and the answer is labels.

### 4. Logistic Bradley-Terry on a few features (no new dependency)

Fit P(after) from differences of at most 4 columns (hops, d(before,after), judge verdict, one construction column) on the 49 decided pairs. That supports roughly 4-5 parameters, and the repeat rate says the ceiling is low. Evaluate leave-one-design-out only. **Success = leave-one-design-out kappa lower bound above 0 and above the best single column.** Low prior; half a session once section 1 exists; run only to close "can instruments combine". Ties need Davidson or Rao-Kupper handling by hand with scipy [U; `choix` does not appear to model ties].

## (d) Rejected and watched

- **IQA-PyTorch / pyiqa (MUSIQ, CLIP-IQA, DISTS):** PolyForm Noncommercial; no-reference scores rate image quality or aesthetics, not stitch construction. REJECT.
- **piq:** Apache-2.0 but stale (2024-05) and duplicates LPIPS. REJECT.
- **PickScore / ImageReward:** trained on text-to-image prompt preferences; no prompt here. REJECT.
- **trueskill:** BSD code with a Microsoft brand restriction (non-commercial or Xbox Live only, README [V]). REJECT.
- **scikit-activeml:** one labeler, ~115 pairs, fixed pool; pick next pairs by hand where instruments and judge disagree. WATCH, trigger: more than ~300 labelled pairs.
- **`choix`:** only useful with a 3-arm round robin per design; every sitting today is before/after. WATCH.
- **`inspect_ai`, lm-evaluation-harness:** model-benchmark harnesses; `vlm_judge.py` is already pre-registered and pinned. WATCH / REJECT.
- **Arena-Hard-Auto, FastChat:** read for the bootstrap-with-ties recipe only. REFERENCE.
- **Embroidery datasets and papers:** MSEmbGAN (30k Wilcom-rendered images, no licence text, images not stitches) already ruled out in `docs/paired-ground-truth-sourcing-2026-09-28.md`; a fresh search found no DST or stitch-quality-labelled corpus. Nothing here helps.
- **Realistic thread-rendering literature** (BRDF-style yarn shading, a parametric-texture patent, US 8,818,773 [U, snippet only]): no embroidery-specific open code found. Patent hazard if anyone builds a normal-map renderer. Not worth it before section 3 says render fidelity matters.

## Cheapest action that is not a library

Keep the renders. Every sitting's pair images were deleted and only 1102 survives. Store each sitting's before / after / pro PNGs and the kit manifest on the Drive backup (not the public repo; they hold client artwork) so any instrument can be retested later. That, more than any metric above, is what lets Phase 1 ever be decided.

## (e) Sources

- https://github.com/richzhang/PerceptualSimilarity ; https://pypi.org/project/lpips/
- https://github.com/ssundaram21/dreamsim ; https://arxiv.org/abs/2306.09344
- https://github.com/NVlabs/flip ; https://pypi.org/project/flip-evaluator/
- https://github.com/chaofengc/IQA-PyTorch (LICENSE: PolyForm Noncommercial 1.0.0)
- https://github.com/photosynthesis-team/piq
- https://github.com/lucasmaystre/choix ; https://github.com/sublee/trueskill
- https://github.com/scikit-activeml/scikit-activeml ; https://github.com/UKGovernmentBEIS/inspect_ai
- https://github.com/lmarena/arena-hard-auto ; https://github.com/lm-sys/FastChat
- https://huggingface.co/Qwen/Qwen2.5-VL-7B-Instruct ; https://huggingface.co/Qwen/Qwen3-VL-8B-Instruct
- https://github.com/yuvalkirstain/PickScore ; https://huggingface.co/zai-org/ImageReward
- https://arxiv.org/abs/2402.04788 ; https://mllm-judge.github.io/
- https://github.com/oorteo/inksim ; https://pypi.org/project/inksim/
- https://hyper.ai/en/datasets/34570 (MSEmbGAN)
- Repo: ROADMAP.md, docs/yardstick-vs-kents-eye-2026-10-11.md, .claude/memory/vlm-judge-2026-11-04.md, .claude/memory/yardstick-pro-pair-2026-11-01.md, docs/external-repo-sourcing-2026-09-12.md, docs/external-repo-sourcing-2026-11-06.md
