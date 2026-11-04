#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""attestation: 可验证推理（verifiable inference）——证明包核验 + 证明可得性探测。

背景（2026-11 Anthropic FlashProve 开源后新增的第四类证据轴）:
黑盒验真的天花板是「行为学推定」：分词器、措辞、延迟、签名都能逼近官方分布，
但没有任何一条能**从数学上**排除「同家族换型号 / 同厂商换权重量化 / 证明来自 A
而回答来自 B」。zkSNARK 系的 verifiable inference 把权重承诺（commitment）和
单次推理证明（约 19MB/次，CPU 上约 17s 可验）绑到具体输出上，
这才是「数学级出生证明」。

本模块不实现 STARK 证明系统本身（那是上游 verifier 的事，如 FlashProve 的
cp_verify），只做中转站场景里**真正会被造假的那一层 —— 绑定关系**：

1. 输出绑定   output.sha256 是否等于你实际拿到的那段文本的哈希
              （不绑定 = 证明可以来自真模型、文字可以来自假模型，最常见的旁路）
2. 主体绑定   proof 声明的模型是否等于商家在售的 SKU（换芯时最容易露馅）
3. 承诺格式   commitment_id 是否是可核对的权重承诺（sha256/blake2 系）
4. 证明体量   证明字节数是否足以覆盖所宣称规模的推理（400B 级实测约 19MB）
5. 新鲜度     request_id / nonce / ts 是否能排除重放旧证明
6. 外部验签   上游 verifier 的结论（passed/failed/absent）——本工具无法代替它

判定:
  attested_verified   +3  绑定自洽 且 上游 verifier 通过 → 密码学级确证
  attested_unverified +1  绑定自洽 但 未做上游验签 → 仅「自洽」，不可称确证
  unverifiable         0  格式可读但缺关键字段/未知 prover → 不下结论
  inconsistent        -3  任一绑定检查失败 → 声称被证伪（强负证据）
  absent             None 端点根本没有可验证推理能力（**不定罪**：2026 年仍是极少数）

探测（probe_attestation）零计费：只读 /v1/models 与 well-known 端点，不发起对话。

用法:
    xh attest verify --bundle bundle.json --response reply.txt --model deepseek-v4
    xh attest probe  --base-url https://x.com --api-key sk-xxx --model deepseek-v4
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timedelta, timezone

import requests

SCHEMA = "xh-attestation/v1"

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126 Safari/537.36")

# ---- 已知证明系统（上游 verifier 的可信锚点）----
# 只登记「有公开代码 + 公开 verifier」的实现；未登记 != 假，只是无法核对。
KNOWN_PROVERS = {
    "flashprove": {
        "vendor": "Anthropic",
        "protocol": "stark (BLAKE2 / sumcheck)",
        "source": "https://github.com/anthropics/FlashProve",
        "reference": {"proof_bytes": 19_780_000, "verify_seconds_cpu": 17,
                      "commit_minutes_h100": 39, "sumchecks_per_request": 2000},
    },
    "stark": {"vendor": "StarkWare", "protocol": "STARK", "source": "starkware.co"},
    "ezkl": {"vendor": "EZKL", "protocol": "halo2/plonk", "source": "ezkl.xyz"},
    "zkllm": {"vendor": "zkLLM", "protocol": "halo2", "source": "ccs.neu.edu"},
}

# 证明体量下限：400B 级 MoE 单次答复实测约 19MB；1MB 以下不足以覆盖千亿参数级推理
PROOF_BYTES_FLOOR = 1_000_000
# 证明包超过这个时长视为旧包（重放风险，仅提示不定罪）
STALE_HOURS = 24

_COMMITMENT_RE = re.compile(
    r"^(?:(?:sha256|blake2b|blake2s|poseidon|keccak256):)?[0-9a-fA-F]{32,128}$")
_ATTEST_KEY_RE = re.compile(r"attest|commitment|proof|verified|zk|stark", re.I)

WELL_KNOWN_PATHS = [
    "/.well-known/verifiable-inference.json",
    "/.well-known/attestation.json",
    "/v1/attestation",
    "/v1/attestations",
    "/api/attestation",
]


# ----------------------------------------------------------------------
# 基础工具
# ----------------------------------------------------------------------
def sha256_hex(data: bytes | str) -> str:
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def _norm_model(name: str | None) -> str:
    """模型名归一：小写、去 provider 前缀、去空的 -/_ 分隔差异。"""
    s = (name or "").strip().lower()
    s = s.split("/")[-1]
    return re.sub(r"[-_.\s]", "", s)


def _check(cid: str, ok: bool, severity: int, detail: str) -> dict:
    return {"id": cid, "ok": bool(ok), "severity": severity, "detail": detail}


def _parse_ts(value) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


# ----------------------------------------------------------------------
# 证明包核验（离线，不需要端点、不需要 GPU）
# ----------------------------------------------------------------------
def verify_bundle(bundle: dict, response_text: str | None = None,
                  claimed_model: str | None = None,
                  now: datetime | None = None) -> dict:
    """核验一份 attestation 证明包的绑定关系。

    bundle:       证明包 JSON（schema 见 examples/attestation_bundle.example.json）
    response_text: 你实际收到的回答原文（用于输出绑定核验）
    claimed_model: 商家在售的 SKU（用于主体绑定核验）
    """
    now = now or datetime.now(timezone.utc)
    checks: list[dict] = []
    bundle = bundle or {}

    # ---- 1. schema ----
    schema = bundle.get("schema")
    checks.append(_check(
        "schema", schema == SCHEMA, 0,
        f"schema={schema}" + ("" if schema == SCHEMA else f"，本工具支持 {SCHEMA}")))

    model = bundle.get("model") or {}
    proof = bundle.get("proof") or {}
    out = bundle.get("output") or {}
    req = bundle.get("request") or {}
    prov = (bundle.get("prover") or {})
    prov_id = str(prov.get("impl") or prov.get("name") or "").strip().lower()

    # ---- 2. 输出绑定（最容易被造假的一环）----
    if response_text is None:
        checks.append(_check("output_binding", False, 0,
                             "未提供原文（--response），跳过输出绑定核验——"
                             "无法排除「证明来自 A、文字来自 B」"))
        bound = None
    elif not out.get("sha256"):
        checks.append(_check("output_binding", False, -2,
                             "证明包无 output.sha256：证明未承诺绑定任何具体回答"))
        bound = False
    else:
        expect = str(out["sha256"]).lower().removeprefix("sha256:")
        actual = sha256_hex(response_text)
        if actual == expect:
            checks.append(_check("output_binding", True, 0,
                                 f"输出哈希吻合（{actual[:16]}…）"))
            bound = True
        elif sha256_hex(response_text.rstrip()) == expect:
            checks.append(_check("output_binding", True, 0,
                                 "输出哈希吻合（仅尾随空白差异，可接受）"))
            bound = True
        else:
            checks.append(_check(
                "output_binding", False, -3,
                f"输出哈希不符：原文 {actual[:16]}… ≠ 证明 {expect[:16]}… —— "
                "证明绑定的是另一段文字，证明与回答可被分别替换"))
            bound = False

    # ---- 3. 主体绑定（在售 SKU vs 证明声明的模型）----
    proved_model = model.get("claimed") or model.get("name")
    if not proved_model:
        checks.append(_check("model_binding", False, -1, "证明包未声明模型名"))
    elif claimed_model:
        same = _norm_model(proved_model) == _norm_model(claimed_model)
        checks.append(_check(
            "model_binding", same, 0 if same else -3,
            (f"证明模型「{proved_model}」与在售 SKU「{claimed_model}」一致"
             if same else
             f"证明模型「{proved_model}」≠ 在售 SKU「{claimed_model}」—— "
             "证明对不上货，等价于没有证明")))
    else:
        checks.append(_check("model_binding", True, 0,
                             f"证明模型「{proved_model}」（未提供对照 SKU，跳过比对）"))

    # ---- 4. 权重承诺格式 ----
    cid = model.get("commitment_id") or model.get("commitment")
    if not cid:
        checks.append(_check("commitment", False, -1, "缺 commitment_id（权重承诺）"))
    elif _COMMITMENT_RE.match(str(cid).strip()):
        checks.append(_check("commitment", True, 0,
                             f"权重承诺格式合法（{str(cid)[:24]}…）"))
    else:
        checks.append(_check("commitment", False, -2,
                             f"commitment_id 格式不可核对：{str(cid)[:48]}"))

    # ---- 5. 证明体量（体积不成立 → 覆盖不了所宣称的规模）----
    pbytes = proof.get("bytes")
    if isinstance(pbytes, (int, float)) and pbytes > 0:
        ok = pbytes >= PROOF_BYTES_FLOOR
        checks.append(_check(
            "proof_size", ok, 0 if ok else -2,
            f"证明 {int(pbytes) / 1e6:.2f} MB" +
            ("" if ok else f" < 下限 {PROOF_BYTES_FLOOR / 1e6:.0f} MB——"
             "STARK 级推理证明的体积与计算轨迹成正比，此体积不足以覆盖"
             "千亿参数级推理（400B 级实测约 19MB/次）")))
    else:
        checks.append(_check("proof_size", False, -1, "证明包无 proof.bytes"))

    # ---- 6. 内联证明体摘要（有 payload 则校验）----
    payload = proof.get("payload") or proof.get("data")
    if payload and proof.get("digest"):
        expect = str(proof["digest"]).lower().removeprefix("sha256:")
        actual = sha256_hex(str(payload))
        same = actual == expect
        checks.append(_check("proof_digest", same, 0 if same else -2,
                             f"内联证明体摘要{'吻合' if same else '不符'}"))
    elif payload:
        checks.append(_check("proof_digest", False, 0,
                             "有内联证明体但未给摘要，无法校验完整性"))

    # ---- 7. 新鲜度 / 重放 ----
    ts = _parse_ts(req.get("ts_utc") or req.get("timestamp"))
    if ts is None:
        checks.append(_check("freshness", False, 0,
                             "缺带时区的时间戳，无法判断证明是否可重放"))
    else:
        age = now - ts
        stale = age > timedelta(hours=STALE_HOURS)
        checks.append(_check(
            "freshness", not stale, 0,
            f"证明生成于 {ts.isoformat()}（{age.total_seconds() / 3600:.1f} 小时前）"
            + ("—— 旧证明可被重放到新回答上，建议要求每次请求带 nonce" if stale else "")))
    if not req.get("nonce"):
        checks.append(_check("nonce", False, 0,
                             "无 request nonce（重放保护缺失）"))

    # ---- 8. 上游验签结论 ----
    ext = str((bundle.get("verification") or {}).get("external") or "absent").lower()
    checks.append(_check("external_verifier", ext == "passed", 0,
                         f"上游 verifier 结论: {ext}"
                         + ("（密码学级）" if ext == "passed" else
                            "—— 本工具只核绑定关系，不代替上游验签")))

    # ---- 汇总 ----
    hard_fails = [c for c in checks if c["severity"] <= -2]
    prov_known = prov_id in KNOWN_PROVERS
    if ext == "failed":
        vid, sev = "inconsistent", -3
        headline = "上游 verifier 判定证明无效——证明被证伪"
    elif hard_fails:
        vid, sev = "inconsistent", -3
        headline = "证明包与输出/货品不一致——声称被证伪：" + \
                   "；".join(c["detail"] for c in hard_fails[:2])
    elif not prov_known:
        vid, sev = "unverifiable", 0
        headline = (f"未知 prover「{prov.get('impl') or '未声明'}」，"
                    "无法对照公开实现——不下结论（不等于假）")
    elif ext == "passed" and bound:
        vid, sev = "attested_verified", 3
        headline = (f"{KNOWN_PROVERS[prov_id]['vendor']} {prov.get('impl')} "
                    "证明通过：绑定自洽 + 上游 verifier 通过 = 密码学级确证")
    else:
        vid, sev = "attested_unverified", 1
        headline = ("绑定关系自洽（输出/主体/承诺一致），但未执行上游验签——"
                    "只能称「自洽」，不可称密码学确证")

    return {
        "probe": "attestation_bundle",
        "verdict_id": vid,
        "severity": sev,
        "headline": headline,
        "provider": prov_id or None,
        "provider_known": prov_known,
        "model": proved_model,
        "commitment_id": cid,
        "checks": checks,
        "n_checks": len(checks),
        "n_failed": sum(1 for c in checks if not c["ok"]),
    }


def verify_bundle_file(path: str, response_text: str | None = None,
                       claimed_model: str | None = None) -> dict:
    with open(path, encoding="utf-8") as f:
        bundle = json.load(f)
    return verify_bundle(bundle, response_text=response_text,
                         claimed_model=claimed_model)


# ----------------------------------------------------------------------
# 证明可得性探测（零计费）
# ----------------------------------------------------------------------
def _get(url: str, key: str | None = None, timeout: float = 6.0) -> dict:
    headers = {"User-Agent": UA}
    if key:
        headers["Authorization"] = f"Bearer {key}"
    try:
        r = requests.get(url, headers=headers, timeout=timeout)
        body = r.text[:20000]
        try:
            js = r.json()
        except ValueError:
            js = None
        return {"url": url, "status": r.status_code, "headers": dict(r.headers),
                "json": js, "body_head": body[:500]}
    except Exception as e:  # noqa: BLE001
        return {"url": url, "error": str(e)[:300]}


def _scan_attest_keys(obj, path: str = "$", depth: int = 0) -> list[str]:
    """递归找工作表里带 attestation 语义的字段（说明端点自称可验证推理）。"""
    hits: list[str] = []
    if depth > 4:
        return hits
    if isinstance(obj, dict):
        for k, v in obj.items():
            if _ATTEST_KEY_RE.search(str(k)):
                hits.append(f"{path}.{k}")
            hits.extend(_scan_attest_keys(v, f"{path}.{k}", depth + 1))
    elif isinstance(obj, list):
        for i, v in enumerate(obj[:5]):
            hits.extend(_scan_attest_keys(v, f"{path}[{i}]", depth + 1))
    return hits[:20]


def probe_attestation(det) -> dict:
    """探测端点是否提供可验证推理能力（只读、不发起对话、零计费）。

    刻意不在模块级 import core（Detective 依赖 openai SDK）——
    离线核验 `xh attest verify` 必须在无 SDK、无网络的环境也能跑。
    """
    base = det.base_url
    origin = base[:-3] if base.endswith("/v1") else base
    key = det.api_key

    signals: list[dict] = []
    endpoints: dict = {}

    # ---- 1. /v1/models 载荷与响应头 ----
    models_res = _get(f"{base}/v1/models" if not base.endswith("/v1")
                      else f"{base}/models", key=key)
    hdr_hits = [h for h in (models_res.get("headers") or {})
                if _ATTEST_KEY_RE.search(h) and h.lower() != "content-type"]
    if hdr_hits:
        signals.append({"kind": "header", "where": "/v1/models",
                        "fields": hdr_hits})
    payload_hits = _scan_attest_keys(models_res.get("json")) if models_res.get("json") else []
    if payload_hits:
        signals.append({"kind": "payload", "where": "/v1/models",
                        "fields": payload_hits})

    # ---- 2. well-known / 专用端点 ----
    for ep in WELL_KNOWN_PATHS:
        r = _get(origin + ep, key=key)
        endpoints[ep] = {"status": r.get("status"), "error": r.get("error")}
        if r.get("status") == 200 and (r.get("json") or r.get("body_head")):
            endpoints[ep]["hit"] = True
            body_hits = _scan_attest_keys(r.get("json")) if r.get("json") else []
            signals.append({"kind": "endpoint", "where": ep,
                            "fields": body_hits or ["(非空响应)"]})

    # ---- 3. 首页/文档里是否公开承诺 ----
    home = _get(origin + "/", key=key)
    text = (home.get("body_head") or "").lower()
    kw = [k for k in ("attestation", "verifiable inference", "零知识",
                      "可验证推理", "commitment", "proof") if k in text]
    if kw:
        signals.append({"kind": "homepage", "where": "/", "fields": kw})

    advertised = bool(signals)
    result = {
        "probe": "attestation",
        "base_url": origin,
        "advertised": advertised,
        "signals": signals,
        "endpoints": endpoints,
        "verdict_id": "advertised_unverifiable" if advertised else "absent",
        "severity": None,   # 缺席不定罪：2026 年可验证推理仍是极少数
        "note": ("端点自称提供可验证推理——请要求服务商给出证明包，"
                 "并用 `xh attest verify` 核验绑定关系"
                 if advertised else
                 "端点未提供可验证推理能力：本次结论只能到行为学推定级，"
                 "无法从数学上排除同家族换型号/换量化，无法给出「正品」级证明"),
    }
    det.ev.save("attestation_probe", result)
    return result


# ----------------------------------------------------------------------
# 供判决引擎 / 报告使用的汇总
# ----------------------------------------------------------------------
def assurance_block(verification: dict | None,
                    probe: dict | None = None) -> dict:
    """把证明核验/可得性探测归并成「保证级别」双轴结论。"""
    v = verification or {}
    vid = v.get("verdict_id")
    if vid in ("attested_verified",):
        level, label = "cryptographic", "密码学确证"
        note = "证明包绑定自洽且上游 verifier 通过——数学级证明，非行为学猜测。"
    elif vid in ("attested_unverified",):
        level, label = "attested", "证明自洽（未验签）"
        note = "绑定关系自洽，但本工具未执行上游验签——不能称密码学确证。"
    elif vid in ("inconsistent", "unverifiable"):
        level, label = "failed", "证明核验未通过"
        note = v.get("headline", "")
    else:
        level, label = "behavioral", "行为学推定"
        note = ("未取得可验证推理证明：结论由分词器/措辞/签名/路由等黑盒证据推出"
                "（行为学推定），无法从数学上排除同家族模型替换或权重量化差异。")
    if probe and probe.get("advertised") and not v:
        label = "自称可验证（未提供证明包）"
        note = probe.get("note", note)
    return {"level": level, "label": label, "note": note,
            "provider": (v.get("provider") if v else None),
            "commitment_id": (v.get("commitment_id") if v else None)}
