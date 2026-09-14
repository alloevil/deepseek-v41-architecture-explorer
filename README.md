<p align="center">
  <img src="./assets/readme/hero.svg" width="100%"
       alt="DeepSeek-V4.1-Flash vs. the 2017 Transformer: a 40-layer CED stack with 20 encoder layers above 20 decoder layers, decoder global KV projected from H20, and a log-scale KV cache cost comparison of 890 bytes per token in FP4 against the 2017 baseline of about 36 kilobytes">
</p>

# DeepSeek-V4.1-Flash vs. the original Transformer — interactive 3D architecture viewer

An interactive, zoomable 3D comparison of two architectures: the **2017 Transformer**
(Vaswani et al., *Attention Is All You Need*) and **DeepSeek-V4.1-Flash**
(DeepSeek-AI, 2026-09-10, *Pushing the Limits of KV Cache Compression*).

Built from the papers themselves — every number in the viewer is traceable to the
technical report (section references are shown in the hover tooltips).

![overview](docs/overview.webp)

---

## What it shows

| | Transformer (2017) | DeepSeek-V4.1-Flash (2026) |
|---|---|---|
| Topology | 6 + 6 encoder/decoder, cross-attention | 20 + 20 **CED** (causal encoder–decoder): decoder global KV is projected from H₂₀, so prefill runs half the stack |
| Attention | dense O(n²), 8 heads | 128-token **SWA** in every layer + **CSA2** global branch (cross-layer KV/index reuse, hierarchical sparse indexer, Top-512) |
| Feed-forward | d_ff = 2048 ReLU MLP | **DeepSeekMoE** in every block: 1 shared + 384 routed experts, 6 active |
| Residual | one stream, LayerNorm | **Single-Pass mHC**: 4 parallel streams, Sinkhorn-stochastic combine |
| Memory | — | **Engram** n-gram hash tables at layers 1 and 14 (196 B params) |
| KV cache | not addressed (≈36 KB/token naive, base model) | **890 B/token** global KV in FP4 (1/4 of V4-Flash, 1/437 of V1) |
| Output | softmax, one token per pass | **DSpark**: 3-block drafter, 5-token semi-autoregressive drafts, confidence-scheduled verification |

## Features

**If you have no background: start here**
- **▶ Learn (8 steps, key `L`)** — a guided path that answers *"how am I supposed to look at this?"*: each step explains one idea in plain language, **auto-navigates the 3D view for you** (camera, highlights, opens the KV calculator / routing panel), and ends with **one check question** so you notice whether it landed. Step 1 starts from "a model only guesses the next token"; step 8 ends with the takeaway you should be able to say yourself: *V4.1 cuts the cost of remembering context to about 1/41*.
- **Two-page intro card** on first visit: what the diagram is about (36 GB vs 890 MB at 1M tokens) and how to read it (colours, reuse brackets, side modules).
- **Glossary drawer** — 19 terms (attention, SWA, FFN, MoE, expert, router, KV cache, prefill/decode, Top-K, CSA2 modes, CED, Engram, DSpark, mHC, FP4, RoPE, 1M context…), one plain sentence each, bilingual; clicking a term highlights the matching structure in the tower.
- **"In short" line** above every topic's technical columns, so no topic starts with jargon.

**Read the structure**
- Two towers side by side; drag to orbit, scroll to zoom, click anything to inspect it
- **Reuse brackets** on the right tower show which layers share KV (1 Full + N Reuse per group)
- **Green strip on every block** = MoE lives in every backbone layer (the cube field on the floor is the same 384 experts, magnified)
- Side modules are drawn outside the backbone: ViT (image path, with a flow wire into the embedding), Engram (memory, with write wires), DSpark

**Understand the mechanism**
- **Click any backbone layer** → the panel switches to a per-layer dataflow cross-section: what is *computed*, what is *reused*, what is *written to cache* (colour-coded badges, tensor shapes, § references)
- **▶ Walk (or press `W`)** → follow one token through all 40 layers, one station at a time, with a caption describing each step
- **Phase toggle (Prefill / Decode)** → prefill dims the decoder's global-attention layers, matching the CED claim
- **KV cost slider (4K → 1M)** → per-token cache cost for both architectures, with the ≈41× gap called out
- **Real MoE routing** → the expert field can be driven by *measured* routing instead of an illustration: see below

## Real routing, not an illustration

The cube field on the floor shows 384 routed experts with 6 lit. To make that data real,
[`tools/train_tiny_moe.py`](tools/train_tiny_moe.py) trains a tiny MoE **from scratch**
(281,282 params: 2 layers × 4 experts, top-2 + 1 shared, d=64, 2 heads, SwiGLU, RMSNorm,
RoPE) on modular arithmetic — predict `(a op b) mod 10` from the tokens `[a, b, op]` — and
exports every router decision to [`moe-trace.json`](moe-trace.json):

```
held-out accuracy   100.0 %   (4096 samples, loss 2.44 → 0.0001)
L0, operator slot   expert usage [2048, 11, 2037, 0]  ← two experts absorb every operator token
routing patterns    6 distinct patterns for 6 prompts  ← routing depends on the input
```

Every number in the panel's **Real MoE routing** section, and every lit cube when you press
**Map to grid**, comes out of an actual forward pass. The mapping is honest about scale: the
toy model's 2 layers × 4 experts are drawn into the first columns of the grid, while the
real V4.1 is 40 layers × 384 experts (6 active) — the panel says so.

Reproduce (CPU only, ~4 minutes):

```bash
python3 -m venv tools/.venv
tools/.venv/bin/pip install torch numpy --index-url https://download.pytorch.org/whl/cpu
tools/.venv/bin/python tools/train_tiny_moe.py --out moe-trace.json
```

**Explore the design space**
- **Cost lab** — turn the published knobs (routed experts 64–384, active experts 2–8, SWA
  window, global Top-K, KV precision FP4/FP8, context 4K–1M) and watch the estimate move:
  KV storage at that context, the bounded SWA cache, attention read per query, MoE compute,
  all-to-all communication, and capacity — each as a bar with its % delta against the real
  V4.1 configuration. Anchored on the reported 890 B/token; everything else is a relative
  estimate from a deliberately simple model, and **quality stays `?`** — there is no basis
  for predicting it, so the panel says so instead of inventing a number.

**Compare**
- **Architectural diff** — one row per aspect (attention, KV cache, prefill, FFN, active
  params, residual, memory, decoding, vision, positions): the 2017 value next to the V4.1
  value, and clicking a row expands *why* it changed plus **what it buys**. The V4.1 value is
  a receipt chip — click it to verify the number. Rows also jump the tower to the matching
  structure.
- Concept chips (input, positional, attention, sparse schedule, FFN/experts, residual, memory, KV cache, output) → side-by-side fact columns, fully bilingual (中文 / EN)
- Keyboard: `↑↓` walk elements, `Esc` clear, `W` token walkthrough, `Space` demo tour
- Scale modes: **by layer / by parameters / by activation** — heights morph (staggered, bottom-up) to show where the parameters and the decode-time cost actually live
- `画质:高/低` (HQ/LQ) toggle for weak GPUs (bloom + shadows + supersampling)

## Run it

```bash
python3 serve.py 8741      # http://localhost:8741
```

`serve.py` is a small static server that sends `Cache-Control: no-store` for text
assets — plain `python -m http.server` lets browsers serve a stale `index.html`,
which makes iteration confusing.

Any static host works (the page has no build step). three.js is vendored locally, so
the viewer also works offline.

## Layout

```
index.html                 the whole app (markup, styles, scene, data)
serve.py                   no-cache static server
three.module.js            three.js r160 (MIT) — vendored
OrbitControls.js           three.js example (MIT)
RoundedBoxGeometry.js      three.js example (MIT)
postprocessing/            EffectComposer, RenderPass, UnrealBloomPass… (MIT)
shaders/                   CopyShader, LuminosityHighPassShader (MIT)
docs/                      screenshots
```

## Provenance: three layers, machine-checked

Every number on the page is filed under one of three layers in
[`claims.json`](claims.json), and [`verify.py`](verify.py) checks each layer differently:

| Layer | What it is | What the gate does |
|---|---|---|
| `paper` (31 claims) | published in the report (or, for the left tower, Vaswani et al. 2017) | requires the section + verbatim quote, and that the page still matches (`must_contain` / `must_not_contain`) |
| `derived` (5 claims) | our own arithmetic — 36 KB/token naive KV, the 1M-token conversions, ≈41×, the by-parameters bar weights | requires `formula` + `inputs`, **re-evaluates `recompute.expr`** and fails on mismatch, and requires the number to appear on the page |
| `visualization` (4 claims) | drawing decisions — one grid standing for a layer's 384 experts, side-module placement, the CED plane | requires both `real_value` and `display_value` plus a note, and the page must carry the stated marker |

Numbers the report does **not** publish are listed in `removed_claims` (θ=160,000, YaRN
extrapolation, which layers feed DSpark, LM-head precision, …) and must stay off the page.

The panel shows the layers as chips (`report` / `derived` / `schematic`) for the topic you
are reading, so a reader can tell an official spec from our arithmetic from a drawing choice.

**Verify mode** — click any of those chips and you get the receipt itself:

- `paper` → the section, the verbatim sentence, and where it is checked
- `derived` → the formula, its inputs, and a **Recompute in browser** button that evaluates
  the same expression the gate evaluates `(18 × 2 × 512 × 2 → 36,864)`
- `schematic` → the real value next to the drawn value, plus why they differ
- every card also runs a **live self-check**: the page fetches its own source and its receipt
  and reports whether they still agree, and KV numbers get a **baseline comparison**
  (2017 naive vs V4.1 FP4 at 1M context)
- a chip marked `?` means the number has no receipt yet — the card says so instead of
  pretending otherwise

```bash
python3 verify.py          # human-readable
python3 verify.py --json   # machine-readable
```

## Sources

- Vaswani et al., *Attention Is All You Need*, 2017 — baseline tower
- DeepSeek-AI, *DeepSeek-V4.1-Flash: Pushing the Limits of KV Cache Compression*,
  2026-09-10 (51 pp.) — right tower; the paper has no arXiv record, the official PDF
  ships with the model release:
  <https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash/resolve/main/DeepSeek_V41_Tech_Report.pdf>
  (verified cell-by-cell against the extracted report text on 2026-09-11)
- three.js r160, MIT — rendering, controls, post-processing (vendored)

## Caveats

- Parameter counts for the **by parameters / by activation** scale modes are
  documented approximations derived from the component totals the report does give;
  they are annotated as approximations in the UI.
- The 2017 tower is drawn at the paper's base configuration (65 M, d=512); the
  "big" variant (213 M, d=1024) is noted in the tower subtitle.
- Re-verified cell-by-cell against the technical report on 2026-09-11. The report
  does not publish four specifics an earlier revision of the viewer asserted —
  the RoPE theta of the compressed main KV, YaRN-style context extension, the
  DSpark drafter's expert configuration, and the LM head's precision. Those were
  removed rather than guessed; the numbers that stayed (window 128, Top-512,
  mHC expansion 4 with 20 Sinkhorn-Knopp iterations, indexer 32×128, 64 query
  heads × head dim 512, Engram at layers 1/14) are quoted from the report's model
  setup. The 36 KB/token baseline and the ≈41× gap are the viewer's own
  arithmetic and are labelled as such in the UI.
- The viewer keeps a few `window.__*` hooks used for layout/collision verification
  during development.

<p align="center">
  <a href="https://github.com/oil-oil/beautify-github-readme"><img src="./assets/readme/made-with-beautify.svg" width="300" alt="README made with beautify-github-readme"></a>
</p>

## License

MIT — see [LICENSE](LICENSE). Vendored three.js files remain under their own MIT
license (Copyright 2010-2023 three.js authors).
