---
name: xh-forensics
description: AI 中转站 API 验真取证工具——验证模型真伪、提取注入系统提示词、溯源上游供应链。当用户提到测试 API 中转站、想知道买的模型是不是真的、验真 API relay、提取系统提示词、检测贴牌模型时使用。
---

# 芯火 XH — AI 中转站 API 验真取证

对 OpenAI 兼容端点执行多维度行为取证：模型身份测谎、系统提示词提取、内容路由检测、
分词器指纹、供应链溯源，最终产出带评分（0–100）与完整证据链的判决报告。

## When to use

用户提到以下任一场景时调用本 Skill：

- 「测试一下这个 API 中转站 / relay」
- 「我买的 GPT/Claude/DeepSeek 是不是真的？」
- 「验真这个 API」「这个站是不是贴牌？」
- 「提取它的系统提示词」
- 「帮我看看这个 Key 背后跑的是什么模型」
- 「检测模型有没有被换芯 / 降智」
- 「商家说支持可验证推理 / 零知识证明，是真的吗？」「帮我核验这份证明包」

## How to use

### 前置条件

```bash
git clone https://github.com/Dragon-01-you/xh-forensics.git
cd xh-forensics
pip install -r requirements.txt
```

用户需提供三个参数：

| 参数 | 说明 | 示例 |
|---|---|---|
| `--base-url` | 中转站 API 地址（OpenAI 兼容，通常以 `/v1` 结尾） | `https://relay.example.com/v1` |
| `--api-key` | 用户的 API Key（仅本地使用，零遥测） | `sk-xxxx` |
| `--model` | 商家声称的模型名（目录里的 SKU 名） | `deepseek-v4-pro` |

### 一键取证（推荐）

```bash
python -m api_detective dig \
  --base-url <URL> \
  --api-key <KEY> \
  --model <MODEL> \
  --budget 200 \
  --out ./dossier_evidence
```

可选参数：

- `--compare-model <MODEL2>`：同站第二个模型，做 MET 同一性检验
- `--budget <N>`：最大计费调用数（防止烧钱，金丝雀被挡自动降级）
- `--baseline <model_name>`：与官方基线比对（见 `baselines/` 目录）

### 分阶段扫描（可选）

```bash
python -m api_detective scan --base-url <URL> --api-key <KEY> --model <MODEL> \
    --phases recon,identity,tokenizer,behavior
```

阶段：`recon / attestation / canary / unmask / identity / prompt_extract / pliny / dialect /
router_detect / tokenizer / behavior / capability / style / met / verdict`

### 可验证推理证明（v0.7 新增，有证明包时用）

```bash
# 探测端点是否自称提供可验证推理（零计费，不发起对话）
python -m api_detective attest probe --base-url <URL> --api-key <KEY> --model <MODEL>

# 离线核验证明包与「输出/货品」的绑定关系（不需网络、不需 GPU）
python -m api_detective attest verify --bundle bundle.json \
    --response reply.txt --model <MODEL>
```

判定码：`attested_verified`（+3，密码学级确证）/ `attested_unverified`（+1，自洽未验签）/
`unverifiable`（0，不下结论）/ `inconsistent`（−3，声称被证伪，CLI 退出码 1）。
**没有证明 ≠ 假货**——端点不具备该能力时不计分、不定罪。

## Output

- `./dossier_evidence/DOSSIER.md` — 判决报告：评分 0–100 + 档位 + 逐条小白可读解释
- `./dossier_evidence/_final_results.json` — 结构化结果（verdict.score / verdict.tier）
- `./dossier_evidence/*.json` — 每次探测一个 JSON，全程可复核

### 评分档位

| 分数 | 档位 |
|---|---|
| ≥85 | 正品官方直连/可信转售 |
| ≥65 | 大体可信，少量疑点 |
| ≥45 | 可疑 |
| ≥25 | 高度可疑（大概率假货） |
| <25 | 确证贴牌/拼装 |

### 向用户汇报时

读取 `DOSSIER.md` 的判决部分，引用 3–5 条最关键证据（如厂商自认矩阵、
系统提示词逐字命中、路由改道率），用小白语言解释结论，并给出维权建议。

## Constraints

- 仅用于用户自己持有 Key 的端点，不用于未授权测试
- API Key 仅通过命令行参数传入，绝不写入代码或配置文件
- 工具零遥测、零上传，所有证据仅保存在本地 `--out` 目录
- 默认预算 $0.02–$0.2；金丝雀探针发现计费被挡会自动降级为零成本测试
