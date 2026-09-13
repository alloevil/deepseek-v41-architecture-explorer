# deepseek-v41-architecture-explorer

单文件 three.js 交互页:对照 2017 Transformer(Vaswani et al.)与 DeepSeek-V4.1-Flash
(DeepSeek-AI, 2026-09-10 技术报告)。

**规则:页面上每个数字都必须能追到技术报告;报告没有公布的,不写。** 机械版本是
`claims.json` 的 `viewer.must_contain` / `must_not_contain`,由 `verify.py` 执行——
改数字不同步收据,门禁就红。

## 常用命令

| 用途 | 命令 |
|---|---|
| 本地预览(no-store,避免浏览器缓存旧页) | `python3 serve.py 8741` → http://localhost:8741 |
| 断言门禁(逐条核对页面 vs 报告原文) | `python3 verify.py`(加 `--json` 出机器可读) |
| 重新核对报告原文 | `claims.json` 的 `source.how_to_recheck`(含 PDF 的 sha256) |
| 左塔依据 | `claims.json` 的 `baseline_source`(arXiv 1706.03762) |

## 边界

### never

- 不新增报告里没有的数字或机制(θ=160,000、YaRN 外推、DSpark 专家数、LM head 精度等,
  报告未公布,曾经写过又被删;见 `claims.json` 的 `removed_claims`)
- 不单独改 `claims.json` 里的 `quote` / `section`——那是收据本体,改断言要连出处一起改
- 不把本页自己的算术(36 KB/token、≈41×)写成报告数字;UI 里已标注为推导

### ask-first

- 新增运行时依赖(现状只有 vendored three.js r160)
- 重新生成 `docs/*.webp`(需渲染后肉眼确认,再用视觉检查复核)

## 数字与宣称

正文（README、docs、发布说明）里出现的每个数字,要么在 `claims.json` 里有一条机检 claim(命令从已提交的数据独立重算),要么有一条 `manual` claim 写明缺哪个产物、为什么复算不了。推之前跑 `verify-claims --root . run`;只改数字不改 claim,CI 会在几分钟后替你发现(`claims.yml`)。

不确定还有哪些数字没人认领,跑 `verify-claims --root . coverage`:它列出正文里没有 claim 的数字——是待办清单,不是判定。

<!-- 这是起点:agent 犯一次错就补一条边界,定期跑 verify.py 与 agentsmd-lint。 -->
