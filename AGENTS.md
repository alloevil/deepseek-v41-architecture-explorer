# deepseek-v41-architecture-explorer

单文件 three.js 交互页:对照 2017 Transformer(Vaswani et al.)与 DeepSeek-V4.1-Flash
(DeepSeek-AI, 2026-09-10 技术报告)。

**规则:页面上每个数字都必须能追到技术报告;报告没有公布的,不写。** 机械版本是
`claims.json` 的 `viewer.must_contain` / `must_not_contain`,由 `verify.py` 执行——
改数字不同步收据,门禁就红。

## 三层来源(2026-09-14 起)

`claims.json` 把页面上的数字分成三层,`verify.py` 分层检查,UI 也用徽章显示:

| 层 | 含义 | 必填字段 | 门禁怎么查 |
|---|---|---|---|
| `paper`(`claims[]`) | 报告(或 2017 论文)公布的数字 | `source.section` + `source.quote`(逐字)+ `viewer.must_contain/must_not_contain` | 页面必须出现 / 必须不出现 |
| `derived`(`derived_claims[]`) | 我方算术(36 KB/token、1M 换算、≈41×、缩放模式权重) | `source.formula` + `source.inputs` + `source.recompute{expr,expect}` | **真的 eval 一遍表达式**,与 `expect` 不符就红;页面必须出现 `page_marker` |
| `visualization`(`visualization_claims[]`) | 为了画面做的取舍(专家阵只画一层、模块画在塔外) | `real_value` + `display_value` + `source.note` + `page_marker` | 三者齐全且页面带上说明文字 |

新增一个数字时的动作:

- 报告里有的 → 加进 `claims[]`,带 section 与逐字 quote
- 自己能算的 → 加进 `derived_claims[]`,写清公式、输入、以及一条可复算的表达式
- 只是为了画得出来 / 画得下 → 加进 `visualization_claims[]`,同时写 `real_value` 与 `display_value`
- 报告没公布又躲不掉要展示 → 不进任何一层,写进 `removed_claims[]` 记录为什么删

配色约定:徽章 `paper`(蓝)/ `derived`(紫)/ `vis`(琥珀),UI 里 `#prov-line` 渲染,
来源与 `claims.json` 必须一致。

---

## 常用命令

| 用途 | 命令 |
|---|---|
| 本地预览(no-store,避免浏览器缓存旧页) | `python3 serve.py 8741` → http://localhost:8741 |
| 断言门禁(逐条核对页面 vs 报告原文) | `python3 verify.py`(加 `--json` 出机器可读) |
| **推之前跑两个门禁(推荐)** | `VERIFY_CLAIMS_DIR=/tmp/verify-claims tools/preflight.sh` —— 先 `verify.py`,再 CI 用的 `verify_claims run`。少跑第二个会让 CI 变红 |
| 重新核对报告原文 | `claims.json` 的 `source.how_to_recheck`(含 PDF 的 sha256) |
| 机检 claim 的复算来源 | `docs/snapshots/deepseek-v41-tech-report-2026-09-14.md`(2026-09-14 抓取的报告原文摘录,头部含 URL 与 sha256) |
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

报告原文里的数字,由机检 claim 从 `docs/snapshots/` 的已提交快照复算:快照是一次抓取的时间切片,门禁只验「数字与快照一致」,不复检上游报告是否已改。

不确定还有哪些数字没人认领,跑 `verify-claims --root . coverage`:它列出正文里没有 claim 的数字——是待办清单,不是判定。

<!-- 这是起点:agent 犯一次错就补一条边界,定期跑 verify.py 与 agentsmd-lint。 -->
