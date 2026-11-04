#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""report: 小白可读报告生成器。"""
from __future__ import annotations


def generate_report(results: dict) -> str:
    meta = results.get("meta") or {}
    v = results.get("verdict") or {}
    lines = []
    a = lines.append

    a("# API 中转站验真报告（xh 自动生成）\n")
    a(f"- **目标**：`{meta.get('base_url')}`")
    a(f"- **声称模型**：`{meta.get('model')}`")
    a(f"- **取证时间**：{meta.get('ts_utc')}")
    a("")
    a(f"## 总判决：{v.get('tier')}（可信度评分 {v.get('score')}/100）\n")
    a(f"> {v.get('tier_desc')}\n")

    asm = v.get("assurance") or {}
    if asm:
        a(f"- **保证级别**：{asm.get('label')}（`{asm.get('level')}`）")
        if asm.get("note"):
            a(f"- {asm['note']}")
        if asm.get("commitment_id"):
            a(f"- 权重承诺：`{asm['commitment_id']}`")
        a("")

    att = v.get("attestation") or {}
    if att.get("verdict_id"):
        a("## 可验证推理证明核验\n")
        a(f"- 核验结论：**{att['verdict_id']}**")
        if att.get("headline"):
            a(f"- {att['headline']}")
        if att.get("provider"):
            a(f"- 证明系统：`{att['provider']}`")
        if att.get("commitment_id"):
            a(f"- 权重承诺：`{att['commitment_id']}`")
        a("")
    elif att.get("advertised"):
        a("## 可验证推理证明核验\n")
        a("- 端点**自称**提供可验证推理，但未提供证明包——"
          "请向服务商索取 bundle 后用 `xh attest verify` 核验绑定关系。")
        a("")

    clues = v.get("clues") or []
    if clues:
        a("## 证据清单（按严重度）\n")
        a("| # | 严重度 | 发现 | 给小白的解释 |")
        a("|---|---|---|---|")
        for i, c in enumerate(clues, 1):
            a(f"| {i} | {'🚨' if c['severity'] <= -3 else '⚠️' if c['severity'] <= -1 else 'ℹ️'} "
              f"| {c['finding']} | {c['layman']} |")
        a("")

    um = results.get("unmask") or {}
    if um:
        uv = um.get("verdict") or {}
        a("## 揭面速览（模型真身）\n")
        vc = um.get("vendor_confessions") or {}
        if vc:
            a("**厂商自认矩阵**（英文明问 'Who developed you?'，绕过中文贴皮话术）：\n")
            for m, x in vc.items():
                a(f"- `{m}` → **{x['vendor']}**（{x['quote'][:60].strip()}）")
            a("")
        if uv.get("single_backend_suspect"):
            a(f"- ⚠️ 单后端贴牌嫌疑：{uv['single_backend_suspect']}")
        tiers = um.get("injection_tiers") or {}
        if tiers:
            a(f"- 注入分层（pt 聚类）：`{tiers}`")
        if uv.get("identity_hijack_models"):
            a(f"- ⚠️ 中文身份问题渠道改道：`{uv['identity_hijack_models']}`")
        if uv.get("phantom_skus"):
            a(f"- ⚠️ 目录虚挂 SKU：`{uv['phantom_skus']}`")
        ctx = um.get("ctx_windows") or {}
        for m, x in ctx.items():
            a(f"- 上下文窗口实测：`{m}` = {x.get('tokens')} tokens")
        vh = um.get("verbatim_hits") or []
        if vh:
            best = max(vh, key=lambda h: h["score"])
            a("")
            a("**系统提示词逐字命中**（最优一条，"
              f"{best['model']}/{best['channel']}）：\n")
            a("```text")
            a(str(best["text"])[:1500])
            a("```")
        a("")

    ident = results.get("identity") or {}
    if ident:
        a("## 身份测谎摘要\n")
        if ident.get("self_claim_counts"):
            a(f"- 自我认定统计：`{ident['self_claim_counts']}`")
        a(f"- 身份问题改道率：{ident.get('routing_anomaly_rate')}；对照组：{ident.get('control_routing_anomaly_rate')}")
        a(f"- 思维链泄露：{ident.get('cot_leak_count')} 条")
        a("")

    dl = results.get("dialect") or {}
    if dl:
        a("## 厂商自我知识归属\n")
        a(f"- **最可能上游**：`{dl.get('top_vendor')}`（生态知识命中置信 {dl.get('confidence')}）")
        vs = dl.get("vendor_scores") or {}
        if vs:
            a("- 归属得分：" + "，".join(f"{k}×{v}" for k, v in sorted(vs.items(), key=lambda x: -x[1])))
        for ev in (dl.get("evidence") or []):
            if ev.get("matched"):
                a(f"- 命中题：「{ev['question']}」→ 指向 `{ev['vendor']}`")
        a("")

    py = results.get("pliny") or {}
    if py:
        a("## 对抗性提取（pliny 武库）\n")
        a(f"- 强命中 {py.get('strong_hits')} 次 / 最高分 {py.get('max_score')}"
          f"（单轮 {py.get('n_single_turn')} 式 + 有状态序列 {py.get('n_stateful_sequences')} 组）")
        for h in (py.get("best_hits") or [])[:5]:
            frag = (h.get("content") or h.get("cot") or "")[:120].replace("\n", " ")
            a(f"- `{h['id']}`（score={h['hit_score']}）：{frag}…")
        a("")

    rt = results.get("router_detect") or {}
    if rt:
        a("## 内容路由探测\n")
        a(f"- **判定**：{rt.get('verdict')}（身份组改道率 {rt.get('identity_reroute_rate')} vs 对照组 {rt.get('control_reroute_rate')}，Fisher p={rt.get('fisher_p')}）\n")

    cap = results.get("capability") or {}
    if cap:
        a("## 学力测验\n")
        a(f"- **能力档位**：{cap.get('capability_tier')}")
        byd = cap.get("by_difficulty") or {}
        for k in ("E", "M", "H"):
            if k in byd:
                a(f"- {k} 难度通过率：{byd[k]['rate']}（{byd[k]['pass']}/{byd[k]['n']}）")
        bydom = cap.get("by_domain") or {}
        if bydom:
            a("- 分学科：" + "，".join(f"{k} {x['rate']}" for k, x in bydom.items()))
        a("")

    met = results.get("met") or {}
    if met:
        a("## 模型同一性检验（MET）\n")
        a(f"- 对比：`{met.get('model_a')}` vs `{met.get('model_b')}`")
        a(f"- 组内相似度 {met.get('within_similarity')} vs 跨组 {met.get('cross_similarity')}"
          f" → {'同一分布（同一模型）' if met.get('same_distribution') else '不同分布（不同模型）'}\n")

    a("## 方法论说明\n")
    a("- 身份测谎 / 提示词提取：参考 CL4R1T4S、system-prompts-and-models-of-ai-tools 社区技术")
    a("- 内容路由探测：请求级 A/B 对照 + Fisher 精确检验")
    a("- 同一性检验：对标 Model Equality Testing (ICLR 2025, Stanford)")
    a("- 可验证推理证明核验：对标 FlashProve（Anthropic, 2026-11 开源）的「权重承诺 + 单次推理证明」"
      "绑定模型；本工具只核绑定关系，上游验签由对应 verifier 执行")
    a("- 整体框架：对标 Real Money, Fake Models: Deceptive Model Claims in Shadow APIs (arXiv:2603.01919)\n")
    a(f"> 免责声明：{v.get('disclaimer')}")
    return "\n".join(lines)
