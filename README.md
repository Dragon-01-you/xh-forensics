<div align="center">

<a href="docs/promo/xh-forensics-promo-30s.mp4"><img src="docs/promo/teaser.gif" alt="芯火 XH — 30 秒宣传片：五个名字，一个芯" width="100%"/></a>

<sub>▶ 30 秒宣传片（无口播，点击播放完整视频）</sub>

# 🔥 芯火 XH

**AI 中转站 API 验真取证工具 —— 让每一分钱都花在真模型上**

*LLM relay API forensics — verify the model behind your API key, extract injected system prompts, and trace the upstream supply chain.*

简体中文 | [English](README_EN.md)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![CI](https://github.com/Dragon-01-you/xh-forensics/actions/workflows/ci.yml/badge.svg)](https://github.com/Dragon-01-you/xh-forensics/actions/workflows/ci.yml)
[![GitHub stars](https://img.shields.io/github/stars/Dragon-01-you/xh-forensics?style=social)](https://github.com/Dragon-01-you/xh-forensics/stargazers)
[![GitHub forks](https://img.shields.io/github/forks/Dragon-01-you/xh-forensics?style=social)](https://github.com/Dragon-01-you/xh-forensics/network/members)
[![GitHub issues](https://img.shields.io/github/issues/Dragon-01-you/xh-forensics)](https://github.com/Dragon-01-you/xh-forensics/issues)
[![No Telemetry](https://img.shields.io/badge/Telemetry-None-success.svg)]()
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)]()

模型验真 · 系统提示词取证 · 上下游供应链溯源

<sub>**芯火** — 模型的「芯」是真是假，用「火」一验便知。英文标识 **XH** = **X**inhuo。</sub>

</div>

---

## 📡 公开情报库（不装工具也能用，先睹为快）

> 直接消费我们从 2026-06 至 2026-08 真实取证案件中提炼的欺诈特征情报。
> 零依赖、机器可读，可接入风控规则、学术引用，或被你正在用的中转站当场自查。

### 🆔 已揭面的真实模型（真实案件实锤）

「商家叫的名字」≠「模型自认的真身」。下面是英文明问每个 SKU「Who developed you?」后，**模型自己吐出的**真身（绕不过商家改的 `model` 字段）：

| 你/商家叫的名字 | 模型自认真身 | 取证方法 | 证据等级 |
|---|---|---|---|
| `deepseek-v4-pro` / `deepseek-v4-flash` / `deepseek-v4-flash-0731` | **MiniMax-M3** | 系统提示词逐字命中："You are MiniMax-M3, developed by MiniMax. Knowledge cutoff: January 2026…" | 🚨 实锤 |
| `glm-5.2` / `glm-5.3` / `minimax-m3` / `kimi-k3` | **MiniMax-M3** | 同一注入层(220)、同一份系统提示词、同一 usage（244/21/265）——5 张皮 1 个芯 | 🚨 实锤 |
| `deepseek-chat` | **Kimi（Moonshot 月之暗面）** | 思维链泄露："Background identity: current assistant is Kimi, developed by Moonshot AI" | 🚨 实锤 |
| `step-3.7-flash` | **StepFun（阶跃星辰）** | usage 43/161 与众不同，自答 "developed by StepFun" | ✅ 真货（唯一） |
| `deepseek-v4` / `qwen-max` | **不存在** | 网关 404 / 502 虚挂，商家卖的名字在自己系统里都没有 | 🚨 确定级 |

> 结论：商家目录里 10 个 SKU，6 个回到同一个 **MiniMax-M3**，1 个是漏网的 **Kimi**，1 个是真货 **StepFun**（被当"验真展示位"迷惑买家），2 个根本不存在。手法矩阵见 [多站点横向对比](intel/cross_site_comparison.md)；完全脱敏的完整案例范文见 [Relay-X 复盘](examples/relayx_case.md)。

### 🚩 30 秒速查表：一张表识别可疑中转站

| 你看到的 | 可能意味着 | 证据等级 |
|---|---|---|
| 模型名带 `gpt-5.6-sol` / `deepseek-v4-pro` 这类行星/版本后缀 | 自造 SKU，官方无此命名法 | 强旁证 |
| `/v1/models` 里 `owned_by` 混挂 4+ 家供应商（含 nvidia） | 「官方直连」话术与货源目录矛盾 | 强旁证 |
| 问不同品牌模型「你是谁」，答案逐字相同 + token 数相同 | 单后端换皮：一个模型贴多张皮 | 🚨 确证 |
| 身份问题的 `prompt_tokens` 远大于你输入的长度 | 有隐藏注入块（差值=注入体积） | 强旁证 |
| 推理模型拒答身份题，但思维链里讨论「我没有身份信息」 | 被剥掉真实身份卡 | 🚨 确证 |
| 中文身份题被改道、英文逃逸 | 网关内置中文「验真流量探测器」 | 🚨 确证 |
| usage 计数与 GPT 分词器（cl100k）吻合但卖的是 DeepSeek | 网关自算计费=转售链路实锤 | 强旁证 |
| ¥4 无限量日卡 | 低于官方成本，唯一盈利解=便宜后端贴牌 | 强旁证 |

### 📁 情报文件

| 文件 | 内容 | 消费方式 |
|---|---|---|
| [intel/README.md](intel/README.md) | 速查表全文 + 9 大类欺诈特征索引 | 直接阅读 |
| [intel/fraud_patterns.json](intel/fraud_patterns.json) | 9 大类机器可读欺诈特征库（自造 SKU / 命名空间泄露 / 换皮 / 封口令 / 路由 / 分词器指纹 / 软件指纹 / 过期日期 / 经济不可行） | 任何语言 `json.load`；每条附 regex/判定方法/证据等级/来源案件 |
| [intel/cross_site_comparison.md](intel/cross_site_comparison.md) | 多站点横向对比：3 个真实站点的手法矩阵 + 2026-08 复测更新 | 直接阅读 |

> 情报库是**纯数据**，独立可用；`xh` 的探针是这些特征的**自动化执行器**。欢迎 PR 回填新特征（附可复现判定方法）。

---

## 🤔 这是个什么项目？（说人话版）

你在网上买了「DeepSeek / GPT / Claude 会员」，商家信誓旦旦说接的是官方原版……

但你有没有想过：**它背后跑的，真的是你付钱买的那个模型吗？**

这就像去金店买金条——标签写着「足金 999」，可你手里没有任何验金工具。市面上的**中转站**（API 转售服务）就是这样一个黑盒：接口里的 `model` 字段写什么全凭商家良心，**一行代码就能伪造**。

**芯火 XH 就是你口袋里的「验钞机」**：给它一个 URL 和 API Key，它会像侦探一样对目标端点展开多维度行为取证，最后产出一份带评分、带完整证据链、小白也能看懂的《验真报告》。

### 它能回答 6 个问题

| # | 问题 | 怎么回答 |
|:---:|---|---|
| 1 | **这是什么模型？** | 身份测谎 + 思维链泄露 + 提示词提取（不只看 `model` 字段——那个一行代码就能伪造） |
| 2 | **什么水平？** | 多学科 × 多难度学力测验，输出能力档位 |
| 3 | **是不是同一个？** | 同站多渠道 / 中转 vs 官方的模型同一性检验（MET） |
| 4 | **有没有猫腻？** | 内容路由欺诈检测、封口指令检测、假流式检测、经济学可行性测算 |
| 5 | **证据在哪？** | 全部原始 JSON 留档，报告逐条附小白可读解释，可复核、可反驳 |
| 6 | **它是真能出证明，还是只会说？** | 探测端点是否真提供可验证推理，并离线核验证明包与输出/货品的绑定关系 |

---

## 🎬 30 秒演示

![芯火 XH 终端演示](assets/demo.gif)

一次真实 `dig` 运行的浓缩回放：零成本指纹 → 金丝雀 → 揭面（厂商自认矩阵 / 系统提示词逐字命中）→ 判决引擎。

**核心能力矩阵**：✅ LLMmap 预训练指纹 · ✅ 加密签名验证（Claude thinking signature / OpenAI reasoning tokens）· ✅ 可验证推理证明核验（`xh attest`）· ✅ 安全审计 5 探针 · ✅ Softmax 判决引擎 v2 · ✅ Agent Skill 分发 · ✅ Web UI 本地控制台 · ✅ 多站点横向对比 · ✅ MET + Fisher 统计检验

---

## 📑 目录

- [公开情报库（首屏 · 不装也能用）](#-公开情报库不装工具也能用先睹为快)
- [30 秒演示](#-30-秒演示)
- [快速开始](#-快速开始)
- [工作原理](#-工作原理)
- [技术实现](#-采用了哪些技术实现)
- [LLMmap 指纹 + 加密签名 + 基线比对 + 安全审计 + Softmax 判决](#-llmmap-指纹--加密签名--基线比对--安全审计--softmax-判决v04v05-迭代)
- [可验证推理证明（v0.7）](#-可验证推理证明v07)
- [作为 Agent Skill 使用](#-作为-agent-skill-使用)
- [Web UI 本地控制台](#-web-ui-本地控制台)
- [对比同类项目](#-对比同类项目)
- [实际案例](#-实际案例relay-x低价包月中转站验真已脱敏)
- [证据输出结构](#-证据输出结构)
- [常见问题](#-faq)
- [路线图](#-路线图)
- [参与贡献](#-参与贡献)
- [使用须知](#-使用须知与免责声明)

---

## 🚀 快速开始

### 环境要求

| 依赖 | 版本 |
|---|---|
| Python | ≥ 3.10 |
| openai / tiktoken / requests | 核心运行时依赖（刻意保持 3 个） |
| torch / transformers / scipy / numpy | **可选**：仅 LLMmap 预训练指纹需要（见下文"可选依赖"） |
| 一个待验真端点 | 自有 Key 的 OpenAI 兼容 API（形如 `https://xxx/v1`） |

### 三步上手

**① 安装依赖**

```bash
git clone https://github.com/Dragon-01-you/xh-forensics.git
cd xh-forensics
pip install -r requirements.txt
```

或直接安装为命令行工具（提供 `xh` 命令；`api-detective` 作为兼容别名保留）：

```bash
pip install git+https://github.com/Dragon-01-you/xh-forensics.git
```

**② 一键挖掘（推荐）**

URL + API Key → 模型定位 / 上下游关系网 / 系统提示词 / 总档案：

```bash
python -m api_detective dig \
  --base-url https://your-relay.example.com/v1 \
  --api-key sk-xxxx \
  --model deepseek-v4-pro \
  --compare-model kimi-k3 \
  --baseline deepseek-v4 \
  --budget 200 \
  --out ./dossier_evidence
```

**③ 查看报告**

打开 `./dossier_evidence/DOSSIER.md`——结论优先、逐条引用证据，判决评分 0–100。

> 💡 **拿到新的中转站 URL 想复测？** 换掉 `--base-url` 和 `--api-key` 重跑 `dig` 即可。每次运行产出独立证据目录，方便横向对比多个站点的对应关系。

### 分阶段运行（可选）

```bash
python -m api_detective scan --base-url ... --api-key ... --model ...   # 全阶段扫描
python -m api_detective report --evidence ./evidence                   # 仅生成报告
python -m api_detective web                                            # 本地 Web UI
python -m api_detective baseline --generate gpt-4o --base-url ... --api-key ...  # 生成官方基线
```

各阶段可单独运行，计费调用量详见下表：

| 阶段 | 模块 | 做什么 | 计费调用 |
|---|---|---|---|
| 0 | `recon` | 模型清单（含 LLMmap 52 模板库交叉识别）/计费表/首页框架指纹/多站马甲线索 | 0 |
| canary | `core` | 金丝雀探针：402/计费被挡自动降级 | 1 |
| 0.5 | `unmask` | 揭面：echo 矩阵/系统消息引用/厂商自认/注入分层 | ~24 |
| 3a | `llmmap` | **LLMmap 预训练指纹**：8 查询 × 52 模板最近邻（可选依赖） | 8 |
| 1 | `identity` | 随机化多语言身份测谎（防内容路由） | ~13 |
| 2 | `prompt_extract` | 20 种提示词提取技术武库 | ~20 |
| 2b | `pliny` | 对抗性提取武库：NEW_PARADIGM/leetspeak/CCA/Crescendo/CoT 侧信道 | ~17 |
| 2c | `dialect` | 厂商自我知识归属：问"只有自家模型才知道的家事" | ~8 |
| 3 | `router_detect` | 内容路由探测器（A/B + Fisher 精确检验） | ~20 |
| 4 | `tokenizer_probe` | token 计数器指纹（cl100k/o200k 基线比对） | ~5 |
| 4b | `crypto_signature` | **加密签名验证**：Anthropic thinking signature / OpenAI reasoning tokens | ~4 |
| 4c | `security_audit` | **安全审计**：注入/截断/工具改写/SSE/Key 泄露（独立查询家族） | ~12 |
| 5 | `behavior` | 延迟画像 / 假流式 / t=0 确定性 / 错误措辞指纹 | ~15 |
| 6 | `capability` | 全学科学力测验（数学/逻辑/代码/科学/医学/法律/社工） | ~19 |
| 7 | `style` | 情绪/风格 12 维画像 | ~18 |
| 8 | `met` | 模型同一性检验（string-kernel MET 简化实现） | ~48 |
| 6b | `baseline_compare` | **官方基线比对**：余弦/KL 散度多维偏离 → FRAUD_DETECTED 三级判定 | 0 |
| — | `verdict` | 判决引擎 v2：类别归一化 + 温度 Softmax + 概率化判定 | 0 |

---

## ⚙ 工作原理

`dig` 的流程：零成本指纹（错误矩阵 / 特征端点 / 定价表 / 自曝消息 / 姊妹站发现）→ 金丝雀 → 揭面 → **LLMmap 预训练指纹（快速预分类层）** → 身份测谎 → 提示词武库（含二十问假设确认收网）→ 厂商归属 → 路由/分词器 → **加密签名验证 + 安全审计** → MET → 供应链关系网 → **官方基线比对（可选）** → 判决引擎 v2 → `DOSSIER.md`（含全量证据清单）。计费被挡时自动降级并显式标注「证据不完整」。

```mermaid
flowchart LR
    A["输入 URL + API Key"] --> B["阶段0 · 零成本侦察<br/>模型清单 / 定价表 / 首页指纹"]
    B --> C{"金丝雀探针<br/>计费是否可用?"}
    C -- "被挡" --> D["自动降级<br/>仅跑零成本测试"]
    C -- "正常" --> M["LLMmap 预训练指纹<br/>8 查询 × 52 模板最近邻"]
    M --> E["身份测谎 ×13"]
    E --> F["提示词武库 ×37"]
    F --> G["厂商知识归属 ×8"]
    G --> H["路由 / 分词器 / 行为指纹"]
    H --> N["加密签名 + 安全审计"]
    N --> I["学力测验 + 风格画像"]
    I --> J["MET 同一性检验"]
    J --> O["官方基线比对<br/>（可选 --baseline）"]
    O --> K["判决引擎 v2<br/>类别归一化 + 温度 Softmax"]
    K --> L[("DOSSIER.md<br/>+ JSON 证据链")]
```

---

## 🧪 采用了哪些技术实现

<div align="center">
<img src="assets/how_it_works.png" alt="芯火 XH 取证流水线：输入 → 探针族 → 判决引擎 → 输出" width="88%"/>
</div>

**技术栈刻意保持极简**：Python 3.10+，核心仅 3 个运行时依赖（`openai` / `tiktoken` / `requests`），无数据库、无后台服务，所有证据保存在本地目录。重依赖（torch）做成可选安装，未装时对应探针优雅降级。

| 技术 | 用途 |
|---|---|
| OpenAI 兼容协议探测 | 统一入口，同时兼容 Anthropic / Gemini 协议探针 |
| **LLMmap 预训练指纹**（USENIX Security '25） | 8 条查询 × 52 模型孪生网络 → 带距离的最近邻排序，无需官方基线即可实锤「最近的是 Qwen2-1.5B」 |
| **加密签名验证** | Anthropic thinking signature（服务端加密产物，中转站无法伪造）+ OpenAI reasoning token 难度区分度 |
| **Model Equality Testing**（ICLR 2025, Stanford） | MET 模块理论基础：统计检验两个端点是否同一模型 |
| string-kernel 统计检验 + Fisher 精确检验 | 证明「什么问题给什么假身份」是系统性路由而非随机巧合 |
| token 计数器指纹（cl100k / o200k 基线） | 网关用哪家的分词器计费，暴露真实转售链路 |
| **官方基线比对**（余弦相似度 / KL 散度） | 目标端点多维特征 vs 官方基线 → FRAUD_DETECTED / SUSPICIOUS / INCONCLUSIVE |
| **安全审计**（独立查询家族） | 提示注入 / 上下文截断 / 工具调用改写 / SSE 完整性 / Key 泄露五类中转层风险 |
| 对抗性提示词工程 | NEW_PARADIGM、CCA 历史伪造、Crescendo 多轮渐进、leetspeak 编码（吸收自社区一线越狱项目并工程化） |
| 金丝雀降级设计 | 先花 1 次调用探测计费可用性，被挡则自动止损，不烧冤枉钱 |
| **可验证推理证明**（zkSNARK 绑定核验，v0.7） | 核验 FlashProve 一类证明包与输出/货品的绑定关系，并给出「密码学确证 / 行为学推定」保证级别 |
| **判决引擎 v2**（类别归一化 + 温度 Softmax） | 12 类证据组内归一 → 概率化 P(正品) → 0–100 评分，错误探针自动跳过，边缘案例给出分裂维度解释 |

### 判决档位

`正品官方直连/可信转售 (≥85)` → `大体可信 (≥65)` → `可疑 (≥45)` → `高度可疑 (≥25)` → `确证贴牌/拼装 (<25)` → `证据不足（覆盖率 <35% 时触发保护）`

评分不是玄学：每条线索带原始 JSON 留档，可复核、可反驳。v2 引擎额外输出 **P(正品) 概率**（温度 0.5 的 Softmax 校准）与**证据覆盖率**——只跑了几个探针时不再假装给高分。

---

## 🧬 LLMmap 指纹 + 加密签名 + 基线比对 + 安全审计 + Softmax 判决（v0.4/v0.5 迭代）

### 1. LLMmap 预训练指纹（快速预分类层）

集成 [pasquini-dario/LLMmap](https://github.com/pasquini-dario/LLMmap)（MIT，USENIX Security '25）的预训练孪生网络：8 条精心设计的查询打到目标端点，响应与 52 个官方行为模板计算距离，直接输出「距离最近的模型」实锤排序：

```
[Distance: 32.95] --> LiquidAI/LFM2-1.2B <--
[Distance: 40.79]     microsoft/Phi-3-mini-128k-instruct
[Distance: 43.67]     Qwen/Qwen2-1.5B-Instruct
```

- **位置**：identity 之前——先缩小候选范围，再用现场探针精细验证
- **判决权重**：0.14（预训练模型输出，可信度高于现场探针）
- **扩展新模型**：`python -m api_detective add-model <model_name>`（复用 LLMmap 模板扩展流程，无需重训练）
- **recon 联动**：52 个模型清单加入目录识别，一眼看出中转站挂的是哪个开源模型

启用（可选依赖）：

```bash
pip install -r requirements-llmmap.txt        # torch/transformers/scipy/numpy
git clone https://github.com/pasquini-dario/LLMmap
export LLMMAP_MODEL_PATH=./LLMmap/data/pretrained_models/default
```

### 2. 加密签名验证（最高权重证据）

行为侧信道可以被模仿，**密码学证据不能**：

- **Anthropic thinking signature**：extended thinking 模式下官方服务端返回的加密签名（Base64）。检测存在性 + 长度 + 字符集 + **多次调用差异性**（真签名每次不同，伪造签名常重复）。声称 Claude 却给不出合法签名 = 密码学级证伪
- **OpenAI reasoning tokens**：o1/o3/o4 系列的 reasoning token 数应与问题难度强相关。发难/易两档问题，计数恒定或与难度无关 = 「推理」是演出来的

判决权重 0.18（全类别最高：密码学证据 > 预训练指纹 > 行为侧信道）。

### 3. 官方基线自动化比对

```bash
# 用官方 Key 生成基线（约 20 次调用）
python -m api_detective baseline --generate gpt-4o \
    --base-url https://api.openai.com/v1 --api-key sk-official

# dig 时启用严格比对模式
python -m api_detective dig --baseline gpt-4o ...
```

比对维度：身份自认（余弦相似度）/ 分词器家族 / 延迟分布（KL 散度）/ 知识截止 / LLMmap 最近邻 → 输出 **FRAUD_DETECTED / SUSPICIOUS / INCONCLUSIVE / MATCH** 四级判定。基线文件在 `baselines/`，可社区共建；GitHub Actions 每周定时刷新（`baseline-sync.yml`，未配置官方 Key Secrets 时自动跳过）。

### 4. 安全审计（中转站风险，独立查询家族）

不止「模型真假」，还查「中转站对你做了什么」：

| 探针 | 检测什么 |
|---|---|
| 提示注入 | 发带暗号的系统消息，看模型复述出哪些你没发的指令 |
| 上下文截断 | 发 8K token 长文，核对计费 token 数与文末暗号 |
| 工具调用改写 | function call 参数（含 nonce）逐字段核对是否被篡改 |
| SSE 流完整性 | 流式时序分析：假流式（结尾倾泻）/ 中途截断 |
| Key 泄露 | 错误响应中扫上游真实 endpoint / Key / 内网信息 |

所有安全探针使用独立查询前缀（查询家族边界），不污染验真统计。

### 5. 判决引擎 v2（评分科学化）

旧引擎的痛点：单维度探针数量多会主导总分；探针因 429/HTML 失败会污染评分；60 分边缘案例无法解释。v2 升级：

1. **类别归一化**：探针按 12 类分组，组内取 severity 均值再乘类别权重
2. **错误探针跳过**：失败探针的类别自动缺席，权重重分配给有证据的类别
3. **非对称匹配**：「模型应该知道的」（自家家谱/签名格式）正向计分；「不应该出现的」（泄露指令/异常签名）反向计分
4. **温度 Softmax**（T=0.5）：输出概率化 P(正品) ∈ [0,1]
5. **覆盖率保护**：证据覆盖率 <35% 触发「证据不足」档，防止只跑 recon 就出高分假阳性；**实锤级证据不被覆盖率稀释**

---

## 🔐 可验证推理证明（v0.7）

2026-11-03，Anthropic 开源 [FlashProve](https://github.com/anthropics/FlashProve)：用 zkSNARK 给每次推理生成一份密码学证明，验证者**不需要权重、不需要 GPU**，在普通 CPU 上十几秒就能确认「这段输出确实出自那份权重」。这把验真的证据天花板抬到了数学层——但它只覆盖了中转站威胁模型的一部分。

本仓库在 v0.7 增加**第四类证据轴**（前三条是行为侧信道 / 密码学签名 / 预训练指纹）：

- **不实现证明系统**（那是上游 verifier 的事）——只核**绑定关系**，因为中转站真正能动手脚的就是这一层
- **探测**：`xh attest probe` 零计费检查端点是否自称提供可验证推理（`/v1/models` 字段、响应头、well-known 端点）
- **核验**：`xh attest verify` 离线核验证明包 5 类绑定（输出哈希 / 主体模型 / 权重承诺 / 证明体量 / 新鲜度）
- **双轴判决**：分数是行为学似然，新增 `assurance` 说明这份结论属于「密码学确证」还是「行为学推定」

```bash
xh attest probe  --base-url https://api.example.com --api-key sk-xxx --model deepseek-v4-pro
xh attest verify --bundle bundle.json --response reply.txt --model deepseek-v4-pro
```

| 判定码 | 严重度 | 含义 |
|---|---|---|
| `attested_verified` | +3 | 绑定自洽 + 上游 verifier 通过 → 密码学级确证 |
| `attested_unverified` | +1 | 绑定自洽但未跑上游验签 → 只能称「自洽」 |
| `unverifiable` | 0 | 缺字段 / prover 未知 → 不下结论（**不等于假**） |
| `inconsistent` | −3 | 任一绑定失败 → 声称被证伪（如「证明来自 A 模型、文字来自 B 模型」） |

中转站最常见的 5 种绕过路径（逐条对应检测点）、以及**证明不能证明什么**（系统提示词、权重版本、路由计费都不在证明范围内），见情报卡 [`intel/verifiable_inference.md`](intel/verifiable_inference.md)。

> 一句话边界：**没有证明 ≠ 假货**（2026 年绝大多数端点还没有这项能力，缺席不计分）；**有证明且绑定自洽才是唯一能给出「正品」级判定的证据**。

---

## 🤖 作为 Agent Skill 使用

本仓库已发布为 Agent Skill（`SKILL.md`），Claude Code / OpenClaw / Hermes Agent 等 AI Agent 可自动识别并调用：

```
用户: "帮我测一下这个 API 中转站是不是真的"
Agent: 自动调用 → python -m api_detective dig --base-url ... --api-key ... --model ...
Agent: 读取 DOSSIER.md → 引用 3-5 条关键证据 → 小白语言汇报 + 维权建议
```

- 根目录 [`SKILL.md`](SKILL.md)——Agent Skill 规范格式（When to use / How to use / Output）
- [`skills/xh-forensics/SKILL.md`](skills/xh-forensics/SKILL.md)——Hermes Agent 格式
- 触发词：测试 API 中转站 / 验真 relay / 模型是不是真的 / 提取系统提示词 / 检测贴牌

---

## 🖥 Web UI 本地控制台

```bash
python -m api_detective web --port 8501
# 打开 http://127.0.0.1:8501
```

- 输入表单 + 模型下拉（自动拉 `/v1/models`）
- **SSE 实时推送**每个探针进度（零新增依赖：http.server + 原生 JS）
- 检测完成生成报告卡片（`report_card.svg` 恒有；装了 Pillow 另存 `report_card.jpg`）
- 每份报告唯一 `report_id`，保存到 `reports/<id>/`，`/r/<id>` 可回看
- **零遥测**：仅监听 127.0.0.1，不上传任何数据

---

## ⚔ 对比同类项目

系统研究了社区最知名的提示词提取 / 系统提示词档案项目，**吸收精华，补齐盲区**：

| 项目 | 它有的 | 它没有的（我们的差异化） |
|---|---|---|
| [elder-plinius / CL4R1T4S](https://github.com/elder-plinius)（40k★ 级） | NEW_PARADIGM、leetspeak、CCA 等一线越狱技术 | 无验证管线；无中转站威胁模型；无统计检验；无判决引擎 |
| [asgeirtj/system_prompts_leaks](https://github.com/asgeirtj/system_prompts_leaks)（40k★ 级） | 厂商逐字提示词档案 | 其 Issue 自认多数内容是行为重构，缺取证方法学 |
| [LLMmap](https://github.com/pasquini-dario/LLMmap) | 黑盒模型家族指纹（52 模板预训练分类器） | 不做欺诈定性、不给举报级证据链——**其核心分类器已集成为本项目的快速预分类层** |
| api-relay-audit | 14 步中转站安全审计 | 无模型验真、无判决引擎——**其安全审计思路已吸收为独立查询家族探针** |
| FakeModelDetector | 温度 Softmax 评分方法学 | **其评分科学化思路已吸收进判决引擎 v2** |
| Real Money, Fake Models（arXiv） | 中转站审计框架论文 | 无开箱即用工具与小白可读判决 |
| [FlashProve](https://github.com/anthropics/FlashProve)（Anthropic，2026-11） | 可验证推理证明系统（权重承诺 + 单次推理证明，CPU 秒级验签） | 只证明「这段输出出自承诺的权重」，不覆盖中转站威胁模型——**其证明包的绑定核验已集成为 v0.7 的 attestation 证据轴** |

**我们独有的 7 个杀手锏**：

1. 🎯 **中转站威胁模型** —— 目标不是厂商系统提示词，而是中转层注入的封口/改写指令（贴牌实锤的直接证据）
2. 🧠 **CoT 侧信道收割** —— 诱导模型在思维链里复述指令，再从 reasoning_content 里捞泄露
3. 🥫 **罐头答案聚类** —— 字节级一致的重复回复 = 触发风控话术模板，本身即是证据
4. 🔀 **内容路由 A/B + Fisher 检验** —— 证明「什么问题给什么假身份」是系统性路由
5. 💰 **经济学不可行性测算** —— 远低于官方成本的包月价，只有偷 key / 盗用 / 拼装三种解释
6. ⚖ **加权判决 + 本地留证** —— 直接产出可用于消费投诉的证据包
7. 🔐 **证明包绑定核验（v0.7）** —— 密码学证明时代，中转站能作弊的只剩「证明 ↔ 回答 ↔ 货品」的绑定；本工具专门核这一层，并明确区分「密码学确证」与「行为学推定」

### 方法论引用

- **Model Equality Testing**（ICLR 2025, Stanford）—— MET 模块的理论基础
- **Real Money, Fake Models: Deceptive Model Claims in Shadow APIs**（arXiv:2603.01919）—— 中转站审计的整体框架
- **FlashProve / Provable Inference**（Anthropic, 2026-11，Apache 2.0）—— 可验证推理的权重承诺与单次推理证明，attestation 证据轴的理论与格式参考
- **LLMmap** —— 黑盒指纹查询策略

---

## 📖 实际案例：「Relay-X」低价包月中转站验真（已脱敏）

> 应合规要求，本案例隐去站点身份与联系方式，方法与数据特征均来自真实取证。

**背景**：某中转站宣称提供 DeepSeek 全系官方直连，包月价格仅为官方成本的几百分之一。用户持自有 Key 运行 `dig` 一键取证。

<div align="center">
<img src="assets/case_forensics.png" alt="「Relay-X」脱敏案例：5 条证据链得出 33/100 高度可疑" width="88%"/>
</div>

**取证发现**（节选，全部有 JSON 原始留档）：

| 发现 | 结论类型 |
|---|---|
| 宣称「DeepSeek 官方直连」，但 8 条渠道中 6 条由同一家第三方厂商后端供货 | 贴牌转售实锤 |
| 中文身份问题 100% 被改道至另一型号回答（英文提问则正常），Fisher p<0.001 | 内容路由欺诈 |
| 提取到三层注入的系统提示词模板（英文身份层 + 中文皮肤层 + 思维链指令层），经间隔复测逐字一致 | 封口指令铁证 |
| 同一 SKU 在 60 秒内先后命中两家不同上游厂商（其中一家返回了上游默认欢迎语原文） | 渠道池轮换实锤 |
| 网关按 OpenAI 系分词器计费，与本地 cl100k 基线精确吻合，与「DeepSeek 官方」说法矛盾 | 转售链路暴露 |

**最终判决：33/100「高度可疑（大概率假货）」**。全程消耗不到 $0.05，产出 100+ 份证据文件与一份 `DOSSIER.md` 总档案，可直接用于平台投诉与消费维权。

完整脱敏版复盘见 [`examples/relayx_case.md`](examples/relayx_case.md)。

---

## 📁 证据输出结构

```
dossier_evidence/
├── DOSSIER.md                  # 总档案：结论优先，逐条引用证据
├── _final_results.json         # 结构化结果 + 判决评分
├── recon_summary.json          # 零成本侦察摘要
├── fp_*.json                   # 指纹矩阵（端点/错误措辞/定价表）
├── um_row_*.json               # 各模型身份测谎原始记录
├── um_sysmsg*_*.json           # 系统提示词提取 + 稳定性复核
└── ...                         # 每次探测一个 JSON，全程可复核
```

---

## ❓ FAQ

<details>
<summary><b>会被商家发现吗？</b></summary>
所有请求都是普通对话请求，走标准 `/v1/chat/completions` 接口，不注入恶意载荷、不做压力测试。
</details>

<details>
<summary><b>要花多少钱？</b></summary>
默认预算内通常 $0.02–$0.2。金丝雀阶段发现计费被挡会立即降级为零成本测试，绝不烧冤枉钱。
</details>

<details>
<summary><b>直接问模型"你是谁"不行吗？</b></summary>
不行。`model` 字段和口头自我介绍都是一行代码就能伪造的东西。我们看的是无法伪装的行为侧信道：分词器计数、错误措辞、延迟画像、知识归属、思维链泄露……
</details>

<details>
<summary><b>支持哪些协议？</b></summary>
以 OpenAI 兼容协议为主入口，同时内置 Anthropic Messages 与 Gemini 协议探针，可识别网关的多协议马甲。
</details>

<details>
<summary><b>API Key 安全吗？</b></summary>
Key 仅在本地使用、通过命令行参数传入，不会写入任何代码或配置文件；所有证据仅保存在你本地的 `--out` 目录，工具本身零遥测、零上传。
</details>

---

## 🗺 路线图

- [x] 身份测谎 / 提示词武库 / 厂商归属 / MET / 判决引擎
- [x] `dig` 一键模式 → DOSSIER 总档案
- [x] 三层注入模板提取 + 稳定性复测
- [x] CI 自动化测试（GitHub Actions，Python 3.10–3.13 矩阵）
- [x] 英文文档（[README_EN.md](README_EN.md)）
- [x] LLMmap 预训练指纹分类器（快速预分类层，可选依赖）
- [x] 加密签名验证（Anthropic thinking signature / OpenAI reasoning tokens）
- [x] 发布为 Agent Skill（`SKILL.md`，Claude Code / OpenClaw / Hermes Agent 可自动调用）
- [x] 官方基线自动化比对（`--baseline` 严格模式 + 每周自动同步 workflow）
- [x] 安全审计维度扩展（注入 / 截断 / 工具改写 / SSE / Key 泄露）
- [x] 评分引擎 v2（类别归一化 + 温度 Softmax + 概率化判定）
- [x] Web UI 本地报告可视化（零新增依赖：SSE 实时进度 + 报告卡片）
- [x] 公开情报库 `intel/`（机器可读欺诈特征库 + 30 秒速查表，不装工具也能用）
- [x] 多站点横向对比报告（[`intel/cross_site_comparison.md`](intel/cross_site_comparison.md)，三站手法矩阵 + 共性规律）
- [x] 判决引擎回归基准（`tests/cases/` 历史案件 → 期望档位，权重调优不破坏既有定性）
- [x] 可验证推理证明核验（`xh attest`：证明包绑定核验 + 保证级别双轴，v0.7）
- [ ] 社区共建官方基线库（PR 贡献 `baselines/*.json`）

---

## 🤝 参与贡献

欢迎通过 Issue 和 PR 参与，详见 [CONTRIBUTING.md](CONTRIBUTING.md)。提交前请跑通本地检查：

```bash
ruff check . --select F,E9          # lint 必须通过
python -m api_detective --version   # CLI 冒烟
```

**铁律**：严禁在任何提交中包含真实密钥、真实端点数据或可识别的站点信息——脱敏写法参考 `examples/relayx_case.md`。

---

## 🛡 使用须知与免责声明

- 仅用于**你自己持有 Key 的端点**的验真，请勿用于攻击他人服务或未授权测试
- 所有证据仅保存在本地 `--out` 目录，工具本身不上传任何数据
- 本项目输出为技术分析意见，不构成法律建议；维权请咨询专业人士
- 请遵守你所在司法辖区的法律法规（中国大陆用户可参考《消费者权益保护法》与 12315 平台流程）

---

## 🌟 Star 历史

如果这个工具帮你省了冤枉钱或避了坑，欢迎点个 Star ⭐ 让更多人看到

[![Star History Chart](https://api.star-history.com/svg?repos=Dragon-01-you/xh-forensics&type=Date)](https://star-history.com/#Dragon-01-you/xh-forensics&Date)

---

<div align="center">

**芯火 XH**（`xh-forensics`）— LLM relay API forensics toolkit

`AI中转站` · `API验真` · `假模型检测` · `模型指纹` · `系统提示词提取` · `System Prompt Extraction` · `LLM Forensics` · `Model Fingerprinting` · `Model Equality Testing` · `API Gateway Audit` · `大模型安全` · `DeepSeek` · `GPT中转` · `Claude中转`

</div>
