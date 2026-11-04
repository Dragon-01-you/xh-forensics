#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""attestation 单元测试（零依赖，不需要 openai SDK / 网络 / GPU）。

覆盖 3 件事:
1. 证明包的绑定核验语义（输出/主体/体量/上游验签）
2. 判定码与严重度（attested_verified / attested_unverified / inconsistent / unverifiable）
3. 与判决引擎的双轴接入（assurance 保证级别 + score 方向）

用法: python tests/test_attestation.py     # 退出码 0 全过 / 1 有失败
"""
import copy
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api_detective.attestation import (  # noqa: E402
    assurance_block, verify_bundle, verify_bundle_file)
from api_detective.verdict import build_verdict  # noqa: E402

BUNDLE_PATH = ROOT / "examples" / "attestation_bundle.example.json"
RESP_PATH = ROOT / "examples" / "attestation_response.example.txt"
NOW = datetime(2026, 11, 4, 12, 0, tzinfo=timezone.utc)


def _bundle() -> dict:
    return json.loads(BUNDLE_PATH.read_text(encoding="utf-8"))


def _resp() -> str:
    return RESP_PATH.read_text(encoding="utf-8")


def check(name: str, cond: bool, detail: str = "") -> bool:
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))
    return cond


def run() -> int:
    ok = True
    resp = _resp()
    model = "deepseek-v4-pro"

    # ---- 1. 正常证明包：绑定自洽 + 上游验签通过 → 密码学级确证 ----
    r = verify_bundle(_bundle(), response_text=resp, claimed_model=model, now=NOW)
    ok &= check("完整证明包 → attested_verified",
                r["verdict_id"] == "attested_verified", r["headline"])
    ok &= check("完整证明包 severity=+3", r["severity"] == 3)
    ok &= check("全部检查通过", r["n_failed"] == 0, f"{r['n_checks']} checks")

    # ---- 2. 输出被换掉（证明来自 A、文字来自 B 的旁路）----
    r = verify_bundle(_bundle(), response_text=resp + "\n（被中转层改写了一行）",
                      claimed_model=model, now=NOW)
    ok &= check("输出被改写 → inconsistent", r["verdict_id"] == "inconsistent")
    ok &= check("输出绑定失败 → severity=-3", r["severity"] == -3)
    ok &= check("失败项含 output_binding",
                any(c["id"] == "output_binding" and not c["ok"] for c in r["checks"]))

    # ---- 3. 没给原文 → 不能升格为密码学确证 ----
    r = verify_bundle(_bundle(), claimed_model=model, now=NOW)
    ok &= check("缺原文 → 不判定为 verified",
                r["verdict_id"] == "attested_unverified", r["headline"])

    # ---- 4. 证明体量不成立（1MB 级证明覆盖不了千亿参数推理）----
    b = _bundle()
    b["proof"]["bytes"] = 65536
    r = verify_bundle(b, response_text=resp, claimed_model=model, now=NOW)
    ok &= check("证明体量过小 → inconsistent", r["verdict_id"] == "inconsistent",
                r["headline"])

    # ---- 5. 上游 verifier 判定失败 ----
    b = _bundle()
    b["verification"]["external"] = "failed"
    r = verify_bundle(b, response_text=resp, claimed_model=model, now=NOW)
    ok &= check("上游验签失败 → inconsistent", r["verdict_id"] == "inconsistent")

    # ---- 6. 未知 prover → 不下结论（不等于假）----
    b = _bundle()
    b["prover"]["impl"] = "mystery-prover"
    r = verify_bundle(b, response_text=resp, claimed_model=model, now=NOW)
    ok &= check("未知 prover → unverifiable", r["verdict_id"] == "unverifiable")
    ok &= check("未知 prover severity=0", r["severity"] == 0)

    # ---- 7. 主体不符：证明模型 ≠ 在售 SKU ----
    r = verify_bundle(_bundle(), response_text=resp,
                      claimed_model="qwen-max", now=NOW)
    ok &= check("证明模型与在售 SKU 不符 → inconsistent",
                r["verdict_id"] == "inconsistent")

    # ---- 8. 文件入口 + 判决引擎双轴 ----
    in_mem = verify_bundle(_bundle(), response_text=resp, claimed_model=model, now=NOW)
    r_file = verify_bundle_file(str(BUNDLE_PATH), response_text=resp, claimed_model=model)
    ok &= check("verify_bundle_file 与内存入口一致",
                r_file["verdict_id"] == in_mem["verdict_id"]
                and r_file["severity"] == in_mem["severity"] == 3)

    base_data = {
        "identity": {"self_claim_counts": {"DeepSeek": 3}, "top_canned": [],
                     "cot_leak_count": 0},
        "crypto_signature": {"evidence": [{"id": "thinking_signature_valid",
                                           "pass": True, "finding": "签名合法且互异"}]},
    }
    v_plain = build_verdict(copy.deepcopy(base_data))
    v_ok = build_verdict({**copy.deepcopy(base_data),
                          "attestation": {"verification": verify_bundle(
                              _bundle(), response_text=resp, claimed_model=model, now=NOW)}})
    v_bad = build_verdict({**copy.deepcopy(base_data),
                           "attestation": {"verification": verify_bundle(
                               _bundle(), response_text="伪造的回答",
                               claimed_model=model, now=NOW)}})
    ok &= check("密码学证明抬高评分", v_ok["score"] > v_plain["score"],
                f"{v_plain['score']} → {v_ok['score']}")
    ok &= check("证明不一致拉低评分", v_bad["score"] < v_plain["score"],
                f"{v_plain['score']} → {v_bad['score']}")
    ok &= check("assurance=密码学确证",
                v_ok["assurance"]["level"] == "cryptographic",
                v_ok["assurance"]["label"])
    ok &= check("无证明时 assurance=行为学推定",
                v_plain["assurance"]["level"] == "behavioral",
                v_plain["assurance"]["label"])
    ok &= check("证据不足时不冒充正品",
                v_plain["assurance"]["note"].find("行为学") >= 0)

    # ---- 9. 端点自称可验证但没给证明包 → 只降级标签，不定罪 ----
    a = assurance_block(None, {"advertised": True, "note": "自称可验证"})
    ok &= check("自称可验证未给包 → 标签降级而非定罪",
                a["level"] == "behavioral" and "自称" in a["label"], a["label"])

    print("\n" + ("ALL PASS" if ok else "SOME CHECKS FAILED"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(run())
