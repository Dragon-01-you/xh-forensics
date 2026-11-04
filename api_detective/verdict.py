#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""verdict: 判决引擎 v2（评分科学化升级）。

v2 相比 v1 的升级（吸收 FakeModelDetector 方法学）:
1. 类别归一化   —— 探针按类别分组，组内取 severity 均值再乘类别权重，
                   单个维度探针数量多不再主导总分
2. 错误探针跳过 —— 探针因 429/HTML/超时失败时该类别自动缺席，
                   权重重分配给有证据的类别，不污染评分
3. 非对称匹配   —— "模型应该知道"（自家家谱/签名格式）正向计分，
                   "模型不应该知道/不应该出现"（泄露指令/异常签名）反向计分
4. 温度 Softmax —— 组内均值 severity 过 sigmoid(mean_sev/0.5)，
                   输出概率化判定 P(正品) ∈ [0,1]，档位边缘案例解释更科学
5. 证据覆盖率   —— 缺席类别过多时向中性收缩并触发「证据不足」保护，
                   防止只跑 recon 就给出高分假阳性

证据类别权重（密码学 > 预训练指纹 > 行为侧信道；总和 1.20，
聚合按「在场类别」权重归一，故总和 > 1 不影响加权平均，只把覆盖率上限截断到 1.0）:
  attestation        0.20  可验证推理证明（zkSNARK 绑定核验，2026-11 FlashProve 后的新证据轴）
  crypto_signature   0.18  密码学证据（Anthropic thinking signature / reasoning tokens）
  llmmap_fingerprint 0.14  预训练指纹分类器输出（52 模板最近邻）
  identity           0.16  自我身份证据
  injected_prompt    0.12  注入指令/封口令证据
  routing            0.08  内容路由异常
  behavior           0.06  行为指纹
  security_audit     0.06  中转站安全风险（注入/截断/改写/泄露）
  spec               0.05  规格/计费矛盾
  tokenizer          0.05  计数器指纹
  style_met          0.05  风格/MET 同源性
  economics          0.05  经济可行性
"""
from __future__ import annotations

import math

WEIGHTS = {
    "attestation": 0.20,        # 可验证推理证明（数学级——绑定自洽且上游验签通过）
    "crypto_signature": 0.18,   # 密码学证据（最高——服务端加密产物难以伪造）
    "llmmap_fingerprint": 0.14, # 预训练指纹（高于现场探针）
    "identity": 0.16,           # 自我身份证据
    "injected_prompt": 0.12,    # 注入指令/封口令证据
    "routing": 0.08,            # 内容路由异常
    "behavior": 0.06,           # 行为指纹
    "security_audit": 0.06,     # 安全审计发现
    "spec": 0.05,               # 规格/计费矛盾
    "tokenizer": 0.05,          # 计数器指纹
    "style_met": 0.05,          # 风格/MET 同源性
    "economics": 0.05,          # 经济可行性
}

SOFTMAX_TEMPERATURE = 0.5   # 温度 Softmax 温度（作用在 severity 尺度上）
NEUTRAL_P = 0.5             # 中性概率（证据缺席时收缩目标）
COVERAGE_FLOOR = 0.35       # 覆盖率低于此值 → 「证据不足」保护

TIERS = [
    (85, "正品官方直连/可信转售", "各维度均符合官方行为，未发现贴牌痕迹"),
    (65, "大体可信，少量疑点", "主证据链干净，存在个别可解释的异常"),
    (45, "可疑", "多项独立证据指向贴牌/换芯，建议补充官方对照"),
    (25, "高度可疑（大概率假货）", "多重独立证据互锁，伪造需要真跑真模型才能骗过"),
    (0,  "确证贴牌/拼装", "实锤级证据（泄露指令/自认他厂/路由欺诈）齐备"),
    (-1, "证据不足（无法判定）", "可用证据覆盖率过低，请提升预算重跑或检查端点可用性"),
]


# ----------------------------------------------------------------------
# 评分核心
# ----------------------------------------------------------------------
def _softmax_p_genuine(mean_sev: float, temperature: float = SOFTMAX_TEMPERATURE) -> float:
    """温度 Softmax（二分类）：severity 均值 → P(正品)。

    等价于对 [genuine, fake] 两类 logits 做 softmax，
    genuine 的 logit = mean_sev/temperature：
      mean_sev=+1 → P≈0.88（正向证据）
      mean_sev= 0 → P= 0.50（中性）
      mean_sev=-1 → P≈0.12（单维度疑点）
      mean_sev=-3 → P≈0.002（实锤级）
    """
    return 1.0 / (1.0 + math.exp(-mean_sev / temperature))


def _score_categories(clues: list) -> tuple[dict, dict]:
    """类别归一化：组内 severity 均值 → 概率。

    返回 (p_by_cat, mean_sev_by_cat)。缺席类别不出现（错误探针跳过）。
    """
    sevs: dict[str, list] = {}
    for cat, s, *_ in clues:
        sevs.setdefault(cat, []).append(s)
    p_by_cat, sev_by_cat = {}, {}
    for cat, ss in sevs.items():
        mean = sum(ss) / len(ss)
        sev_by_cat[cat] = round(mean, 3)
        p_by_cat[cat] = round(_softmax_p_genuine(mean), 4)
    return p_by_cat, sev_by_cat


def _aggregate(p_by_cat: dict, sev_by_cat: dict) -> dict:
    """加权聚合 + 非对称覆盖率收缩 + 概率化判定。

    收缩规则（防两类偏差）:
    - 正向证据（p>0.5）按覆盖率全收缩：没测过的维度不能给"正品"背书
    - 负向证据（p<0.5）部分收缩：缺席维度不应稀释已到手的实锤；
      含 -3 实锤级线索时不收缩（实锤无法用"没测够"解释）
    """
    present_w = sum(WEIGHTS.get(c, 0) for c in p_by_cat)
    if not p_by_cat or present_w <= 0:
        return {"p_genuine": NEUTRAL_P, "coverage": 0.0,
                "score": 50, "inconclusive": True}
    p = sum(p_by_cat[c] * WEIGHTS.get(c, 0) for c in p_by_cat) / present_w
    coverage = round(min(1.0, present_w), 4)
    has_hard = any(s <= -3 for s in sev_by_cat.values())
    if p >= NEUTRAL_P:
        rate = coverage                       # 正向：按覆盖率收缩
    else:
        rate = 1.0 if has_hard else max(coverage, 0.6)  # 负向：温和收缩
    p_final = NEUTRAL_P + (p - NEUTRAL_P) * rate
    score = round(p_final * 100)
    return {"p_genuine": round(p_final, 4), "coverage": coverage,
            "score": score, "inconclusive": coverage < COVERAGE_FLOOR}


def _tier_for(score: int, inconclusive: bool) -> tuple:
    if inconclusive:
        return TIERS[-1]
    return next(t for t in TIERS if score >= t[0])


def _edge_case_note(score: int, inconclusive: bool, p_by_cat: dict,
                    coverage: float) -> str:
    """边缘案例（40–70 分带）的科学解释。"""
    if inconclusive:
        return (f"证据覆盖率仅 {coverage:.0%}（阈值 {COVERAGE_FLOOR:.0%}），"
                "缺席维度的权重已向中性收缩——本档结论不代表验真通过，"
                "建议加大 --budget 重跑。")
    if 40 <= score <= 70:
        hi = max(p_by_cat.items(), key=lambda kv: abs(kv[1] - 0.5),
                 default=None)
        if hi:
            c, p = hi
            side = "偏正品" if p > 0.5 else "偏贴牌"
            return (f"处于边缘分带：最分裂的维度是「{c}」"
                    f"（P(正品)={p:.2f}，{side}）。"
                    "建议补跑该维度的探针或用 --baseline 官方基线做严格比对。")
    return ""


# ----------------------------------------------------------------------
# 线索收集（非对称匹配：should-know 正向 / should-not 反向）
# ----------------------------------------------------------------------
def _collect_clues(data: dict) -> list:
    clues: list[tuple] = []

    # ---- 身份（should-know：模型应该知道自己是谁）----
    ident = data.get("identity") or {}
    if ident:
        claims = ident.get("self_claim_counts") or {}
        foreign = {k: v for k, v in claims.items()
                   if k not in ("DeepSeek", "深度求索")}
        if foreign:
            top = max(foreign, key=foreign.get)
            clues.append(("identity", -3, "foreign_self_id",
                          f"模型自我认定为「{top}」×{foreign[top]} 次",
                          "问它自己是谁，它反复自认是别家模型。模型最了解自己——"
                          "这是最强的身份证据，除非网关伪造，否则无法造假。"))
        canned = ident.get("top_canned") or []
        if canned and canned[0][1] >= 3:
            clues.append(("identity", -2, "canned_answers",
                          f"身份问题回答完全雷同 ×{canned[0][1]}",
                          "对同一个问题，多次回答一字不差——真人对话不可能这样，"
                          "说明答案被预设指令锁死（罐头话术）。"))
        cot = ident.get("cot_leak_count") or 0
        if cot:
            clues.append(("injected_prompt", -3, "cot_leak",
                          f"思维链泄露系统指令引用 ×{cot}",
                          "推理模型的'思考过程'会复述它收到的指令。网关能改最终回答，"
                          "但改不了思考过程——除非下封口令，否则它会把真话想出来。"))

    # ---- LLMmap 预训练指纹（should-match：最近邻应与声称 SKU 同厂）----
    lm = data.get("llmmap") or {}
    if lm.get("available") and lm.get("ranking"):
        top1 = lm.get("top1") or {}
        t1m, t1d = top1.get("model", "?"), top1.get("distance", "?")
        ranking_txt = " | ".join(f"{r['model']}({r['distance']})"
                                 for r in lm["ranking"][:3])
        if lm.get("claimed_in_pool") and lm.get("brand_match") is False:
            clues.append(("llmmap_fingerprint", -3, "llmmap_mismatch",
                          f"LLMmap 最近邻「{t1m}」与声称 SKU「{lm.get('claimed_model')}」"
                          f"不同厂（distance={t1d}；top3: {ranking_txt}）",
                          "预训练指纹分类器（USENIX Security '25，52 个模型模板）"
                          f"给出距离最近的模型是「{t1m}」——它与商家宣称的不是同一家。"
                          "这不是现场出题的猜测，是与 52 个官方行为模板比对出的最近邻。"))
        elif lm.get("brand_match") is True:
            clues.append(("llmmap_fingerprint", 1, "llmmap_match",
                          f"LLMmap 最近邻「{t1m}」与声称 SKU 同厂（distance={t1d}）",
                          "预训练指纹与商家宣称的厂商一致（型号级别仍需现场探针确认）。"))
        elif lm.get("close_foreign_template"):
            clues.append(("llmmap_fingerprint", -2, "llmmap_close_foreign",
                          f"声称「{lm.get('claimed_model')}」（不在 52 模板池），"
                          f"但行为与「{t1m}」距离仅 {t1d}——异常接近",
                          "商家卖的是一个指纹库里没有的型号，但它的行为模式"
                          f"和「{t1m}」几乎重合——很可能是同一个开源模型换皮。"))
    elif lm and lm.get("reason"):
        pass  # 依赖未装/模型缺失 → 类别缺席，不污染评分（错误探针跳过）

    # ---- 可验证推理证明（attestation，第四类证据轴）----
    # 只在拿到证明包核验结果时计分；端点「没有这项能力」不定罪（2026 年仍是极少数）
    att = data.get("attestation") or {}
    ver = att.get("verification") if isinstance(att.get("verification"), dict) else att
    if ver.get("verdict_id") in ("attested_verified", "attested_unverified",
                                 "inconsistent", "unverifiable"):
        vid, sev = ver["verdict_id"], ver.get("severity")
        lay = {
            "attested_verified": (
                "FlashProve 一类可验证推理系统把「权重承诺 + 单次推理证明」绑到"
                "这段输出上，并在普通 CPU 上验签通过：这是数学级出生证明，"
                "不是行为学猜测。"),
            "attested_unverified": (
                "证明包与输出/货品的绑定关系自洽，但没跑上游 verifier——"
                "只能说明「格式与承诺对得上」，不能当作密码学确证。"),
            "inconsistent": (
                "证明包声称证明了某个模型，但与它绑定的输出/货品对不上——"
                "证明与回答可以被分别替换，这正是中转层最方便的作弊点。"),
            "unverifiable": (
                "证明包格式可读但缺关键字段或 prover 未知，无法对照公开实现，"
                "因此不作正负判断（不等于假货）。"),
        }[vid]
        if sev:
            clues.append(("attestation", sev, vid,
                          ver.get("headline", ""), lay))

    # ---- 加密签名（should-exist：真 Claude 的 thinking 签名应存在且每次不同）----
    cs = data.get("crypto_signature") or {}
    for ev in cs.get("evidence", []):
        cat = "crypto_signature"
        if ev.get("id") == "thinking_signature_missing" and not ev.get("pass"):
            clues.append((cat, -3, "thinking_signature_missing",
                          ev.get("finding", ""),
                          "Anthropic extended thinking 的 signature 是服务端加密产物，"
                          "中转站理论上无法伪造。声称 Claude 却给不出合法签名——"
                          "密码学证据直接证伪。"))
        elif ev.get("id") == "thinking_signature_valid" and ev.get("pass"):
            clues.append((cat, 2, "thinking_signature_valid",
                          ev.get("finding", ""),
                          "thinking 签名存在、格式合法且多次调用各不相同——"
                          "符合官方服务端加密产物特征，密码学级加分。"))
        elif ev.get("id") == "reasoning_token_anomaly" and not ev.get("pass"):
            clues.append((cat, -2, "reasoning_token_anomaly",
                          ev.get("finding", ""),
                          "推理模型的 reasoning token 数量应与问题难度相关；"
                          "固定不变或异常偏低说明'推理'是演出来的。"))
        elif ev.get("id") == "reasoning_token_plausible" and ev.get("pass"):
            clues.append((cat, 1, "reasoning_token_plausible",
                          ev.get("finding", ""),
                          "reasoning token 计数随难度变化，符合真实推理模型特征。"))

    # ---- 厂商自我知识归属（dialect，should-know 正向/反向）----
    dl = data.get("dialect") or {}
    if dl and dl.get("top_vendor"):
        top = dl["top_vendor"]
        conf = dl.get("confidence", 0)
        if top not in ("DeepSeek",):
            sev = -3 if conf >= 0.25 else -2
            clues.append(("identity", sev, "vendor_attribution",
                          f"厂商生态知识归属「{top}」（命中 {dl.get('vendor_scores', {})}）",
                          "问它只有自家模型才知道的'家事'：官方模型叫什么名、开放平台叫什么、"
                          f"独有接口字段是什么。它的回答指向 {top} 的生态——"
                          "冒牌货背不出正主的家谱。"))
        else:
            clues.append(("identity", 1, "vendor_attribution_ok",
                          f"厂商生态知识归属 DeepSeek（置信 {conf}）",
                          "它答得出深度求索自家的接口细节，身份自洽。"))

    # ---- 提示词提取（should-not-exist：系统提示词不该被吐出）----
    px = data.get("prompt_extract") or {}
    if px:
        best = px.get("best_hits") or []
        strong = [b for b in best if (b.get("hit_score", 0) + b.get("cot_hit_score", 0)) >= 4]
        if strong:
            clues.append(("injected_prompt", -3, "prompt_extracted",
                          f"提取到疑似系统提示词内容 ×{len(strong)}",
                          "用绕行话术让模型吐出了它收到的隐藏指令——"
                          "里面如果出现'不得回答XX'的封口名单，名单就是底牌。"))

    # ---- 对抗性提取（pliny，should-not-exist）----
    py = data.get("pliny") or {}
    if py:
        strong = py.get("strong_hits") or 0
        if strong >= 2:
            clues.append(("injected_prompt", -3, "pliny_extracted",
                          f"对抗性武库强命中 ×{strong}（最高分 {py.get('max_score')}）",
                          "换着花样绕（编码走私/伪造对话历史/多轮升级/要求先复述指令），"
                          "它多次吐出隐藏指令内容。单次可能是巧合，"
                          "多次互证就是后端确实揣着一封'封口令'。"))
        elif strong == 1:
            clues.append(("injected_prompt", -1, "pliny_weak_hit",
                          "对抗性武库有一次命中",
                          "一次绕出疑似指令片段，值得加采样复核。"))

    # ---- 路由 ----
    rt = data.get("router_detect") or {}
    if rt:
        if rt.get("verdict") == "检出内容路由":
            clues.append(("routing", -3, "content_router",
                          f"身份题改道率 {rt['identity_reroute_rate']} vs 对照 {rt['control_reroute_rate']}（p={rt['fisher_p']}）",
                          "问'你是谁'的请求被悄悄送到另一个渠道回答，普通问题则正常。"
                          "卖真货的商家永远不需要造这套系统。"))
        if rt.get("identity_answer_clustered"):
            clues.append(("routing", -1, "clustered_identity",
                          "身份组回答高度聚簇",
                          "改道后所有身份问题得到同一个模板答案。"))

    # ---- 安全审计（should-not-happen：中转层不该注入/截断/改写/泄露）----
    sa = data.get("security_audit") or {}
    sev_map = {"high": -3, "medium": -2, "low": -1}
    findings = sa.get("findings") or []
    for f in findings:
        risk = f.get("risk", "low")
        if risk in sev_map:
            clues.append(("security_audit", sev_map[risk],
                          f"sec_{f.get('name', 'unknown')}",
                          f"{f.get('name')}: {f.get('detail', '')}",
                          f.get("layman", "")))
    if findings and all(f.get("risk") == "none" for f in findings):
        clues.append(("security_audit", 1, "sec_clean",
                      f"安全审计 {len(findings)} 项全部通过",
                      "未检出中转层注入/截断/改写/泄露行为。"))

    # ---- 基线比对（should-match：与官方基线的偏离度）----
    bc = data.get("baseline_compare") or {}
    if bc.get("verdict") == "FRAUD_DETECTED":
        clues.append(("identity", -3, "baseline_fraud",
                      f"官方基线比对: FRAUD_DETECTED（总偏离度 {bc.get('total_deviation')}）",
                      "与官方端点的多维特征基线（错误措辞/延迟/token 计数/知识截止）"
                      "显著偏离——不是同一个模型的行为分布。"))
    elif bc.get("verdict") == "SUSPICIOUS":
        clues.append(("identity", -2, "baseline_suspicious",
                      f"官方基线比对: SUSPICIOUS（总偏离度 {bc.get('total_deviation')}）",
                      "与官方基线存在不可忽略的偏离，建议加大采样复核。"))
    elif bc.get("verdict") == "MATCH":
        clues.append(("identity", 2, "baseline_match",
                      "官方基线比对: MATCH",
                      "多维特征与官方基线吻合——最强旁证之一。"))

    # ---- 规格 ----
    spec = data.get("spec") or {}
    if spec.get("context_window_anomaly"):
        clues.append(("spec", -2, "ctx_anomaly",
                      f"上下文窗口注册值 {spec.get('context_window_anomaly')}",
                      "运营者自己填的渠道规格和官方不符——填表的人最清楚背后是什么。"))
    if spec.get("price_anomaly"):
        clues.append(("economics", -2, "price_anomaly",
                      str(spec.get("price_anomaly")),
                      "按官方价格转售必亏的定价，数学上只有换便宜后端才盈利。"))

    # ---- 计数器 ----
    tk = data.get("tokenizer") or {}
    if tk.get("counter_verdict") in ("cl100k", "o200k"):
        clues.append(("tokenizer", -2, "gateway_counter",
                      f"token 计数与 {tk['counter_verdict']} 吻合（GPT 系尺子）",
                      "网关用别人家的分词器自己数 token 计费，而不是透传官方 usage——"
                      "官方转售不需要重新量。"))

    # ---- MET / 风格 ----
    met = data.get("met") or {}
    if met.get("model_b") and met.get("same_distribution") is False:
        clues.append(("style_met", -1, "met_diff",
                      f"两渠道分布距离显著（cross={met['cross_similarity']} < within={met['within_similarity']}）",
                      "同一个站点的两个'模型'，输出分布完全不同——"
                      "至少其中一个不是它声称的东西。"))
    if met.get("model_b") and met.get("same_distribution") is True:
        clues.append(("style_met", 1, "met_same",
                      "两个渠道输出分布一致",
                      "两个名字背后是同一个模型（同源加分项：至少没换芯）。"))

    # ---- 行为 ----
    beh = data.get("behavior") or {}
    if beh.get("fake_stream", {}).get("fake_stream_suspect"):
        clues.append(("behavior", -1, "fake_stream",
                      "流式响应疑似假流式（结尾倾泻）",
                      "网关先攒完整回答再一次性吐出——说明中间有缓冲层改写。"))
    if beh.get("determinism", {}).get("exact_match") is False:
        clues.append(("behavior", -1, "nondeterministic",
                      "温度=0 重复输出不一致",
                      "官方原版在 t=0 下高度一致；频繁漂移提示后端被改/量化/换芯。"))

    # ---- 揭面（unmask）----
    um = data.get("unmask") or {}
    if um:
        uv = um.get("verdict") or {}
        vc = um.get("vendor_confessions") or {}
        if vc:
            # 与 SKU 品牌前缀不符的厂商自认 = 贴牌实锤
            from .unmask import _brand
            foreign = {m: x["vendor"] for m, x in vc.items()
                       if _brand(m) not in x["vendor"].lower()
                       and x["vendor"].lower() not in _brand(m)}
            if foreign:
                top = max(set(foreign.values()), key=list(foreign.values()).count)
                clues.append(("identity", -3, "unmask_vendor_confession",
                              f"英文明问自认真实厂商：{foreign}",
                              "绕过中文身份问题的贴皮话术直接用英文问'Who developed you'，"
                              "模型亲口说出真正开发商——与 SKU 品牌不符即为贴牌实锤。"))
        sb = uv.get("single_backend_suspect") or {}
        if sb:
            clues.append(("identity", -2, "unmask_single_backend",
                          f"多 SKU 共享同一注入层/自认同厂：{sb}",
                          "多个'不同品牌'的模型给出同一个厂商自认、且注入块体积一致——"
                          "一个后端换几张皮。"))
        if uv.get("verbatim_extracted"):
            bv = uv.get("best_verbatim") or {}
            clues.append(("injected_prompt", -3, "unmask_sysmsg_verbatim",
                          f"系统消息逐字提取命中（{bv.get('model')}/{bv.get('channel')}，score={bv.get('score')}）",
                          "让模型'引用你收到的系统消息'，它把完整系统提示词逐字吐出来——"
                          "双语双层结构（英文真身层+中文品牌贴皮层）一翻到底。"))
        ph = uv.get("phantom_skus") or []
        if ph:
            clues.append(("spec", -2, "unmask_phantom_skus",
                          f"目录虚挂 SKU（502/503 无渠道）：{ph}",
                          "模型列表里挂着卖、实际一问就 503——收钱的名目和真实货盘对不上。"))
        hij = uv.get("identity_hijack_models") or []
        if len(hij) >= 2:
            clues.append(("routing", -2, "unmask_identity_hijack",
                          f"中文身份问题触发渠道改道 ×{len(hij)}：{hij[:6]}",
                          "问'你是谁'时请求被改道到别的渠道应答（贴皮话术渠道），"
                          "普通问题走真渠道——按问题语义分流的内容防火墙。"))
        shared = uv.get("shared_injection_tiers") or {}
        if shared:
            clues.append(("injected_prompt", -1, "unmask_shared_tiers",
                          f"注入块分层共享：{shared}",
                          "不同 SKU 的请求背负同体积的隐藏注入块——共用同一套系统提示词配置。"))

    return clues


# ----------------------------------------------------------------------
def build_verdict(data: dict) -> dict:
    """data: {phase_name: phase_result}，各阶段可缺省（缺省=错误探针跳过）。"""
    from .attestation import assurance_block

    clues = _collect_clues(data)

    # 类别归一化 → 温度 Softmax → 概率化判定
    p_by_cat, sev_by_cat = _score_categories(clues)
    agg = _aggregate(p_by_cat, sev_by_cat)
    score, inconclusive = agg["score"], agg["inconclusive"]
    tier = _tier_for(score, inconclusive)
    edge_note = _edge_case_note(score, inconclusive, p_by_cat, agg["coverage"])

    # 保证级别（双轴）：分数是行为学似然，assurance 说明「证据强度属于哪一类」
    att = data.get("attestation") or {}
    ver = att.get("verification") if isinstance(att.get("verification"), dict) else att
    probe = att.get("probe") if isinstance(att.get("probe"), dict) else (
        att if att.get("advertised") is not None else None)
    assurance = assurance_block(ver if ver.get("verdict_id") else None, probe)

    return {
        "score": score,
        "p_genuine": agg["p_genuine"],
        "coverage": agg["coverage"],
        "inconclusive": inconclusive,
        "temperature": SOFTMAX_TEMPERATURE,
        "tier": tier[1],
        "tier_desc": tier[2],
        "assurance": assurance,                # 证据强度层级（行为学推定 / 密码学确证）
        "attestation": {
            "verdict_id": ver.get("verdict_id"),
            "headline": ver.get("headline"),
            "provider": ver.get("provider"),
            "commitment_id": ver.get("commitment_id"),
            "advertised": None if probe is None else probe.get("advertised"),
        } if (ver.get("verdict_id") or probe) else None,
        "category_scores": p_by_cat,          # 每类 P(正品)（概率化）
        "category_mean_severity": sev_by_cat, # 每类 severity 均值
        "edge_case_note": edge_note,
        "n_clues": len(clues),
        "clues": [
            {"category": c, "severity": s, "id": cid, "finding": f,
             "layman": lay}
            for c, s, cid, f, lay in clues
        ],
        "weights": WEIGHTS,
        "disclaimer": (
            "结论基于黑盒行为证据（保证级别见 assurance）。'确证'级结论"
            "（泄露指令/自认他厂/内容路由/密码学签名）在造假方不真跑真模型的前提下"
            "无法翻案；要 100% 铁证可加跑官方端点同题对照（--baseline / MET 模块），"
            "或要求服务商提供可验证推理证明包并用 `xh attest verify` 核验绑定关系"
            "（2026-11 起 FlashProve 类系统已开源）。"),
    }
