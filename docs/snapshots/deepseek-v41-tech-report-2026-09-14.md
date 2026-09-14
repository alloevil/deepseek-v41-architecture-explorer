# Snapshot - DeepSeek-V4.1-Flash technical report (excerpts)

Committed so `claims.json` can re-derive offline the numbers this repository publishes
from the report. Only the sentences those claims quote are kept.

| field | value |
|---|---|
| source | DeepSeek-V4.1-Flash: Pushing the Limits of KV Cache Compression |
| publisher | DeepSeek-AI |
| url | https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash/resolve/main/DeepSeek_V41_Tech_Report.pdf |
| report date | 2026-09-10 (51 pages) |
| sha256 | ba68e2e40408125ae6d2f63a9a241b61c73910691c74ec1a2a7023c851eac08d |
| fetched | 2026-09-14 |
| extraction | `pdftotext -layout DeepSeek_V41_Tech_Report.pdf -`, page-break control bytes removed |

> **Point-in-time capture.** The text below was copied out of the PDF fetched on 2026-09-14.
> The claims that read this file recompute a number from the committed text; freshness is
> *not* checked, so a revised upstream report does not move them. To refresh: re-fetch the
> PDF, confirm the sha256 above, replace the excerpts, and bump the `as_of` dates in
> `claims.json`.


## Figure 1 caption (front matter)

<!-- pdftotext -layout lines 37-38 -->
```
achieves approximately 4-fold and 437-fold reductions in per-token global KV cache size relative
to DeepSeek-V4-Flash and DeepSeek-V1, respectively.
```

## 1. Introduction

<!-- pdftotext -layout lines 133-138 -->
```
more aggressive KV cache compression. DeepSeek-V4.1-Flash has 552B backbone parameters,
natively supports multimodal inputs, and accommodates contexts of up to one million tokens.
We adopt a Causal Encoder-Decoder (CED) architecture, in which decoder global KV is projected
from the final encoder hidden states. This design enables the model to activate 8B parameters per
token during prefill and 16B during decode, which is particularly cost-effective for input-heavy
agentic scenarios. Despite being considerably larger than DeepSeek-V4-Flash, DeepSeek-V4.1-
```

<!-- pdftotext -layout lines 177-178 -->
```
of prefill recomputation. With SWA Bounded Replay, the persistent KV cache footprint is further
reduced to approximately 1/8 of that of DeepSeek-V4-Flash. Together, these optimizations
```

<!-- pdftotext -layout lines 206-208 -->
```
     During pre-training, we train DeepSeek-V4.1-Flash on a large-scale multimodal corpus
comprising 45T tokens. Sparse attention is trained from scratch at a sequence length of 64K,
without any dense attention warmup stages. After pre-training, the model possesses native
```

## 2.1. Overview

<!-- pdftotext -layout lines 320-321 -->
```
has 552B backbone parameters and 196B Engram parameters, activating 8B parameters per
token during prefill and 16B during decode. Figure 3 illustrates the overall architecture of
```

## 2.1.1. Multimodal Architecture (vision encoder)

<!-- pdftotext -layout lines 355-364 -->
```
DeepSeek-ViT We train a vision encoder named DeepSeek-ViT from scratch to natively
process images at varying resolutions. We build DeepSeek-ViT on the Vision Transformer (Doso-
vitskiy et al., 2021) architecture with several modifications. To accommodate inputs of arbitrary
resolutions, we replace standard absolute positional embeddings with 2D-RoPE. To align the
ViT more closely with LLM design principles, we replace the patch embedding layer’s convolu-
tion with a linear projection to ensure compatibility with the Muon optimizer. We also adopt
RMSNorm (Zhang and Sennrich, 2019) for normalization and SwiGLU (Shazeer, 2020) as the
activation function. Before feeding visual features into the LLM, we apply a pixel-unshuffle op-
eration with 3 × 3 downsampling to reduce the visual token count by a factor of nine, effectively
supporting input resolutions up to approximately 1344 × 1344 pixels.
```

## 2.4.2. Engram

<!-- pdftotext -layout lines 647-647 -->
```
    We allocate 196B Engram parameters evenly across two modules. Each module uses 𝑁 -gram
```

## 2.4.4. FP4 Main KV Cache

<!-- pdftotext -layout lines 689-690 -->
```
    Among the approximately four-bit formats evaluated, we select E2M1 with one E4M3 scale
per 16 channels, following NVFP4 (Alvarez et al., 2025) but omitting its second-level global
```

<!-- pdftotext -layout lines 701-702 -->
```
training. The non-RoPE and RoPE components use the same quantization format. We quantize
the cache after RoPE: quantizing before RoPE yields only a marginal accuracy improvement
```

## 3.2.2. SWA Bounded Replay (mechanism only - no ratio is printed here)

<!-- pdftotext -layout lines 990-993 -->
```
3.2.2. SWA Bounded Replay

Since SWA dependencies accumulate across layers, exactly reconstructing the SWA KV of 𝐿 layers
would require replaying 𝐿 × 𝑛win tokens. SWA Bounded Replay instead replays only the most
```

## 4.2.1. Model Setups

<!-- pdftotext -layout lines 1093-1120 -->
```
We set the number of Transformer layers to 40 and the hidden dimension 𝑑 to 5120. We adopt
a Causal Encoder-Decoder architecture, with 20 layers in the encoder and 20 layers in the

                                                21
decoder. For the first two layers, we use pure sliding window attention. The remaining 18
encoder layers use CSA2 with a compression rate of 𝑚 = 2. These layers are divided into three
identically configured groups of six layers. In each group, the first layer operates in Full Mode,
and the remaining five layers operate in Reuse Mode. The 20 decoder layers use CSA2 with a
compression rate of 𝑚 = 1. These layers are divided into five groups of four layers. In the first
group, the first layer operates in Full Mode, and the remaining three layers operate in Reuse
Mode. The remaining four groups share the same configuration: the first layer operates in
Reindex Mode, and the remaining three layers operate in Reuse Mode. For all CSA2 layers, we
set the number of indexer query heads to 32, the indexer head dimension to 128, and the number
of KV entries selected for sparse attention (i.e., attention top-k) to 512. We set the number of
query heads to 64, the head dimension to 512, and the query compression dimension to 1280.
For the Hierarchical Sparse Indexer, we select a maximum of 2,048 blocks with 8 positions,
yielding up to 16,384 candidate positions in total. The number of output projection groups is set
to 8, and the dimension of each intermediate attention output is set to 1024. For the additional
branch of sliding window attention, the window size 𝑛win is set to 128. We employ MoE layers
in all Transformer blocks, using SwiGLU activation function with clamping (OpenAI, 2025) at a
threshold of 10. Each MoE layer consists of 1 shared expert and 384 routed experts, where the
intermediate hidden dimension of each expert is 2304. Among the routed experts, 6 experts
will be activated for each token. As for mHC, the expansion factor is set to 4, and the number
of Sinkhorn-Knopp iterations is set to 20. For the vision encoder, we set its number of layers
to 32, the hidden dimension to 1024, the number of attention heads to 16, and the image patch
size to 14. The vision MLP projector has 2 layers with a hidden dimension of 5120. Under this
configuration, DeepSeek-V4.1-Flash comprises 552B backbone parameters, with 8B activated
per token during prefill and 16B during decode.
```

## 4.2.2. Training Setups

<!-- pdftotext -layout lines 1137-1138 -->
```
from 40T to 45T tokens. We train the model from scratch with sparse attention at a sequence
length of 64K and extend the sequence length to 1M at 34T tokens. For auxiliary-loss-free load
```

## 5.1.4. Controllable Reasoning Effort in RL

<!-- pdftotext -layout lines 1548-1551 -->
```
  Reasoning Effort:           {effort} (range 1–100; higher values request more
                                    thorough reasoning)

Here, 𝑏 ∈ {1, . . . , 100} denotes the requested effort level.
```

## 6. Conclusion, Limitations, and Future Directions

<!-- pdftotext -layout lines 2014-2016 -->
```
corresponding footprint of DeepSeek-V4-Flash. SWA Bounded Replay further reduces its
persistent KV cache footprint (always on SSD or in host memory) to roughly 1/8 of that of
DeepSeek-V4-Flash. These reductions alleviate HBM and SSD capacity pressure while the
```

## 1. Introduction — kernel counts of a CSA2 Reuse layer

<!-- pdftotext -layout lines 202-203 -->
```
overlap, sharded Engram embedding tables, and inference kernel fusion. In particular, each
CSA2 Reuse Mode layer executes with only 15 kernels during prefill and 11 during decode. We
```
