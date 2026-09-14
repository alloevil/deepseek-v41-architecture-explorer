#!/usr/bin/env python3
"""Train a tiny Mixture-of-Experts model on a toy task and export its REAL routing.

Why: the architecture viewer needs real routing data (which experts a token picks),
not an illustration. This trains a small MoE from scratch on modular arithmetic
(predict (a op b) mod 10) and dumps per-token, per-layer router decisions, so the
viewer can show numbers that came out of an actual forward pass.

The task is deliberately simple: a tiny model reaches ~100% accuracy quickly, and the
routing is interpretable (experts specialise by operand / operator).

Usage (CPU only, needs torch):
    tools/.venv/bin/python tools/train_tiny_moe.py --out moe-trace.json

Output: JSON with model config, accuracy, and for a set of prompts the per-layer
router probabilities + chosen experts, plus aggregate expert-usage statistics.
"""

import argparse
import json
import math
import torch
import torch.nn as nn
import torch.nn.functional as F

DIGITS = 10
PLUS, MINUS = 10, 11
VOCAB = DIGITS + 2


class RMSNorm(nn.Module):
    def __init__(self, d, eps=1e-6):
        super().__init__()
        self.w = nn.Parameter(torch.ones(d))
        self.eps = eps

    def forward(self, x):
        return self.w * x * torch.rsqrt(x.pow(2).mean(-1, keepdim=True) + self.eps)


def rope(x, base=10000.0):
    """Rotary position embedding applied to (B, H, T, Dh)."""
    b, h, t, dh = x.shape
    half = dh // 2
    pos = torch.arange(t, device=x.device, dtype=torch.float32)
    inv = base ** (-torch.arange(half, device=x.device, dtype=torch.float32) / half)
    freqs = torch.outer(pos, inv)                       # (T, dh/2)
    cos, sin = freqs.cos()[None, None], freqs.sin()[None, None]
    x1, x2 = x[..., :half], x[..., half:]
    return torch.cat([x1 * cos - x2 * sin, x1 * sin + x2 * cos], dim=-1)


class Attention(nn.Module):
    def __init__(self, d, n_head):
        super().__init__()
        self.h = n_head
        self.dh = d // n_head
        self.wq = nn.Linear(d, d, bias=False)
        self.wk = nn.Linear(d, d, bias=False)
        self.wv = nn.Linear(d, d, bias=False)
        self.wo = nn.Linear(d, d, bias=False)

    def forward(self, x):
        b, t, d = x.shape
        q, k, v = (m(x).view(b, t, self.h, self.dh).transpose(1, 2) for m in (self.wq, self.wk, self.wv))
        q, k = rope(q), rope(k)
        y = F.scaled_dot_product_attention(q, k, v, is_causal=True)
        return self.wo(y.transpose(1, 2).reshape(b, t, d))


class Expert(nn.Module):
    """SwiGLU expert (no bias), matching the modern MoE FFN shape."""

    def __init__(self, d, hidden):
        super().__init__()
        self.gate = nn.Linear(d, hidden, bias=False)
        self.up = nn.Linear(d, hidden, bias=False)
        self.down = nn.Linear(hidden, d, bias=False)

    def forward(self, x):
        return self.down(F.silu(self.gate(x)) * self.up(x))


class MoEBlock(nn.Module):
    """One transformer block: attention + MoE FFN (1 shared expert + N routed, top-k)."""

    def __init__(self, d, n_head, n_expert, top_k, hidden):
        super().__init__()
        self.n_expert, self.top_k = n_expert, top_k
        self.norm1, self.norm2 = RMSNorm(d), RMSNorm(d)
        self.attn = Attention(d, n_head)
        self.router = nn.Linear(d, n_expert, bias=False)
        self.shared = Expert(d, hidden)
        self.shared_gate = nn.Parameter(torch.zeros(1))
        self.experts = nn.ModuleList(Expert(d, hidden) for _ in range(n_expert))
        # captured during forward: last batch's routing decisions
        self.trace = None

    def forward(self, x):
        x = x + self.attn(self.norm1(x))
        h = self.norm2(x)
        probs = F.softmax(self.router(h), dim=-1)                       # (B, T, E)
        top = probs.topk(self.top_k, dim=-1)                            # values, indices
        w = top.values / top.values.sum(-1, keepdim=True).clamp_min(1e-9)
        out = torch.sigmoid(self.shared_gate) * self.shared(h)
        for slot in range(self.top_k):
            idx = top.indices[..., slot]                                # (B, T)
            for e in idx.unique():
                sel = idx == e
                out = out + torch.where(sel.unsqueeze(-1), w[..., slot].unsqueeze(-1) * self.experts[int(e)](h), torch.zeros_like(out))
        self.trace = {"probs": probs.detach(), "chosen": top.indices.detach(),
                      "shared_gate": torch.sigmoid(self.shared_gate).detach()}
        return x + out


class TinyMoE(nn.Module):
    def __init__(self, d=64, n_layer=2, n_head=2, n_expert=4, top_k=2, hidden=128):
        super().__init__()
        self.emb = nn.Embedding(VOCAB, d)
        self.pos = nn.Embedding(8, d)                       # learned positions (short sequences)
        self.blocks = nn.ModuleList(MoEBlock(d, n_head, n_expert, top_k, hidden) for _ in range(n_layer))
        self.norm_f = RMSNorm(d)
        self.head = nn.Linear(d, DIGITS, bias=False)
        self.cfg = dict(d_model=d, n_layer=n_layer, n_head=n_head, n_expert=n_expert,
                        top_k=top_k, expert_hidden=hidden, shared_experts=1, vocab=VOCAB)

    def forward(self, idx):
        t = idx.shape[1]
        x = self.emb(idx) + self.pos(torch.arange(t, device=idx.device))[None]
        for blk in self.blocks:
            x = blk(x)
        return self.head(self.norm_f(x)[:, -1])             # predict last position


def make_batch(bs, gen):
    a = gen.integers(0, 10, size=bs)
    b = gen.integers(0, 10, size=bs)
    op = gen.integers(0, 2, size=bs)                        # 0 = '+', 1 = '-'
    tok = torch.tensor([[int(x), int(y), PLUS if int(o) == 0 else MINUS] for x, y, o in zip(a, b, op)])
    tgt = torch.tensor([(int(x) + int(y)) % 10 if int(o) == 0 else (int(x) - int(y)) % 10
                        for x, y, o in zip(a, b, op)])
    return tok, tgt


def accuracy(model, n=4096, seed=123):
    gen = torch.Generator().manual_seed(seed)
    import numpy as np
    rng = np.random.default_rng(seed)
    tok, tgt = make_batch(n, rng)
    with torch.no_grad():
        pred = model(tok).argmax(-1)
    return float((pred == tgt).float().mean())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="moe-trace.json")
    ap.add_argument("--steps", type=int, default=4000)
    ap.add_argument("--batch", type=int, default=256)
    ap.add_argument("--lr", type=float, default=3e-3)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    import numpy as np
    torch.manual_seed(args.seed)
    rng = np.random.default_rng(args.seed)
    model = TinyMoE()
    n_params = sum(p.numel() for p in model.parameters())
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=0.01)
    sched = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=args.lr, total_steps=args.steps)
    losses = []
    for step in range(args.steps):
        tok, tgt = make_batch(args.batch, rng)
        loss = F.cross_entropy(model(tok), tgt)
        opt.zero_grad(); loss.backward(); opt.step(); sched.step()
        if step % 200 == 0:
            losses.append((step, round(float(loss), 4)))
    acc = accuracy(model)

    # --- export real routing for a set of prompts ---
    prompts = []
    sample = [(3, 7, 0), (3, 7, 1), (5, 5, 0), (9, 2, 1), (0, 4, 0), (8, 8, 1)]
    with torch.no_grad():
        for a, b, op in sample:
            toks = [a, b, PLUS if op == 0 else MINUS]
            logits = model(torch.tensor([toks]))
            pred = int(logits.argmax(-1))
            layers = []
            for li, blk in enumerate(model.blocks):
                tr = blk.trace
                layers.append({
                    "layer": li,
                    "tokens": [{
                        "tok": "0123456789+-"[t],
                        "probs": [round(float(p), 4) for p in tr["probs"][0, ti]],
                        "chosen": [int(c) for c in tr["chosen"][0, ti]],
                    } for ti, t in enumerate(toks)],
                    "shared_gate": round(float(tr["shared_gate"]), 3),
                })
            prompts.append({
                "tokens": ["0123456789+-"[t] for t in toks],
                "target": (a + b) % 10 if op == 0 else (a - b) % 10,
                "pred": pred, "layers": layers,
            })

    # aggregate usage over a held-out batch (per layer, per expert, per token slot)
    usage = []
    with torch.no_grad():
        rng2 = np.random.default_rng(999)
        tok, _ = make_batch(2048, rng2)
        model(tok)
        for blk in model.blocks:
            chosen = blk.trace["chosen"]                     # (B, T, k)
            per_slot = [[int((chosen[:, t] == e).any(-1).sum()) for e in range(model.cfg["n_expert"])]
                        for t in range(tok.shape[1])]
            usage.append(per_slot)

    out = {
        "model": dict(model.cfg, params=n_params),
        "task": "modular arithmetic: predict (a op b) mod 10 from tokens [a, b, op]",
        "training": {"steps": args.steps, "batch": args.batch, "lr": args.lr, "loss_curve": losses},
        "accuracy": round(acc, 4),
        "prompts": prompts,
        "expert_usage": usage,   # [layer][token_slot][expert] = count
        "usage_batch": 2048,
    }
    with open(args.out, "w") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"params={n_params} acc={acc:.4f} loss {losses[0][1]} -> {losses[-1][1]}")
    print("wrote", args.out)


if __name__ == "__main__":
    main()
