"""xh-forensics（芯火 XH）: 中转站 API 验真取证工具包。

给任何 OpenAI 兼容端点做"验真体检"：它背后到底是什么模型？
方法论对标:
- Model Equality Testing (ICLR 2025, Stanford) — 同一性两样本检验
- Real Money, Fake Models: Deceptive Model Claims in Shadow APIs (arXiv:2603.01919)
- LLMmap — 黑盒指纹
- FlashProve / 可验证推理（Anthropic, 2026-11 开源）— zkSNARK 证明与权重承诺
- CL4R1T4S / asgeirtj/system_prompts_leaks — 系统提示词泄露档案与提取技术谱系
- elder-plinius 对抗性提取分类学（NEW_PARADIGM / leetspeak / 假设框架）

差异化能力（上述项目均不具备）:
- 中转站威胁模型、reasoning_content 侧信道收割、罐头答案聚类、
  多实例日期指纹、内容路由 A/B + Fisher 检验、计费分词器交叉验证、
  假流式时序检测、厂商自我知识归属、经济不可行性测算、小白可读判决引擎
v0.3.0 新增:
- dig 一键模式: URL+API → 全自动挖掘 → DOSSIER.md 总档案
- fingerprint 零成本指纹: 错误矩阵/特征端点/定价表/自曝消息/姊妹站发现
- pliny v2: Policy Puppetry / 配置合成 / 二十问假设确认收网 / FITD 登门槛
- supplychain: 供应链关系网 mermaid 图谱 + 置信度分级边清单
v0.4.0 新增（四大开源项目核心技术集成）:
- LLMmap 预训练指纹分类器（USENIX Security '25）: 8 查询 × 52 模板最近邻，
  快速预分类层，可选依赖优雅降级（probes/llmmap_fingerprint.py）
- 加密签名验证: Anthropic thinking signature 结构化验证 + OpenAI reasoning
  token 难度区分度，证据类别权重最高（probes/crypto_signature.py）
- 安全审计: 提示注入/上下文截断/工具改写/SSE 完整性/Key 泄露，
  独立查询家族（probes/security_audit.py）
- 官方基线自动化比对: 余弦/KL 散度多维偏离 → FRAUD_DETECTED 四级判定
  （baseline_compare.py + baselines/ + 每周自动同步 workflow）
- 判决引擎 v2: 类别归一化 + 错误探针跳过 + 非对称匹配 + 温度 Softmax
  概率化判定 + 覆盖率保护（verdict.py）
- Agent Skill 发布: SKILL.md（Claude Code / OpenClaw / Hermes Agent 可自动调用）
- Web UI 本地控制台: 零新增依赖（http.server + SSE），报告卡片 + 实时进度
  （webapp.py）
v0.5.0 新增（对标顶尖项目的「数据即产品」基因）:
- 公开情报库 intel/: 机器可读欺诈特征库（9 大类，fraud_patterns.json）
  + 多站点横向对比报告（cross_site_comparison.md）——不装工具也能消费
- 判决引擎回归基准: tests/cases/ 历史已定案件 → 期望档位
  （tests/run_regression.py，对标 LLMmap test_model.py 的量化标尺模式）
- 学术引用: CITATION.cff（GitHub 渲染 "Cite this repository" 按钮）
v0.7.0 新增（可验证推理：把证据轴抬到数学层）:
- attestation 证据轴（attestation.py）: 核验证明包与「输出/货品」的绑定关系
  输出哈希 / 主体模型 / 权重承诺 / 证明体量 / 新鲜度-nonce 五类绑定；
  判定 attested_verified(+3) / attested_unverified(+1) / unverifiable(0) / inconsistent(-3)
- `xh attest probe|verify` 子命令：探测端点能力（零计费）+ 离线核验（无需网络/GPU）
- 判决引擎双轴: score（行为学似然）+ assurance（保证级别：密码学确证 / 行为学推定）
- 情报卡 intel/verifiable_inference.md: 中转站 5 种绕过路径 + 证明不能证明什么
"""

__version__ = "0.7.0"
