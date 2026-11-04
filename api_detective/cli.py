#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""cli: 命令行入口。

用法:
  python -m api_detective scan --base-url https://x.com --api-key sk-xxx \
      --model deepseek-v4 --phases recon,identity,behavior --budget 60

  python -m api_detective report --evidence ./evidence --out report.md
"""
from __future__ import annotations

import argparse
import json
import os

from . import __version__


def cmd_scan(args) -> None:
    from .core import Detective
    from .recon import recon as do_recon

    det = Detective(args.base_url, args.api_key, args.model,
                    out_dir=args.out, seed=args.seed)

    phases = args.phases.split(",") if args.phases != "all" else [
        "recon", "attestation", "canary", "unmask", "identity", "prompt_extract",
        "pliny", "dialect", "router_detect", "tokenizer", "behavior", "capability",
        "style", "met", "verdict"]

    results: dict = {"meta": {
        "base_url": args.base_url, "model": args.model,
        "ts_utc": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        "version": __version__,
    }}

    def budget_left():
        return args.budget is None or det.billable_calls < args.budget

    # ---- Phase 0: recon（不耗配额）----
    if "recon" in phases:
        print("[*] 阶段0 基础设施侦察 ...")
        results["recon"] = do_recon(det)
        det.ev.save("recon_summary", results["recon"])

    # ---- 可验证推理能力探测（零计费，不发起对话）----
    if "attestation" in phases:
        from .attestation import probe_attestation, verify_bundle_file
        print("[*] 阶段0a 可验证推理能力探测（零计费）...")
        att: dict = {"probe": probe_attestation(det)}
        if getattr(args, "attestation_bundle", None):
            text = None
            if getattr(args, "attestation_response", None):
                with open(args.attestation_response, encoding="utf-8") as f:
                    text = f.read()
            att["verification"] = verify_bundle_file(
                args.attestation_bundle, response_text=text, claimed_model=args.model)
            print(f"[{'!' if att['verification']['severity'] == -3 else '+'}] "
                  f"证明包核验: {att['verification']['headline']}")
        elif att["probe"].get("advertised"):
            print("[+] 端点自称提供可验证推理——请索取证明包并用 `xh attest verify` 核验")
        results["attestation"] = att

    # ---- 金丝雀 ----
    if "canary" in phases:
        print("[*] 金丝雀计费探测 ...")
        canary = det.canary()
        results["canary"] = canary
        det.ev.save("canary", canary)
        if canary.get("blocked"):
            print(f"[!] 计费被挡: {canary.get('body', '')[:80]}")
            print("[*] 对话类阶段跳过（仅完成 recon）。")
            phases = [p for p in phases if p in ("recon", "verdict")]

    # ---- 各对话阶段 ----
    from .identity import identity_battery
    from .prompt_extract import extract_battery
    from .pliny import pliny_battery
    from .dialect import dialect_quiz
    from .router_detect import router_detect
    from .tokenizer_probe import tokenizer_probe, usage_shape
    from .behavior import latency_profile, fake_stream_check, determinism_check, error_fingerprint
    from .capability import capability_ladder
    from .style import style_profile
    from .met import met_compare
    from .unmask import unmask

    if "unmask" in phases and budget_left():
        print("[*] 阶段0.5 揭面（echo矩阵/系统消息引用/英文绕过/注入分层）...")
        models = None
        if isinstance(results.get("recon"), dict):
            models = results["recon"].get("models")
        results["unmask"] = unmask(det, models=models,
                                   max_models=args.unmask_models)
        uvd = (results["unmask"].get("verdict") or {})
        if uvd.get("vendor_confession_matrix"):
            print(f"[+] 厂商自认矩阵: {uvd['vendor_confession_matrix']}")
        if uvd.get("verbatim_extracted"):
            print("[+] 系统提示词逐字命中（详见 unmask_summary）")
        if uvd.get("phantom_skus"):
            print(f"[!] 目录虚挂 SKU: {uvd['phantom_skus']}")
        if uvd.get("single_backend_suspect"):
            print(f"[!] 单后端贴牌嫌疑: {uvd['single_backend_suspect']}")
    if "identity" in phases and budget_left():
        print("[*] 阶段1 身份测谎 ...")
        results["identity"] = identity_battery(det)
    if "prompt_extract" in phases and budget_left():
        print("[*] 阶段2 提示词提取武库 ...")
        results["prompt_extract"] = extract_battery(det)
    if "pliny" in phases and budget_left():
        print("[*] 阶段2b 对抗性提取武库（pliny）...")
        results["pliny"] = pliny_battery(det)
    if "dialect" in phases and budget_left():
        print("[*] 阶段2c 厂商自我知识归属（dialect）...")
        results["dialect"] = dialect_quiz(det)
    if "router_detect" in phases and budget_left():
        print("[*] 阶段3 内容路由探测 ...")
        results["router_detect"] = router_detect(det)
    if "tokenizer" in phases and budget_left():
        print("[*] 阶段4 分词器指纹 ...")
        results["tokenizer"] = tokenizer_probe(det)
        results["usage_shape"] = usage_shape(det)
    if "behavior" in phases and budget_left():
        print("[*] 阶段5 行为指纹 ...")
        results["behavior"] = {
            "latency": latency_profile(det, n=args.latency_n),
            "fake_stream": fake_stream_check(det),
            "determinism": determinism_check(det),
            "errors": error_fingerprint(det),
        }
    if "capability" in phases and budget_left():
        print("[*] 阶段6 全学科学力测验 ...")
        results["capability"] = capability_ladder(det, reps=1)
    if "style" in phases and budget_left():
        print("[*] 阶段7 风格画像 ...")
        results["style"] = style_profile(det, samples=args.style_samples)
    if "met" in phases and budget_left() and args.compare_model:
        print(f"[*] 阶段8 同一性检验: {args.model} vs {args.compare_model} ...")
        results["met"] = met_compare(det, args.model, args.compare_model)

    # ---- 判决 ----
    from .verdict import build_verdict
    print("[*] 判决引擎 ...")
    spec = _spec_from_recon(results.get("recon"))
    if spec:
        results["spec"] = spec
    verdict_data = dict(results)
    verdict_data["spec"] = spec
    results["verdict"] = build_verdict(verdict_data)
    det.ev.save("_final_results", results)

    print(json.dumps({"score": results["verdict"]["score"],
                      "tier": results["verdict"]["tier"],
                      "billable_calls": det.billable_calls},
                     ensure_ascii=False, indent=2))
    print(f"[*] 证据目录: {args.out}/  （报告: python -m api_detective report --evidence {args.out}）")


def _spec_from_recon(rec: dict | None) -> dict:
    """从 recon 结果中抽规格矛盾。"""
    if not rec:
        return {}
    out = {}
    pub = rec.get("public_endpoints") or {}
    pricing = pub.get("/api/models") or pub.get("/api/pricing") or ""
    if pricing:
        out["pricing_table_head"] = pricing[:500]
        # 1M 上下文 = 1,048,576
        if "1048576" in pricing.replace(",", ""):
            out["context_window_anomaly"] = "有渠道注册 1,048,576 (1M) 上下文窗口"
    return out


def cmd_report(args) -> None:
    from .report import generate_report
    path = os.path.join(args.evidence, "_final_results.json")
    with open(path, encoding="utf-8") as f:
        results = json.load(f)
    md = generate_report(results)
    out = args.out or os.path.join(args.evidence, "report.md")
    with open(out, "w", encoding="utf-8") as f:
        f.write(md)
    print(f"[*] 报告已生成: {out}")


def cmd_dig(args) -> None:
    import datetime
    from .core import Detective
    from .fingerprint import fingerprint as do_fingerprint
    from .identity import identity_battery
    from .prompt_extract import extract_battery
    from .pliny import pliny_battery
    from .dialect import dialect_quiz
    from .tokenizer_probe import tokenizer_probe
    from .router_detect import router_detect
    from .supplychain import build_supplychain
    from .verdict import build_verdict
    from .dossier import generate_dossier

    det = Detective(args.base_url, args.api_key, args.model, out_dir=args.out)
    results: dict = {"meta": {
        "base_url": args.base_url, "model": args.model,
        "ts_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "version": __version__,
    }}

    def left():
        return args.budget is None or det.billable_calls < args.budget

    print("[*] dig/1 零成本指纹（免费）...")
    results["fingerprint"] = do_fingerprint(det)

    print("[*] dig/1b 可验证推理能力探测（零计费）...")
    from .attestation import probe_attestation
    att_probe = probe_attestation(det)
    results["attestation"] = {"probe": att_probe}
    if att_probe.get("advertised"):
        print(f"[+] 端点自称提供可验证推理：{att_probe['signals'][:2]}")
    else:
        print("[-] 端点无可验证推理能力（结论只能到行为学推定级）")

    print("[*] dig/2 金丝雀 ...")
    canary = det.canary()
    results["canary"] = canary
    if not canary.get("blocked"):
        print("[*] dig/3 核心挖掘：揭面（echo矩阵+系统消息+厂商自认）...")
        from .unmask import unmask as do_unmask
        try:
            fp_models = (results.get("fingerprint") or {}).get("models")
        except Exception:
            fp_models = None
        results["unmask"] = do_unmask(det, models=fp_models,
                                      max_models=getattr(args, "unmask_models", 8))
        uvd = (results["unmask"].get("verdict") or {})
        if uvd.get("vendor_confession_matrix"):
            print(f"[+] 厂商自认矩阵: {uvd['vendor_confession_matrix']}")
        if uvd.get("verbatim_extracted"):
            print("[+] 系统提示词逐字命中！")
        if uvd.get("single_backend_suspect"):
            print(f"[!] 单后端贴牌嫌疑: {uvd['single_backend_suspect']}")
        # LLMmap 预训练指纹：快速预分类层（可选依赖，未装时优雅降级）
        if not getattr(args, "no_llmmap", False):
            try:
                from .probes.llmmap_fingerprint import llmmap_fingerprint
                print("[*] dig/3a LLMmap 预训练指纹（8 查询 × 52 模板）...")
                results["llmmap"] = llmmap_fingerprint(det)
                lm = results["llmmap"]
                if lm.get("available") and lm.get("ranking"):
                    print(f"[+] LLMmap 最近邻: {lm['top1']['model']} "
                          f"(distance={lm['top1']['distance']})")
                elif not lm.get("available"):
                    print(f"[-] LLMmap 跳过: {lm.get('reason', '')[:100]}")
            except Exception as e:  # noqa: BLE001
                print(f"[-] LLMmap 异常跳过: {e}")
        print("[*] dig/3b 身份 → 提示词武库 → 厂商归属 ...")
        results["identity"] = identity_battery(det)
        if left():
            results["prompt_extract"] = extract_battery(det)
        if left():
            print("[*] dig/4 对抗性提取 v2（含二十问收网）...")
            results["pliny"] = pliny_battery(det)
        if left():
            results["dialect"] = dialect_quiz(det)
        if left():
            results["tokenizer"] = tokenizer_probe(det)
        if left() and args.compare_model:
            from .met import met_compare
            results["met"] = met_compare(det, args.model, args.compare_model)
        if left():
            results["router_detect"] = router_detect(det)
        # 加密签名验证（Anthropic thinking signature / OpenAI reasoning tokens）
        if left():
            try:
                from .probes.crypto_signature import crypto_signature_probe
                print("[*] dig/4b 加密签名验证（thinking signature / reasoning tokens）...")
                results["crypto_signature"] = crypto_signature_probe(det)
                cs = results["crypto_signature"]
                for ev_ in cs.get("evidence", []):
                    print(f"[{'+' if ev_.get('pass') else '!'}] {ev_.get('name')}: "
                          f"{ev_.get('finding', '')[:100]}")
            except Exception as e:  # noqa: BLE001
                print(f"[-] 加密签名探针跳过: {e}")
        # 安全审计（注入/截断/工具改写/SSE/Key泄露——独立查询家族）
        if left() and not getattr(args, "no_security", False):
            try:
                from .probes.security_audit import security_audit
                print("[*] dig/4c 安全审计（注入/截断/工具改写/SSE/Key泄露）...")
                results["security_audit"] = security_audit(det)
                sa = results["security_audit"].get("findings", [])
                for f_ in sa:
                    if f_.get("risk") in ("high", "medium"):
                        print(f"[!] {f_.get('name')}: {f_.get('detail', '')[:100]}")
            except Exception as e:  # noqa: BLE001
                print(f"[-] 安全审计跳过: {e}")
    else:
        print(f"[!] 计费被挡，跳过对话类阶段: {str(canary.get('body'))[:80]}")

    print("[*] dig/5 供应链关系网重建 ...")
    sc_data = dict(results)
    sc_data["base_url"] = args.base_url
    results["supplychain"] = build_supplychain(sc_data)

    verdict_data = dict(results)
    from .recon import recon as do_recon
    try:
        results["recon"] = do_recon(det)
        vd = _spec_from_recon(results.get("recon"))
        verdict_data["spec"] = vd
    except Exception:
        pass
    # 官方基线比对（--baseline gpt-4o 时启用，输出 FRAUD_DETECTED/SUSPICIOUS/INCONCLUSIVE）
    if getattr(args, "baseline", None):
        try:
            from .baseline_compare import compare_with_baseline
            print(f"[*] dig/6 官方基线比对: {args.baseline} ...")
            results["baseline_compare"] = compare_with_baseline(
                results, args.baseline)
            bc = results["baseline_compare"]
            print(f"[{'!' if bc.get('verdict') == 'FRAUD_DETECTED' else '*'}] "
                  f"基线判定: {bc.get('verdict')}（总偏离度 {bc.get('total_deviation')}）")
        except Exception as e:  # noqa: BLE001
            print(f"[-] 基线比对跳过: {e}")
    results["verdict"] = build_verdict(verdict_data)
    det.ev.save("_final_results", results)

    md = generate_dossier(results, args.out)
    out = os.path.join(args.out, "DOSSIER.md")
    with open(out, "w", encoding="utf-8") as f:
        f.write(md)
    print(json.dumps({"score": results["verdict"].get("score"),
                      "tier": results["verdict"].get("tier"),
                      "nodes": results["supplychain"]["stats"],
                      "billable_calls": det.billable_calls},
                     ensure_ascii=False, indent=2))
    print(f"[*] 总档案: {out}")


def cmd_add_model(args) -> None:
    """扩展 LLMmap 新模型模板（封装 add_new_template.py）。"""
    from .probes.llmmap_fingerprint import add_model_template
    print(f"[*] 为 LLMmap 添加新模型模板: {args.model_name} (type={args.llm_type})")
    r = add_model_template(args.model_name, args.llm_type,
                           num_prompt_confs=args.num_prompt_confs,
                           llmmap_path=args.llmmap_path,
                           prompt_conf_path=args.prompt_conf_path)
    print(json.dumps(r, ensure_ascii=False, indent=2)[:3000])
    if r.get("ok"):
        print(f"[+] 模板已写入。下次 dig 即可识别 {args.model_name}。")
    else:
        print("[!] 失败。请检查 LLMmap 仓库完整性 / API Key 环境变量。")


def cmd_attest(args) -> None:
    """可验证推理（verifiable inference）：证明包核验 / 能力探测。"""
    from .attestation import probe_attestation, verify_bundle_file

    if args.attest_cmd == "verify":
        text = None
        if args.response:
            with open(args.response, encoding="utf-8") as f:
                text = f.read()
        r = verify_bundle_file(args.bundle, response_text=text,
                               claimed_model=args.model)
        print(json.dumps(r, ensure_ascii=False, indent=2))
        print(f"\n[{'!' if r['severity'] is not None and r['severity'] < 0 else '+'}] "
              f"{r['headline']}")
        if r["verdict_id"] == "attested_verified":
            print("[+] 密码学级确证：可写入报告作为「正品」的直接证据")
        elif r["verdict_id"] == "inconsistent":
            raise SystemExit(1)   # 绑定不一致 → 体现为失败退出，便于接入 CI/风控
        return

    from .core import Detective
    det = Detective(args.base_url, args.api_key, args.model, out_dir=args.out)
    r = probe_attestation(det)
    print(json.dumps({
        "advertised": r["advertised"],
        "verdict_id": r["verdict_id"],
        "signals": r["signals"],
        "note": r["note"],
    }, ensure_ascii=False, indent=2))


def cmd_web(args) -> None:
    """本地 Web UI（FastAPI + 静态页，零遥测，仅监听 localhost）。"""
    from .webapp import run_webapp
    run_webapp(port=args.port, reports_dir=args.reports)


def cmd_baseline(args) -> None:
    """官方基线生成/比对。"""
    from .baseline_compare import generate_baseline, compare_with_baseline
    if args.generate:
        if not (args.base_url and args.api_key):
            raise SystemExit("--generate 需要同时提供 --base-url 与 --api-key（官方端点）")
        print(f"[*] 用官方端点生成基线: {args.generate} ...")
        out = generate_baseline(args.generate, args.base_url, args.api_key,
                                out_dir=args.out)
        print(f"[+] 基线已保存: {out}")
    elif args.compare:
        evidence_dir, baseline_name = args.compare
        import json as _json
        path = os.path.join(evidence_dir, "_final_results.json")
        if not os.path.isfile(path):
            raise SystemExit(f"找不到 {path}——请先用 dig 生成证据目录")
        with open(path, encoding="utf-8") as f:
            results = _json.load(f)
        try:
            r = compare_with_baseline(results, baseline_name)
        except FileNotFoundError as e:
            raise SystemExit(str(e))
        print(_json.dumps(r, ensure_ascii=False, indent=2))
    else:
        raise SystemExit("需要 --generate MODEL 或 --compare EVIDENCE_DIR BASELINE")


def main() -> None:
    ap = argparse.ArgumentParser(prog="xh",
                                 description="中转站 API 验真取证工具")
    ap.add_argument("--version", action="version", version=__version__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("scan", help="对目标端点执行全面取证")
    s.add_argument("--base-url", required=True)
    s.add_argument("--api-key", required=True)
    s.add_argument("--model", required=True, help="商家声称的模型名")
    s.add_argument("--compare-model", default=None, help="第二个模型名（MET 同一性检验）")
    s.add_argument("--phases", default="all",
                   help="逗号分隔: recon,attestation,canary,identity,prompt_extract,pliny,"
                        "dialect,router_detect,tokenizer,behavior,capability,"
                        "style,met,verdict")
    s.add_argument("--budget", type=int, default=None, help="最大计费调用数")
    s.add_argument("--out", default="./evidence")
    s.add_argument("--seed", type=int, default=None)
    s.add_argument("--latency-n", type=int, default=8)
    s.add_argument("--style-samples", type=int, default=3)
    s.add_argument("--unmask-models", type=int, default=8,
                   help="揭面阶段最多扫描的 SKU 数（echo 矩阵规模）")
    s.add_argument("--attestation-bundle", default=None,
                   help="可验证推理证明包 JSON（有则离线核验并计入判决）")
    s.add_argument("--attestation-response", default=None,
                   help="与证明包对应的回答原文文件（用于输出绑定核验）")
    s.set_defaults(func=cmd_scan)

    r = sub.add_parser("report", help="从证据生成小白可读报告")
    r.add_argument("--evidence", default="./evidence")
    r.add_argument("--out", default=None)
    r.set_defaults(func=cmd_report)

    d = sub.add_parser("dig", help="一键挖掘: URL+API → 模型定位/上下游关系网/系统提示词/总档案")
    d.add_argument("--base-url", required=True)
    d.add_argument("--api-key", required=True)
    d.add_argument("--model", required=True, help="商家声称的模型名")
    d.add_argument("--compare-model", default=None)
    d.add_argument("--unmask-models", type=int, default=8,
                   help="揭面阶段最多扫描的 SKU 数（echo 矩阵规模）")
    d.add_argument("--budget", type=int, default=None, help="最大计费调用数")
    d.add_argument("--out", default="./dossier_evidence")
    d.add_argument("--baseline", default=None,
                   help="官方基线模型名（如 gpt-4o），启用基线比对严格模式")
    d.add_argument("--no-llmmap", action="store_true",
                   help="跳过 LLMmap 预训练指纹阶段")
    d.add_argument("--no-security", action="store_true",
                   help="跳过安全审计阶段（注入/截断/工具改写/SSE/Key泄露）")
    d.set_defaults(func=cmd_dig)

    am = sub.add_parser("add-model",
                        help="为 LLMmap 指纹库扩展新模型模板（需本地 LLMmap 仓库）")
    am.add_argument("model_name", help="新模型名（如 gpt-4.1 / Qwen/Qwen3-8B）")
    am.add_argument("--llm-type", type=int, default=1,
                    choices=[0, 1, 2],
                    help="后端类型: 0=HuggingFace 1=OpenAI 2=Anthropic")
    am.add_argument("--num-prompt-confs", type=int, default=100)
    am.add_argument("--llmmap-path", default=None,
                    help="预训练模型目录（默认 LLMMAP_MODEL_PATH 或自动探测）")
    am.add_argument("--prompt-conf-path", default=None)
    am.set_defaults(func=cmd_add_model)

    at = sub.add_parser("attest",
                        help="可验证推理：核验证明包绑定关系 / 探测端点是否提供证明")
    atsub = at.add_subparsers(dest="attest_cmd", required=True)
    av = atsub.add_parser("verify", help="离线核验一份 attestation 证明包（不需端点/GPU）")
    av.add_argument("--bundle", required=True, help="证明包 JSON 路径")
    av.add_argument("--response", default=None,
                    help="你实际收到的回答原文文件（核验输出绑定，强烈建议提供）")
    av.add_argument("--model", default=None, help="商家在售的 SKU（核验主体绑定）")
    atp = atsub.add_parser("probe", help="探测端点是否提供可验证推理能力（零计费）")
    atp.add_argument("--base-url", required=True)
    atp.add_argument("--api-key", required=True)
    atp.add_argument("--model", required=True)
    atp.add_argument("--out", default="./attestation_evidence")
    at.set_defaults(func=cmd_attest)

    w = sub.add_parser("web", help="本地 Web UI 报告可视化（零遥测，仅监听 localhost）")
    w.add_argument("--port", type=int, default=8501)
    w.add_argument("--reports", default="./reports")
    w.set_defaults(func=cmd_web)

    bl = sub.add_parser("baseline", help="生成/比对官方基线（需官方 API Key）")
    bl.add_argument("--generate", metavar="MODEL", default=None,
                    help="用官方端点生成基线: --generate gpt-4o --base-url ... --api-key ...")
    bl.add_argument("--compare", nargs=2, metavar=("EVIDENCE_DIR", "BASELINE"),
                    help="比对: --compare ./dossier_evidence gpt-4o")
    bl.add_argument("--base-url", default=None, help="官方端点（--generate 时必填）")
    bl.add_argument("--api-key", default=None, help="官方 Key（--generate 时必填）")
    bl.add_argument("--out", default="./baselines")
    bl.set_defaults(func=cmd_baseline)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
