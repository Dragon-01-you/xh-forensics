# 更新日志

本项目遵循 [语义化版本](https://semver.org/lang/zh-CN/)。所有重要变更都会记录在此文件。

格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)。

---

## [Unreleased]

## [0.7.0] — 2026-11-04

> 本次为**证据轴扩展 + 仓库迁移收尾**版本：吸收 Anthropic FlashProve（2026-11-03 开源）
> 带来的可验证推理能力，新增第四类证据轴；原有探针与评分逻辑不变（回归基准 5/5 通过）。

### 新增
- **可验证推理证明核验（`xh attest`）**：`attestation.py`
  - `xh attest probe`：零计费探测端点是否自称提供可验证推理（`/v1/models` 字段、
    响应头、`.well-known` 端点、首页文案）
  - `xh attest verify`：离线核验证明包 5 类绑定——输出哈希（证明是否绑定你实际收到的
    那段文字）、主体模型（证明的模型 vs 在售 SKU）、权重承诺格式、证明体量下限
    （STARK 级证明体积与计算轨迹成正比，400B 级实测约 19 MB/次）、新鲜度/nonce 防重放；
    内联证明体额外校验摘要
  - 判定码：`attested_verified`(+3) / `attested_unverified`(+1) / `unverifiable`(0) /
    `inconsistent`(-3)；绑定不一致时 CLI 以退出码 1 结束，便于接入风控与 CI
  - **未实现 STARK 证明系统本身**：真正的密码学验签由上游 verifier 执行，
    本工具核的是中转站唯一能动手脚的那层（绑定关系）
- **判决引擎双轴（`assurance`）**：分数仍是行为学似然，新增保证级别
  `cryptographic`（密码学确证）/ `attested`（自洽未验签）/ `behavioral`（行为学推定）/ `failed`。
  新增证据类别 `attestation`（权重 0.20，全类别最高）；**端点没有该能力时不计分、不定罪**
- **`scan` / `dig` 接入**：`--attestation-bundle` / `--attestation-response`
  把证明包并入整体判决；`dig` 增加零计费能力探测步骤
- **情报卡 `intel/verifiable_inference.md`**：三段式流程（按手印/开证明/验真）的公开口径数据、
  中转站 5 种绕过路径（双源拼装/换货不换证/体积缩水/重放旧证/空头承诺）、
  以及「证明不能证明什么」（系统提示词、量化版本、路由计费均不在证明范围内）
- **示例与测试**：`examples/attestation_bundle.example.json` +
  `examples/attestation_response.example.txt`（可立即跑通 `xh attest verify`）；
  `tests/test_attestation.py`（19 项断言，零依赖）+ CI 步骤

### 变更
- **仓库地址迁移完成**：GitHub 仓库由 `Dragon-01-you/api-detective` 更名为
  `Dragon-01-you/xh-forensics`，与产品名、PyPI 包名、命令名统一。README 徽章、
  clone 地址、`pyproject.toml` 的 `[project.urls]`、`CITATION.cff`、Skill 包、
  两张配图页脚、30 秒宣传片片尾地址均已同步。GitHub 保留旧名 301 重定向，
  历史链接不会失效。`api-detective` 命令行别名继续保留。
- 证据类别由 11 类增至 12 类；权重总和 1.20（聚合按「在场类别」归一，
  覆盖率上限截断到 1.0，历史案件评分不变）
- 报告的「总判决」下新增**保证级别**一行：明确本次结论是密码学确证还是行为学推定

### 修复
- `tools/make_readme_art.py` 未使用的 `import shutil`（ruff `F401`）导致 CI 连续两次失败

## [0.6.0] — 2026-08-25

> 本次为**品牌重塑 + 工程化补全**版本，探针与判决逻辑无改动。

### 变更
- **项目更名为「芯火 XH」**（产品名与 PyPI 包名 `xh-forensics`）；GitHub 仓库路径
  暂沿用 `api-detective`，以保证徽章、clone 与历史链接即刻可用。日后迁移到
  `xh-forensics` 时，GitHub 会自动 301 重定向，无需改动任何链接。
- PyPI 包名统一为 `xh-forensics`，新增命令 `xh` 与 `xh-forensics`；
  原 `api-detective` 命令**保留为兼容别名**，已有脚本无需修改。
- Python 导入路径 `api_detective.*` **保持不变**，属于内部实现，不随品牌改名。

### 新增
- `MANIFEST.in`：sdist 打包清单，确保公开情报库（`intel/`）、基线模板、Skill 包、
  文档与回归用例随源码包一起分发。
- `[tool.setuptools.data-files]`：wheel 安装时把 `intel/`、`baselines/_template.json`、
  Skill 包释放到 `<prefix>/share/xh-forensics/`，解决此前「pip 安装后情报库丢失」的问题。
- `CHANGELOG.md`（本文件）、`CODE_OF_CONDUCT.md`、`.github/dependabot.yml`、
  `.github/pull_request_template.md`。
- Python 3.14 分类器；新增 `dev` 可选依赖（`build`、`ruff`）。
- **30 秒宣传片**：`docs/promo/`（MP4 + 循环 GIF + 海报），README 中英文首屏直接播放；
  片中数据全部取自真实复测案件与回归基准，并加入两张真实界面截图（报告卡片 / 本机 Web UI）。
- `pyproject.toml` 补充 `Repository` / `Changelog` / `Intelligence` 项目链接。

### 修复
- wheel 不再遗漏公开情报库数据文件。
- Web UI 本地控制台页头残留旧品牌名，已改为「芯火 XH 本地控制台」。
- **合规修复（重要）**：此前 `MANIFEST.in` 缺省时，含可识别站点域名与商号的未脱敏案例
  `examples/yunjunet_case.md` 会被打进 sdist。现已在 `MANIFEST.in` 加硬排除、
  并把同名规则写进 `.gitignore` 随仓库传播，双重拦截。已验证 sdist 与 wheel 均不含该文件。
- **修复两处死链**：`README.md` 与 `intel/cross_site_comparison.md` 此前指向未公开的
  未脱敏案例文件（公网 404）。改为指向可公开的 `intel/cross_site_comparison.md`
  与 `examples/relayx_case.md`。

---

## [0.5.0] — 2026-08-24

### 新增
- **公开情报库 `intel/`**：从 2026-06 至 2026-08 真实取证案件提炼的机器可读欺诈特征库。
  - `intel/README.md` — 30 秒速查表 + 9 大类欺诈特征索引。
  - `intel/fraud_patterns.json` — 9 大类机器可读特征（自造 SKU / 命名空间泄露 / 换皮 /
    封口令 / 内容路由 / 分词器指纹 / 软件指纹 / 过期日期 / 经济不可行），
    每条附 regex、判定方法、证据等级、来源案件。
  - `intel/cross_site_comparison.md` — 多站点横向对比手法矩阵（含 2026-08 复测更新）。
- **判决回归基准 `tests/run_regression.py`**：5 个历史用例覆盖边界混合、真货阳性收缩、
  覆盖不足守卫、单后端换皮、弱信号中危档位，防止判决引擎改动引入回归。
- 学术引用支持：`CITATION.cff`，方法论对标 LLMmap (USENIX Security '25) /
  Model Equality Testing (ICLR 2025) / Real Money, Fake Models。

### 变更
- README 首屏重排：公开情报库前置，无需安装工具即可消费。

---

## 0.5.0 之前

早期迭代完成了核心探针体系与工程化基建，未打版本标签：

- 12+ 探针模块：LLMmap 预训练指纹（52 模板最近邻）、加密签名验证（Claude thinking
  signature / OpenAI reasoning tokens）、内容路由 Fisher 精确检验、计费分词器指纹、
  三层注入模板系统提示词提取、安全审计 5 探针、身份测谎、能力测验、模型同一性检验（MET）、
  供应链溯源。
- Softmax 判决引擎 v2（类别归一化 + 概率化 0–100 打分 + 证据不足守卫）。
- 零依赖 Web UI 本地控制台；DOSSIER 小白可读总档案。
- CI：Python 3.10–3.13 四版本矩阵、7 个 CLI 入口冒烟、判决引擎单测、回归基准、
  LLMmap 优雅降级验证、零成本 recon 冒烟。
- 双语文档（README.md / README_EN.md）、社区规范、演示素材。
